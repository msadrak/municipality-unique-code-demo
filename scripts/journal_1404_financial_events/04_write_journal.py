"""Deliverable B: journal workbook with provisional financial events and dimensions.

Built from the v4 workbook by ZIP-level streaming:
  * main sheet (renamed «دفتر_روزنامه_کامل»): every original cell, style, shared string and formula kept byte-identical;
    28 event/dimension columns appended after AQ (AR:BS)
  * new sheets: مراکز_هزینه, هزینه_ها, درآمدها (filtered views), ارتباط_سطر_رویداد (multi-association table), QA_تطبیق_و_راهنما
  * original reference sheets kept; the v4 CC-only sheets (Cost_Center_Summary/Review) are dropped — their row-level
    proposals are carried in the new CC columns.
"""
import zipfile, copy, re, pickle, time, sys, json
from collections import Counter
from xml.sax.saxutils import escape
sys.path.insert(0, 'H:/Freelancing_Project/KalaniProject/municipality_demo/scripts/journal_1404_financial_events')
import fe_rules as F

W = 'H:/Freelancing_Project/KalaniProject/municipality_demo/data/work/fe_model/'
V4 = 'C:/Users/sadra/Desktop/دفتر_روزنامه_1404_مراکز_هزینه_فعالیت_محور_v4.xlsx'
OUT = 'C:/Users/sadra/Desktop/دفتر_روزنامه_1404_با_رویدادهای_مالی_و_شناورها_DRAFT.xlsx'
MAIN_OLD, MAIN_NEW = 'کدینگ جامع 1404 شهرداری', 'دفتر_روزنامه_کامل'
t0 = time.time()
_J = pickle.load(open(W + 'journal_v4.pkl', 'rb')); ROWS = _J['rows']; FORMULAS_AD = _J['formula_cols'].get(29, 0)
K = pickle.load(open(W + 'classified.pkl', 'rb'))
REC, REL, EV, DOCINFO = K['REC'], K['REL'], K['EV'], K['DOCINFO']
BYROW = {r[0]: i for i, r in enumerate(ROWS)}
g, s = F.g, F.s

BAD = re.compile('[\x00-\x08\x0b\x0c\x0e-\x1f]')
def x(v): return escape(BAD.sub('', '' if v is None else str(v)))
def L(n):  # 0-based column index -> letters
    out = ''
    n += 1
    while n: n, r = divmod(n - 1, 26); out = chr(65 + r) + out
    return out

STATUS_FA = {'MAPPED_DIRECT': 'MAPPED_DIRECT — نگاشت مستقیم', 'MAPPED_EVENT_COMPONENT': 'MAPPED_EVENT_COMPONENT — جزء رویداد',
             'MULTI_EVENT': 'MULTI_EVENT — چندرویدادی', 'AMBIGUOUS': 'AMBIGUOUS — مبهم', 'INSUFFICIENT_EVIDENCE': 'INSUFFICIENT_EVIDENCE — شواهد ناکافی',
             'REQUIRES_NEW_EVENT_REVIEW': 'REQUIRES_NEW_EVENT_REVIEW — شکاف فرهنگ رویداد'}

def ev_title(rec):
    if rec['ev']: return EV[rec['ev']]['title']
    if rec['cands']: return 'مبهم میان: ' + ' / '.join(f"{c} {EV[c]['title']}" for c in rec['cands'])
    return ''

def newvals(i):
    r, rec = ROWS[i], REC[i]
    e = EV.get(rec['ev'], {})
    cls = s(g(r, F.C_CLS))
    nature = f"{F.NATURE.get(cls, cls)} — {F.CAT_FA.get(rec['cat'], rec['cat'])} — {'بدهکار' if rec['side'] == 'D' else 'بستانکار' if rec['side'] == 'C' else 'صفر'}"
    kind = '' if not rec['ev'] else ('رویداد کانونی v7.1' if e.get('canonical') else 'شکاف فرهنگ — پیشنهاد رویداد جدید (تأییدنشده)')
    cc_note = rec.get('cc_basis', '')
    return [rec['ev'], ev_title(rec), e.get('family', ''), kind, rec['doc'], rec['inst'], rec['role'], nature,
            STATUS_FA[rec['status']], rec['method'], rec['basis'], '، '.join(rec['cands']),
            rec['cc_related'], rec['cc_status'], rec['cc_direct'], rec.get('cc_prov', ''), rec['cc_event'] + (f' [{cc_note}]' if cc_note and rec['cc_event'] else ''),
            rec['cc_prop'], rec['con_status'], rec['con_value'], rec['proj_status'], rec['proj_value'], rec['btype'],
            rec['bank_status'], rec['bank_value'], rec['review'], rec['review_why'], 'پیش‌نویس — تأییدنشده توسط کارفرما']
NEWHEAD = ['کد رویداد مالی پیشنهادی', 'عنوان رویداد مالی پیشنهادی', 'خانواده رویداد مالی', 'نوع رویداد در فرهنگ', 'شناسه سند ترکیبی (سال-منطقه-شماره سند)',
           'شناسه نمونه رویداد / گروه رویداد', 'نقش ردیف در رویداد', 'ماهیت حسابداری ردیف', 'وضعیت تشخیص رویداد', 'روش تشخیص', 'مبنای تشخیص / شواهد',
           'رویدادهای کاندید / همزمان دیگر', 'مرکز هزینه مرتبط با رویداد', 'وضعیت ارتباط مرکز هزینه', 'مرکز هزینه مستقیم سطر (AF:AI بومی)', 'منشأ مرکز هزینه مستقیم',
           'مرکز هزینه سطح رویداد', 'مرکز هزینه پیشنهادی CC-only (غیربومی)', 'ارتباط قرارداد', 'شماره قرارداد (از متن منبع)', 'ارتباط پروژه',
           'پروژه / ردیف بودجه پروژه', 'نوع بودجه (مستمر / غیرمستمر)', 'ارتباط بانک', 'حساب بانکی', 'نیازمند بررسی کارشناسی', 'علت بررسی', 'وضعیت تأیید']
NEWW = [12, 40, 16, 22, 18, 26, 30, 34, 30, 30, 55, 22, 42, 30, 42, 26, 50, 34, 30, 18, 34, 45, 26, 26, 50, 10, 45, 26]
assert len(NEWHEAD) == len(NEWW) == 28
FIRST = 43   # AR

# ---------------- styles
zin = zipfile.ZipFile(V4)
st = zin.read('xl/styles.xml').decode('utf-8')
nf = int(re.search(r'<fills count="(\d+)"', st).group(1))
fills = ['1F4E79', 'C6EFCE', 'E2EFDA', 'FFEB9C', 'F8CBAD', 'DDEBF7', 'FCE4D6']
st = re.sub(r'<fills count="\d+">', f'<fills count="{nf + len(fills)}">', st)
st = st.replace('</fills>', ''.join(f'<fill><patternFill patternType="solid"><fgColor rgb="FF{c}"/><bgColor indexed="64"/></patternFill></fill>' for c in fills) + '</fills>')
nfo = int(re.search(r'<fonts count="(\d+)"', st).group(1))
st = re.sub(r'<fonts count="\d+"', f'<fonts count="{nfo + 2}"', st, count=1)
st = st.replace('</fonts>', '<font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="B Nazanin"/><charset val="178"/></font>'
                            '<font><sz val="11"/><color theme="1"/><name val="B Nazanin"/><charset val="178"/></font></fonts>')
FB, FR = nfo, nfo + 1
nx = int(re.search(r'<cellXfs count="(\d+)"', st).group(1))
def xf(font, fill=None, num=0, wrap=False):
    fa = f' fillId="{fill}" applyFill="1"' if fill is not None else ''
    al = '<alignment horizontal="right" vertical="center" wrapText="1" readingOrder="2"/>' if wrap else '<alignment horizontal="right" vertical="center" readingOrder="2"/>'
    return f'<xf numFmtId="{num}" fontId="{font}"{fa} borderId="0" xfId="0" applyFont="1" applyNumberFormat="1" applyAlignment="1">{al}</xf>'
xfs = [xf(FB, nf, wrap=True), xf(FR), xf(FR, num=3), xf(FR, nf + 1), xf(FR, nf + 2), xf(FR, nf + 3), xf(FR, nf + 4), xf(FB, nf + 5, wrap=True), xf(FR, nf + 6)]
st = re.sub(r'<cellXfs count="\d+">', f'<cellXfs count="{nx + len(xfs)}">', st)
st = st.replace('</cellXfs>', ''.join(xfs) + '</cellXfs>')
S_HDR, S_TXT, S_NUM, S_DIRECT, S_COMP, S_YEL, S_RED, S_GRP, S_GAP = range(nx, nx + len(xfs))
STATUS_STYLE = {'MAPPED_DIRECT': S_DIRECT, 'MAPPED_EVENT_COMPONENT': S_COMP, 'MULTI_EVENT': S_YEL, 'AMBIGUOUS': S_RED, 'INSUFFICIENT_EVIDENCE': S_RED, 'REQUIRES_NEW_EVENT_REVIEW': S_GAP}

def cell(ref, v, style=S_TXT):
    if v is None or v == '': return ''
    if isinstance(v, bool): v = str(v)
    if isinstance(v, (int, float)):
        return f'<c r="{ref}" s="{S_NUM if style == S_TXT else style}"><v>{v}</v></c>'
    return f'<c r="{ref}" s="{style}" t="inlineStr"><is><t xml:space="preserve">{x(v)}</t></is></c>'

def new_cells(rn, i):
    vals = newvals(i)
    out = []
    for k, v in enumerate(vals):
        style = STATUS_STYLE[REC[i]['status']] if k == 8 else S_TXT
        out.append(cell(f'{L(FIRST + k)}{rn}', v, style))
    return ''.join(out)

# ---------------- main sheet streaming edit
LASTL = L(FIRST + len(NEWHEAD) - 1)
NCOL = FIRST + len(NEWHEAD)
ROWRX = re.compile(r'<row [^>]*?(?:/>|>.*?</row>)', re.S)
RNRX = re.compile(r'<row r="(\d+)"')
def edit_row(xml):
    rn = int(RNRX.match(xml).group(1))
    xml = re.sub(r'spans="1:\d+"', f'spans="1:{NCOL}"', xml, count=1)
    if rn == 1: add = cell(f'{L(FIRST)}1', 'رویداد مالی و شناورها — پیش‌نویس پیشنهادی برای تأیید کارفرما (قاعده مصوب ERP نیست)', S_GRP)
    elif rn == 5: add = ''.join(cell(f'{L(FIRST + k)}5', h, S_HDR) for k, h in enumerate(NEWHEAD))
    elif rn >= 6: add = new_cells(rn, BYROW[rn])
    else: add = ''
    if not add: return xml
    if xml.endswith('/>'): return xml[:-2] + '>' + add + '</row>'
    return xml[:-6] + add + '</row>'

def main_head(h):
    h = re.sub(r'<dimension ref="A1:AQ(\d+)"/>', lambda m: f'<dimension ref="A1:{LASTL}{m.group(1)}"/>', h)
    h = h.replace(' tabSelected="1"', '').replace('topLeftCell="Y337198" ', '')
    h = h.replace('</cols>', ''.join(f'<col min="{FIRST + k + 1}" max="{FIRST + k + 1}" width="{w}" customWidth="1"/>' for k, w in enumerate(NEWW)) + '</cols>')
    return h

# ---------------- view sheets
SRC_COLS = [(None, 'سطر منبع (ردیف اکسل شیت کامل)'), ('B', 'شناسه سند (B)'), ('FY', 'سال مالی'), ('C', 'کد منطقه'), ('D', 'نام منطقه'), ('E', 'شماره سند'),
            ('H', 'سرفصل حساب'), ('I', 'کد کل'), ('J', 'کد معین'), ('K', 'کد تفضیلی'), ('L', 'کد جزء'), ('M', 'عنوان کل'), ('N', 'عنوان معین'),
            ('O', 'عنوان تفضیلی'), ('P', 'عنوان جزء'), ('Q', 'مبلغ بدهکار'), ('R', 'مبلغ بستانکار'), ('S', 'نوع سند'), ('T', 'شرح سند'), ('U', 'کاربر'),
            ('V', 'شماره درخواست'), ('W', 'کد بودجه'), ('X', 'طبقه (کد)'), ('Y', 'طبقه (عنوان)'), ('Z', 'کل (کد مطلوب)'), ('AA', 'کل (عنوان مطلوب)'),
            ('AB', 'معین (کد مطلوب)'), ('AC', 'معین (عنوان مطلوب)'), ('AE', 'واحد سازمانی'), ('AF', 'مرکز هزینه سطح۱ کد (AF)'), ('AG', 'مرکز هزینه سطح۱ عنوان (AG)'),
            ('AH', 'مرکز هزینه سطح۲ کد (AH)'), ('AI', 'مرکز هزینه سطح۲ عنوان (AI)'), ('AJ', 'کد شخص (AJ)'), ('AK', 'عنوان شخص (AK)')]
def colidx(letters):
    n = 0
    for ch in letters: n = n * 26 + ord(ch) - 64
    return n - 1
SRC_IDX = [(None if c in (None, 'FY') else colidx(c), c) for c, _ in SRC_COLS]
VIEW_HEAD = [h for _, h in SRC_COLS] + NEWHEAD
VIEW_W = [10, 10, 7, 7, 20, 9, 20, 7, 7, 8, 8, 22, 26, 28, 34, 15, 15, 22, 16, 10, 10, 13, 6, 12, 8, 22, 9, 24, 20, 6, 24, 8, 24, 10, 26] + NEWW
SHEET_HEAD = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
              'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">')
def view_rows(idx):
    for n, i in enumerate(idx, start=2):
        r = ROWS[i]
        cells = []
        for k, (ci, c) in enumerate(SRC_IDX):
            v = r[0] if c is None else ('1404' if c == 'FY' else g(r, ci))
            if isinstance(v, str) and v.startswith('='): v = None
            cells.append(cell(f'{L(k)}{n}', v))
        vals = newvals(i)
        base = len(SRC_IDX)
        for k, v in enumerate(vals):
            cells.append(cell(f'{L(base + k)}{n}', v, STATUS_STYLE[REC[i]['status']] if k == 8 else S_TXT))
        yield f'<row r="{n}">' + ''.join(cells) + '</row>'

def write_sheet(zout, name, head, widths, rows_iter, nrows, selected=False, filter_=True, title_style=S_HDR):
    ncol = len(head)
    with zout.open(name, 'w', force_zip64=True) as f:
        f.write((SHEET_HEAD + f'<dimension ref="A1:{L(ncol - 1)}{nrows + 1}"/>'
                 f'<sheetViews><sheetView rightToLeft="1" {"tabSelected=\"1\" " if selected else ""}workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
                 '<sheetFormatPr defaultRowHeight="18"/><cols>' + ''.join(f'<col min="{k + 1}" max="{k + 1}" width="{w}" customWidth="1"/>' for k, w in enumerate(widths)) + '</cols><sheetData>').encode('utf-8'))
        f.write(('<row r="1" ht="45" customHeight="1">' + ''.join(cell(f'{L(k)}1', h, title_style) for k, h in enumerate(head)) + '</row>').encode('utf-8'))
        buf = []
        for k, row in enumerate(rows_iter):
            buf.append(row)
            if len(buf) >= 5000:
                f.write(''.join(buf).encode('utf-8')); buf = []
        f.write(''.join(buf).encode('utf-8'))
        f.write(('</sheetData>' + (f'<autoFilter ref="A1:{L(ncol - 1)}{nrows + 1}"/>' if filter_ else '') +
                 '<pageMargins left="0.7" right="0.7" top="0.75" bottom="0.75" header="0.3" footer="0.3"/></worksheet>').encode('utf-8'))

CC_VIEW = {'DIRECT_LINE_NATIVE', 'DIRECT_LINE_NATIVE_REVENUE_FLAG', 'EVENT_LEVEL_FROM_DOCUMENT', 'EVENT_LEVEL_MULTI_CC', 'EVENT_LEVEL_ACTIVITY_PROPOSED', 'PROPOSED_CC_ONLY', 'EVENT_LEVEL_VIA_CONTRACT', 'EVENT_LEVEL_VIA_CONTRACT_MULTI'}
IDX_CC = [i for i in range(len(ROWS)) if REC[i]['cc_status'] in CC_VIEW]
IDX_EXP = [i for i in range(len(ROWS)) if s(g(ROWS[i], F.C_CLS)) == '6']
IDX_REV = [i for i in range(len(ROWS)) if s(g(ROWS[i], F.C_CLS)) == '4']
print('views cc/exp/rev', len(IDX_CC), len(IDX_EXP), len(IDX_REV), flush=True)

REL_HEAD = ['سطر منبع (ردیف اکسل شیت کامل)', 'شناسه سند ترکیبی', 'شناسه نمونه رویداد', 'کد رویداد', 'عنوان رویداد', 'نوع رویداد در فرهنگ', 'نوع ارتباط', 'مبنای ارتباط', 'وضعیت سطر در شیت کامل']
def rel_rows():
    for n, (i, dk, inst, ev, typ, basis) in enumerate(REL, start=2):
        e = EV[ev]
        vals = [ROWS[i][0], dk, inst, ev, e['title'], 'رویداد کانونی v7.1' if e['canonical'] else 'شکاف فرهنگ (تأییدنشده)', typ, basis, REC[i]['status']]
        yield f'<row r="{n}">' + ''.join(cell(f'{L(k)}{n}', v) for k, v in enumerate(vals)) + '</row>'

# ---------------- QA / reconciliation sheet
def num(v): return F.num(v)
N = len(ROWS)
st_c = Counter(r['status'] for r in REC)
gap_c = Counter(r['ev'] for r in REC if r['status'] == 'REQUIRES_NEW_EVENT_REVIEW')
gap_kind = Counter(r['kind'] for r in REC if r['status'] == 'REQUIRES_NEW_EVENT_REVIEW')
D = sum(num(g(r, F.C_DR)) for r in ROWS); C = sum(num(g(r, F.C_CR)) for r in ROWS)
dE = sum(num(g(ROWS[i], F.C_DR)) for i in IDX_EXP); cE = sum(num(g(ROWS[i], F.C_CR)) for i in IDX_EXP)
dR = sum(num(g(ROWS[i], F.C_DR)) for i in IDX_REV); cR = sum(num(g(ROWS[i], F.C_CR)) for i in IDX_REV)
def cnt(key, vals): return sum(1 for r in REC if r[key] in vals)
QA = [['بخش', 'شاخص', 'مقدار', 'تعریف / توضیح']]
def q(sec, a, b, c=''): QA.append([sec, a, b, c])
q('الف) جامعه', 'سطرهای دفتر روزنامه منبع (شیت اصلی، ردیف ۶ تا آخر)', N, 'دفتر روزنامه 1404 - با اشخاص جدید / v4؛ ردیف‌های ۱ تا ۵ سرستون')
q('الف) جامعه', 'سطرهای شیت دفتر_روزنامه_کامل', N, 'همه سطرها؛ هیچ سطری حذف یا تکرار نشد')
q('الف) جامعه', 'سطرهای شیت هزینه_ها (طبقه 6)', len(IDX_EXP), 'شامل تعهدات سنواتی (652) و بازپرداخت تسهیلات (620) با برچسب ماهیت')
q('الف) جامعه', 'سطرهای شیت درآمدها (طبقه 4)', len(IDX_REV), '')
q('الف) جامعه', 'سطرهای شیت مراکز_هزینه', len(IDX_CC), 'سطرهای دارای مرکز هزینه مستقیم، سطح رویداد یا CC-only؛ نماها هم‌پوشانی دارند و جمع‌پذیر نیستند')
q('الف) جامعه', 'اسناد حسابداری (سال-منطقه-شماره سند)', len(DOCINFO), 'شناسه B با کلید ترکیبی منطقه+شماره سند یک‌به‌یک است')
q('الف) جامعه', 'اسناد نامتوازن (بدهکار ≠ بستانکار)', sum(1 for d in DOCINFO.values() if not d['balanced']), 'در علت بررسی علامت خورده‌اند')
for k in ['MAPPED_DIRECT', 'MAPPED_EVENT_COMPONENT', 'MULTI_EVENT', 'AMBIGUOUS', 'INSUFFICIENT_EVIDENCE', 'REQUIRES_NEW_EVENT_REVIEW']:
    q('ب) وضعیت تشخیص رویداد (کل جامعه)', STATUS_FA[k], st_c.get(k, 0), '')
q('ب) وضعیت تشخیص رویداد (کل جامعه)', 'جمع وضعیت‌ها', sum(st_c.values()), 'باید با کل سطرها برابر باشد: ' + ('PASS' if sum(st_c.values()) == N else 'FAIL'))
q('ب) وضعیت تشخیص رویداد (کل جامعه)', 'سطرهای دارای رویداد کانونی (DIRECT+COMPONENT+MULTI)', st_c['MAPPED_DIRECT'] + st_c['MAPPED_EVENT_COMPONENT'] + st_c['MULTI_EVENT'], '')
q('ب) وضعیت تشخیص رویداد (کل جامعه)', 'رویدادهای کانونی استفاده‌شده', len({r['ev'] for r in REC if r['ev'] and not r['ev'].startswith('GAP')}), 'از ۷۰ رویداد فرهنگ v7.1')
for k, v in gap_c.most_common():
    q('ج) شکاف‌های فرهنگ (REQUIRES_NEW_EVENT_REVIEW)', f'{k} {EV[k]["title"]}', v, '')
q('ج) شکاف‌های فرهنگ (REQUIRES_NEW_EVENT_REVIEW)', 'از این میان: ردیف محرک / کسور / جزء وراثتی', f"{gap_kind.get('DRIVER', 0)} / {gap_kind.get('WITHHOLD', 0)} / {gap_kind.get('COMPONENT', 0)}", '')
for key, title in [('cc_status', 'د) مرکز هزینه'), ('con_status', 'هـ) قرارداد'), ('proj_status', 'و) پروژه'), ('bank_status', 'ز) بانک')]:
    for k, v in Counter(r[key] for r in REC).most_common():
        q(title, k, v, '')
    if key == 'cc_status':
        for k, v in Counter(r.get('cc_prov', '') for r in REC if r['cc_direct']).most_common():
            q(title, f'منشأ AF:AI مستقیم: {k}', v, 'منبع اصلی فقط نام (AG/AI) داشت؛ کدها و سایر مقادیر حاصل غنی‌سازی‌های پیشین است')
q('ح) مبالغ', 'جمع بدهکار کل دفتر', D, '')
q('ح) مبالغ', 'جمع بستانکار کل دفتر', C, 'تراز: ' + ('PASS' if abs(D - C) < 1 else 'FAIL'))
q('ح) مبالغ', 'جمع بدهکار / بستانکار شیت هزینه_ها', f'{dE:,.0f} / {cE:,.0f}', '')
q('ح) مبالغ', 'جمع بدهکار / بستانکار شیت درآمدها', f'{dR:,.0f} / {cR:,.0f}', '')
q('ط) حفظ داده', 'ستون‌های A:AQ شیت کامل', 'بدون تغییر', 'ویرایش جریانی XML؛ فقط ستون‌های AR:BS افزوده شد. نتیجه بررسی مستقل در گزارش اجرای اسکریپت 05')
q('ط) حفظ داده', 'فرمول‌های ستون AD (VLOOKUP واحد سازمانی)', FORMULAS_AD, 'فرمول‌ها دست‌نخورده باقی ماندند')
q('ط) حفظ داده', 'ستون‌های AF:AI', 'بدون بازنویسی', 'رویداد مالی در ستون‌های جدید است، نه در AF:AI')
LEG = [('MAPPED_DIRECT', 'رویداد کانونی از خود سطر (حساب + جهت + متن) تشخیص داده شد'), ('MAPPED_EVENT_COMPONENT', 'سطر طرف تسویه/بدهی/بانک است و رویداد از تنها رویداد محرک همان سند (یا تطبیق مبلغ) گرفته شد'),
       ('MULTI_EVENT', 'سطر به چند رویداد سند مربوط است؛ همه در شیت ارتباط_سطر_رویداد آمده‌اند'), ('AMBIGUOUS', 'چند رویداد محتمل؛ رویداد انتخاب نشد'),
       ('INSUFFICIENT_EVIDENCE', 'سند هیچ ردیف محرک قابل استنادی ندارد'), ('REQUIRES_NEW_EVENT_REVIEW', 'رویداد در فرهنگ v7.1 وجود ندارد؛ کد GAP پیشنهادی است و تأیید نشده')]
for k, v in LEG: q('ی) راهنمای وضعیت‌ها', k, '', v)
q('ی) راهنمای وضعیت‌ها', 'هشدار', '', 'این دفتر کاربرد آزمایشی مدل پیشنهادی است و پیکربندی مصوب ERP نیست. ارتباط سطح رویداد ≠ شناسایی هزینه؛ پیش‌پرداخت مرتبط با مرکز هزینه همچنان پیش‌پرداخت است.')
def qa_rows():
    for n, row in enumerate(QA[1:], start=2):
        yield f'<row r="{n}">' + ''.join(cell(f'{L(k)}{n}', v) for k, v in enumerate(row)) + '</row>'

# ---------------- workbook parts
wbx = zin.read('xl/workbook.xml').decode('utf-8')
rels = zin.read('xl/_rels/workbook.xml.rels').decode('utf-8')
ct = zin.read('[Content_Types].xml').decode('utf-8')
app = zin.read('docProps/app.xml').decode('utf-8')
for part in ('xl/worksheets/sheet2.xml', 'xl/worksheets/sheet3.xml', 'xl/worksheets/sheet4.xml', 'xl/worksheets/sheet5.xml'):
    assert MAIN_OLD not in zin.read(part).decode('utf-8'), part   # no cross-sheet formula references the renamed sheet
NEWS = [('مراکز_هزینه', 'sheet8.xml', 'rId101', 201), ('هزینه_ها', 'sheet9.xml', 'rId102', 202), ('درآمدها', 'sheet10.xml', 'rId103', 203),
        (MAIN_NEW, 'sheet1.xml', 'rId1', 1), ('ارتباط_سطر_رویداد', 'sheet11.xml', 'rId104', 204), ('QA_تطبیق_و_راهنما', 'sheet12.xml', 'rId105', 205),
        ('حسابهای بانکی', 'sheet2.xml', 'rId2', 5), ('فیلتر اسناد دارای سرفصل هزینه', 'sheet3.xml', 'rId3', 2), ('واحد سازمانی', 'sheet4.xml', 'rId4', 3),
        ('بودجه 1404 + مراکز هزینه', 'sheet5.xml', 'rId5', 4)]
sheets_xml = '<sheets>' + ''.join(f'<sheet name="{x(n)}" sheetId="{sid}" r:id="{rid}"/>' for n, _, rid, sid in NEWS) + '</sheets>'
wbx = re.sub(r'<sheets>.*?</sheets>', sheets_xml, wbx, flags=re.S)
idx = {n: k for k, (n, *_ ) in enumerate(NEWS)}
dn = (f'<definedNames><definedName name="_xlnm._FilterDatabase" localSheetId="{idx["بودجه 1404 + مراکز هزینه"]}" hidden="1">\'بودجه 1404 + مراکز هزینه\'!$A$2:$J$2832</definedName>'
      f'<definedName name="_xlnm._FilterDatabase" localSheetId="{idx["حسابهای بانکی"]}" hidden="1">\'حسابهای بانکی\'!$A$1:$C$153789</definedName>'
      f'<definedName name="_xlnm._FilterDatabase" localSheetId="{idx[MAIN_NEW]}" hidden="1">{MAIN_NEW}!$A$5:${LASTL}$5</definedName>')
for n, fn, rid, sid in NEWS:
    if sid > 200:
        nrows = {'مراکز_هزینه': len(IDX_CC), 'هزینه_ها': len(IDX_EXP), 'درآمدها': len(IDX_REV), 'ارتباط_سطر_رویداد': len(REL), 'QA_تطبیق_و_راهنما': len(QA) - 1}[n]
        ncol = {'ارتباط_سطر_رویداد': len(REL_HEAD), 'QA_تطبیق_و_راهنما': 4}.get(n, len(VIEW_HEAD))
        dn += f'<definedName name="_xlnm._FilterDatabase" localSheetId="{idx[n]}" hidden="1">{n}!$A$1:${L(ncol - 1)}${nrows + 1}</definedName>'
dn += '</definedNames>'
wbx = re.sub(r'<definedNames>.*?</definedNames>', dn, wbx, flags=re.S)
wbx = re.sub(r'activeTab="\d+"', 'activeTab="0"', wbx)
rels = re.sub(r'<Relationship Id="rId[67]" [^>]*?/>', '', rels)
rels = rels.replace('</Relationships>', ''.join(f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/{fn}"/>'
                                                 for n, fn, rid, sid in NEWS if sid > 200) + '</Relationships>')
ct = re.sub(r'<Override PartName="/xl/worksheets/sheet[67]\.xml"[^>]*?/>', '', ct)
ct = ct.replace('</Types>', ''.join(f'<Override PartName="/xl/worksheets/{fn}" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                                    for n, fn, rid, sid in NEWS if sid > 200) + '</Types>')
app = re.sub(r'<vt:i4>\d+</vt:i4>', f'<vt:i4>{len(NEWS)}</vt:i4>', app, count=1)
app = re.sub(r'<TitlesOfParts><vt:vector size="\d+" baseType="lpstr">.*?</vt:vector>',
             f'<TitlesOfParts><vt:vector size="{len(NEWS)}" baseType="lpstr">' + ''.join(f'<vt:lpstr>{x(n)}</vt:lpstr>' for n, *_ in NEWS) + '</vt:vector>', app, flags=re.S)
REPL = {'xl/styles.xml': st, 'xl/workbook.xml': wbx, 'xl/_rels/workbook.xml.rels': rels, '[Content_Types].xml': ct, 'docProps/app.xml': app}
DROP = {'xl/worksheets/sheet6.xml', 'xl/worksheets/sheet7.xml'}

zout = zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True)
done = 0
for info in zin.infolist():
    if info.filename in DROP: continue
    ni = copy.copy(info); ni.compress_type = zipfile.ZIP_DEFLATED
    if info.filename in REPL:
        zout.writestr(ni, REPL[info.filename].encode('utf-8')); continue
    if info.filename != 'xl/worksheets/sheet1.xml':
        zout.writestr(ni, zin.read(info.filename)); continue
    with zin.open(info) as fi, zout.open(ni, 'w', force_zip64=True) as fo:
        buf = ''; head_done = False; dec = __import__('codecs').getincrementaldecoder('utf-8')()
        while True:
            chunk = fi.read(1 << 24)
            buf += dec.decode(chunk, final=not chunk)
            if not head_done:
                p = buf.find('<sheetData>')
                if p < 0 and chunk: continue
                fo.write(main_head(buf[:p + len('<sheetData>')]).encode('utf-8')); buf = buf[p + len('<sheetData>'):]; head_done = True
            out = []; pos = 0
            for m in ROWRX.finditer(buf):
                out.append(edit_row(m.group(0))); pos = m.end(); done += 1
            if not chunk:
                tail = buf[pos:]
                tail = re.sub(r'<autoFilter ref="A5:AQ5"', f'<autoFilter ref="A5:{LASTL}5"', tail)
                fo.write((''.join(out) + tail).encode('utf-8')); break
            fo.write(''.join(out).encode('utf-8')); buf = buf[pos:]
print('main rows streamed', done, round(time.time() - t0), flush=True)
write_sheet(zout, 'xl/worksheets/sheet8.xml', VIEW_HEAD, VIEW_W, view_rows(IDX_CC), len(IDX_CC), selected=True)
write_sheet(zout, 'xl/worksheets/sheet9.xml', VIEW_HEAD, VIEW_W, view_rows(IDX_EXP), len(IDX_EXP))
write_sheet(zout, 'xl/worksheets/sheet10.xml', VIEW_HEAD, VIEW_W, view_rows(IDX_REV), len(IDX_REV))
write_sheet(zout, 'xl/worksheets/sheet11.xml', REL_HEAD, [10, 18, 28, 10, 45, 24, 36, 60, 30], rel_rows(), len(REL))
write_sheet(zout, 'xl/worksheets/sheet12.xml', QA[0], [36, 60, 24, 110], qa_rows(), len(QA) - 1)
zout.close()
json.dump(dict(rows=N, cc=len(IDX_CC), exp=len(IDX_EXP), rev=len(IDX_REV), rel=len(REL), status=dict(st_c), D=D, C=C), open(W + 'write_stats.json', 'w'))
print('done', round(time.time() - t0))
