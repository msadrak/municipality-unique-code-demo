"""Write v4 from v3: stream-edit AF:AI of the main sheet; regenerate Cost_Center_Summary / Cost_Center_Review; keep every other ZIP member byte-identical."""
import zipfile, copy, re, pickle, json, time, codecs
from collections import Counter, defaultdict
from xml.sax.saxutils import escape
from activity_rules import R as RULES
from importlib import import_module as _im
_c = _im("04_classify")
NATIVE, XW, KIND_LABEL, WRITABLE, CC_MASTER = _c.NATIVE, _c.XW, _c.KIND_LABEL, _c.WRITABLE, _c.CC_MASTER

V3 = 'C:/Users/sadra/Desktop/دفتر_روزنامه_1404_مراکز_هزینه_فعالیت_محور_v3.xlsx'
V4 = 'C:/Users/sadra/Desktop/دفتر_روزنامه_1404_مراکز_هزینه_فعالیت_محور_v4.xlsx'
t0 = time.time()
DEC = pickle.load(open('zz_decisions.pkl', 'rb'))['DEC']
ROWS = {r[0]: r for r in pickle.load(open('zz_v3.pkl', 'rb'))['rows']}
def s(v): return '' if v is None else str(v).strip()
BAD = re.compile('[\x00-\x08\x0b\x0c\x0e-\x1f]')
def x(v): return escape(BAD.sub('', '' if v is None else str(v)))

# ---------------- styles ----------------
zin = zipfile.ZipFile(V3)
st = zin.read('xl/styles.xml').decode('utf-8')
nf = int(re.search(r'<fills count="(\d+)"', st).group(1))
fills = ['C6EFCE', 'FFEB9C', 'F8CBAD', '1F4E79', 'DDEBF7']   # verified, proposed, cleared, header, section
st = re.sub(r'<fills count="\d+">', f'<fills count="{nf + len(fills)}">', st)
st = st.replace('</fills>', ''.join(f'<fill><patternFill patternType="solid"><fgColor rgb="FF{c}"/><bgColor indexed="64"/></patternFill></fill>' for c in fills) + '</fills>')
nfo = int(re.search(r'<fonts count="(\d+)"', st).group(1))
st = re.sub(r'<fonts count="\d+"', f'<fonts count="{nfo + 2}"', st, count=1)
st = st.replace('</fonts>', '<font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="B Nazanin"/><charset val="178"/></font>'
                            '<font><sz val="11"/><color theme="1"/><name val="B Nazanin"/><charset val="178"/></font></fonts>')
FB, FR = nfo, nfo + 1
nx = int(re.search(r'<cellXfs count="(\d+)"', st).group(1))
xfs = [
    f'<xf numFmtId="0" fontId="1" fillId="{nf}" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment horizontal="center"/></xf>',      # verified
    f'<xf numFmtId="0" fontId="1" fillId="{nf + 1}" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment horizontal="center"/></xf>',  # proposed
    f'<xf numFmtId="0" fontId="1" fillId="{nf + 2}" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment horizontal="center"/></xf>',  # cleared
    f'<xf numFmtId="0" fontId="{FB}" fillId="{nf + 3}" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf>',  # header
    f'<xf numFmtId="0" fontId="{FR}" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>',              # body text
    f'<xf numFmtId="3" fontId="{FR}" fillId="0" borderId="0" xfId="0" applyNumberFormat="1" applyFont="1"/>',                                                     # number
    f'<xf numFmtId="0" fontId="1" fillId="{nf + 4}" borderId="0" xfId="0" applyFont="1" applyFill="1"/>',                                                        # section title
]
st = re.sub(r'<cellXfs count="\d+">', f'<cellXfs count="{nx + len(xfs)}">', st)
st = st.replace('</cellXfs>', ''.join(xfs) + '</cellXfs>')
S_VER, S_PROP, S_CLR, S_HDR, S_TXT, S_NUM, S_SEC = range(nx, nx + len(xfs))

# ---------------- main-sheet changes ----------------
COLS = ('AF', 'AG', 'AH', 'AI')
CHANGE = {}
for rn, d in DEC.items():
    a = d.get('action')
    if a in ('WRITE', 'CORRECT'):
        vals = NATIVE[d['native']]
        CHANGE[rn] = (vals, S_VER if d['status'] == 'VERIFIED_NATIVE' else S_PROP)
    elif a == 'CLEAR':
        CHANGE[rn] = (None, S_CLR)
def colnum(c):
    n = 0
    for ch in c: n = n * 26 + ord(ch) - 64
    return n
CELL = re.compile(r'<c r="([A-Z]+)\d+"(?:[^>]*?/>|[^>]*?>.*?</c>)', re.S)
def edit_row(row_xml, rn, vals, style):
    m = re.match(r'(<row [^>]*>)(.*)(</row>)$', row_xml, re.S)
    head, body, tail = m.groups()
    cells = [(colnum(c.group(1)), c.group(0)) for c in CELL.finditer(body)]
    assert ''.join(c for _, c in cells) == body, rn
    cells = [c for c in cells if c[0] not in (32, 33, 34, 35)]
    for i, col in enumerate(COLS):
        if vals is None:
            cells.append((32 + i, f'<c r="{col}{rn}" s="{style}"/>'))
        else:
            cells.append((32 + i, f'<c r="{col}{rn}" s="{style}" t="inlineStr"><is><t xml:space="preserve">{x(vals[i])}</t></is></c>'))
    cells.sort(key=lambda t: t[0])
    return head + ''.join(c for _, c in cells) + tail

# ---------------- review sheet rows ----------------
POP_FA = {'EXPENSE_BLANK_IN_V3': 'هزینه — خالی در v3', 'EXPENSE_SOURCE_ORIGINAL_NAMES': 'هزینه — نام مرکز منبع اصلی', 'EXPENSE_V1_NATIVE_REFERENCE': 'هزینه — غنی‌سازی مرجع بومی v1',
          'EXPENSE_V3_ADDED': 'هزینه — افزوده v3 (۶۲۳ سطر؛ شامل ۴۹۰ ناژوان)', 'REVENUE_WITH_SOURCE_EXPENSE_CC': 'درآمد با نام مرکز هزینه منبع', 'NON_EXPENSE_CLASS_1': 'غیرهزینه — طبقه 1 دارایی', 'NON_EXPENSE_CLASS_2': 'غیرهزینه — طبقه 2 بدهی'}
ACT_FA = {'WRITE': 'نوشته شد (جدید)', 'CORRECT': 'اصلاح شد (مقدار v3 جایگزین شد)', 'CLEAR': 'پاک شد (مقدار نادرست v3)', 'RETAIN_FLAG': 'حفظ + علامت',
          'FLAG_EXISTING': 'فقط علامت‌گذاری (مقدار منبع حفظ شد)', 'REVIEW_ONLY': 'فقط شیت بازبینی', 'UNCHANGED_CONFIRMED': 'بدون تغییر — تأیید فعالیت'}
def lab(nat):
    if not nat: return ''
    v = NATIVE[nat]; return f'{v[0]} {v[1].strip()} / {v[2]} {v[3].strip()}'
REVIEW = []
for rn in sorted(DEC):
    d = DEC[rn]; a = d.get('action')
    if a in (None, 'NONE', 'UNCHANGED'):
        continue
    r = ROWS[rn]
    w = s(r[16]); pop = POP_FA.get(d['population'], d['population'])
    if d['population'] == 'EXPENSE_BLANK_IN_V3' and w.startswith('31') and len(w) == 11:
        pop += ' — تعهد انتقالی سنواتی (بودجه 31)'
    if s(r[2]) == '31' and d['population'].startswith('EXPENSE'):
        pop += ' — منطقه 31 ناژوان'
    cc = d.get('cc') or ''
    rel = (XW.get(cc, (None, '', ''))[1] if cc else ('NATIVE_ONLY — بدون CC پیشنهادی' if d.get('native') else ''))
    old = ' | '.join(d.get('old', ())) if any(d.get('old', ())) else ''
    new = ' | '.join(NATIVE[d['native']]) if a in ('WRITE', 'CORRECT') else ('[پاک شد]' if a == 'CLEAR' else '')
    REVIEW.append([rn, s(r[1]), s(r[2]), s(r[3]), s(r[4]), s(r[5]), s(r[17]), s(r[8]), s(r[9]), s(r[10]), s(r[11]), (s(r[14]) + ' | ' + s(r[15])).strip(' |'), w,
                   r[12], r[13], pop, d.get('act', ''), KIND_LABEL.get(d.get('kind'), 'رابطه سند' if d.get('kind') == 'EVENT' else ''), cc,
                   CC_MASTER.get(cc, {}).get('title', '') if cc else '', rel, lab(d.get('native')), old, new, d.get('evidence', ''), d.get('method', ''),
                   d['status'], ACT_FA.get(a, a), d.get('note', '')])
RHEAD = ['سطر منبع (ردیف اکسل شیت اصلی)', 'شناسه (A)', 'کد منطقه', 'نام منطقه', 'شماره سند', 'کد حساب', 'طبقه', 'عنوان کل', 'عنوان معین', 'عنوان تفضیلی', 'عنوان جزء / شرح ردیف بودجه',
         'نوع و شرح سند', 'کد بودجه', 'بدهکار', 'بستانکار', 'جامعه آماری', 'فعالیت شهری شناسایی‌شده', 'نوع فعالیت', 'کد CC پیشنهادی', 'عنوان CC پیشنهادی',
         'رابطه CC با سلسله‌مراتب بومی', 'مرکز بومی پیشنهادی (سطح۱ / سطح۲)', 'AF:AI قبلی (v3)', 'AF:AI نوشته‌شده در v4', 'منبع شواهد', 'روش طبقه‌بندی', 'وضعیت بازبینی', 'اقدام v4', 'توضیح تصمیم']
WIDTH = [10, 22, 7, 22, 9, 20, 6, 22, 30, 30, 45, 34, 13, 15, 15, 30, 32, 20, 10, 40, 22, 45, 50, 50, 55, 40, 22, 26, 70]

def cell(ref, v, style=None):
    sa = f' s="{style}"' if style is not None else ''
    if v is None or v == '':
        return ''
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return f'<c r="{ref}"{sa}><v>{v}</v></c>'
    try:
        if isinstance(v, str) and re.fullmatch(r'-?\d+(\.\d+)?', v) and len(v) < 15 and not v.startswith('0'):
            return f'<c r="{ref}"{sa}><v>{v}</v></c>'
    except Exception:
        pass
    return f'<c r="{ref}"{sa} t="inlineStr"><is><t xml:space="preserve">{x(v)}</t></is></c>'
def L(i):
    s_ = ''
    i += 1
    while i: i, r_ = divmod(i - 1, 26); s_ = chr(65 + r_) + s_
    return s_
SHEET_HEAD = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
              'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">')
def sheet_xml(rows, widths, freeze=None, autofilter=None, row_styles=None):
    ncol = max(len(r) for r in rows)
    out = [SHEET_HEAD, f'<dimension ref="A1:{L(ncol - 1)}{len(rows)}"/>', '<sheetViews><sheetView rightToLeft="1" workbookViewId="0">']
    if freeze:
        out.append(f'<pane ySplit="{freeze}" topLeftCell="A{freeze + 1}" activePane="bottomLeft" state="frozen"/>')
    out.append('</sheetView></sheetViews><sheetFormatPr defaultRowHeight="15"/><cols>')
    out += [f'<col min="{i + 1}" max="{i + 1}" width="{w_}" customWidth="1"/>' for i, w_ in enumerate(widths)]
    out.append('</cols><sheetData>')
    for i, r in enumerate(rows, start=1):
        stl = (row_styles or {}).get(i)
        cs = []
        for j, v in enumerate(r):
            style = stl if stl is not None else (S_NUM if isinstance(v, (int, float)) and not isinstance(v, bool) else S_TXT)
            cs.append(cell(f'{L(j)}{i}', v, style))
        out.append(f'<row r="{i}">' + ''.join(cs) + '</row>')
    out.append('</sheetData>')
    if autofilter:
        out.append(f'<autoFilter ref="{autofilter}"/>')
    out.append('<pageMargins left="0.7" right="0.7" top="0.75" bottom="0.75" header="0.3" footer="0.3"/></worksheet>')
    return ''.join(out)

review_rows = [RHEAD] + REVIEW
review_xml = sheet_xml(review_rows, WIDTH, freeze=1, autofilter=f'A1:{L(len(RHEAD) - 1)}{len(review_rows)}', row_styles={1: S_HDR})

# ---------------- summary sheet ----------------
cnt = Counter((d['population'], d['status'], d.get('action')) for d in DEC.values())
RV4 = [r[0] for r in json.load(open('cc_review_v4.json', encoding='utf-8'))]
rv4_added = sum(1 for rn in RV4 if DEC[rn]['population'] == 'EXPENSE_V3_ADDED')
def C(**kw):
    return sum(v for (p, st_, a), v in cnt.items() if all({'p': p, 's': st_, 'a': a}[k[0]] in (vv if isinstance(vv, tuple) else (vv,)) for k, vv in kw.items()))
exp_total = sum(1 for r in ROWS.values() if s(r[17]) == '6')
v3_complete = sum(1 for r in ROWS.values() if any(s(v) for v in r[23:27]))
v3_exp_complete = sum(1 for r in ROWS.values() if s(r[17]) == '6' and any(s(v) for v in r[23:27]))
new_w = C(a='WRITE'); corr = C(a='CORRECT'); clr = C(a='CLEAR')
v4_complete = v3_complete + new_w - clr
v4_exp_complete = v3_exp_complete + new_w - clr
fin = C(p='EXPENSE_BLANK_IN_V3', s='NOT_APPLICABLE')
kind_w = Counter((DEC[rn]['kind'], DEC[rn]['status']) for rn in DEC if DEC[rn].get('action') in ('WRITE', 'CORRECT'))
def kw(k): return sum(v for (kk, _), v in kind_w.items() if kk in k)
blank_rows = [rn for rn, d in DEC.items() if d['population'] == 'EXPENSE_BLANK_IN_V3']
w31 = sum(1 for rn in blank_rows if s(ROWS[rn][16]).startswith('31') and DEC[rn]['action'] == 'WRITE')
nz = sum(1 for rn in blank_rows if s(ROWS[rn][2]) == '31' and DEC[rn]['action'] == 'WRITE')
cconly = Counter(d['cc'] for d in DEC.values() if d['status'] == 'PROPOSED_CC_ONLY')
evt = Counter(d['population'] for d in DEC.values() if d['status'] == 'EVENT_LEVEL_ONLY')
unres = C(p='EXPENSE_BLANK_IN_V3', s=('AMBIGUOUS', 'INSUFFICIENT_EVIDENCE'))
pct = lambda a, b: f'{100 * a / b:.2f}%'
SUM = [['شاخص', 'مقدار', 'تعریف / مخرج کسر']]
sec = []
def H(t): sec.append(len(SUM) + 1); SUM.append([t, '', ''])
H('الف) خط مبنا (v3) — اندازه‌گیری مستقیم از فایل v3')
SUM += [['کل سطرهای دفتر روزنامه', len(ROWS), 'شیت «کدینگ جامع 1404 شهرداری»، ردیف ۶ تا ۵۵۳٬۶۷۲'],
        ['سطرهای دارای AF:AI کامل در v3', v3_complete, 'هر چهار ستون AF، AG، AH، AI پر'],
        ['  رقم ادعاشده در خلاصه v3', 64787, 'خلاصه v3 «سطرهای کامل پس از پردازش»'],
        ['  اختلاف (همان ۴۹۰ سطر گزارش‌شده)', v3_complete - 64787, '۴۹۰ سطر منطقه 31 (مدیریت طرح ساماندهی ناژوان) پس از محاسبه خلاصه v3 و عمدتاً بر پایه ماهیت حساب افزوده شده بودند'],
        ['سطرهای هزینه (طبقه 6)', exp_total, 'مخرج اصلی پوشش هزینه'],
        ['  هزینه با AF:AI کامل در v3', v3_exp_complete, pct(v3_exp_complete, exp_total)],
        ['    نام مرکز از منبع اصلی', C(p='EXPENSE_SOURCE_ORIGINAL_NAMES'), 'AG/AI در فایل اصلی پر بوده؛ کدها با مرجع بومی تکمیل شده'],
        ['    غنی‌سازی مرجع بومی v1 (کد بودجه)', C(p='EXPENSE_V1_NATIVE_REFERENCE'), 'اتصال کد بودجه به شیت «بودجه 1404 + مراکز هزینه»'],
        ['    افزوده v3 بدون نام منبع', C(p='EXPENSE_V3_ADDED'), '۴۹۰ سطر ناژوان + ۱۳۳ سطر سایر مناطق'],
        ['  هزینه خالی در v3', len(blank_rows), '۵٬۶۱۲ تعهد انتقالی سنواتی (بودجه 31) + ۴۸۷ بازپرداخت تسهیلات (بودجه 32) + ۱٬۱۳۳ ناژوان بدون کد بودجه'],
        ['سطرهای درآمدی (طبقه 4) با نام مرکز هزینه منبع', C(p='REVENUE_WITH_SOURCE_EXPENSE_CC'), 'حفظ و علامت‌گذاری؛ اصلاح نشد'],
        ['cc_review_v4.json (۱٬۰۳۶ = ۹۳۳ + ۱۰۳)', len(RV4), f'همگی سطرهای منطقه 31 ناژوان (ردیف ۴۸۷٬۸۴۳ تا ۴۹۸٬۰۴۶)؛ {rv4_added} سطر همان افزوده‌های v3 و {len(RV4) - rv4_added} سطر خالی در v3 بودند؛ پیشنهادهای این فایل در v3 نوشته نشده بود'],
        ['blank_tafs.json / taf_rules.json (۲٬۲۶۸ و ۷۹۷)', '', 'فهرست بسامد عنوان تفضیلی بدون شناسه سطر؛ جامعه آماری سطرمحور نیست و در این اجرا جایگزین طبقه‌بندی کامل ۴۶٬۰۱۵ سطر هزینه شد']]
H('ب) نتیجه v4 — سطرهای AF:AI')
SUM += [['انتساب جدید در سطرهای خالی هزینه', new_w, 'AF:AI جدید؛ هیچ مقدار منبعی بازنویسی نشد'],
        ['  VERIFIED_NATIVE (سبز)', C(a='WRITE', s='VERIFIED_NATIVE'), 'امضای فعالیت + عنوان ردیف بودجه مرجع با همان سطح۲ بومی (دو شاهد مستقل)'],
        ['  PROPOSED_ACTIVITY (زرد)', C(a='WRITE', s='PROPOSED_ACTIVITY'), 'فقط امضای فعالیت؛ مرجع بودجه ناموجود یا ناسازگار؛ نیازمند تأیید کارشناس'],
        ['  از جمله تعهدات انتقالی سنواتی (بودجه 31)', w31, 'پروژه سرمایه‌ای دارای عنوان فعالیت؛ قابل فیلتر در شیت بازبینی'],
        ['  از جمله منطقه 31 ناژوان', nz, ''],
        ['اصلاح انتساب‌های نادرست v3 (افزوده v3)', corr, 'مقدار قبلی در شیت بازبینی ثبت شده'],
        ['پاک‌سازی انتساب‌های نادرست v3', clr, 'مثلاً نگهداری وسایط نقلیه → «نگهداری ساختمان» (۷۷)؛ رنگ قرمز روشن'],
        ['افزوده‌های v3 تأییدشده بدون تغییر', C(a='UNCHANGED_CONFIRMED'), ''],
        ['افزوده‌های v3 حفظ‌شده با علامت (سبد پشتیبانی عمومی)', C(a='RETAIN_FLAG'), ''],
        ['سطرهای دارای AF:AI کامل در v4', v4_complete, f'v3 {v3_complete} + جدید {new_w} − پاک‌شده {clr}'],
        ['پوشش هزینه v4', v4_exp_complete, pct(v4_exp_complete, exp_total) + f' از {exp_total} سطر هزینه (v3: {pct(v3_exp_complete, exp_total)})'],
        ['پوشش هزینه v4 بدون ردیف‌های تأمین مالی', v4_exp_complete, pct(v4_exp_complete, exp_total - fin) + f' از {exp_total - fin} (بدون {fin} بازپرداخت تسهیلات)']]
H('ج) ماهیت انتساب‌های نوشته‌شده (جدید + اصلاح‌شده)')
SUM += [['فعالیت عملیاتی مستقیم', kw(('op',)), 'خدمت شهری مستقیم'],
        ['پروژه سرمایه‌ای/احداث', kw(('cap',)), 'احداث/توسعه/تملک'],
        ['جمع فعالیت‌محور', kw(('op', 'cap')), ''],
        ['پشتیبانی داخلی (حقوقی، خزانه، فناوری، رسانه، نگهداری ساختمان)', kw(('sup',)), 'کارکرد پشتیبان قابل شناسایی'],
        ['پرسنلی/منابع مشترک (ماهیت حساب)', kw(('per',)), 'حقوق، رفاه، آموزش کارکنان — فعالیت خدمت شهری نیست'],
        ['AMBREF رفع‌شده با مرجع', kw(('AMBREF',)), '']]
H('د) پیشنهادهای غیرقابل نوشتن در AF:AI')
SUM += [['PROPOSED_CC_ONLY (کل)', sum(cconly.values()), f'CC پیشنهادی بدون معادل بومی؛ کد بومی جعل نشد. سطر خالی: {C(p="EXPENSE_BLANK_IN_V3", s="PROPOSED_CC_ONLY")}، افزوده v3 پاک‌شده: {C(p="EXPENSE_V3_ADDED", s="PROPOSED_CC_ONLY")}، سطر منبع علامت‌خورده: {C(s="PROPOSED_CC_ONLY", a="FLAG_EXISTING")}']]
SUM += [[f'  {k} — {CC_MASTER.get(k, {}).get("title", "")}', v, XW.get(k, ('', '', ''))[2]] for k, v in cconly.most_common()]
SUM += [['EVENT_LEVEL_ONLY (کل)', sum(evt.values()), 'سند با یک فعالیت یکتا؛ سطر غیرهزینه یا هزینه بدون شاهد؛ نوشته نشد']]
SUM += [[f'  {POP_FA.get(k, k)}', v, ''] for k, v in evt.most_common()]
H('هـ) باقی‌مانده واجد شرایط و حل‌نشده (سطرهای هزینه خالی)')
SUM += [['AMBIGUOUS', C(p='EXPENSE_BLANK_IN_V3', s='AMBIGUOUS'), 'چند فعالیت/مکان به‌جای فعالیت/شکاف taxonomy'],
        ['INSUFFICIENT_EVIDENCE', C(p='EXPENSE_BLANK_IN_V3', s='INSUFFICIENT_EVIDENCE'), 'نهاده عمومی یا شرح بدون فعالیت'],
        ['جمع حل‌نشده واجد شرایط', unres, ''],
        ['NOT_APPLICABLE — تأمین مالی', fin, 'بازپرداخت اصل و سود تسهیلات/اوراق'],
        ['سطرهای منبع با تعارض فعالیت (فقط علامت)', C(a='FLAG_EXISTING', p=('EXPENSE_SOURCE_ORIGINAL_NAMES', 'EXPENSE_V1_NATIVE_REFERENCE')), 'مقدار منبع/مرجع حفظ شد؛ تعارض در شیت بازبینی'],
        ['سطرهای غیرهزینه NOT_APPLICABLE', sum(v for (p, st_, a), v in cnt.items() if p.startswith('NON_EXPENSE') and st_ == 'NOT_APPLICABLE'), 'دارایی، بدهی، حقوق صاحبان سرمایه، درآمد، انتظامی/بستن']]
H('و) راهنمای رنگ ستون‌های AF:AI')
SUM += [['سبز', 'VERIFIED_NATIVE', ''], ['زرد', 'PROPOSED_ACTIVITY — نیازمند تأیید', ''], ['قرمز روشن', 'انتساب نادرست v3 پاک شد', ''], ['بدون رنگ جدید', 'مقدار v3/منبع بدون تغییر', '']]
H('ز) ارزیابی مجدد crosswalk مراکز پیشنهادی ← سلسله‌مراتب بومی (بر پایه تعریف فعالیت)')
use = Counter(d.get('cc') for d in DEC.values() if d.get('cc') and d.get('action') in ('WRITE', 'CORRECT', 'REVIEW_ONLY', 'FLAG_EXISTING', 'CLEAR'))
SUM.append(['کد CC | عنوان', 'سطح۲ بومی | رابطه', 'توضیح | سطرهای مرتبط در v4'])
for k in CC_MASTER:
    nat, rel, note = XW.get(k, (None, 'NOT_EVALUATED', ''))
    SUM.append([f'{k} | {CC_MASTER[k]["title"]}', f'{lab(nat) or "—"} | {rel}', f'{note} | {use.get(k, 0)}'])
H('ح) کاتالوگ امضاهای فعالیت (ترتیب = اولویت؛ اولین تطابق)')
SUM.append(['شناسه قاعده | فعالیت', 'CC | سطح۲ پیش‌فرض | سطوح۲ سازگار | نوع', 'الگوی تطبیق (پس از نرمال‌سازی) | الگوی استثنا'])
for rid, inc, exc, cc, nat, compat, kind, act in RULES:
    SUM.append([f'{rid} | {act}', f'{cc or "—"} | {nat or "—"} | {",".join(compat)} | {kind}', f'{inc.pattern}' + (f' | EXC: {exc.pattern}' if exc else '')])
summary_xml = sheet_xml(SUM, [62, 48, 110], freeze=1, row_styles={1: S_HDR, **{i: S_SEC for i in sec}})

# ---------------- workbook.xml: filter name for review sheet ----------------
wbx = zin.read('xl/workbook.xml').decode('utf-8')
wbx = wbx.replace('</definedNames>', f'<definedName name="_xlnm._FilterDatabase" localSheetId="6" hidden="1">Cost_Center_Review!$A$1:${L(len(RHEAD) - 1)}${len(review_rows)}</definedName></definedNames>')

# ---------------- write ZIP ----------------
REPL = {'xl/styles.xml': st, 'xl/worksheets/sheet6.xml': summary_xml, 'xl/worksheets/sheet7.xml': review_xml, 'xl/workbook.xml': wbx}
zout = zipfile.ZipFile(V4, 'w', zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True)
done = 0
for info in zin.infolist():
    ni = copy.copy(info); ni.compress_type = zipfile.ZIP_DEFLATED
    if info.filename in REPL:
        zout.writestr(ni, REPL[info.filename].encode('utf-8')); continue
    if info.filename != 'xl/worksheets/sheet1.xml':
        zout.writestr(ni, zin.read(info.filename)); continue
    with zin.open(info) as fi, zout.open(ni, 'w', force_zip64=True) as fo:
        buf = ''; dec = codecs.getincrementaldecoder('utf-8')()
        while True:
            chunk = fi.read(16 * 1024 * 1024)
            if not chunk:
                buf += dec.decode(b'', final=True); fo.write(buf.encode('utf-8')); break
            buf += dec.decode(chunk)
            out = []; pos = 0
            while True:
                i = buf.find('<row ', pos)
                if i < 0: break
                j = buf.find('</row>', i)
                if j < 0: break
                j += 6
                out.append(buf[pos:i])
                row = buf[i:j]
                rn = int(re.match(r'<row r="(\d+)"', row).group(1))
                if rn in CHANGE:
                    vals, style = CHANGE[rn]; row = edit_row(row, rn, vals, style); done += 1
                out.append(row); pos = j
            fo.write(''.join(out).encode('utf-8')); buf = buf[pos:]
zout.close()
print('rows edited', done, 'of', len(CHANGE), 'review rows', len(REVIEW), 'secs', round(time.time() - t0))
json.dump({'new': new_w, 'corr': corr, 'clear': clr, 'v3_complete': v3_complete, 'v4_complete': v4_complete, 'review_rows': len(REVIEW)}, open('zz_write_stats.json', 'w'))
