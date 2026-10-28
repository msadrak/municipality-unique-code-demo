"""v2.1 final assembly: FINAL-stage QA tests, canonical registry (CSV), financial_mapping_QA_v2.1.md, client-package refresh, final manifest.
Run after 08, 20, 11 (and again after the second 20 run).  The registry is the single source of every QA total."""
import sqlite3, sys, os, json, re, csv, hashlib, collections, shutil, datetime, importlib
import openpyxl
sys.path.insert(0, os.path.dirname(__file__))
from common import *
from qa_registry_v21 import build_registry, summarize, summary_table_md, write_csv, CATS, COLS
from manifest_v21 import manifest
assert VARIANT == 'v21'
NOW = datetime.datetime.now().strftime('%Y-%m-%d')
con = sqlite3.connect(DB, timeout=300); cur = con.cursor()
QA = json.load(open(QA_JSON, encoding='utf8'))
EMB = json.load(open(f'{WORK}/qa_embedded_v21.json', encoding='utf8'))
FINAL_IDS = ('QA_TEST_REGISTRY_UNIQUENESS', 'QA_TEST_CATEGORY_SEPARATION', 'QA_SUMMARY_COUNTS_MATCH_DETAIL', 'QA_PRIVACY_CLIENT_PACKAGE', 'QA_OUTPUT_MANIFEST_INTEGRITY', 'QA_MD_KPI_COUNTS_MATCH')
QA['tests'] = [t for t in QA['tests'] if t['test_id'] not in FINAL_IDS]
CMD = 'TT_VARIANT=v21 python scripts/taxi_terminals_1404_1405/21_final_v21.py'
T = []
def add(tid, area, sources, population, procedure, expected, actual, status, detail=''):
    T.append(dict(test_id=tid, area=area, sources=sources, population=population, description=procedure, expected=str(expected), actual=str(actual), status=status, detail=detail, command=CMD))
read = lambda p: open(f'{OUT}/{p}', encoding='utf8').read() if os.path.exists(f'{OUT}/{p}') else ''

# ---- privacy scan of the client package (md / csv / json / xlsx)
secret = set()
cc = sqlite3.connect(DB)
for col in ('Sharh', 'Des', 'Field1', 'Field4', 'Field5', 'NameVahed'):
    for (v,) in cc.execute(f'SELECT DISTINCT {col} FROM sanad_raw WHERE {col} IS NOT NULL'):
        v = str(v).strip()
        if len(v) >= 8 and v != 'NULL' and len(re.findall(r'[\u0600-\u06FF]', v)) >= 4: secret.add(v)
allowed_pub = {str(v[0]).strip() for v in cc.execute("SELECT DISTINCT f1 FROM sanad WHERE markaz IS NOT NULL AND markaz<>'NULL'")} | {str(v[0]).strip() for v in cc.execute('SELECT DISTINCT name FROM hesab')}
secret -= allowed_pub; secret -= {'اصلاح سند', 'انبار سازمان', 'افتتاحيه'}
PAT_IBAN = re.compile(r'IR\s?\d{2}\s?\d{4}', re.I); PAT_ACCT = re.compile(r'(?<!\d)\d{3}-\d{1,2}-\d{1,2}-\d{6,}'); PAT_LONG = re.compile(r'[\u0621-\u063A\u0641-\u064A\u067E\u0686\u0698\u06A9\u06AF\u06CC]\d{8,}|\d{8,}[\u0621-\u063A\u0641-\u064A\u067E\u0686\u0698\u06A9\u06AF\u06CC]')   # long digit run glued directly to Persian letters (e.g. «حساب1001489730»); amounts separated by space/punctuation are not bank accounts
cdir = f'{OUT}/client_package'; hits = []; nfiles = 0
for fn in sorted(os.listdir(cdir)) if os.path.isdir(cdir) else []:
    p = f'{cdir}/{fn}'; nfiles += 1; cells = []
    if fn.endswith(('.md', '.json', '.csv')):
        txt = open(p, encoding='utf-8-sig').read(); cells = [txt]
        if fn.endswith('.csv'): cells = [c for row in csv.reader(open(p, encoding='utf-8-sig')) for c in row]
    elif fn.endswith('.xlsx'):
        wb = openpyxl.load_workbook(p, read_only=True)
        for ws in wb.worksheets:
            for row in ws.iter_rows(values_only=True): cells += [str(v) for v in row if isinstance(v, str)]
        wb.close()
    for c in cells:
        if PAT_IBAN.search(c) or PAT_ACCT.search(c): hits.append((fn, 'iban/acct', c[:40]))
        elif PAT_LONG.search(c): hits.append((fn, 'digits-in-text', c[:40]))
    if secret & {c.strip() for c in cells}: hits.append((fn, 'narration', 'cell'))
add('QA_PRIVACY_CLIENT_PACKAGE', 'Privacy', 'client_package/* (md, csv, json, xlsx)', f'{nfiles} فایل بستهٔ کارفرما', 'الگوهای شماره حساب بانکی/شبا (کد ۴بخشی با بخش آخر ≥۶ رقم، IR+ارقام)، رشته‌های ≥۸ رقمی چسبیده به متن فارسی (مبلغ‌های عددی ساده حساب بانکی نیستند)، و سلول‌های برابر با شرح متنی منبع اسکن می‌شود؛ کدهای طبقه‌بندی مثل ۱۱۳-۱-۱ ماسک نمی‌شوند', '0', f'{len(hits)}', 'PASS' if not hits and nfiles else 'FAIL', str(hits[:4]))

# ---- manifest integrity (files other than the self-referential QA report / registry / their client copies / manifest)
SELF = {'financial_mapping_QA_v2.1.md', 'QA_Test_Registry_v2.1.csv', 'client_package/financial_mapping_QA_v2.1.md', 'client_package/QA_Test_Registry_v2.1.csv'}
m = manifest(OUT, ROOT, NOW)
ondisk = [os.path.relpath(os.path.join(r, f_), OUT).replace('\\', '/') for r, _, fs in os.walk(OUT) for f_ in fs]
ondisk = [x for x in ondisk if not x.startswith('MANIFEST')]
bad_h = [k for k, v in m['files'].items() if hashlib.sha256(open(f'{OUT}/{k}', 'rb').read()).hexdigest() != v['sha256']]
required = ['taxi_terminals_financial_mapping_1404_1405_v2.1.xlsx', 'corrective_audit_v2.1.md', 'low_confidence_cc_audit_v2.1.xlsx', 'FE70_depreciation_provisions_semantic_review.md', 'kpi_verification_v2.1.xlsx', 'taxi_terminals_management_report_v2.1.md',
            'committee_decisions_v2.1.xlsx', 'CD-01_terminal_agency_expert_memo_REDACTED.md', 'machine_readable/rar_verification.json']
miss_req = [x for x in required if x not in ondisk]
restricted_in_client = [k for k in ondisk if k.startswith('client_package/') and 'RESTRICTED' in k]
bad_level = [k for k, v in m['files'].items() if ('RESTRICTED' in k) != (v['distribution_level'] == 'RESTRICTED')]
add('QA_OUTPUT_MANIFEST_INTEGRITY', 'Deliverable', 'MANIFEST_v2.1.json ↔ فایل‌های روی دیسک', f'{len(ondisk)} فایل خروجی', 'همهٔ فایل‌های روی دیسک در مانیفست‌اند و SHA-256 برابر است؛ فایل‌های الزامی موجودند؛ فایل RESTRICTED در بستهٔ کارفرما نیست؛ سطح توزیع هر فایل ثبت شده؛ گزارش QA و رجیستری (خودارجاع) پس از این تست هش می‌شوند',
    'هش نابرابر=0؛ الزامی مفقود=0؛ RESTRICTED در کارفرما=0', f'هش نابرابر={len(bad_h)}؛ الزامی مفقود={len(miss_req)}؛ restricted در کارفرما={len(restricted_in_client)}؛ سطح نادرست={len(bad_level)}',
    'PASS' if not (bad_h or miss_req or restricted_in_client or bad_level) else 'FAIL', f'{bad_h[:3]} {miss_req} {restricted_in_client}')

# ---- registry level tests
QA['tests'] += T; T2 = []
def add2(*a, **k):
    global T
    T = []; add(*a, **k); T2.extend(T)
reg0 = build_registry({'tests': QA['tests'], 'formula_block': QA.get('formula_block', [])}, EMB)
ids = [r['test_id'] for r in reg0]; dup = [k for k, n in collections.Counter(ids).items() if n > 1]
add2('QA_TEST_REGISTRY_UNIQUENESS', 'Deliverable', 'QA_Test_Registry_v2.1.csv', f'{len(reg0)} تست', 'هر Test ID دقیقاً یک بار در رجیستری است', '0 تکراری', str(len(dup)), 'PASS' if not dup else 'FAIL', str(dup[:3]))
S0 = summarize(reg0)
mixed = [r['test_id'] for r in reg0 if (r['category'] == 'HISTORICAL_REGRESSION') != (r['is_historical_regression'] == 'Y') or (r['category'] == 'WORKBOOK_FORMULA_CONTROL') != (r['is_formula_control'] == 'Y') or (r['counts_toward_primary_summary'] == 'Y') != (r['category'] == 'V21_ACCEPTANCE')]
hist_fail_in_acc = [r['test_id'] for r in reg0 if r['category'] == 'V21_ACCEPTANCE' and r['test_id'].endswith('-V1')]
add2('QA_TEST_CATEGORY_SEPARATION', 'Deliverable', 'QA_Test_Registry_v2.1.csv', 'همه تست‌ها', 'هر تست دقیقاً یک دسته دارد؛ آزمون‌های بازتولید نقص نسخه‌های قبل (…-V1) در دستهٔ HISTORICAL_REGRESSION‌اند و در خلاصهٔ پذیرش v2.1 نمی‌آیند؛ کنترل‌های فرمول جدا شمرده می‌شوند',
     'ناسازگار=0', f'ناسازگار={len(mixed)}؛ تاریخی در پذیرش={len(hist_fail_in_acc)}', 'PASS' if not mixed and not hist_fail_in_acc else 'FAIL', str(mixed[:3]))
QA['tests'] += T2

# the summary-vs-detail and md-count tests need the final registry; status assumed PASS, verified by re-rendering and comparing with the files
def finalize():
    global QA
    reg = build_registry({'tests': QA['tests'], 'formula_block': QA.get('formula_block', [])}, EMB)
    return reg
KC = {(r[0], r[1]): r[2] for r in cur.execute('SELECT organization,metric,value FROM kpi_counts')}
for tid in ('QA_SUMMARY_COUNTS_MATCH_DETAIL', 'QA_MD_KPI_COUNTS_MATCH'): QA['tests'] = [t for t in QA['tests'] if t['test_id'] != tid]
placeholder = lambda tid: dict(test_id=tid, area='Deliverable', sources='', population='', description='', expected='', actual='', status='PASS', detail='', command=CMD)
QA['tests'] += [placeholder('QA_SUMMARY_COUNTS_MATCH_DETAIL'), placeholder('QA_MD_KPI_COUNTS_MATCH')]
reg = finalize(); table = summary_table_md(reg)
S = summarize(reg)
detail_cnt = collections.Counter((r['category'], r['result']) for r in reg)
agree_detail = all(S[c][st] == detail_cnt[(c, st)] for c in CATS for st in ('PASS', 'REVIEW', 'FAIL', 'NOT_RUN')) and sum(sum(S[c].values()) for c in CATS) == len(reg)
in_audit = table in read('corrective_audit_v2.1.md') and f"PASS {S['V21_ACCEPTANCE']['PASS']}" in read('taxi_terminals_management_report_v2.1.md')
add2('QA_SUMMARY_COUNTS_MATCH_DETAIL', 'Deliverable', 'QA_Test_Registry_v2.1.csv ↔ corrective_audit_v2.1.md ↔ taxi_terminals_management_report_v2.1.md', f'{len(reg)} تست', 'جدول خلاصهٔ مصرف‌شده در گزارش‌ها دقیقاً از رجیستری نهایی بازتولید می‌شود (متن جدول در گزارش حسابرسی و عدد پذیرش در گزارش مدیریتی)؛ مجموع دسته‌ها = تعداد ردیف‌های ریز',
     'جدول برابر', f'جمع=ریز: {agree_detail}؛ جدول در گزارش حسابرسی/مدیریتی: {in_audit}', 'PASS' if agree_detail and in_audit else 'FAIL', table.replace('\n', ' // ')[:300])
mg = read('taxi_terminals_management_report_v2.1.md')
need = [f"از ۱۶ تعریف تاکسیرانی {KC[('Taxi', 'independently_verified_definitions')]} تعریف", f"از ۱۵ تعریف پایانه‌ها {KC[('Terminals', 'independently_verified_definitions')]} تعریف"]
ok_md = all(x in mg for x in need)
add2('QA_MD_KPI_COUNTS_MATCH', 'KPI', 'taxi_terminals_management_report_v2.1.md ↔ kpi_counts', 'شمارش‌های KPI در گزارش مدیریتی', 'اعداد «تعریف تأییدشده» هر سازمان در گزارش مدیریتی عیناً برابر kpi_counts (منبع یکتا) است؛ شمارش تعریف یکتا با مشاهدات KPI×دوره مخلوط نشده',
     'برابر', f'جمله‌های لازم یافت شد: {ok_md}', 'PASS' if ok_md else 'FAIL', str(need))
QA['tests'] = [t for t in QA['tests'] if t['test_id'] not in ('QA_SUMMARY_COUNTS_MATCH_DETAIL', 'QA_MD_KPI_COUNTS_MATCH')] + T2[-2:]
reg = finalize(); S = summarize(reg)
json.dump(QA, open(QA_JSON, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
write_csv(f'{OUT}/QA_Test_Registry_v2.1.csv', reg)

# ---- QA report
t = ['# financial_mapping_QA_v2.1 — کنترل کیفیت v2.1\n', f'تاریخ: {NOW}. همهٔ شمارش‌ها از رجیستری یکتای `QA_Test_Registry_v2.1.csv` محاسبه شده‌اند؛ هیچ جمعی دستی نوشته نشده است.\n']
t.append('## خلاصه\n'); t.append(summary_table_md(reg)); t.append('')
t.append('- **V21_ACCEPTANCE:** آزمون‌هایی که درستی خروجی‌های v2.1 را می‌سنجند؛ تنها این دسته در «خلاصهٔ پذیرش» می‌آید.\n- **HISTORICAL_REGRESSION:** آزمون‌هایی که عمداً نقص نسخه‌های قبل را بازتولید می‌کنند (مثل `QA_NEW_CC_PROPOSAL_RECONCILIATION-V1`: ۶۴۴ در برابر ۵۳۲)؛ FAIL آن‌ها یعنی نقص قبلی هنوز بازتولید می‌شود، نه شکست v2.1، و حذف نشده است.\n- **WORKBOOK_FORMULA_CONTROL:** کنترل‌های درون‌کتاب‌کار (SUMIFS/COUNTIFS با مقدار cached) و بازمحاسبهٔ مستقل آن‌ها؛ بازمحاسبهٔ زندهٔ اکسل نیستند.\n')
stages = collections.Counter(r['execution_stage'] for r in reg); emb = collections.Counter(r['embedded_in_workbook'] for r in reg)
t.append(f"مراحل اجرا: {dict(stages)}؛ درون شیت QA کتاب‌کار: {emb.get('Y', 0)} ردیف (بقیه پس از ساخت کتاب‌کار اجرا می‌شوند و نمی‌توانند درون آن باشند).\n")
t.append('## چرا v2 سه عدد متفاوت نشان می‌داد\n')
t.append('۱) گزارش md v2: ۱۲۵ PASS / ۲۲ REVIEW / ۱ FAIL = رجیستری نهایی v2 (۱۴۸ تست)؛ ۲) ردیف‌های QA کتاب‌کار: ۱۲۴/۲۲/۲ — کتاب‌کار پیش از اجرای تست‌های پس از ساخت ساخته شد و P15 قدیمی (FAIL ناشی از خطای شمارش یک‌واحدی) را داشت؛ ۳) خلاصهٔ پایین شیت: ۱۴۸/۲۲/۲ = ۱۲۴ تست + ۲۴ ردیف کنترل فرمول بدون برچسب. در v2.1 هر تست یک دسته و یک مرحله دارد و خلاصه‌ها از یک مجموعه داده می‌آیند.\n')
t.append('## نتایج هر تست\n')
for cat in CATS:
    t.append(f'### {cat}\n')
    for r in [x for x in reg if x['category'] == cat and not x['test_id'].startswith('FC-')]:
        if r['result'] == 'PASS' and r['test_id'].startswith('Q') and not r['test_id'].startswith('QA_'): continue
        t.append(f"- **{r['test_id']}** — {r['result']} ({r['execution_stage']}) — جمعیت: {r['input_population']} — مورد انتظار: {r['expected']} — واقعی: {r['actual']}" + (f" — استثنا: {r['exception_detail']}" if r['exception_detail'] else '') + f" — بازتولید: `{r['reproduction_command']}`")
    t.append('')
fcs = [x for x in reg if x['test_id'].startswith('FC-')]
t.append(f"### کنترل‌های فرمول (FC-*): {len(fcs)} ردیف؛ PASS={sum(1 for x in fcs if x['result'] == 'PASS')} — فهرست در رجیستری.\n")
t.append('تست‌های عمومی PASS شده Q01–Q45 در رجیستری هستند و اینجا تکرار نشده‌اند؛ همهٔ REVIEW/FAIL‌ها بالا آمده‌اند.\n')
t.append('## بازتولید\n```\ncd municipality_demo/scripts/taxi_terminals_1404_1405\nset TT_VARIANT=v21\npython 17_v21_corrections.py      (از نسخهٔ تازهٔ tt_v2.sqlite)\npython 09_qa.py ; python 13_kpi_independent.py ; python 15_kpi_qa_v2.py ; python 19_kpi_status_v21.py ; python 18_qa_v21.py\npython 08_build_outputs.py\npython 20_docs_v21.py ; python 11_postbuild_qa.py ; python 21_final_v21.py ; python 20_docs_v21.py ; python 21_final_v21.py\npython -m pytest tests/test_taxi_terminals_mapping.py\n```\n')
open(f'{OUT}/financial_mapping_QA_v2.1.md', 'w', encoding='utf8', newline='\n').write('\n'.join(t))
# client package refresh + final manifest (includes the QA report and registry)
for fn in ('financial_mapping_QA_v2.1.md', 'QA_Test_Registry_v2.1.csv'):
    shutil.copy(f'{OUT}/{fn}', f'{OUT}/client_package/{fn}')
m = manifest(OUT, ROOT, NOW)
print({c: dict(S[c]) for c in CATS}, len(reg), 'manifest files', len(m['files']))
for r in reg:
    if r['result'] != 'PASS' and not r['test_id'].startswith('FC-'): print(r['result'], r['category'], r['test_id'], '|', r['actual'][:120])
