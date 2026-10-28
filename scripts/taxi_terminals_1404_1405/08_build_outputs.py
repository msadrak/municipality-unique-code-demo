"""Phase 4 — deliverables A (workbook) and D (machine-readable).  Reads only the pipeline SQLite + qa_results.json.

Privacy: the workbook and CSV summaries carry NO free-text narration (Sharh/Des often contain person and counterparty names).
The complete narration stays in the RESTRICTED line-level lineage CSV, addressed by Source_Record_ID.
"""
import sqlite3, sys, os, json, csv, hashlib, collections, re
import xlsxwriter
sys.path.insert(0, os.path.dirname(__file__))
from common import *
from rules import TT_EVENTS, EVENT_STATUS_V2, EVENT_REVIEW, EXCEPTION_TYPES
import importlib.util
spec = importlib.util.spec_from_file_location('cc05', os.path.join(os.path.dirname(__file__), '05_classify_cost_centers.py'))
src05 = open(os.path.join(os.path.dirname(__file__), '05_classify_cost_centers.py'), encoding='utf8').read()
ns = {'__file__': os.path.join(os.path.dirname(os.path.abspath(__file__)), '05_classify_cost_centers.py')}
exec(src05[:src05.index("con = sqlite3.connect(DB)")], ns)       # reuse NEW_CC / MZ / CC definitions without re-running the classifier
NEW_CC, MZ, CC = ns['NEW_CC'], ns['MZ'], ns['CC']

os.makedirs(MR, exist_ok=True)
con = sqlite3.connect(DB)
cur = con.cursor()
q = lambda s, *a: cur.execute(s, a).fetchall()
def one(s, *a):
    r = cur.execute(s, a).fetchone()
    return r[0] if r and r[0] is not None else 0

cur.execute('CREATE INDEX IF NOT EXISTS i_raw_k ON sanad_raw(org,fy,src_row)'); cur.execute('CREATE INDEX IF NOT EXISTS i_s_k ON sanad(org,fy,src_row)'); con.commit()
V2 = V2FAMILY
V21 = VARIANT == 'v21'
import re as _re0
def mcode(c):
    """mask the bank-account part (>=6 digits) of a hierarchical account code in client-facing outputs; the hierarchy (e.g. 113-1-1) is kept"""
    if not isinstance(c, str): return c
    return _re0.sub(r'(?<=-)(\d{6,})$', lambda m: '•' * (len(m.group(1)) - 3) + m.group(1)[-3:], c)
QA = json.load(open(QA_JSON, encoding='utf8'))
GEN = VSUF
FILE = f'{OUT}/taxi_terminals_financial_mapping_1404_1405_{VSUF}.xlsx'
ORGFA = {'Taxi': 'سازمان تاکسیرانی', 'Terminals': 'سازمان پایانه‌ها'}

# ----------------------------------------------------------------------------------------------- FE catalogue (v7.1, read only)
import openpyxl
V71 = f'{ROOT}/data/deliverables/financial_event_discovery/revisions/1404-r20260922-canonical-events-v7.1/financial_event_discovery_1404-r20260922_canonical-events_v7.1.xlsx'
wbx = openpyxl.load_workbook(V71, read_only=True)
FE = {}
for r in wbx['فرهنگ_رویداد_مالی_کاندید'].iter_rows(min_row=2, values_only=True):
    if r[0]: FE[r[0]] = dict(title=r[1], short=r[2], definition=r[3], family=r[4], nature=r[5], stage=r[6])
wbx.close()
V71_SHA = hashlib.sha256(open(V71, 'rb').read()).hexdigest()

# ----------------------------------------------------------------------------------------------- workbook helpers
wb = xlsxwriter.Workbook(FILE, {'strings_to_numbers': False, 'strings_to_formulas': False})
F = dict(
    h=wb.add_format({'bold': True, 'bg_color': '#1F3864', 'font_color': 'white', 'align': 'center', 'valign': 'vcenter', 'text_wrap': True, 'border': 1, 'reading_order': 2}),
    k=wb.add_format({'italic': True, 'font_color': '#7F7F7F', 'font_size': 8, 'align': 'center', 'bg_color': '#F2F2F2', 'border': 1}),
    t=wb.add_format({'text_wrap': True, 'valign': 'top', 'reading_order': 2, 'border': 1}),
    n=wb.add_format({'num_format': '#,##0', 'valign': 'top', 'border': 1}),
    p=wb.add_format({'num_format': '0.0%', 'valign': 'top', 'border': 1}),
    d=wb.add_format({'num_format': '0.0000', 'valign': 'top', 'border': 1}),
    title=wb.add_format({'bold': True, 'font_size': 14, 'reading_order': 2}),
    warn=wb.add_format({'bold': True, 'font_color': '#C00000', 'text_wrap': True, 'reading_order': 2}),
    pass_=wb.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100', 'border': 1, 'align': 'center'}),
    rev=wb.add_format({'bg_color': '#FFEB9C', 'font_color': '#9C5700', 'border': 1, 'align': 'center'}),
    fail=wb.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006', 'border': 1, 'align': 'center'}),
)
SHEETS = {}
V2_SKIP = {'New_CC_Proposals', 'Committee_Decisions'}
V2_EXTRA = {}
def sheet(name, cols, rows, title=None, note=None, widths=None, freeze=True, rtl=True):
    """cols = [(key, persian_header, kind)] kind in t/n/p/d ; rows = iterable of tuples aligned with cols"""
    if V2 and name in V2_SKIP: return None
    if V2 and name in V2_EXTRA:
        xc, xf = V2_EXTRA[name]; cols = list(cols) + list(xc); rows = [tuple(r) + tuple(xf(r)) for r in rows]
    ws = wb.add_worksheet(name)
    if rtl: ws.right_to_left()
    r0 = 0
    if title:
        ws.write(r0, 0, title, F['title']); r0 += 1
    if note:
        ws.merge_range(r0, 0, r0, min(len(cols) - 1, 8), note, F['warn']); ws.set_row(r0, 45); r0 += 1
    for j, (k, fa, kind) in enumerate(cols):
        ws.write(r0, j, fa, F['h']); ws.write(r0 + 1, j, k, F['k'])
        ws.set_column(j, j, (widths or {}).get(k, 14 if kind != 't' else 26))
    first = r0 + 2
    i = 0
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            kind = cols[j][2]
            if v is None: ws.write_blank(first + i, j, None, F['t'])
            elif kind in ('n', 'p', 'd') and isinstance(v, (int, float)): ws.write_number(first + i, j, v, F[kind])
            else: ws.write_string(first + i, j, str(v), F['t'])
    nrows = i + 1 if rows else 0
    ws.freeze_panes(first, 1 if freeze else 0)
    if nrows: ws.autofilter(r0 + 1, 0, first + nrows - 1, len(cols) - 1)
    SHEETS[name] = dict(ws=ws, first=first, n=nrows, cols=[c[0] for c in cols], r0=r0)
    return ws

def colL(name, key):
    idx = SHEETS[name]['cols'].index(key)
    n = idx; s = ''
    while True:
        s = chr(65 + n % 26) + s; n = n // 26 - 1
        if n < 0: break
    return s

# ----------------------------------------------------------------------------------------------- README
ws = wb.add_worksheet('README_راهنما'); ws.right_to_left(); ws.set_column(0, 0, 130)
lines = [
 (f'Unified Financial Mapping — Taxi & Terminals, FY1404 + FY1405 ({VSUF})', 'title'),
 ('سه لایهٔ حاکمیتی: A = شواهد مشاهده‌شده (OBSERVED)، B = پیشنهاد مدل (PROPOSED)، C = تأیید مرجع (APPROVED). در این فایل هیچ سطری در لایهٔ C نیست؛ هیچ تصمیم کمیته یا مصوبه‌ای وجود ندارد.', 'warn'),
 ('مرجع پایه: کاتالوگ رویداد مالی v7.1 (FE-01..FE-70، کاندید؛ مصوب نیست) و master مراکز هزینه v3 + افزودنی CC-109 (cc_master.json؛ وضعیت PROPOSED).', 't'),
 ('شناسه‌های TT-NE-xx = رویداد کاندید جدید؛ TTCC-P-xx = مرکز هزینه کاندید جدید. هر دو فضای نام موقت‌اند و با شناسه‌های رسمی شهرداری اشتباه گرفته نمی‌شوند.', 't'),
 ('کد فعالیت/مرکز منبع (CodeMarkaz) و واحد منبع (CodeVahed) فقط شاهدند؛ با شناسه مرکز هزینهٔ شهرداری برابر فرض نشده‌اند.', 't'),
 ('واحد پول در فایل‌های منبع تصریح نشده است (سازگار با ریال، تأییدنشده). مبالغ بدون تبدیل و گرد کردن آورده شده‌اند.', 't'),
 ('حریم خصوصی: این فایل شرح متنی اسناد (که شامل نام اشخاص است) را ندارد. شرح کامل فقط در machine_readable/document_lineage_RESTRICTED.csv و با Source_Record_ID قابل بازیابی است.', 'warn'),
 ('سال ۱۴۰۵ ناقص است (تاکسیرانی تا ۱۴۰۵/۰۷/۱۳، پایانه‌ها تا ۱۴۰۵/۰۷/۱۴). فقط «پنجره مشترک» قابل‌مقایسه است و آن هم فقط شاخص (INDICATIVE).', 'warn'),
 ('فرمول‌ها: در QA_Reconciliation بلوک کنترل با فرمول زنده (SUMIFS) وجود دارد؛ مقدار ذخیره‌شده توسط اسکریپت محاسبه شده است (موتور صفحه‌گسترده برای بازمحاسبه در دسترس نبود).', 't'),
]
if V2:
    lines += [('v2 = بازبینی اصلاحی و مستقل v1 (Audited, Reconciled, Decision-Ready). v1 دست‌نخورده است؛ شیت V1_V2_Change_Log همه تغییرات را ردیف‌به‌ردیف ثبت می‌کند. هیچ مورد APPROVED نیست؛ activate_in_production = NO.', 'warn'),
              ('تفاوت‌های کلیدی v2: (۱) سه شمارندهٔ جدا برای پیشنهادهای مرکز هزینه (Direct/Ambiguous/Evidence_Support) و حذف مرکز انتخاب‌شده از ردیف‌های MULTIPLE؛ (۲) بازبینی مفهومی همه ۲۸ کاندید رویداد؛ (۳) KPIها با بازمحاسبه مستقل و وضعیت‌های جدید؛ (۴) تأیید محتوای RAR با 7-Zip؛ (۵) ماتریس Decision_Readiness.', 't'),
              ('مقدار ذخیره‌شده فرمول‌های QA_Reconciliation توسط اسکریپت محاسبه شده (cached) و بازمحاسبه زنده توسط موتور اکسل نیست؛ بازمحاسبهٔ مستقل در 15_kpi_qa_v2.py / 13_kpi_independent.py / 11_postbuild_qa.py انجام می‌شود.', 'warn')]
for i, (txt, k) in enumerate(lines):
    ws.write(i, 0, txt, F['title'] if k == 'title' else F['warn'] if k == 'warn' else F['t'])
    ws.set_row(i, 18 if k == 'title' else 48)

# ----------------------------------------------------------------------------------------------- 1 Source_Inventory
inv = q('SELECT org,fy,kind,file,sheet,sha256,bytes,header_ok,data_rows FROM inventory ORDER BY org,fy,kind')
if V2:
    _rv = json.load(open(f'{OUT}/machine_readable/rar_verification.json', encoding='utf8'))
    def _inv_x(r):
        if r[2] == 'آرشیو RAR': return ('7z t = OK (Rar5، ۴ فایل، CRC سالم)',)
        for e in _rv:
            if e['org'] == r[0] and e['year'] == r[1] and r[3].endswith(e['file']): return ('برابر با فایل استخراج‌شده از RAR (SHA-256)' if e['match'] else 'عدم تطابق',)
        return ('—',)
    V2_EXTRA['Source_Inventory'] = ([('rar_content_check', 'تأیید محتوای RAR با 7-Zip', 't')], _inv_x)
sheet('Source_Inventory', [('organization', 'سازمان', 't'), ('fiscal_year', 'سال مالی', 't'), ('file_kind', 'نوع فایل', 't'), ('source_file', 'مسیر فایل منبع', 't'), ('source_sheet', 'برگه', 't'),
      ('sha256', 'SHA-256', 't'), ('bytes', 'اندازه (بایت)', 'n'), ('header_matches_expected_schema', 'سرستون مطابق شمای مشاهده‌شده', 't'), ('data_rows', 'ردیف داده (بدون سرستون)', 'n')],
      [(r[0], r[1], 'حساب (Hesab)' if r[2] == 'Hesab' else 'سند (Sanad)', r[3], r[4], r[5], r[6], 'بله' if r[7] else 'خیر', r[8]) for r in inv] +
      [(o, 'همه', 'آرشیو RAR', f'{ORGS[o][1]}.rar', '—', hashlib.sha256(open(f'{SRC}/{ORGS[o][1]}.rar', 'rb').read()).hexdigest(), os.path.getsize(f'{SRC}/{ORGS[o][1]}.rar'), 'n/a', None) for o in ORGS],
      title='فهرست هشت فایل منبع', note='مسیرها نسبت به H:/Freelancing_Project/KalaniProject/Taxi_Gate هستند. فایل‌های اصلی و RARها بدون تغییر ماندند.', widths={'source_file': 34, 'sha256': 70})

# ----------------------------------------------------------------------------------------------- 2 Source_Profile
orgyears = [(o, y) for o in ORGS for y in YEARS]
metrics = []
def pm(name, fn, kind='n', note=''):
    metrics.append((name, [fn(o, y) for o, y in orgyears], kind, note))
nonnull = lambda col: (lambda o, y: one(f"SELECT count(*) FROM sanad WHERE org=? AND fy=? AND {col} IS NOT NULL AND {col}<>'' AND {col}<>'NULL'", o, y))
pm('ردیف حساب (Hesab)', lambda o, y: one('SELECT count(*) FROM hesab WHERE org=? AND fy=?', o, y))
pm('ردیف سند (Sanad) = خطوط حسابداری', lambda o, y: one('SELECT count(*) FROM sanad WHERE org=? AND fy=?', o, y))
pm('اسناد یکتا (سازمان+سال+Sanad_Num)', lambda o, y: one('SELECT count(DISTINCT doc_key) FROM sanad WHERE org=? AND fy=?', o, y))
pm('HCode متمایز در سند', lambda o, y: one('SELECT count(DISTINCT hcode) FROM sanad WHERE org=? AND fy=?', o, y))
pm('جمع بدهکار (واحد منبع)', lambda o, y: one('SELECT sum(bed) FROM sanad WHERE org=? AND fy=?', o, y))
pm('جمع بستانکار (واحد منبع)', lambda o, y: one('SELECT sum(bes) FROM sanad WHERE org=? AND fy=?', o, y))
pm('اختلاف بدهکار−بستانکار', lambda o, y: one('SELECT sum(bed)-sum(bes) FROM sanad WHERE org=? AND fy=?', o, y))
pm('کمترین تاریخ', lambda o, y: q('SELECT min(date) FROM sanad WHERE org=? AND fy=?', o, y)[0][0], 't')
pm('بیشترین تاریخ (آخرین تراکنش واقعی)', lambda o, y: q('SELECT max(date) FROM sanad WHERE org=? AND fy=?', o, y)[0][0], 't')
pm('تاریخ نامعتبر', lambda o, y: one('SELECT count(*) FROM sanad WHERE org=? AND fy=? AND date_ok=0', o, y))
pm('اسناد نامتوازن', lambda o, y: one('SELECT count(*) FROM (SELECT doc_key,sum(bed)-sum(bes) d FROM sanad WHERE org=? AND fy=? GROUP BY doc_key HAVING d<>0)', o, y))
pm('ردیف بدون حساب متناظر در Hesab', lambda o, y: one('SELECT count(*) FROM sanad s WHERE org=? AND fy=? AND NOT EXISTS(SELECT 1 FROM hesab h WHERE h.org=s.org AND h.fy=s.fy AND h.hcode=s.hcode)', o, y))
pm('گروه‌های رکورد تکراری کاندید', lambda o, y: one('SELECT count(*) FROM (SELECT 1 FROM sanad WHERE org=? AND fy=? GROUP BY doc_key,date,des,hcode,bed,bes,sharh,f1,person HAVING count(*)>1)', o, y))
for col, fa in (('markaz', 'CodeMarkaz (کد فعالیت/مرکز منبع) دارای مقدار'), ('vahed', 'CodeVahed (واحد) دارای مقدار'), ('person', 'CodePerson دارای مقدار'), ('f1', 'Field1 دارای مقدار'), ('f2', 'Field2 دارای مقدار'),
                ('f3', 'Field3 دارای مقدار'), ('f4', 'Field4 دارای مقدار'), ('f5', 'Field5 دارای مقدار'), ('sharh', 'Sharh دارای مقدار')):
    pm(fa + ' (بدون NULL متنی/خالی)', nonnull(col))
pm('ردیف با متن «NULL» در CodeMarkaz', lambda o, y: one("SELECT count(*) FROM sanad WHERE org=? AND fy=? AND markaz='NULL'", o, y))
pm('ردیف با مقدار تهی واقعی در CodeMarkaz', lambda o, y: one("SELECT count(*) FROM sanad WHERE org=? AND fy=? AND markaz IS NULL", o, y))
for kind, fa in (('OPENING', 'ردیف‌های سند افتتاحیه'), ('CLOSING_PERMANENT', 'ردیف‌های سند اختتامیه'), ('CLOSING_TEMPORARY', 'ردیف‌های بستن حساب موقت'), ('INTERNAL_SETTLEMENT', 'ردیف‌های تهاتر/بستن حساب فی‌مابین'), ('REGULAR', 'ردیف‌های اسناد منظم')):
    pm(fa, (lambda kd: (lambda o, y: one('SELECT count(*) FROM sanad s JOIN doc_class d ON d.doc_key=s.doc_key WHERE s.org=? AND s.fy=? AND d.kind=?', o, y, kd)))(kind))
for ac, fa in (('EXP', 'ردیف‌های هزینه‌ای (۶۱۱–۶۱۳)'), ('REV_OP', 'ردیف‌های درآمد عملیاتی'), ('REV_NONOP', 'ردیف‌های درآمد غیرعملیاتی (۸۱۲)'), ('FIXED_ASSET', 'ردیف‌های دارایی ثابت'),
               ('PREPAY', 'ردیف‌های پیش‌پرداخت'), ('INVENTORY', 'ردیف‌های موجودی'), ('AR', 'ردیف‌های حساب‌های دریافتنی (۱۱۳-۱)'), ('NOTES_REC', 'ردیف‌های اسناد دریافتنی'),
               ('AP', 'ردیف‌های حساب‌های پرداختنی (۲۱۱-۱)'), ('DEPOSIT', 'ردیف‌های سپرده (۲۱۲-۶)'), ('BANK', 'ردیف‌های بانک'), ('TANKHAH', 'ردیف‌های تنخواه'), ('MEMO', 'ردیف‌های انتظامی')):
    pm(fa + ' — تمام اسناد', (lambda a_: (lambda o, y: one('SELECT count(*) FROM line_event WHERE org=? AND fy=? AND acat=?', o, y, a_)))(ac))
sheet('Source_Profile', [('metric', 'شاخص', 't')] + [(f'{o}_{y}', f'{ORGFA[o]} {y}', 'n') for o, y in orgyears] + [('note', 'یادداشت', 't')],
      [[m[0]] + m[1] + [m[3]] for m in metrics],
      title='پروفایل ساختاری و مالی (شمارش مستقل از فایل منبع در QA تأیید شده است)',
      note='NULL متنی (رشته «NULL»)، سلول تهی و صفر عددی از هم تفکیک شده‌اند. مقادیر پولی بدون تبدیل واحد.', widths={'metric': 58, 'note': 30})
SP_ROW = {m[0]: SHEETS['Source_Profile']['first'] + i for i, m in enumerate(metrics)}

# ----------------------------------------------------------------------------------------------- 3/4 accounts
ad = q('SELECT org,fy,hcode,title,parent_hcode,kol,moeen,taf1,taf2,level,is_leaf,src_kind,src_type,src_p,proposed_nature,confidence,n_lines,bed_total,bes_total,hid FROM account_dictionary ORDER BY org,fy,hid')
if V21: ad = [tuple(mcode(x) if i in (2, 4) else x for i, x in enumerate(r)) for r in ad]
sheet('Account_Dictionary', [('organization', 'سازمان', 't'), ('fiscal_year', 'سال', 't'), ('account_code', 'کد حساب (HCode)', 't'), ('account_title', 'عنوان حساب (منبع)', 't'), ('parent_code', 'کد والد', 't'),
      ('kol', 'کل', 't'), ('moeen', 'معین', 't'), ('tafsili1', 'تفصیلی ۱', 't'), ('tafsili2', 'تفصیلی ۲', 't'), ('level', 'سطح سلسله‌مراتب (۱=کل..۴=تفصیلی۲)', 'n'), ('is_leaf', 'برگ؟ (HaveChild=0)', 'n'),
      ('src_kind', 'Kind منبع', 't'), ('src_type', 'Type منبع', 't'), ('src_p', 'P منبع', 't'), ('proposed_nature', 'ماهیت پیشنهادی حساب', 't'), ('confidence', 'اطمینان', 't'),
      ('n_lines', 'ردیف‌های سند', 'n'), ('bed_total', 'جمع بدهکار', 'n'), ('bes_total', 'جمع بستانکار', 'n'), ('source_record_id', 'Source_Record_ID (Hesab)', 't')],
      ad, title='فرهنگ حساب‌های هر سازمان و سال (۲٬۱۷۸ ردیف Hesab)',
      note='ستون‌های Kind/Type/P منبع معنایشان تأیید نشده و بدون تفسیر نگه‌داری شده‌اند. سطح سلسله‌مراتب از اجزای کد استخراج شده است نه از ستون‌های Tabageh/Gorooh.', widths={'account_title': 40, 'source_record_id': 20})
acw = q('SELECT org,fy,org_kol,org_moeen,org_title,org_hcode,mun_kol,mun_moin,mun_kol_title,mun_moin_title,match_level,match_status,note,n_lines,bed_total,bes_total,code_collision FROM account_crosswalk ORDER BY org,fy,cast(org_kol as int),cast(org_moeen as int)')
if V21: acw = [tuple(mcode(x) if i == 5 else x for i, x in enumerate(r)) for r in acw]
sheet('Account_Crosswalk', [('organization', 'سازمان', 't'), ('fiscal_year', 'سال', 't'), ('org_kol', 'کل (سازمان)', 't'), ('org_moeen', 'معین (سازمان)', 't'), ('org_title', 'عنوان حساب سازمان', 't'), ('org_hcode', 'HCode', 't'),
      ('mun_kol', 'کل شهرداری (نامزد)', 't'), ('mun_moin', 'معین شهرداری (نامزد)', 't'), ('mun_kol_title', 'عنوان کل شهرداری', 't'), ('mun_moin_title', 'عنوان معین شهرداری', 't'),
      ('match_level', 'سطح تطبیق (L4 عنوان+ماهیت موقت / L5 بازبینی / NONE)', 't'), ('match_status', 'وضعیت', 't'), ('note', 'توضیح', 't'), ('n_lines', 'ردیف‌های سند', 'n'), ('bed_total', 'بدهکار', 'n'),
      ('bes_total', 'بستانکار', 'n'), ('code_collision', 'برخورد کد (شماره یکسان، معنای متفاوت)', 'n')],
      acw, title='نگاشت حساب سازمان به نامزد حساب شهرداری',
      note='سطوح L1/L2/L3 (کد و تعریف یکسان / سلسله‌مراتب / مرجع معتبر) تهی‌اند: مرجع معتبر برای هم‌ارزی وجود ندارد و برابری عددی کد شاهد نیست. L4 فقط موقت است. کد حساب‌های هر سازمان بدون تغییر حفظ شده است.', widths={'org_title': 36, 'note': 50, 'mun_kol_title': 28, 'mun_moin_title': 34})
adv = q('SELECT kind,org_a,org_b,fy_a,fy_b,hcode,title_a,title_b,n_lines_a,n_lines_b,note FROM account_divergence ORDER BY kind,hcode')
if V21: adv = [tuple(mcode(x) if i == 5 else x for i, x in enumerate(r)) for r in adv]
sheet('Account_Divergence', [('kind', 'نوع واگرایی', 't'), ('org_a', 'سازمان الف', 't'), ('org_b', 'سازمان ب', 't'), ('fy_a', 'سال الف', 't'), ('fy_b', 'سال ب', 't'), ('hcode', 'HCode', 't'), ('title_a', 'عنوان الف', 't'),
      ('title_b', 'عنوان ب', 't'), ('n_lines_a', 'ردیف الف', 'n'), ('n_lines_b', 'ردیف ب', 'n'), ('note', 'توضیح', 't')], adv,
      title='واگرایی طبقه‌بندی حساب: فقط تاکسیرانی / فقط پایانه‌ها / هم‌کد-هم‌عنوان / هم‌کد-عنوان متفاوت / تغییرات ۱۴۰۴→۱۴۰۵',
      note='«هم‌کد-هم‌عنوان» هنوز اثبات هم‌معنایی نیست.', widths={'title_a': 36, 'title_b': 36, 'note': 40})

# ----------------------------------------------------------------------------------------------- 5 Document_Lineage (document level)
dl = q('''SELECT d.doc_key,d.org,d.fy,d.kind,d.n_lines,d.bed_total,d.date_first,d.date_last,d.primary_event,d.outcome,d.composite,d.driver_events,d.conf,d.rule_id,d.review,
  (SELECT min(src_row) FROM sanad s WHERE s.doc_key=d.doc_key),(SELECT max(src_row) FROM sanad s WHERE s.doc_key=d.doc_key),
  (SELECT group_concat(DISTINCT cc_status) FROM line_cc c WHERE c.doc_key=d.doc_key AND c.eligible=1),
  (SELECT group_concat(DISTINCT cc_id) FROM line_cc c WHERE c.doc_key=d.doc_key AND c.eligible=1 AND cc_id IS NOT NULL),
  (SELECT sanad_num FROM sanad s WHERE s.doc_key=d.doc_key LIMIT 1), (SELECT sum(bes) FROM sanad s WHERE s.doc_key=d.doc_key)
  FROM doc_class d ORDER BY d.org,d.fy,d.doc_key''')
DOC_ROWS = []
for r in dl:
    dk, org, fy, kind, nl, bt, d1, d2, pe, oc, comp, drv, conf, rid, rev, r1, r2, ccst, ccid, num, bes = r
    DOC_ROWS.append((dk, org, fy, f'{ORGS[org][1]}/{fy}/Sanad.xlsx', num, nl, bt, bes, d1, d2, r1, r2, kind, pe, oc, comp, drv, conf, rid, ccst or '', ccid or '', 'بله' if rev else 'خیر'))
sheet('Document_Lineage', [('doc_key', 'شناسه سند (سازمان-سال-Sanad_Num)', 't'), ('organization', 'سازمان', 't'), ('fiscal_year', 'سال', 't'), ('source_file', 'فایل منبع', 't'), ('sanad_num', 'Sanad_Num', 't'),
      ('n_lines', 'تعداد خطوط', 'n'), ('debit_total', 'جمع بدهکار', 'n'), ('credit_total', 'جمع بستانکار', 'n'), ('date_first', 'اولین تاریخ', 't'), ('date_last', 'آخرین تاریخ', 't'),
      ('src_row_min', 'اولین ردیف اکسل', 'n'), ('src_row_max', 'آخرین ردیف اکسل', 'n'), ('doc_kind', 'نوع سند', 't'), ('primary_event', 'رویداد اصلی', 't'), ('outcome', 'نتیجه طبقه‌بندی', 't'),
      ('composite_flag', 'ترکیبی؟', 'n'), ('driver_events', 'رویدادهای محرک', 't'), ('confidence', 'اطمینان', 't'), ('rule_id', 'قاعده', 't'), ('cc_statuses', 'وضعیت‌های مرکز هزینه', 't'),
      ('cc_ids', 'مراکز هزینه (پیشنهادی)', 't'), ('review_required', 'نیازمند بازبینی', 't')],
      DOC_ROWS, title='ردیابی در سطح سند (۴٬۵۱۲ سند). ردیابی کامل سطح خط (۱۱۱٬۶۰۰ ردیف، شامل شرح اصلی) در فایل محدود جدا نگهداری شده است',
      note='هر سطر منبع با Source_Record_ID = «TAXI|TERM»-سال-S-شماره ردیف اکسل در machine_readable/document_lineage_RESTRICTED.csv پیدا می‌شود. شرح متنی عمداً در این فایل نیست (حاوی نام اشخاص).', widths={'doc_key': 20, 'source_file': 26, 'driver_events': 28, 'cc_ids': 22, 'cc_statuses': 28})

# ----------------------------------------------------------------------------------------------- 6 Canonical_Events
usage = {}
for ev, org, n, nd, dr, cr, f, l in q("""SELECT e.own_event,e.org,count(*),count(DISTINCT e.doc_key),sum(e.amount_dr),sum(e.amount_cr),min(s.date),max(s.date) FROM line_event e JOIN sanad s ON s.sid=e.sid
        WHERE e.own_event IS NOT NULL AND e.role IN ('DRIVER','SETTLEMENT') GROUP BY 1,2"""):
    usage[(ev, org)] = (n, nd, dr, cr, f, l)
stat = collections.defaultdict(collections.Counter)
for ev, oc, n in q("SELECT own_event,outcome,count(*) FROM line_event WHERE own_event IS NOT NULL AND role='DRIVER' GROUP BY 1,2"): stat[ev][oc] = n
dims = {}
for ev in set(e for e, _ in usage):
    tot = one("SELECT count(*) FROM line_event WHERE own_event=? AND role='DRIVER'", ev) or 1
    pe = one("SELECT count(*) FROM line_event e JOIN sanad s ON s.sid=e.sid WHERE e.own_event=? AND e.role='DRIVER' AND s.person IS NOT NULL AND s.person NOT IN ('NULL','')", ev) / tot
    un = one("SELECT count(*) FROM line_event e JOIN sanad s ON s.sid=e.sid WHERE e.own_event=? AND e.role='DRIVER' AND s.vahed IS NOT NULL AND s.vahed NOT IN ('NULL','') AND s.org='Terminals'", ev) / tot
    mk = one("SELECT count(*) FROM line_event e JOIN sanad s ON s.sid=e.sid WHERE e.own_event=? AND e.role='DRIVER' AND s.markaz IS NOT NULL AND s.markaz NOT IN ('NULL','')", ev) / tot
    bank = one("SELECT count(DISTINCT e.doc_key) FROM line_event e WHERE e.own_event=? AND e.role='DRIVER' AND EXISTS(SELECT 1 FROM sanad s WHERE s.doc_key=e.doc_key AND s.kol='111' AND s.moeen='2')", ev) / (one("SELECT count(DISTINCT doc_key) FROM line_event WHERE own_event=? AND role='DRIVER'", ev) or 1)
    ct = one("SELECT count(*) FROM line_event e JOIN sanad s ON s.sid=e.sid WHERE e.own_event=? AND e.role='DRIVER' AND (s.des_norm LIKE '%قرارداد%' OR s.sharh_norm LIKE '%قرارداد%' OR s.sharh_norm LIKE '%صورت وضعیت%')", ev) / tot
    dims[ev] = (pe, un, mk, bank, ct)
ce_rows = []
for ev in sorted(set(FE) | set(TT_EVENTS), key=lambda x: (x.startswith('TT'), x)):
    orgs_used = [o for o in ORGS if (ev, o) in usage]
    if ev in FE and not orgs_used: continue   # FE ids with no observation are not reproduced (the dictionary stays in v7.1)
    if ev in FE:
        d = FE[ev]; origin = 'FE v7.1 (بازاستفاده، بدون بازتعریف)'; title, fam, nat, defn = d['title'], d['family'], d['nature'], d['definition']; gap = ''; why = ''
        gov = 'OBSERVED — شواهد جدید برای رویداد کاندید v7.1؛ تأیید نشده'
    else:
        t = TT_EVENTS[ev]; origin = 'TT-NE پیشنهادی جدید (موقت)'; title, fam, nat, defn, gap, _o, why = t; gov = ('PROPOSED — کاندید باقی‌مانده پس از بازبینی v2؛ نیازمند تصمیم کمیته' if EVENT_STATUS_V2.get(ev) == 'RETAINED_CANDIDATE' else 'PROPOSED — کاندید در انتظار شواهد (INSUFFICIENT_EVIDENCE)') if V2 else 'PROPOSED — کاندید جدید؛ نیازمند تصمیم کمیته'
    n = sum(usage[(ev, o)][0] for o in orgs_used); nd = sum(usage[(ev, o)][1] for o in orgs_used)
    dr = sum(usage[(ev, o)][2] for o in orgs_used); cr = sum(usage[(ev, o)][3] for o in orgs_used)
    firsts = [usage[(ev, o)][4] for o in orgs_used]; lasts = [usage[(ev, o)][5] for o in orgs_used]
    st = stat[ev]
    dd = dims.get(ev, (0, 0, 0, 0, 0))
    ce_rows.append((ev, origin, title, fam, nat, defn, gov, gap, ' و '.join(ORGFA[o] for o in orgs_used), n, nd, dr, cr, min(firsts), max(lasts),
                    st.get('EXISTING_EVENT_CONFIRMED', 0), st.get('EXISTING_EVENT_PROVISIONAL', 0), st.get('NEW_EVENT_CANDIDATE', 0), dd[0], dd[1], dd[2], dd[3], dd[4], why))
if V2:
    for _x, (_t, _why) in EXCEPTION_TYPES.items():
        _o = [o for o in ORGS if (_x, o) in usage]; _dd = dims.get(_x, (0, 0, 0, 0, 0)); _u = [usage[(_x, o)] for o in _o]
        ce_rows.append((_x, 'استثنا/تعلیق v2 (نه رویداد canonical)', _t, 'استثنا', 'در انتظار شناسایی', _why, 'EXCEPTION — صف تعلیق؛ درآمد شناخته نمی‌شود', '', ' و '.join(ORGFA[o] for o in _o), sum(u[0] for u in _u), sum(u[1] for u in _u), sum(u[2] for u in _u), sum(u[3] for u in _u),
                        min(u[4] for u in _u), max(u[5] for u in _u), 0, 0, 0, *_dd, 'طرف‌حساب و نوع درآمد در منبع مشخص نیست'))
    _lc = collections.defaultdict(set)
    for _e, _a in q("SELECT own_event,lifecycle_action FROM line_event WHERE own_event IS NOT NULL AND lifecycle_action IS NOT NULL AND lifecycle_action<>'' GROUP BY 1,2"): _lc[_e].add(_a)
    V2_EXTRA['Canonical_Events'] = ([('v1_review_outcome', 'نتیجه بازبینی v2 (از کاندید v1)', 't'), ('lifecycle_actions', 'اقدام‌های چرخه‌عمر مشاهده‌شده', 't')],
                                    lambda r: ((EVENT_REVIEW[r[0]][0] if r[0] in EVENT_REVIEW else ''), ' ، '.join(sorted(_lc.get(r[0], [])))))
sheet('Canonical_Events', [('event_id', 'شناسه رویداد', 't'), ('origin', 'منشأ', 't'), ('title_fa', 'عنوان', 't'), ('family', 'خانواده', 't'), ('nature', 'ماهیت', 't'), ('definition', 'تعریف', 't'),
      ('governance_status', 'وضعیت حاکمیتی', 't'), ('gap_link', 'پیوند به شکاف v7.1', 't'), ('organizations', 'سازمان‌های مشاهده‌کننده', 't'), ('driver_lines', 'ردیف‌های محرک', 'n'), ('documents', 'اسناد', 'n'),
      ('debit_sum', 'جمع بدهکار ردیف‌های محرک', 'n'), ('credit_sum', 'جمع بستانکار ردیف‌های محرک', 'n'), ('first_date', 'اولین تاریخ مشاهده', 't'), ('last_date', 'آخرین تاریخ مشاهده', 't'),
      ('lines_confirmed', 'ردیف‌های CONFIRMED', 'n'), ('lines_provisional', 'ردیف‌های PROVISIONAL', 'n'), ('lines_new_candidate', 'ردیف‌های NEW_CANDIDATE', 'n'),
      ('share_person_code', 'سهم ردیف با CodePerson (شاهد بُعد شخص)', 'p'), ('share_org_unit', 'سهم ردیف با CodeVahed (فقط پایانه‌ها)', 'p'), ('share_source_activity', 'سهم ردیف با کد فعالیت منبع', 'p'),
      ('share_docs_with_bank', 'سهم اسناد با خط بانکی (بُعد بانک)', 'p'), ('share_contract_mention', 'سهم ردیف با اشاره متنی به قرارداد/صورت‌وضعیت (بُعد قرارداد)', 'p'), ('why_new', 'چرا رویداد موجود کافی نیست', 't')],
      ce_rows, title='فرهنگ رویداد: رویدادهای v7.1 مشاهده‌شده + کاندیدهای جدید TT-NE',
      note='بُعد پروژه در منبع وجود ندارد (ستون‌های پروژه/قرارداد در Sanad نیست) → Unknown. سهم‌ها شواهد مشاهده‌ای‌اند نه قاعده الزامی. FE-xx بازتعریف نشده است؛ عنوان/تعریف از v7.1 خوانده شده است.',
      widths={'title_fa': 44, 'definition': 56, 'why_new': 56, 'governance_status': 36, 'organizations': 24})

# ----------------------------------------------------------------------------------------------- 7 Event_Mapping (rule-level)
_EMSQL = (lambda t: t.replace("e.rule_id,min(e.basis)", "e.rule_id||CASE WHEN coalesce(e.lifecycle_action,'')='' THEN '' ELSE ' ['||e.lifecycle_action||']' END,min(e.basis)")) if V2 else (lambda t: t)
em = q(_EMSQL("""SELECT e.org,e.fy,e.role,coalesce(e.own_event,'—'),e.outcome,e.conf,e.rule_id,min(e.basis),count(*),count(DISTINCT e.doc_key),sum(e.amount_dr),sum(e.amount_cr),sum(e.review),min(e.evidence_n),max(e.evidence_n)
         FROM line_event e GROUP BY 1,2,3,4,5,6,7 ORDER BY 1,2,3,4"""))
EM_ROWS = [(o, y, role, ev, oc, cf, rid, basis, n, nd, dr, cr, 'بله' if rv else 'خیر', f'{e1}..{e2}', 'شواهد: زیرحساب منبع + شرح همان سطر؛ قاعده در scripts/taxi_terminals_1404_1405/rules.py و 04_classify_events.py') for o, y, role, ev, oc, cf, rid, basis, n, nd, dr, cr, rv, e1, e2 in em]
sheet('Event_Mapping', [('organization', 'سازمان', 't'), ('fiscal_year', 'سال', 't'), ('line_role', 'نقش سطر', 't'), ('event_id', 'رویداد (شاهد خود سطر)', 't'), ('outcome', 'نتیجه', 't'), ('confidence', 'اطمینان', 't'),
      ('matching_rule', 'قاعده تطبیق (کلید)', 't'), ('example_basis', 'مبنای تطبیق (نمونه)', 't'), ('lines', 'ردیف‌ها', 'n'), ('documents', 'اسناد', 'n'), ('debit_sum', 'جمع بدهکار', 'n'), ('credit_sum', 'جمع بستانکار', 'n'),
      ('review_required', 'بازبینی لازم', 't'), ('evidence_count', 'تعداد شاهد مستقل', 't'), ('explanation', 'توضیح', 't')],
      EM_ROWS, title='نگاشت تراکنش به رویداد (تجمیع بر اساس قاعده؛ نگاشت ردیف‌به‌ردیف در machine_readable/event_mapping_lines.csv)',
      note='خطوط COMPONENT (بانک/تنخواه/طرف حساب) رویداد سند را به ارث می‌برند و جداگانه به‌عنوان رخداد مستقل شمرده نمی‌شوند. برای مبالغ رویدادی فقط ردیف‌های DRIVER را جمع بزنید تا دوباره‌شماری نشود.',
      widths={'matching_rule': 26, 'example_basis': 44, 'explanation': 40})

# ----------------------------------------------------------------------------------------------- 8 Event_CC_Matrix
mx = q("""SELECT e.own_event,c.cc_id,c.cc_status,count(*),count(DISTINCT e.doc_key),sum(s.bed),sum(s.bes),min(s.date),max(s.date),count(DISTINCT s.fy||s.org)
         FROM line_cc c JOIN line_event e ON e.sid=c.sid JOIN sanad s ON s.sid=c.sid WHERE c.eligible=1 AND e.own_event IS NOT NULL GROUP BY 1,2,3 ORDER BY 1,4 DESC""")
ev_cc_count = collections.defaultdict(lambda: collections.defaultdict(set))
for ev, dk, cc in q("SELECT e.own_event,e.doc_key,c.cc_id FROM line_cc c JOIN line_event e ON e.sid=c.sid WHERE c.eligible=1 AND e.own_event IS NOT NULL AND c.cc_id IS NOT NULL"):
    ev_cc_count[ev][dk].add(cc)
cc_ev = collections.defaultdict(set)
for ev, dk, cc in q("SELECT e.own_event,e.doc_key,c.cc_id FROM line_cc c JOIN line_event e ON e.sid=c.sid WHERE c.eligible=1 AND e.own_event IS NOT NULL AND c.cc_id IS NOT NULL"):
    cc_ev[cc].add(ev)
MX_ROWS = []
def title_of(ev): return (FE.get(ev) or {}).get('title') or (TT_EVENTS.get(ev) or ('',))[0]
def cc_title(c):
    if c is None: return ''
    return CC[c]['title'] if c in CC else (NEW_CC[c]['title'] if c in NEW_CC else '')
for ev, cc, st, n, nd, dr, cr, d1, d2, ny in mx:
    per_doc = [len(v) for v in ev_cc_count[ev].values()] or [0]
    obs_ev_cc = f'{min(per_doc)}..{max(per_doc)}'
    strength = 'قوی (بیش از ۱۰ سند)' if nd > 10 else ('متوسط (۳ تا ۱۰ سند)' if nd >= 3 else 'ضعیف (کمتر از ۳ سند)')
    prop = '0..N' if max(per_doc) > 1 else '0..1'
    MX_ROWS.append((ev, title_of(ev), cc or '—', cc_title(cc), st, n, nd, dr - cr, d1, d2, strength, 'OBSERVED — NOT AUTHORIZED (مشاهده‌شده؛ مجاز نیست)', obs_ev_cc, prop, 'Needs Decision',
                    len(cc_ev.get(cc, [])) if cc else 0))
sheet('Event_CC_Matrix', [('event_id', 'رویداد', 't'), ('event_title', 'عنوان رویداد', 't'), ('cc_id', 'مرکز هزینه (پیشنهادی/نامزد)', 't'), ('cc_title', 'عنوان مرکز هزینه', 't'), ('cc_status', 'وضعیت نگاشت', 't'),
      ('lines', 'ردیف‌ها', 'n'), ('documents', 'اسناد', 'n'), ('net_debit', 'خالص بدهکار', 'n'), ('first_date', 'اولین تاریخ', 't'), ('last_date', 'آخرین تاریخ', 't'), ('evidence_strength', 'قوت شواهد', 't'),
      ('governance', 'وضعیت حاکمیتی', 't'), ('Observed_Cardinality', 'کاردینالیتی مشاهده‌شده (CC در هر سند)', 't'), ('Proposed_Cardinality', 'کاردینالیتی پیشنهادی', 't'),
      ('Approved_Cardinality', 'کاردینالیتی مصوب', 't'), ('events_for_this_cc', 'تعداد رویدادهای مشاهده‌شده برای این CC', 'n')],
      MX_ROWS, title='ماتریس شواهد رویداد × مرکز هزینه',
      note='کاردینالیتی مشاهده‌شده هرگز مصوب نمی‌شود. ستون Approved_Cardinality عمداً «Needs Decision» است. فقط ردیف‌های دارای مرکز هزینهٔ تعیین‌شده (نه MULTIPLE/INSUFFICIENT) وارد این ماتریس می‌شوند.', widths={'event_title': 40, 'cc_title': 40, 'governance': 30})

# ----------------------------------------------------------------------------------------------- 9 Cost_Center_Mapping
cm = q("""SELECT c.org,c.fy,c.cc_status,coalesce(c.cc_id,'—'),c.alt_ccs,coalesce(c.activity_id,''),coalesce(c.source_markaz,''),c.rule_id,min(c.basis),c.conf,count(*),count(DISTINCT c.doc_key),sum(s.bed),sum(s.bes)
         FROM line_cc c JOIN sanad s ON s.sid=c.sid GROUP BY 1,2,3,4,5,6,7,8,10 ORDER BY 1,2,3,11 DESC""")
CM_ROWS = [(o, y, st, cc, cc_title(cc) if cc != '—' else '', alt, act, mz, rid, basis, cf, n, nd, dr, cr, 'خیر' if st == 'CC_NOT_APPLICABLE' else 'بله') for o, y, st, cc, alt, act, mz, rid, basis, cf, n, nd, dr, cr in cm]
sheet('Cost_Center_Mapping', [('organization', 'سازمان', 't'), ('fiscal_year', 'سال', 't'), ('cc_status', 'وضعیت', 't'), ('cc_id', 'مرکز هزینه', 't'), ('cc_title', 'عنوان', 't'), ('alternative_ccs', 'جایگزین‌ها', 't'),
      ('activity_id', 'شناسه فعالیت', 't'), ('source_activity_code', 'کد فعالیت/مرکز منبع (CodeMarkaz) — فقط شاهد', 't'), ('rule_id', 'قاعده', 't'), ('basis', 'مبنا', 't'), ('confidence', 'اطمینان', 't'),
      ('lines', 'ردیف‌ها', 'n'), ('documents', 'اسناد', 'n'), ('debit_sum', 'بدهکار', 'n'), ('credit_sum', 'بستانکار', 'n'), ('review_required', 'بازبینی لازم', 't')],
      CM_ROWS, title='نگاشت مرکز هزینه (تجمیع بر اساس قاعده؛ ردیف‌به‌ردیف در machine_readable/cost_center_mapping_lines.csv)',
      note='EXACT_EXISTING_CC و VALIDATED_EXISTING_CC تعمداً صفرند: هیچ crosswalk مصوب و هیچ مرجع اعتبارسنجی وجود ندارد. درآمد، بانک، بدهی و اسناد افتتاحیه/اختتامیه CC_NOT_APPLICABLE‌اند.', widths={'cc_title': 44, 'basis': 50, 'alternative_ccs': 22})

# ----------------------------------------------------------------------------------------------- 10 New_CC_Proposals
NP_ROWS = []
for cid, d in NEW_CC.items():
    r = q("""SELECT count(*),count(DISTINCT c.doc_key),sum(s.bed-s.bes),min(s.date),max(s.date) FROM line_cc c JOIN sanad s ON s.sid=c.sid WHERE c.cc_id=?""", cid)[0]
    alt = q("SELECT count(*),sum(s.bed-s.bes) FROM line_cc c JOIN sanad s ON s.sid=c.sid WHERE c.alt_ccs LIKE ? AND (c.cc_id IS NULL OR c.cc_id<>?)", f'%{cid}%', cid)[0]
    evs = [x[0] for x in q("SELECT e.own_event FROM line_cc c JOIN line_event e ON e.sid=c.sid WHERE c.cc_id=? AND e.own_event IS NOT NULL GROUP BY 1 ORDER BY count(*) DESC LIMIT 6", cid)]
    acts = sorted({v[0] + ' ' + v[1] for k, v in MZ.items() if v[3] == cid}) if d['orgs'] == 'Taxi' else ['ACT-TM-01 (کد منبع 008) — به‌عنوان جایگزین']
    NP_ROWS.append((cid, d['title'], d['definition'], d['domain'], d['why_existing_insufficient'], d['orgs'], ' | '.join(acts), ' ، '.join(evs), r[0] or 0, r[1] or 0, r[2] or 0, f'{alt[0] or 0} ردیف / {alt[1] or 0:,} (به‌عنوان جایگزین)', d['owner'], d['alternatives'], d['overlap'],
                    'آیا مرکز مستقل لازم است یا زیرفعالیت مرکز موجود؟ مالکیت مرکز؟ شمول سایر سازمان‌ها؟', 'PROPOSED — نیازمند تصمیم؛ در master شهرداری وارد نشده است'))
sheet('New_CC_Proposals', [('provisional_id', 'شناسه موقت', 't'), ('title_fa', 'عنوان پیشنهادی', 't'), ('definition', 'تعریف', 't'), ('parent_domain', 'حوزه خدمت والد', 't'), ('why_existing_insufficient', 'چرا مراکز موجود کافی نیستند', 't'),
      ('organizations', 'سازمان', 't'), ('source_activities', 'فعالیت‌های منبع پشتیبان', 't'), ('top_events', 'رویدادهای پرتکرار', 't'), ('supporting_lines', 'ردیف‌های مستقیماً نگاشت‌شده', 'n'),
      ('supporting_docs', 'اسناد', 'n'), ('net_debit', 'خالص بدهکار', 'n'), ('as_alternative', 'ردیف‌هایی که به‌عنوان جایگزین ذکر شده', 't'), ('owner', 'متولی بالقوه', 't'), ('alternatives_considered', 'گزینه‌های موجود بررسی‌شده', 't'),
      ('overlap_risk', 'ریسک هم‌پوشانی', 't'), ('decisions_required', 'تصمیم‌های لازم کارشناسی', 't'), ('governance_status', 'وضعیت حاکمیتی', 't')],
      NP_ROWS, title='مراکز هزینه کاندید جدید (فضای نام موقت TTCC-P)',
      note='هیچ کد CC-xxx جدیدی به master شهرداری افزوده نشده است. TTCC-P-03 مستقیم به هزینه‌ای نگاشت نشده و فقط به‌عنوان جایگزین (ریسک هم‌پوشانی با CC-403) ثبت است. ملاک ایجاد مرکز صرفاً مالکیت سازمانی نیست.', widths={'definition': 56, 'why_existing_insufficient': 60, 'title_fa': 44, 'source_activities': 50})

# ----------------------------------------------------------------------------------------------- 11 Activity_Service_Map
AS_ROWS = []
mzrows = q("""SELECT s.markaz,min(s.f1),count(*),sum(case when s.fy='1404' then s.bed-s.bes else 0 end),sum(case when s.fy='1405' then s.bed-s.bes else 0 end) FROM sanad s JOIN doc_class d ON d.doc_key=s.doc_key
              WHERE s.org='Taxi' AND s.markaz IS NOT NULL AND s.markaz<>'NULL' AND d.kind='REGULAR' AND s.kol IN ('611','612','613') GROUP BY 1 ORDER BY 1""")
for mz, f1, n, a, b in mzrows:
    if mz in MZ:
        aid, at, kind, cc, alts, cf, note = MZ[mz]
        AS_ROWS.append((aid, at, 'Taxi', mz, f1, n, a, b, cc, cc_title(cc), ' ، '.join(alts), {'OLD': 'PROVISIONAL_EXISTING_CC', 'NEW': 'NEW_CC_CANDIDATE', 'MULTI': 'MULTIPLE_CC_CANDIDATES'}[kind], cf, note, 'کد منبع حفظ شد؛ برابر CC فرض نشد'))
    else:
        AS_ROWS.append((('ACT-TX-CATCHALL' if mz == '100' else 'ACT-TX-??'), 'کد عمومی/نامعتبر منبع: «ارائه خدمات رفاهی به پرسنل و خانواده‌ها»' if mz == '100' else '—', 'Taxi', mz, f1, n, a, b, '—', '', '', 'EVENT_BASED_FALLBACK' if mz == '100' else 'UNMAPPED', 'LOW',
                        'پر کاربردترین کد منبع؛ شامل کارمزد بانکی، برون‌سپاری و رفاه — تعیین مرکز هزینه از رویداد انجام شد', ''))
for mz, f1, n, a, b in q("""SELECT s.markaz,min(s.f1),count(*),sum(case when s.fy='1404' then s.bed-s.bes else 0 end),sum(case when s.fy='1405' then s.bed-s.bes else 0 end) FROM sanad s JOIN doc_class d ON d.doc_key=s.doc_key
              WHERE s.org='Terminals' AND s.markaz IS NOT NULL AND s.markaz<>'NULL' AND d.kind='REGULAR' GROUP BY 1"""):
    AS_ROWS.append(('ACT-TM-01', 'بهبود نگهداری و تعمیرات و تجهیز پایانه‌ها', 'Terminals', mz, f1, n, a, b, 'CC-403', cc_title('CC-403'), 'TTCC-P-03', 'PROVISIONAL_EXISTING_CC', 'MEDIUM', 'تنها کد فعالیت منبع در پایانه‌هاست', ''))
# facilities (Terminals): organizational unit evidence
for seg, nm in (('001', 'پایانه کاوه'), ('002', 'پایانه صفه'), ('003', 'پایانه زاینده‌رود'), ('004', 'پایانه جی'), ('007', 'پایانه صمدیه'), ('005', 'دفتر مرکزی'), ('008', 'دفتر کار طالقانی'), ('010', 'اندیشه'), ('006', 'انبار سازمان')):
    n, a, b = q("""SELECT count(*),sum(case when fy='1404' then bed-bes else 0 end),sum(case when fy='1405' then bed-bes else 0 end) FROM sanad WHERE org='Terminals' AND substr(vahed,1,3)=?""", seg)[0]
    AS_ROWS.append(('ORGUNIT-TM-' + seg, nm, 'Terminals', 'CodeVahed ' + seg + '-xxx-xxx', 'بخش اول CodeVahed (واحد سازمانی/تأسیسات) — بُعد واحد سازمانی نه مرکز هزینه', n, a or 0, b or 0, '—', '', '', 'ORG_UNIT_DIMENSION', 'MEDIUM', 'راستی‌آزمایی با NameVahed: %d نام واحد متمایز با همین بخش اول (نام‌ها در فایل محدود)' % one("SELECT count(DISTINCT name_vahed) FROM sanad WHERE org='Terminals' AND substr(vahed,1,3)=?", seg), 'واحد سازمانی با مرکز هزینه یکی نیست'))
# 1405 service-audit evidence (read-only, existing)
svc = openpyxl.load_workbook(f'{ROOT}/data/deliverables/service_activity_coverage/revisions/1405-r20260922-service-coverage/service_activity_coverage_1405-r20260922_QA-remapped_v2.xlsx', read_only=True)
for r in svc['تطبیق_اصلاح‌شده_خدمات'].iter_rows(min_row=2, values_only=True):
    t = ' '.join(str(x) for x in r if x)
    owner = str(r[2] or '')
    if any(k in owner for k in ('تاکسیرانی', 'پایانه')) or ('تاکسی' in str(r[4] or '') or 'پایانه' in str(r[4] or '')):
        AS_ROWS.append(('SVC-1405:' + str(r[0]), str(r[4])[:150], 'Taxi/Terminals' if ('تاکسی' in owner and 'پایانه' in owner) else ('Taxi' if 'تاکسیرانی' in owner or 'تاکسی' in str(r[4]) else 'Terminals'), '—', 'شناسنامه خدمات ۱۴۰۵ (ممیزی موجود)', None, None, None, r[8], r[9], ' ، '.join(x for x in (r[13], r[14]) if x), r[10], r[11], 'منبع: ممیزی خدمات ۱۴۰۵ (مخزن)', 'شاهد تکمیلی؛ بدون مبلغ'))
svc.close()
if V2:
    AS_ROWS = [list(r) for r in AS_ROWS]
    for r in AS_ROWS:
        if r[11] == 'MULTIPLE_CC_CANDIDATES' and r[8]:
            r[10] = ' ، '.join(x for x in [r[8], r[10]] if x); r[8] = ''; r[9] = ''
    _st = collections.defaultdict(lambda: [0, 0, 0, 0])
    for _o, _m, _s, _n in q("SELECT org,source_markaz,cc_status,count(*) FROM line_cc WHERE eligible=1 AND source_markaz IS NOT NULL GROUP BY 1,2,3"):
        _a = _st[(_o, _m)]; _a[0] += _n
        if _s in ('PROVISIONAL_EXISTING_CC', 'NEW_CC_CANDIDATE'): _a[1] += _n
        elif _s == 'MULTIPLE_CC_CANDIDATES': _a[2] += _n
        elif _s == 'INSUFFICIENT_INFORMATION': _a[3] += _n
    V2_EXTRA['Activity_Service_Map'] = ([('eligible_lines', 'ردیف‌های واجد شرایط تخصیص', 'n'), ('selected_lines', 'با مرکز انتخاب‌شده', 'n'), ('multiple_lines', 'MULTIPLE (بدون مرکز انتخاب‌شده)', 'n'), ('insufficient_lines', 'INSUFFICIENT', 'n'), ('non_eligible_lines', 'ردیف هزینه‌ای غیرمحرک (COMPONENT مانند کارمزد)', 'n')],
                                        lambda r: ((_st[(r[2], r[3])][0], _st[(r[2], r[3])][1], _st[(r[2], r[3])][2], _st[(r[2], r[3])][3], max(0, (r[5] or 0) - _st[(r[2], r[3])][0])) if (r[2], r[3]) in _st else (None,) * 5))
sheet('Activity_Service_Map', [('activity_id', 'شناسه فعالیت', 't'), ('activity_title', 'عنوان فعالیت/خدمت/واحد', 't'), ('organization', 'سازمان', 't'), ('source_code', 'کد منبع', 't'), ('source_title', 'عنوان منبع (Field1)', 't'),
      ('lines', 'ردیف‌های هزینه', 'n'), ('net_debit_1404', 'خالص بدهکار ۱۴۰۴', 'n'), ('net_debit_1405', 'خالص بدهکار ۱۴۰۵ (ناقص)', 'n'), ('cc_id', 'مرکز هزینه (پیشنهادی)', 't'), ('cc_title', 'عنوان', 't'),
      ('alternatives', 'جایگزین‌ها', 't'), ('status', 'وضعیت', 't'), ('confidence', 'اطمینان', 't'), ('note', 'یادداشت', 't'), ('caveat', 'احتیاط', 't')],
      AS_ROWS, title='نقشه فعالیت/خدمت: کد فعالیت منبع، واحدهای سازمانی پایانه‌ها و شواهد ممیزی خدمات ۱۴۰۵',
      note='کد فعالیت منبع (CodeMarkaz) هزینه‌ها در تاکسیرانی روی ۹۹٫۸٪ ردیف‌های هزینه موجود است؛ کد ۱۰۰ عمومی است. در پایانه‌ها بُعد واحد (CodeVahed) هویت پایانه را می‌دهد.', widths={'activity_title': 50, 'source_title': 44, 'cc_title': 40, 'note': 40})

# ----------------------------------------------------------------------------------------------- 12/13 KPI
kc = q('SELECT kpi_id,org,title_fa,title_en,category,activity,cost_centers,purpose,formula,numerator,denominator,unit,period,financial_fields,operational_fields,method,filters,exclusions,data_availability,calc_status,governance,confidence,notes,metrics FROM kpi_catalogue ORDER BY org,kpi_id')
if V2:
    _kx = {r[0]: r[1:] for r in q('SELECT kpi_id,basis_type,v1_status,v2_verdict,v2_note FROM kpi_catalogue')}
    V2_EXTRA['KPI_Catalogue'] = ([('basis_type', 'نوع مبنا (FLOW/STOCK/RATIO)', 't'), ('v1_status', 'وضعیت v1', 't'), ('v2_verdict', 'قضاوت v2', 't'), ('v2_note', 'یادداشت v2', 't')], lambda r: _kx.get(r[0], ('', '', '', '')))
if V21:
    _kx = {r[0]: r[1:] for r in q('SELECT kpi_id,basis_type,v1_status,v2_verdict,v2_note,definition_status,calculation_status,verification_status,governance_status FROM kpi_catalogue')}
    V2_EXTRA['KPI_Catalogue'] = ([('basis_type', 'نوع مبنا (FLOW/STOCK/RATIO)', 't'), ('v1_status', 'وضعیت v1', 't'), ('v2_verdict', 'قضاوت v2', 't'), ('v2_note', 'یادداشت v2', 't'),
        ('definition_status', 'Definition_Status', 't'), ('calculation_status', 'Calculation_Status', 't'), ('verification_status', 'Verification_Status', 't'), ('governance_status', 'Governance_Status', 't')], lambda r: _kx.get(r[0], ('',) * 8))
sheet('KPI_Catalogue', [('kpi_id', 'شناسه KPI', 't'), ('organization', 'سازمان', 't'), ('title_fa', 'عنوان فارسی', 't'), ('title_en', 'English technical name', 't'), ('category', 'دسته', 't'), ('activity', 'فعالیت مرتبط', 't'),
      ('cost_centers', 'مراکز هزینه مرتبط', 't'), ('purpose', 'هدف', 't'), ('formula', 'فرمول', 't'), ('numerator', 'صورت', 't'), ('denominator', 'مخرج', 't'), ('unit', 'واحد اندازه‌گیری', 't'), ('period', 'دوره', 't'),
      ('financial_fields', 'فیلدهای مالی منبع', 't'), ('operational_fields', 'فیلدهای عملیاتی لازم', 't'), ('method', 'روش محاسبه', 't'), ('filters', 'فیلترها', 't'), ('exclusions', 'استثناها', 't'),
      ('data_availability', 'دسترس‌پذیری داده', 't'), ('calc_status', 'وضعیت محاسبه', 't'), ('governance', 'حاکمیت', 't'), ('confidence', 'اطمینان', 't'), ('notes', 'یادداشت', 't'), ('metric_ids', 'شاخص‌های پایه در Source (metric_values)', 't')],
      kc, title='کاتالوگ KPI (تعریف؛ نه نتیجه)',
      note='هیچ مخرج عملیاتی (تعداد تاکسی فعال، مسافر، مساحت، شکایت، درخواست) در منبع نیست و تخمین زده نشد. هدف‌گذاری KPI وجود ندارد.', widths={'title_fa': 44, 'formula': 44, 'purpose': 30, 'notes': 44, 'data_availability': 34})
kr = q('SELECT r.kpi_id,r.org,r.fy,r.window,r.numerator_name,r.numerator,r.denominator_name,r.denominator,r.value,r.unit,r.status,r.caveat,c.title_fa FROM kpi_results r JOIN kpi_catalogue c ON c.kpi_id=r.kpi_id ORDER BY r.org,r.kpi_id,r.fy,r.window')
if V21:
    _kv = {(r[0], r[1], r[2]): r[3:] for r in q('SELECT kpi_id,fy,window,calculation_status,verification_status FROM kpi_results')}
    V2_EXTRA['KPI_Results'] = ([('calculation_status', 'Calculation_Status', 't'), ('verification_status', 'Verification_Status', 't')], lambda r: _kv.get((r[0], r[3], r[4]), ('', '')))
sheet('KPI_Results', [('kpi_id', 'KPI', 't'), ('title_fa', 'عنوان', 't'), ('organization', 'سازمان', 't'), ('fiscal_year', 'سال', 't'), ('window', 'پنجره', 't'), ('numerator_name', 'صورت', 't'), ('numerator', 'مقدار صورت', 'n'),
      ('denominator_name', 'مخرج', 't'), ('denominator', 'مقدار مخرج', 'n'), ('value', 'مقدار KPI (نسبت/واحد)', 'd'), ('unit', 'واحد', 't'), ('status', 'وضعیت محاسبه', 't'), ('caveat', 'احتیاط', 't')],
      [(r[0], r[12], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9], r[10], r[11]) for r in kr], title='نتایج KPI — فقط آنچه از منبع پشتیبانی می‌شود',
      note='سطرهای دارای مخرج تهی «صورت کسر» اند و مقدار KPI ندارند. نسبت‌ها بدون واحد؛ مبالغ در واحد منبع (احتمالاً ریال، تأییدنشده). پنجره WINDOW = ماه‌های مشترک؛ ALL_AVAILABLE ۱۴۰۵ ناقص است.', widths={'title_fa': 44, 'caveat': 44})
bt = q('SELECT fy,window,facility_code,facility_name,billed,collected,n_units FROM billed_by_terminal ORDER BY fy,window,billed DESC')
sheet('KPI_Terminal_Breakdown', [('fiscal_year', 'سال', 't'), ('window', 'پنجره', 't'), ('facility_code', 'کد بخش اول CodeVahed', 't'), ('facility_name', 'پایانه/واحد', 't'), ('billed', 'مطالبه صادرشده (TM-K02)', 'n'),
      ('collected', 'وصول', 'n'), ('n_units', 'واحدهای دارای مطالبه', 'n')], bt, title='TM-K02 — مطالبه درآمد به تفکیک پایانه', note='نام پایانه با NameVahed راستی‌آزمایی شد؛ تفکیک هزینه به پایانه به‌دلیل ثبت با کد دفتر مرکزی ممکن نیست.')

# ----------------------------------------------------------------------------------------------- 14 Comparison
pc = q('SELECT org,fy,first_date,last_date,last_month,n_docs,n_lines,window_months,window_rule,warning FROM period_coverage ORDER BY org,fy')
sheet('Period_Coverage', [('organization', 'سازمان', 't'), ('fiscal_year', 'سال', 't'), ('first_date', 'اولین تاریخ', 't'), ('last_date', 'آخرین تاریخ واقعی', 't'), ('last_month', 'ماه آخر', 'n'), ('n_docs', 'اسناد', 'n'),
      ('n_lines', 'ردیف‌ها', 'n'), ('window_months', 'پنجره مقایسه‌پذیر (ماه‌ها)', 't'), ('window_rule', 'قاعده پنجره', 't'), ('warning', 'هشدار', 't')], pc,
      title='پوشش دوره‌ای هر منبع', note='قاعده پنجره یک شاخص تراکم ثبت است نه اثبات کامل بودن داده.', widths={'warning': 80, 'window_rule': 50})
ms = q('SELECT org,fy,month,n_docs_regular,n_lines,revenue_own,expense_own,billed,collected,density_vs_1404 FROM monthly_series ORDER BY org,fy,month')
sheet('Monthly_Series', [('organization', 'سازمان', 't'), ('fiscal_year', 'سال', 't'), ('month', 'ماه', 't'), ('docs_regular', 'اسناد منظم', 'n'), ('lines', 'ردیف‌ها', 'n'), ('revenue_own', 'درآمد ثبت‌شده (۴۱۳/۸۱۲)', 'n'),
      ('expense_own', 'هزینه ثبت‌شده (۶۱۱–۶۱۳ بدون استهلاک)', 'n'), ('billed', 'مطالبه (پایانه‌ها)', 'n'), ('collected', 'وصول (پایانه‌ها)', 'n'), ('density_vs_1404', 'نسبت تراکم ثبت به همان ماه ۱۴۰۴', 'p')], ms,
      title='سری ماهانه (برای قضاوت درباره کامل بودن ماه‌های ۱۴۰۵)')
cmp_ = q('SELECT org,metric_id,title_fa,v1404_full,v1404_window,v1405_window,v1405_all_available,window_months,change_pct_window,comparability,note FROM comparison ORDER BY org,metric_id')
sheet('Comparison_1404_1405', [('organization', 'سازمان', 't'), ('metric_id', 'شاخص', 't'), ('title_fa', 'عنوان', 't'), ('v1404_full_year', '۱۴۰۴ سال کامل', 'n'), ('v1404_window', '۱۴۰۴ پنجره مشترک', 'n'),
      ('v1405_window', '۱۴۰۵ پنجره مشترک', 'n'), ('v1405_all_available', '۱۴۰۵ همه داده موجود (ناقص — فقط اطلاعات)', 'n'), ('window_months', 'ماه‌های پنجره', 't'), ('change_pct_window', 'تغییر پنجره (٪)', 'd'),
      ('comparability', 'قابلیت مقایسه', 't'), ('note', 'توضیح', 't')],
      cmp_, title='مقایسه ۱۴۰۴ و ۱۴۰۵ با آگاهی از ناقص بودن دوره',
      note='درصد رشد سالانه محاسبه نشده است. «تغییر پنجره» فقط ماه‌های مشترک را مقایسه می‌کند و می‌تواند ناشی از تغییر ثبت، تأخیر ثبت یا ترکیب فعالیت باشد، نه عملکرد. ستون همه‌داده‌ی ۱۴۰۵ را با ۱۴۰۴ کامل مقایسه نکنید.', widths={'title_fa': 52, 'note': 60})

# ----------------------------------------------------------------------------------------------- 15 Exceptions
EX = []
for dk, org, fy, oc, bt_, reason, drv, conf, comp in q("SELECT doc_key,org,fy,outcome,bed_total,reason,driver_events,conf,composite FROM doc_class WHERE outcome IN ('AMBIGUOUS_EVENT','COMPOSITE_TRANSACTION','PENDING_IDENTIFICATION') ORDER BY bed_total DESC"):
    EX.append((dk, org, fy, 'EVENT', oc, bt_, reason, drv, 'کمیته رویداد'))
for dk, org, fy, n, a in q("SELECT c.doc_key,c.org,c.fy,count(*),sum(s.bed-s.bes) FROM line_cc c JOIN sanad s ON s.sid=c.sid WHERE c.cc_status='INSUFFICIENT_INFORMATION' GROUP BY 1,2,3 ORDER BY 5 DESC LIMIT 1500"):
    EX.append((dk, org, fy, 'COST_CENTER', 'INSUFFICIENT_INFORMATION', a, f'{n} ردیف هزینه‌ای بدون مرکز هزینه قابل‌دفاع', '', 'کمیته مرکز هزینه'))
for dk, org, fy, n, a in q("SELECT c.doc_key,c.org,c.fy,count(*),sum(s.bed-s.bes) FROM line_cc c JOIN sanad s ON s.sid=c.sid WHERE c.cc_status='MULTIPLE_CC_CANDIDATES' GROUP BY 1,2,3 ORDER BY 5 DESC LIMIT 1500"):
    EX.append((dk, org, fy, 'COST_CENTER', 'MULTIPLE_CC_CANDIDATES', a, f'{n} ردیف با چند مرکز هزینه نامزد', '', 'کمیته مرکز هزینه'))
for org, fy, dk, n in q("SELECT org,fy,doc_key,count(*) FROM sanad GROUP BY doc_key,date,des,hcode,bed,bes,sharh,f1,person HAVING count(*)>1 ORDER BY 4 DESC"):
    EX.append((dk, org, fy, 'SOURCE_DUPLICATE_CANDIDATE', 'REVIEW', None, f'{n} ردیف با همه ویژگی‌های کلیدی یکسان؛ حذف نشد', '', 'سرپرست داده منبع'))
sheet('Exceptions', [('doc_key', 'شناسه سند', 't'), ('organization', 'سازمان', 't'), ('fiscal_year', 'سال', 't'), ('queue', 'صف', 't'), ('outcome', 'نتیجه/وضعیت', 't'), ('amount', 'مبلغ (بدهکار سند یا خالص)', 'n'),
      ('reason', 'دلیل عدم حل/ارجاع', 't'), ('events', 'رویدادهای محرک', 't'), ('owner', 'مرجع تصمیم', 't')], EX,
      title='صف استثناها: اسناد مبهم/ترکیبی، ردیف‌های بدون مرکز هزینه، تکرار کاندید',
      note='صف CC حداکثر ۱٬۵۰۰ سند پرمبلغ هر نوع را نشان می‌دهد؛ فهرست کامل ردیف‌به‌ردیف در machine_readable/exceptions_queue.csv است.', widths={'reason': 60, 'events': 30})

# ----------------------------------------------------------------------------------------------- 16 Committee_Decisions
nTT = {r[0]: r[1] for r in q("SELECT own_event,count(DISTINCT doc_key) FROM line_event WHERE own_event LIKE 'TT-NE-%' AND role IN ('DRIVER','SETTLEMENT') GROUP BY 1")}
CD = []
def cd(i, topic, question, options, evidence, impact, rec):
    CD.append((i, topic, question, options, evidence, impact, rec, 'OPEN', '', ''))
cd('CD-01', 'مبنای حسابداری پایانه‌ها', 'آیا هزینه‌های ثبت‌شده در بدهکار ۱۱۳-۱ (هزینه تحمیل‌شده به شهرداری) هزینه سازمان پایانه‌هاست، یا پرداخت از طرف شهرداری با مطالبه بازپرداخت؟ و آیا درآمد (بستانکار ۲۱۱-۱) متعلق به شهرداری است؟', 'الف) سازمان عامل (agent)؛ ب) سازمان با صورت مالی مستقل', 'Document_Lineage؛ Source_Profile؛ KPI TM-K01/K05', 'تعیین عددی بودن KPI هزینه/درآمد پایانه‌ها', 'تأیید توسط حسابداری سازمان؛ تا آن زمان KPIهای پایانه PARTIALLY_CALCULABLE')
cd('CD-02', 'واحد پول', 'واحد پولی فایل‌های Sanad (ریال/تومان) را تأیید کنید.', 'ریال / تومان', 'Source_Profile (بدون تصریح)', 'همه مبالغ', 'تأیید کتبی سرپرست داده')
cd('CD-03', 'مدل داده درآمد', 'درآمدها مرکز درآمد/مرکز خدمت دریافت کنند یا بُعد جدا؟ فعلاً CC_NOT_APPLICABLE.', 'مرکز درآمد جدا / بُعد منبع درآمد / مرکز هزینه', 'Cost_Center_Mapping (درآمد = CC_NOT_APPLICABLE)', 'ماتریس رویداد-مرکز برای FE-60 و TT-NE-01/02/15', 'ثبت بُعد «منبع درآمد» جدا از مرکز هزینه')
cd('CD-04', 'مرکز هزینه جدید TTCC-P-01', 'ساماندهی/صدور مجوز/نظارت تاکسیرانی: مرکز مستقل یا زیرفعالیت CC-406؟', 'مرکز جدید / زیرمجموعه CC-406 / CC-1502', 'New_CC_Proposals؛ ممیزی ۱۴۰۵', f"{q('SELECT count(*) FROM line_cc WHERE cc_id=?', 'TTCC-P-01')[0][0]} ردیف", 'ایجاد مرکز مستقل (حوزه حمل‌ونقل)')
cd('CD-05', 'مرکز هزینه جدید TTCC-P-02', 'سرویس مدارس/دانش‌آموزان استثنایی/معلولین (عاملیتی با منبع مصرف‌معین): مرکز مستقل؟', 'مرکز جدید / CC-406 / CC-904', 'New_CC_Proposals', f"{q('SELECT count(*) FROM line_cc WHERE cc_id=?', 'TTCC-P-02')[0][0]} ردیف", 'ایجاد مرکز مستقل')
cd('CD-06', 'مرکز هزینه TTCC-P-03', 'مدیریت و اجاره‌دهی پایانه‌ها: توسعه شمول CC-403 یا مرکز جدید؟', 'گسترش CC-403 / مرکز جدید', 'New_CC_Proposals؛ ریسک هم‌پوشانی', f"{q('SELECT count(*) FROM line_cc WHERE alt_ccs LIKE ?', '%TTCC-P-03%')[0][0]} ردیف (جایگزین)", 'تصمیم همراه با CD-03')
cd('CD-07', 'تأیید crosswalk فعالیت منبع', 'کدهای فعالیت منبع (CodeMarkaz) تاکسیرانی ← مراکز هزینه: تأیید، اصلاح یا رد؟', 'تأیید فهرست Activity_Service_Map / اصلاح', 'Activity_Service_Map', f"{q('SELECT count(*) FROM line_cc WHERE cc_status=?', 'PROVISIONAL_EXISTING_CC')[0][0]} ردیف PROVISIONAL", 'تأیید پس از بازبینی ۳۳ کد')
cd('CD-08', 'کد منبع ۱۰۰ تاکسیرانی', 'کد ۱۰۰ («خدمات رفاهی») عملاً کد عمومی است؛ اصلاح در منبع لازم است یا نادیده گرفتن؟', 'اصلاح منبع (Source Correction) / نادیده', 'Cost_Center_Mapping', f"{q('SELECT count(*) FROM sanad WHERE org=? AND markaz=?', 'Taxi', '100')[0][0]} ردیف", 'درخواست تصحیح منبع')
for ev, nd in sorted(nTT.items()):
    t = TT_EVENTS[ev]
    cd('CD-EV-' + ev[-2:], f'کاندید رویداد {ev}', f'پذیرش «{t[0]}» به‌عنوان رویداد canonical جدید (یا ادغام با رویداد موجود)؟', 'پذیرش / ادغام با FE موجود / رد', 'Canonical_Events؛ Event_Mapping', f'{nd} سند', 'بازبینی ' + (f'(پیوند {t[4]})' if t[4] else ''))
cd('CD-FE-60', 'FE-60 گسترده', 'FE-60 «وصول بهای خدمات، کرایه اماکن و غرفه‌ها» دو ماهیت (بهای خدمات تاکسیرانی و اجاره غرفات پایانه) را یکجا دارد؛ تفکیک شود؟', 'ادغام / تفکیک بر اساس ADR-0009', 'Canonical_Events (FE-60)', 'بزرگ‌ترین رویداد درآمدی', 'تفکیک اگر مدارک/تأییدها متفاوت باشد')
cd('CD-CARD', 'کاردینالیتی', 'کاردینالیتی رویداد×مرکز/قرارداد/پروژه/شخص/بانک: همه Needs Decision.', '0..1 / 1..1 / 0..N / 1..N', 'Event_CC_Matrix (Observed و Proposed)', 'قواعد معتبرسازی آینده', 'تصمیم پس از CD-01..CD-08')
cd('CD-ACC', 'نگاشت حساب', 'نگاشت L4/L5 حساب‌های سازمان به حساب شهرداری و ۱۱۰ مورد برخورد کد: تأیید مرجع حسابداری.', 'تأیید / اصلاح', 'Account_Crosswalk', f"{q('SELECT count(*) FROM account_crosswalk WHERE match_level=?', 'L5')[0][0]} حساب L5", 'تأیید با مرجع حسابداری شهرداری')
cd('CD-GUAR', 'ضمانت‌نامه‌ها', 'ضمانت‌نامه و چک ضمانت شرکت‌های حمل‌ونقل (حساب انتظامی) با FE-15/FE-16 هم‌ارز است یا رویداد مستقل؟', 'FE-15/16 / رویداد جدید', 'Event_Mapping (MEMO-GUARANTEE)', f"{q('SELECT count(*) FROM doc_class WHERE rule_id=?', 'MEMO-GUARANTEE')[0][0]} سند", 'بازبینی')
cd('CD-PERIOD', 'ناقص بودن ۱۴۰۵', 'تأیید تاریخ برش داده‌های ۱۴۰۵ و دریافت نسخه کامل برای مقایسه سالانه.', '—', 'Period_Coverage؛ Monthly_Series', 'مقایسه ۱۴۰۴/۱۴۰۵', 'درخواست داده کامل‌تر')
cd('CD-OPS', 'داده عملیاتی KPI', 'ارائه ناوگان فعال، تعداد درخواست/پروانه، مساحت و مسافر پایانه‌ها، تعداد شکایت و بودجه سازمان‌ها.', '—', 'KPI_Catalogue', 'KPIهای REQUIRES_*', 'درخواست رسمی از دو سازمان')
sheet('Committee_Decisions', [('id', 'شناسه', 't'), ('topic', 'موضوع', 't'), ('question', 'پرسش تصمیم', 't'), ('options', 'گزینه‌ها', 't'), ('evidence', 'ارجاع شواهد', 't'), ('impact', 'دامنه/اثر', 't'),
      ('recommendation', 'توصیه مدل (غیرالزام‌آور)', 't'), ('status', 'وضعیت', 't'), ('decision_evidence', 'مدرک تصمیم', 't'), ('decided_by', 'تصمیم‌گیرنده', 't')], CD,
      title='موارد نیازمند تصمیم کارشناسی/کمیته', note='ستون‌های «مدرک تصمیم» و «تصمیم‌گیرنده» عمداً خالی‌اند؛ هیچ تصمیمی جعل نشده است.', widths={'question': 70, 'topic': 24, 'recommendation': 40, 'options': 34})

if V2: exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'v2_sheets.py'), encoding='utf8').read())
if V21: exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'v21_sheets.py'), encoding='utf8').read())
# ----------------------------------------------------------------------------------------------- 17 QA_Reconciliation (with live formulas)
wsq = wb.add_worksheet('QA_Reconciliation'); wsq.right_to_left()
wsq.write(0, 0, 'کنترل‌های QA (مستقل از پایپ‌لاین؛ شمارش مجدد از فایل‌های منبع)', F['title'])
if V21:
    from qa_registry_v21 import category_of, build_registry, summarize, CATS
    EMBED_IDS = [t['test_id'] for t in QA['tests']]
    hdr = ['Test ID', 'دسته', 'حوزه', 'منابع (جدول/شیت)', 'جمعیت ورودی', 'روش محاسبه', 'مقدار مورد انتظار', 'مقدار واقعی', 'نتیجه', 'جزئیات استثنا', 'دستور بازتولید / فرمول']
    wsq.write(1, 0, 'فقط تست‌های پیش از ساخت (PRE_BUILD) و بلوک فرمول در این شیت‌اند؛ تست‌های پس از ساخت و مونتاژ نهایی در QA_Test_Registry_v2.1.csv و financial_mapping_QA_v2.1.md هستند (روی فایل نهایی اجرا می‌شوند و نمی‌توانند درون آن باشند). مقدار ذخیره‌شده فرمول‌ها cached است.', F['warn'])
    for j, h in enumerate(hdr): wsq.write(2, j, h, F['h'])
    for j, w in enumerate((34, 22, 12, 34, 30, 60, 26, 40, 9, 60, 46)): wsq.set_column(j, j, w)
    for i, t in enumerate(QA['tests']):
        r = 3 + i
        for j, v in enumerate((t['test_id'], category_of(t), t['area'], t.get('sources') or 'tt_v21.sqlite + فایل‌های منبع', t.get('population') or 'ر.ک. روش', t['description'], t['expected'], t['actual'])): wsq.write(r, j, v, F['t'])
        wsq.write(r, 8, t['status'], F[{'PASS': 'pass_', 'REVIEW': 'rev', 'FAIL': 'fail'}[t['status']]]); wsq.write(r, 9, t['detail'], F['t']); wsq.write(r, 10, t.get('command') or 'TT_VARIANT=v21 python scripts/taxi_terminals_1404_1405/09_qa.py', F['t'])
elif V2:
    hdr = ['Test ID', 'حوزه', 'منابع (جدول/شیت)', 'جمعیت ورودی', 'روش محاسبه', 'مقدار مورد انتظار', 'مقدار واقعی', 'نتیجه', 'جزئیات استثنا', 'دستور بازتولید / فرمول']
    wsq.write(1, 0, 'نتیجه‌ها خروجی اجرای اسکریپت‌اند؛ مقدار ذخیره‌شده فرمول‌های بلوک پایین cached است و بازمحاسبه زنده نیست. FAIL با حوزه V1_ARTIFACT بازتولید نقص نسخه v1 است و حذف نشده است.', F['warn'])
    for j, h in enumerate(hdr): wsq.write(2, j, h, F['h'])
    for j, w in enumerate((30, 12, 34, 30, 60, 26, 40, 9, 60, 46)): wsq.set_column(j, j, w)
    for i, t in enumerate(QA['tests']):
        r = 3 + i
        for j, v in enumerate((t['test_id'], t['area'], t.get('sources') or 'tt_v2.sqlite + فایل‌های منبع', t.get('population') or 'ر.ک. روش', t['description'], t['expected'], t['actual'])): wsq.write(r, j, v, F['t'])
        wsq.write(r, 7, t['status'], F[{'PASS': 'pass_', 'REVIEW': 'rev', 'FAIL': 'fail'}[t['status']]]); wsq.write(r, 8, t['detail'], F['t']); wsq.write(r, 9, t.get('command') or 'TT_VARIANT=v2 python scripts/taxi_terminals_1404_1405/09_qa.py', F['t'])
else:
    hdr = ['شناسه', 'حوزه', 'شرح', 'مقدار مورد انتظار', 'مقدار واقعی', 'وضعیت', 'توضیح']
    for j, h in enumerate(hdr): wsq.write(2, j, h, F['h'])
    for j, w in enumerate((14, 12, 70, 28, 28, 10, 70)): wsq.set_column(j, j, w)
    for i, t in enumerate(QA['tests']):
        r = 3 + i
        wsq.write(r, 0, t['test_id'], F['t']); wsq.write(r, 1, t['area'], F['t']); wsq.write(r, 2, t['description'], F['t']); wsq.write(r, 3, t['expected'], F['t']); wsq.write(r, 4, t['actual'], F['t'])
        wsq.write(r, 5, t['status'], F[{'PASS': 'pass_', 'REVIEW': 'rev', 'FAIL': 'fail'}[t['status']]]); wsq.write(r, 6, t['detail'], F['t'])
r = 3 + len(QA['tests']) + 2
wsq.write(r, 0, 'بلوک کنترل با فرمول زنده: جمع ورق‌های همین فایل در برابر Source_Profile (که از خواندن مستقل فایل منبع پر شده)', F['title']); r += 1
for j, h in enumerate(['سازمان', 'سال', 'معیار', 'Source_Profile', 'فرمول (از Document_Lineage یا Event_Mapping)', 'وضعیت']): wsq.write(r, j, h, F['h'])
r += 1
DL = SHEETS['Document_Lineage']; EMS = SHEETS['Event_Mapping']; CMS = SHEETS['Cost_Center_Mapping']
def rng(sh, key):
    L = colL(sh, key); f = SHEETS[sh]['first'] + 1; l = SHEETS[sh]['first'] + SHEETS[sh]['n']
    return f"{sh}!${L}${f}:${L}${l}"
sp_cols = {(o, y): colL('Source_Profile', f'{o}_{y}') for o, y in orgyears}
formula_rows = []
for o, y in orgyears:
    for label, mkey, sheetname, valkey in (('ردیف‌های Sanad', 'ردیف سند (Sanad) = خطوط حسابداری', 'Document_Lineage', 'n_lines'), ('جمع بدهکار', 'جمع بدهکار (واحد منبع)', 'Document_Lineage', 'debit_total'),
                                           ('جمع بستانکار', 'جمع بستانکار (واحد منبع)', 'Document_Lineage', 'credit_total'), ('اسناد یکتا', 'اسناد یکتا (سازمان+سال+Sanad_Num)', 'Document_Lineage', None),
                                           ('ردیف‌ها در Event_Mapping', 'ردیف سند (Sanad) = خطوط حسابداری', 'Event_Mapping', 'lines'), ('ردیف‌ها در Cost_Center_Mapping', 'ردیف سند (Sanad) = خطوط حسابداری', 'Cost_Center_Mapping', 'lines')):
        sp_ref = f"Source_Profile!{sp_cols[(o, y)]}{SP_ROW[mkey] + 1}"
        org_rng, fy_rng = rng(sheetname, 'organization'), rng(sheetname, 'fiscal_year')
        if valkey is None:
            fml = f'=COUNTIFS({org_rng},"{o}",{fy_rng},"{y}")'
            cached = one('SELECT count(*) FROM doc_class WHERE org=? AND fy=?', o, y)
        else:
            fml = f'=SUMIFS({rng(sheetname, valkey)},{org_rng},"{o}",{fy_rng},"{y}")'
            if sheetname == 'Document_Lineage':
                cached = {'n_lines': one('SELECT sum(n_lines) FROM doc_class WHERE org=? AND fy=?', o, y), 'debit_total': one('SELECT sum(bed) FROM sanad WHERE org=? AND fy=?', o, y), 'credit_total': one('SELECT sum(bes) FROM sanad WHERE org=? AND fy=?', o, y)}[valkey]
            elif sheetname == 'Event_Mapping': cached = one('SELECT count(*) FROM line_event WHERE org=? AND fy=?', o, y)
            else: cached = one('SELECT count(*) FROM line_cc WHERE org=? AND fy=?', o, y)
        spv = [m for m in metrics if m[0] == mkey][0][1][orgyears.index((o, y))]
        if valkey is None: spv = one('SELECT count(DISTINCT doc_key) FROM sanad WHERE org=? AND fy=?', o, y)
        wsq.write(r, 0, o, F['t']); wsq.write(r, 1, y, F['t']); wsq.write(r, 2, label, F['t'])
        if valkey is None: wsq.write_number(r, 3, spv, F['n'])
        else: wsq.write_formula(r, 3, f'={sp_ref}', F['n'], spv)
        wsq.write_formula(r, 4, fml, F['n'], cached)
        st = 'PASS' if cached == spv else 'FAIL'
        wsq.write_formula(r, 5, f'=IF(D{r+1}=E{r+1},"PASS","FAIL")', F['pass_' if st == 'PASS' else 'fail'], st)
        formula_rows.append((o, y, label, spv, cached, st)); r += 1
wsq.conditional_format(3, 5, r, 5, {'type': 'cell', 'criteria': '==', 'value': '"FAIL"', 'format': F['fail']})
QA['formula_block'] = formula_rows
summ = collections.Counter(t['status'] for t in QA['tests']); summ.update(x[5] for x in formula_rows)
if V21:
    _reg = build_registry(QA, EMBED_IDS); _S = summarize(_reg)
    wsq.write(r + 1, 0, 'خلاصه شمارش‌ها (از یک مجموعه داده: رجیستری QA؛ فقط تست‌های درون‌فایلی — تست‌های پس از ساخت جدا هستند)', F['title'])
    for j, h in enumerate(['دسته', 'PASS', 'REVIEW', 'FAIL', 'NOT_RUN']): wsq.write(r + 2, j, h, F['h'])
    for k, cname in enumerate(CATS):
        wsq.write(r + 3 + k, 0, cname, F['t'])
        for j, st in enumerate(('PASS', 'REVIEW', 'FAIL', 'NOT_RUN')): wsq.write_number(r + 3 + k, 1 + j, _S[cname][st], F['n'])
    json.dump(QA, open(QA_JSON, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
    json.dump(EMBED_IDS, open(f'{WORK}/qa_embedded_v21.json', 'w', encoding='utf8'))
else:
    wsq.write(r + 1, 0, f"خلاصه: PASS={summ['PASS']} ، REVIEW={summ['REVIEW']} ، FAIL={summ['FAIL']}", F['title'])
wb.close()
print('workbook written', FILE, os.path.getsize(FILE))

# ===================================================================================================== machine-readable outputs
def wcsv(name, header, rows, bom=True):
    p = f'{MR}/{name}'
    with open(p, 'w', encoding='utf-8-sig' if bom else 'utf-8', newline='') as f:
        w = csv.writer(f); w.writerow(header)
        for r in rows: w.writerow(r)
    return p

# canonical events
ce_hdr = ['event_id', 'origin', 'title_fa', 'family', 'nature', 'definition', 'governance_status', 'gap_link', 'organizations', 'driver_lines', 'documents', 'debit_sum', 'credit_sum', 'first_date', 'last_date',
          'lines_confirmed', 'lines_provisional', 'lines_new_candidate', 'share_person_code', 'share_org_unit', 'share_source_activity', 'share_docs_with_bank', 'share_contract_mention', 'why_new']
wcsv('canonical_events.csv', ce_hdr, ce_rows)
json.dump([dict(zip(ce_hdr, r)) for r in ce_rows], open(f'{MR}/canonical_events.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
# line-level event mapping + CC mapping + restricted lineage
SQL_LINE = """SELECT s.sid,s.doc_key,s.org,s.fy,s.src_file,s.src_sheet,s.src_row,s.sanad_num,s.date,s.kol,s.moeen,s.taf1,s.taf2,s.hcode,s.bed,s.bes,
  e.role,e.acat,e.own_event,e.event_id,e.outcome,e.conf,e.rule_id,e.evidence_n,e.basis,e.doc_primary_event,e.doc_outcome,e.review,
  c.eligible,c.cc_status,c.cc_id,c.alt_ccs,c.activity_id,c.source_markaz,c.source_unit,c.conf,c.rule_id,c.basis,d.kind
  FROM sanad s JOIN line_event e ON e.sid=s.sid JOIN line_cc c ON c.sid=s.sid JOIN doc_class d ON d.doc_key=s.doc_key ORDER BY s.org,s.fy,s.src_row"""
if V2: SQL_LINE = SQL_LINE.replace('d.kind\n  FROM', "d.kind,coalesce(e.lifecycle_action,'')\n  FROM")
f_ev = open(f'{MR}/event_mapping_lines.csv', 'w', encoding='utf-8-sig', newline=''); w_ev = csv.writer(f_ev)
f_cc = open(f'{MR}/cost_center_mapping_lines.csv', 'w', encoding='utf-8-sig', newline=''); w_cc = csv.writer(f_cc)
w_ev.writerow(['Source_Record_ID', 'Doc_Key', 'Organization_ID', 'Fiscal_Year', 'Source_File', 'Source_Sheet', 'Source_Row_Number', 'Sanad_Num', 'Account_Code', 'Debit', 'Credit', 'Doc_Kind', 'Line_Role', 'Account_Category',
               'Line_Event_Evidence', 'Assigned_Event', 'Event_Outcome', 'Confidence', 'Matching_Rule', 'Independent_Evidence_Count', 'Matching_Basis', 'Doc_Primary_Event', 'Doc_Outcome', 'Reviewer_Required', 'Governance_Layer'] + (['Lifecycle_Action'] if V2 else []))
w_cc.writerow(['Source_Record_ID', 'Doc_Key', 'Organization_ID', 'Fiscal_Year', 'Source_File', 'Source_Row_Number', 'Account_Code', 'Debit', 'Credit', 'Eligible_For_Cost_Center', 'CC_Status', 'CC_ID', ('Candidate_CCs_Or_Alternatives' if V2 else 'Alternative_CCs'),
               'Activity_ID', 'Source_Activity_Code_CodeMarkaz', 'Source_Unit_CodeVahed', 'Confidence', 'Matching_Rule', 'Matching_Basis', 'Reviewer_Required', 'Governance_Layer'])
nline = 0
for r in cur.execute(SQL_LINE):
    (sid, dk, org, fy, sf, ss, sr, num, date, kol, moe, t1, t2, hc, bed, bes, role, acat, own, ev, oc, cf, rid, evn, basis, pev, doc_oc, rev, elig, ccst, ccid, alt, act, mz, unit, ccf, ccr, ccb, kind, *lcx) = r
    w_ev.writerow([sid, dk, org, fy, sf, ss, sr, num, hc, bed, bes, kind, role, acat, own, ev, oc, cf, rid, evn, basis, pev, doc_oc, 'Y' if rev else 'N', 'B_PROPOSED' if oc != 'NOT_AN_OPERATIONAL_EVENT' else 'A_OBSERVED'] + list(lcx))
    w_cc.writerow([sid, dk, org, fy, sf, sr, hc, bed, bes, elig, ccst, ccid or '', alt, act or '', mz or '', unit or '', ccf, ccr, ccb, 'Y' if elig and ccst != 'CC_NOT_APPLICABLE' else 'N', 'B_PROPOSED' if elig else 'A_OBSERVED'])
    nline += 1
f_ev.close(); f_cc.close()
# restricted full lineage (original narration)
f_l = open(f'{MR}/document_lineage_RESTRICTED.csv', 'w', encoding='utf-8-sig', newline=''); w_l = csv.writer(f_l)
w_l.writerow(['Source_Record_ID', 'Organization_ID', 'Fiscal_Year', 'Source_File', 'Source_Sheet', 'Source_Row_Number', 'Doc_Key', 'Sanad_Num', 'Date', 'Des', 'Kol', 'Moeen', 'Tafsili1', 'Tafsili2', 'Bed', 'Bes', 'HCode', 'Sharh',
              'Field1', 'Field2', 'Field3', 'Field4', 'Field5', 'CodeVahed', 'CodeMarkaz', 'CodePerson', 'NameVahed', 'Assigned_Event', 'Event_Outcome', 'CC_Status', 'CC_ID'])
LN = {r[0]: r[1:] for r in cur.execute('SELECT e.sid,s.doc_key,e.own_event,e.outcome,c.cc_status,c.cc_id FROM line_event e JOIN line_cc c ON c.sid=e.sid JOIN sanad s ON s.sid=e.sid')}
for r in cur.execute("SELECT org,fy,src_file,src_sheet,src_row,Sanad_Num,Date,Des,Kol,Moeen,Tafsili1,Tafsili2,Bed,Bes,HCode,Sharh,Field1,Field2,Field3,Field4,Field5,CodeVahed,CodeMarkaz,CodePerson,NameVahed FROM sanad_raw ORDER BY rid"):
    org, fy, sf, ss, srow = r[:5]
    sid = f'{ORGS[org][0]}-{fy}-S-{srow:06d}'
    dk, own, oc, ccst, ccid = LN[sid]
    w_l.writerow((sid, org, fy, sf, ss, srow, dk) + tuple(r[5:]) + (own, oc, ccst, ccid))
f_l.close()
wcsv('document_lineage_docs.csv', ['Doc_Key', 'Organization_ID', 'Fiscal_Year', 'Source_File', 'Sanad_Num', 'Lines', 'Debit', 'Credit', 'Date_First', 'Date_Last', 'Src_Row_Min', 'Src_Row_Max', 'Doc_Kind', 'Primary_Event', 'Outcome',
         'Composite', 'Driver_Events', 'Confidence', 'Rule', 'CC_Statuses', 'CC_IDs', 'Review_Required'], DOC_ROWS)
wcsv('account_dictionary.csv', ['Organization_ID', 'Fiscal_Year', 'Account_Code', 'Title', 'Parent_Code', 'Kol', 'Moeen', 'Tafsili1', 'Tafsili2', 'Level', 'Is_Leaf', 'Src_Kind', 'Src_Type', 'Src_P', 'Proposed_Nature', 'Confidence', 'Lines', 'Debit', 'Credit', 'Source_Record_ID'], ad)
wcsv('account_crosswalk.csv', ['Organization_ID', 'Fiscal_Year', 'Org_Kol', 'Org_Moeen', 'Org_Title', 'Org_HCode', 'Mun_Kol', 'Mun_Moin', 'Mun_Kol_Title', 'Mun_Moin_Title', 'Match_Level', 'Match_Status', 'Note', 'Lines', 'Debit', 'Credit', 'Code_Collision'], acw)
wcsv('account_divergence.csv', ['Kind', 'Org_A', 'Org_B', 'FY_A', 'FY_B', 'HCode', 'Title_A', 'Title_B', 'Lines_A', 'Lines_B', 'Note'], adv)
wcsv('kpi_results.csv', ['KPI_ID', 'Organization_ID', 'Fiscal_Year', 'Window', 'Numerator_Name', 'Numerator', 'Denominator_Name', 'Denominator', 'Value', 'Unit', 'Status', 'Caveat', 'Title'], kr)
kpi_cols = ['kpi_id', 'org', 'title_fa', 'title_en', 'category', 'activity', 'cost_centers', 'purpose', 'formula', 'numerator', 'denominator', 'unit', 'period', 'financial_fields', 'operational_fields', 'method', 'filters', 'exclusions', 'data_availability', 'calc_status', 'governance', 'confidence', 'notes', 'metric_ids']
json.dump([dict(zip(kpi_cols, r)) for r in kc], open(f'{MR}/kpi_definitions.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
wcsv('exceptions_queue.csv', ['Doc_Key', 'Organization_ID', 'Fiscal_Year', 'Queue', 'Outcome', 'Amount', 'Reason', 'Events', 'Decision_Owner'], EX)
json.dump({k: dict(title_fa=v['title'], definition=v['definition'], parent_domain=v['domain'], organizations=v['orgs'], governance='PROPOSED', why_existing_insufficient=v['why_existing_insufficient'],
           alternatives=v['alternatives'], overlap_risk=v['overlap'], potential_owner=v['owner']) for k, v in NEW_CC.items()}, open(f'{MR}/new_cost_center_candidates.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
# import-ready (NOT activated; mirrors app/models.py FinancialEventRef(code,title) and CostCenterRef(code,title) plus governance columns)
os.makedirs(f'{MR}/import_ready', exist_ok=True)
wcsv('import_ready/proposed_financial_event_refs.csv', ['code', 'title', 'origin', 'governance_status', 'activate_in_production'], [(r[0], r[2], r[1], r[6], 'NO') for r in ce_rows])
wcsv('import_ready/proposed_cost_center_refs.csv', ['code', 'title', 'origin', 'governance_status', 'activate_in_production'],
     [(c, CC[c]['title'], 'municipality master v3 (+CC-109)', CC[c]['status'], 'NO') for c in sorted({r[0] for r in q('SELECT DISTINCT cc_id FROM line_cc WHERE cc_id IS NOT NULL') if r[0] in CC})] +
     [(c, d['title'], 'TTCC-P provisional candidate', 'PROPOSED — NOT A MASTER ENTRY', 'NO') for c, d in NEW_CC.items()])
cat = {}
for ev, org, n, nd, dr, cr, f, l in [(k[0], k[1], *v[:2], v[2], v[3], v[4], v[5]) for k, v in usage.items()]:
    cat.setdefault(org, []).append(dict(event_id=ev, title=title_of(ev), driver_lines=n, documents=nd, governance='OBSERVED/PROPOSED — not approved'))
json.dump(cat, open(f'{MR}/import_ready/organization_event_catalog.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
wcsv('import_ready/event_cost_center_observed_matrix.csv', ['event_id', 'event_title', 'cc_id', 'cc_title', 'cc_status', 'lines', 'documents', 'net_debit', 'first_date', 'last_date', 'evidence_strength', 'governance', 'Observed_Cardinality', 'Proposed_Cardinality', 'Approved_Cardinality', 'events_for_this_cc'], MX_ROWS)
SCHEMAS = {
 'event_mapping_lines.csv': 'One row per source accounting line (111,600). Key Source_Record_ID = <TAXI|TERM>-<FY>-S-<6-digit Excel row>. Assigned_Event = FE-xx (v7.1) or TT-NE-xx; COMPONENT lines inherit the document primary event; Line_Event_Evidence is the line\'s own evidence.',
 'cost_center_mapping_lines.csv': 'One row per source line. CC_Status in {PROVISIONAL_EXISTING_CC, NEW_CC_CANDIDATE, MULTIPLE_CC_CANDIDATES, INSUFFICIENT_INFORMATION, CC_NOT_APPLICABLE}; EXACT/VALIDATED never assigned. CC_ID is CC-xxx (baseline v3, PROPOSED) or TTCC-P-xx (provisional). Source_Activity_Code_CodeMarkaz is evidence only.',
 'document_lineage_RESTRICTED.csv': 'RESTRICTED. All 20 source columns verbatim (narration may contain person/counterparty names) + assigned event/CC. Key Source_Record_ID.',
 'document_lineage_docs.csv': 'One row per source-scoped document (Doc_Key = ORG-FY-Sanad_Num).', 'canonical_events.csv': 'FE ids observed in the data (v7.1, not redefined) + TT-NE candidates.',
 'account_crosswalk.csv': 'Org account (kol/moeen) → municipality candidate. Match_Level L4 provisional title+nature, L5 expert review, NONE no equivalent. L1-L3 not assertable.',
 'kpi_definitions.json': 'KPI definitions (not results).', 'kpi_results.csv': 'Only supportable results; rows with empty Denominator have no KPI value.',
 'exceptions_queue.csv': 'Unresolved/ambiguous/composite documents, CC gaps, duplicate candidates.',
 'import_ready/': 'Mirrors app.models FinancialEventRef/CostCenterRef (code,title) with governance columns; activate_in_production=NO everywhere; no database was modified.',
}
json.dump(SCHEMAS, open(f'{MR}/SCHEMAS.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
if V2:
    if not V21: wcsv('v1_to_v2_change_log.csv', ['Source_Record_ID', 'Organization_ID', 'Fiscal_Year', 'Original_Document_Ref', 'Field_Changed', 'Old_Value', 'New_Value', 'Reason', 'Supporting_Evidence', 'Rule_Or_Code_Path', 'Confidence', 'Governance_Effect'], cl)
    cur.execute('SELECT * FROM cc_resolution ORDER BY org,fy,sid')
    if not V21: wcsv('cc_unresolved_resolution.csv', [d[0] for d in cur.description], cur.fetchall())
    for tname, fname in (('event_review', 'event_concept_review.csv'), ('event_crosswalk', 'event_crosswalk_v1_v2.csv'), ('cc_proposal_recon', 'cc_proposal_reconciliation.csv'), ('cc_proposal_moves', 'cc_proposal_moves.csv'), ('cc_coverage', 'cc_coverage_v1_v2.csv'),
                         ('kpi_verification', 'kpi_verification.csv'), ('kpi_v1_v2', 'kpi_v1_v2.csv'), ('doc_transitions', 'doc_outcome_transitions.csv'), ('terminal_agency', 'terminal_agency_evidence.csv')):
        cur.execute(f'SELECT * FROM {tname}'); wcsv(fname, [d[0] for d in cur.description], cur.fetchall())
    wcsv('decision_readiness.csv', HDR13, DEC_ROWS_FOR_EXPORT)
    json.dump({k: dict(recommendation=v['recommendation'], title_v2=v['title_v2'], reasoning=v['reasoning'], alternatives=v['alternatives'], overlap=v['overlap'], experts=v['experts'], approval=v['approval'], open_questions=v['open_questions'],
                       governance='PROPOSED — not approved; not a master entry') for k, v in CC_AUDIT.items()}, open(f'{MR}/new_cost_center_candidates.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
    json.dump({r[0]: dict(status=r[1], v1_status=r[2], verdict=r[3], basis=r[4]) for r in q('SELECT kpi_id,calc_status,v1_status,v2_verdict,basis_type FROM kpi_catalogue')}, open(f'{MR}/kpi_status_v2.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
    SCHEMAS.update({'v1_to_v2_change_log.csv': 'One row per consequential v1→v2 change at Source_Record_ID level (event, role, CC status/selected/candidates, doc kind, lifecycle action) with reason and rule/code path.',
                    'cc_unresolved_resolution.csv': 'The 5,409 v1 unresolved CC rows (MULTIPLE/INSUFFICIENT) with their v2 outcome and rule-level evidence (no narration).',
                    'event_concept_review.csv': 'All 28 v1 TT-NE candidates with review outcome and v2 disposition.'})
    json.dump(SCHEMAS, open(f'{MR}/SCHEMAS.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
if V21:
    wcsv('v2_to_v21_change_log.csv', ['Change_ID', 'Change_Class', 'Source_Record_ID', 'Organization_ID', 'Fiscal_Year', 'Source_Document', 'Affected_Component', 'V2_Value', 'V21_Value', 'Reason', 'Evidence', 'Rule_Change', 'Confidence_Change', 'QA_Reference', 'Governance_Impact'], cl21)
    cur.execute('SELECT * FROM low_audit ORDER BY organization,fiscal_year,source_record_id'); _h = [d[0] for d in cur.description]; _rows = [tuple(mcode(x) if _h[i] == 'account_code' else x for i, x in enumerate(r)) for r in cur.fetchall()]
    wcsv('low_confidence_cc_audit.csv', _h, _rows)
    json.dump([dict(zip(_h, r)) for r in _rows], open(f'{MR}/low_confidence_cc_audit.json', 'w', encoding='utf8'), ensure_ascii=False, indent=0)
    for tname, fname in (('low_rule_analysis', 'low_confidence_rule_analysis.csv'), ('low_sample', 'low_confidence_sample_round2.csv'), ('low_sample_round1', 'low_confidence_sample_round1.csv'), ('low_postfix_changes', 'low_confidence_postfix_changes.csv'),
                         ('cc_confidence_coverage', 'cc_confidence_coverage_v2_v21.csv'), ('cc_bridge_v2_v21', 'cc_population_bridge_v2_v21.csv'), ('kpi_status_consistency', 'kpi_status_consistency.csv'), ('kpi_counts', 'kpi_counts.csv'),
                         ('kpi_recharge_bridge', 'kpi_recharge_bridge.csv'), ('fe70_review', 'fe70_review.csv'), ('event_crosswalk_v2_v21', 'event_crosswalk_v2_v21.csv')):
        cur.execute(f'SELECT * FROM {tname}'); wcsv(fname, [d[0] for d in cur.description], cur.fetchall())
    cur.execute('SELECT * FROM account_dictionary_restricted'); wcsv('RESTRICTED_account_dictionary_unmasked.csv', [d[0] for d in cur.description], cur.fetchall())
    cur.execute('SELECT kpi_id,org,calc_status,definition_status,calculation_status,verification_status,governance_status,verification_basis,basis_type FROM kpi_catalogue ORDER BY kpi_id')
    json.dump([dict(zip([d[0] for d in cur.description], r)) for r in cur.fetchall()], open(f'{MR}/kpi_status_v21.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
    SCHEMAS.update({'low_confidence_cc_audit.csv': 'One row per newly assigned LOW-confidence cost-center line of v2 (1,016): v2 values, audit decision, v2.1 status/cc/confidence/candidates, reason and evidence (no narration).',
                    'v2_to_v21_change_log.csv': 'Every consequential v2→v2.1 change (CLASSIFICATION / ACCOUNTING_INTERPRETATION / METADATA / PRIVACY) with Change_ID, evidence, rule change, confidence change and QA reference. No accounting amount changed.',
                    'RESTRICTED_account_dictionary_unmasked.csv': 'RESTRICTED. Original (unmasked) account titles incl. bank-account numbers; never distribute to the client package.',
                    'kpi_counts.csv': 'Single source of KPI counts: unique definitions vs calculable vs independently verified vs KPI×period observations.'})
    json.dump(SCHEMAS, open(f'{MR}/SCHEMAS.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
# manifest with hashes
man = {}
for root, _, fs in os.walk(OUT):
    for fn in sorted(fs):
        p = os.path.join(root, fn)
        man[os.path.relpath(p, OUT).replace('\\', '/')] = dict(bytes=os.path.getsize(p), sha256=hashlib.sha256(open(p, 'rb').read()).hexdigest())
json.dump(dict(generated_for=f'Taxi/Terminals FY1404-1405 {VSUF}', baseline_v71_sha256=V71_SHA, files=man), open(f'{OUT}/MANIFEST{("_" + VSUF) if V2 else ""}.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
print('lines exported', nline, 'files', len(man))
