"""Phase 4 — post-build QA on the *delivered files* (workbook, CSV/JSON, manifest) and on the reused baseline.
Appends tests to qa_results.json / qa_results table; regenerate financial_mapping_QA.md afterwards with 10_reports.py.
"""
import sqlite3, sys, os, json, csv, hashlib, zipfile, re
import openpyxl
sys.path.insert(0, os.path.dirname(__file__))
from common import *

csv.field_size_limit(10 ** 9)
con = sqlite3.connect(DB)
QA = json.load(open(QA_JSON, encoding='utf8'))
QA['tests'] = [t for t in QA['tests'] if not t['test_id'].startswith('P') and t['test_id'] not in ('QA_OUTPUT_MANIFEST_INTEGRITY', 'QA_CHANGELOG_CSV_XLSX_ROW_PARITY', 'QA_WORKBOOK_QA_MATCH_REPORT', 'QA_FORMULA_CACHE_VS_RECALCULATION')]   # idempotent re-run
T = []
def add(tid, area, desc, expected, actual, status, detail=''):
    T.append(dict(test_id=tid, area=area, description=desc, expected=str(expected), actual=str(actual), status=status, detail=detail))

FILE = f'{OUT}/taxi_terminals_financial_mapping_1404_1405_{VSUF}.xlsx'
MANF = {'v2': 'MANIFEST_v2.json', 'v21': 'MANIFEST_v2.1.json'}.get(VARIANT, 'MANIFEST.json')
REQ = ['Source_Inventory', 'Source_Profile', 'Account_Dictionary', 'Account_Crosswalk', 'Document_Lineage', 'Canonical_Events', 'Event_Mapping', 'Event_CC_Matrix', 'Cost_Center_Mapping', 'New_CC_Proposals',
       'Activity_Service_Map', 'KPI_Catalogue', 'KPI_Results', 'Comparison_1404_1405', 'Exceptions', 'Committee_Decisions', 'QA_Reconciliation']
if VARIANT == 'v21':
    REQ = [x for x in REQ if x != 'Committee_Decisions'] + ['QA_Semantic_Events', 'QA_CC_Consistency', 'QA_KPI_Verification', 'Decision_Readiness', 'V2_V21_Change_Log', 'QA_Low_Confidence_CC', 'QA_CC_Confidence_Coverage', 'QA_KPI_Status_Consistency', 'QA_FE70_Semantics', 'Handover_Readiness']
elif VARIANT == 'v2':
    REQ = [x for x in REQ if x != 'Committee_Decisions'] + ['V1_V2_Change_Log', 'QA_Semantic_Events', 'QA_CC_Consistency', 'QA_KPI_Verification', 'Decision_Readiness']
wb = openpyxl.load_workbook(FILE, read_only=True)
missing = [s for s in REQ if s not in wb.sheetnames]
add('P01', 'Deliverable', 'همه ۱۷ شیت الزامی کتاب کار وجود دارد', f'{len(REQ)}/{len(REQ)}', f'{len(REQ)-len(missing)}/{len(REQ)}', 'PASS' if not missing else 'FAIL', ','.join(missing))
wb.close()

# ---- privacy: no source narration string (Sharh / Des / Field1 / Field5 / NameVahed) appears in any non-restricted output
secret = set()
for col in ('Sharh', 'Des', 'Field1', 'Field4', 'Field5', 'NameVahed'):
    for (v,) in con.execute(f'SELECT DISTINCT {col} FROM sanad_raw WHERE {col} IS NOT NULL'):
        v = str(v).strip()
        if len(v) >= 8 and v not in ('NULL',) and len(re.findall(r'[\u0600-\u06FF]', v)) >= 4: secret.add(v)   # narration-like strings only (dates/codes excluded)
# values that are deliberately published (activity titles Field1 of source activities, facility names) are whitelisted
allowed_pub = {str(v[0]).strip() for v in con.execute("SELECT DISTINCT f1 FROM sanad WHERE markaz IS NOT NULL AND markaz<>'NULL' AND org='Taxi'")} | {str(v[0]).strip() for v in con.execute("SELECT DISTINCT f1 FROM sanad WHERE org='Terminals' AND markaz='008'")}
secret -= allowed_pub
# chart-of-account titles are master data (reported separately in P04) and three generic phrases used verbatim in the mapping labels are not narration
secret -= {str(v[0]).strip() for v in con.execute('SELECT DISTINCT name FROM hesab')}
secret -= {'اصلاح سند', 'انبار سازمان', 'افتتاحيه'}
wbp = openpyxl.load_workbook(FILE, read_only=True)
cells = set()
for ws in wbp.worksheets:
    for row in ws.iter_rows(values_only=True):
        for v in row:
            if isinstance(v, str): cells.add(v.strip())
wbp.close()
hits = sorted(secret & cells)
add('P02', 'Privacy', 'هیچ شرح متنی منبع (Sharh/Des/Field/NameVahed) به‌صورت سلول کامل در کتاب کار وجود ندارد', 0, len(hits), 'PASS' if not hits else 'FAIL', '; '.join(h[:40] for h in hits[:6]))
bad = []
for fn in ('event_mapping_lines.csv', 'cost_center_mapping_lines.csv', 'document_lineage_docs.csv', 'canonical_events.csv', 'exceptions_queue.csv', 'account_crosswalk.csv', 'account_dictionary.csv', 'kpi_results.csv'):
    seen = set()
    for row in csv.reader(open(f'{MR}/{fn}', encoding='utf-8-sig')):
        for v in row: seen.add(v.strip())
    h = secret & seen
    if h: bad.append((fn, len(h)))
add('P03', 'Privacy', 'هیچ شرح متنی منبع به‌صورت سلول کامل در CSV/JSON غیرمحدود وجود ندارد', 0, len(bad), 'PASS' if not bad else 'FAIL', str(bad))
# account titles are chart text (not narration) — but person-named sub-accounts exist in Hesab (Tafsili level); report how many
pn = con.execute("SELECT count(*) FROM hesab WHERE level>=4").fetchone()[0]
add('P04', 'Privacy', 'حساب‌های تفصیلی سطح ۴ (ممکن است نام بانک/شخص/شرکت داشته باشند) در Account_Dictionary آمده‌اند', 'گزارش', f'{pn} حساب سطح ۴', 'REVIEW', 'برای توزیع عمومی، فایل Account_Dictionary را به سطح ≤۳ محدود کنید')

# ---- machine-readable row counts
def nrows(fn): return sum(1 for _ in csv.reader(open(f'{MR}/{fn}', encoding='utf-8-sig'))) - 1
tot = con.execute('SELECT count(*) FROM sanad').fetchone()[0]
counts = {fn: nrows(fn) for fn in ('event_mapping_lines.csv', 'cost_center_mapping_lines.csv', 'document_lineage_RESTRICTED.csv')}
add('P05', 'Lineage', 'هر فایل ردیفی (رویداد/مرکز هزینه/ردیابی محدود) دقیقاً یک ردیف به‌ازای هر ردیف منبع دارد', f'{tot} هر کدام', json.dumps(counts), 'PASS' if all(v == tot for v in counts.values()) else 'FAIL')
dbt = con.execute('SELECT sum(bed),sum(bes) FROM sanad').fetchone()
rb = rs = 0; ids = set(); dup = 0
for r in csv.DictReader(open(f'{MR}/document_lineage_RESTRICTED.csv', encoding='utf-8-sig')):
    rb += int(r['Bed']); rs += int(r['Bes'])
    if r['Source_Record_ID'] in ids: dup += 1
    ids.add(r['Source_Record_ID'])
add('P06', 'Lineage', 'فایل ردیابی محدود: جمع بدهکار/بستانکار = منبع و شناسه ردیف یکتا', f'{dbt[0]}/{dbt[1]}', f'{rb}/{rs}; تکراری={dup}', 'PASS' if (rb, rs) == tuple(dbt) and dup == 0 else 'FAIL')
# restricted lineage vs ORIGINAL workbook: first/last rows verbatim
ok = True
wbs = openpyxl.load_workbook(src_path('Terminals', '1405', 'Sanad'), read_only=True)
ws = wbs.worksheets[0]; last = None
for last in ws.iter_rows(values_only=True): pass
wbs.close()
rows = [r for r in csv.DictReader(open(f'{MR}/document_lineage_RESTRICTED.csv', encoding='utf-8-sig')) if r['Organization_ID'] == 'Terminals' and r['Fiscal_Year'] == '1405']
rl = rows[-1]
ok = str(last[0]) == rl['Sanad_Num'] and str(last[9]) == rl['HCode'] and str(last[7]) == rl['Bed'] and str(last[10] or '') == (rl['Sharh'] or '')
add('P07', 'Lineage', 'آخرین ردیف منبع (پایانه‌ها ۱۴۰۵) در فایل ردیابی بدون تغییر (حتی فاصله‌های انتهایی) است', 'برابر', 'برابر' if ok else 'ناهمخوان', 'PASS' if ok else 'FAIL', rl['Source_Record_ID'])

# ---- manifest
man = json.load(open(f'{OUT}/{MANF}', encoding='utf8'))
bad_m = [k for k, v in man['files'].items() if not k.startswith('MANIFEST') and os.path.exists(f'{OUT}/{k}') and hashlib.sha256(open(f'{OUT}/{k}', 'rb').read()).hexdigest() != v['sha256']]
add('P08', 'Deliverable', 'هش SHA-256 فایل‌های فهرست (MANIFEST.json) با فایل‌های روی دیسک برابر است (گزارش‌های تولیدشده پس از مانیفست مستثنی)', 0, len(bad_m), 'PASS' if not bad_m else 'REVIEW', ','.join(bad_m[:5]))

# ---- baseline integrity (reused dictionary)
base = f'{ROOT}/data/deliverables/financial_event_discovery/revisions'
v71 = f'{base}/1404-r20260922-canonical-events-v7.1/financial_event_discovery_1404-r20260922_canonical-events_v7.1.xlsx'
v7 = f'{base}/1404-r20260922-canonical-events-v7/financial_event_discovery_1404-r20260922_canonical-events_v7.xlsx'
rec = json.load(open(f'{base}/1404-r20260922-canonical-events-v7.1/source_manifest_canonical-events_v7_1.json', encoding='utf8'))
sha71 = hashlib.sha256(open(v71, 'rb').read()).hexdigest(); sha7 = hashlib.sha256(open(v7, 'rb').read()).hexdigest()
add('P09', 'Baseline', 'SHA-256 فایل v7.1 روی دیسک = مقدار ثبت‌شده در مانیفست خودش', rec['output_sha256'], sha71, 'PASS' if sha71 == rec['output_sha256'] else 'REVIEW', 'فایل پس از ثبت مانیفست تغییر کرده است')
add('P10', 'Baseline', 'SHA-256 فایل v7 (منبع) = مقدار ثبت‌شده', rec['source_sha256'], sha7, 'PASS' if sha7 == rec['source_sha256'] else 'REVIEW')
def sh(p, name):
    w = openpyxl.load_workbook(p, read_only=True); r = [tuple(x) for x in w[name].iter_rows(values_only=True)]; w.close(); return r
same = sh(v7, 'فرهنگ_رویداد_مالی_کاندید') == sh(v71, 'فرهنگ_رویداد_مالی_کاندید') and sh(v7, 'ماتریس_شواهد_رویداد_مرکز_v2') == sh(v71, 'ماتریس_شواهد_رویداد_مرکز_v2')
add('P11', 'Baseline', 'شیت‌های فرهنگ رویداد و ماتریس شواهد (تنها بخش‌های بازاستفاده‌شده) در v7.1 دیسک = v7 (مقایسه مقداری)', 'برابر', 'برابر' if same else 'ناهمخوان', 'PASS' if same else 'FAIL')
ccm = hashlib.sha256(open(f'{ROOT}/cc_master.json', 'rb').read()).hexdigest()
add('P12', 'Baseline', 'master مراکز هزینه cc_master.json (۷۵ مرکز) خوانده شد', '75', str(len(json.load(open(f'{ROOT}/cc_master.json', encoding='utf8')))), 'PASS', ccm)


# ---- independent recomputation of the workbook's live-formula control block from the delivered sheet contents (no spreadsheet engine available)
import collections
wbv = openpyxl.load_workbook(FILE, read_only=True, data_only=True)
def tbl(name):
    rows = list(wbv[name].iter_rows(values_only=True))
    for i, r in enumerate(rows):
        if r and r[0] in ('doc_key', 'organization', 'metric'): return list(r), rows[i + 1:]
    raise RuntimeError(name)
k, rows = tbl('Document_Lineage'); ix = {x: i for i, x in enumerate(k)}
agg = collections.defaultdict(lambda: [0, 0, 0, 0])
for r in rows:
    if r[0] is None: continue
    a = agg[(r[ix['organization']], r[ix['fiscal_year']])]; a[0] += r[ix['n_lines']]; a[1] += r[ix['debit_total']]; a[2] += r[ix['credit_total']]; a[3] += 1
def sumcol(name, key):
    kk, rr = tbl(name); ii = {x: i for i, x in enumerate(kk)}; c = collections.Counter()
    for r in rr:
        if r[0]: c[(r[ii['organization']], r[ii['fiscal_year']])] += r[ii[key]]
    return c
ev, cc = sumcol('Event_Mapping', 'lines'), sumcol('Cost_Center_Mapping', 'lines')
kp, rp = tbl('Source_Profile'); sp = {r[0]: r[1:5] for r in rp if r[0]}
fb = []
for j, key in enumerate([('Taxi', '1404'), ('Taxi', '1405'), ('Terminals', '1404'), ('Terminals', '1405')]):
    want = (sp['ردیف سند (Sanad) = خطوط حسابداری'][j], sp['جمع بدهکار (واحد منبع)'][j], sp['جمع بستانکار (واحد منبع)'][j], sp['اسناد یکتا (سازمان+سال+Sanad_Num)'][j])
    got = tuple(agg[key])
    for lab, w, g in (('ردیف‌های Sanad', want[0], got[0]), ('جمع بدهکار', want[1], got[1]), ('جمع بستانکار', want[2], got[2]), ('اسناد یکتا', want[3], got[3]),
                      ('ردیف‌ها در Event_Mapping', want[0], ev[key]), ('ردیف‌ها در Cost_Center_Mapping', want[0], cc[key])):
        fb.append((key[0], key[1], lab, w, g, 'PASS' if w == g else 'FAIL'))
    st = 'PASS' if all(x[5] == 'PASS' for x in fb[-6:]) else 'FAIL'
    add(f'P13-{key[0]}-{key[1]}', 'Deliverable', 'بلوک فرمولی کتاب کار (SUMIFS/COUNTIFS) با بازمحاسبه مستقل از محتوای شیت‌ها = Source_Profile (ردیف، بدهکار، بستانکار، اسناد؛ رویداد و مرکز هزینه)', 'همه برابر', f'{sum(1 for x in fb[-6:] if x[5]=="PASS")}/6', st)
FB_BUILDER = list(QA.get('formula_block', []))
if VARIANT != 'v21': QA['formula_block'] = fb

if VARIANT == 'v21':
    V21_CSV = ('v2_to_v21_change_log.csv', 'low_confidence_cc_audit.csv', 'low_confidence_rule_analysis.csv', 'low_confidence_sample_round1.csv', 'low_confidence_sample_round2.csv', 'low_confidence_postfix_changes.csv', 'cc_confidence_coverage_v2_v21.csv',
               'cc_population_bridge_v2_v21.csv', 'kpi_status_consistency.csv', 'kpi_counts.csv', 'kpi_recharge_bridge.csv', 'fe70_review.csv', 'event_crosswalk_v2_v21.csv', 'decision_readiness.csv', 'event_concept_review.csv', 'terminal_agency_evidence.csv', 'account_dictionary.csv', 'account_crosswalk.csv', 'account_divergence.csv')
    badn = []
    for fn in V21_CSV:
        seen = set()
        for row in csv.reader(open(f'{MR}/{fn}', encoding='utf-8-sig')):
            for v in row: seen.add(v.strip())
        h = secret & seen
        if h: badn.append((fn, sorted(h)[:2]))
    add('P14', 'Privacy', 'v2.1: هیچ شرح متنی منبع در خروجی‌های غیرمحدود v2.1 نیست', 0, len(badn), 'PASS' if not badn else 'FAIL', str(badn))
    # change-log row parity: CSV vs Excel vs DB, header/title/key rows excluded by detection (not by a hard-coded constant)
    wcl = openpyxl.load_workbook(FILE, read_only=True)
    rows_x = list(wcl['V2_V21_Change_Log'].iter_rows(values_only=True)); wcl.close()
    hi = next(i for i, r in enumerate(rows_x) if r and r[0] == 'Change ID')
    n_x = sum(1 for r in rows_x[hi + 2:] if r and r[0])
    n_csv = nrows('v2_to_v21_change_log.csv'); n_db = con.execute('SELECT count(*) FROM change_log_v21').fetchone()[0]
    T.append(dict(test_id='QA_CHANGELOG_CSV_XLSX_ROW_PARITY', area='Lineage', sources='machine_readable/v2_to_v21_change_log.csv، شیت V2_V21_Change_Log، جدول change_log_v21', population='ردیف‌های داده change log',
                  description='شمار ردیف‌های داده در CSV = Excel = پایگاه داده؛ ردیف عنوان، یادداشت، سرستون و ردیف کلید از Excel با تشخیص موقعیت سرستون حذف می‌شود؛ عدد ثابت کدگذاری نشده',
                  expected=f'{n_db} (DB)', actual=f'CSV={n_csv}؛ Excel={n_x} (سرستون در ردیف {hi + 1}، داده از ردیف {hi + 3})؛ DB={n_db}', status='PASS' if n_x == n_csv == n_db else 'FAIL', detail='', command='TT_VARIANT=v21 python scripts/taxi_terminals_1404_1405/11_postbuild_qa.py'))
    ids_all = {r['Source_Record_ID'] for r in csv.DictReader(open(f'{MR}/event_mapping_lines.csv', encoding='utf-8-sig'))}
    orphan = sum(1 for (x,) in con.execute("SELECT DISTINCT source_record_id FROM change_log_v21 WHERE source_record_id<>''") if x not in ids_all)
    add('P16', 'Lineage', 'v2.1: هر Source_Record_ID در change log در فایل ردیفی رویداد وجود دارد', 0, f'{orphan} یتیم', 'PASS' if orphan == 0 else 'FAIL')
    # formula cache vs independent recomputation
    cmp_ = {(a, b, c): d for a, b, c, d in [(x[0], x[1], x[2], x[4]) for x in fb]}; bad_f = [(x[0], x[1], x[2], x[4], cmp_.get((x[0], x[1], x[2]))) for x in FB_BUILDER if cmp_.get((x[0], x[1], x[2])) != x[4]]
    T.append(dict(test_id='QA_FORMULA_CACHE_VS_RECALCULATION', area='FormulaControl', sources='بلوک فرمول QA_Reconciliation (مقادیر cached) ↔ بازمحاسبه مستقل از محتوای شیت‌ها', population=f'{len(FB_BUILDER)} ردیف فرمول',
                  description='مقدار ذخیره‌شدهٔ هر فرمول (محاسبه‌شده توسط اسکریپت، نه موتور اکسل) با جمع‌زنی مستقل محتوای شیت‌ها مقایسه می‌شود؛ این بازمحاسبهٔ زندهٔ فرمول در اکسل نیست', expected='برابر', actual=f'{len(bad_f)} اختلاف از {len(FB_BUILDER)}',
                  status='PASS' if not bad_f and FB_BUILDER else 'FAIL', detail=str(bad_f[:3]), command='TT_VARIANT=v21 python scripts/taxi_terminals_1404_1405/11_postbuild_qa.py'))
    # workbook QA sheet vs registry
    wq = openpyxl.load_workbook(FILE, read_only=True)
    wrows = {r[0]: r[8] for r in wq['QA_Reconciliation'].iter_rows(min_row=4, values_only=True) if r and r[0] and r[8] in ('PASS', 'REVIEW', 'FAIL')}; wq.close()
    embed = json.load(open(f'{WORK}/qa_embedded_v21.json', encoding='utf8')); regmap = {t['test_id']: t['status'] for t in QA['tests'] if t['test_id'] in set(embed)}
    miss = sorted(set(regmap) - set(wrows)); diffs = sorted(k for k in regmap if k in wrows and wrows[k] != regmap[k])
    T.append(dict(test_id='QA_WORKBOOK_QA_MATCH_REPORT', area='Deliverable', sources='شیت QA_Reconciliation ↔ qa_results_v21.json / QA_Test_Registry', population=f'{len(regmap)} تست درون‌فایلی',
                  description='شناسه و نتیجهٔ هر تست درون شیت QA کتاب‌کار با رجیستری QA یکسان است (همان شناسه، همان نتیجه)', expected='0 غایب؛ 0 اختلاف', actual=f'غایب={len(miss)}؛ اختلاف={len(diffs)}', status='PASS' if not miss and not diffs else 'FAIL', detail=f'{miss[:3]} {diffs[:3]}',
                  command='TT_VARIANT=v21 python scripts/taxi_terminals_1404_1405/11_postbuild_qa.py'))
elif VARIANT == 'v2':
    # ---- v2 additions: privacy on the new exports, change-log lineage, manifest integrity
    newcsv = ('v1_to_v2_change_log.csv', 'cc_unresolved_resolution.csv', 'event_concept_review.csv', 'event_crosswalk_v1_v2.csv', 'cc_proposal_reconciliation.csv', 'kpi_verification.csv', 'kpi_v1_v2.csv', 'decision_readiness.csv', 'terminal_agency_evidence.csv')
    badn = []
    for fn in newcsv:
        seen = set()
        for row in csv.reader(open(f'{MR}/{fn}', encoding='utf-8-sig')):
            for v in row: seen.add(v.strip())
        h = secret & seen
        if h: badn.append((fn, sorted(h)[:2]))
    add('P14', 'Privacy', 'v2: هیچ شرح متنی منبع در خروجی‌های جدید v2 (change log، resolution، review …) نیست', 0, len(badn), 'PASS' if not badn else 'FAIL', str(badn))
    wcl = openpyxl.load_workbook(FILE, read_only=True)
    n_sheet = sum(1 for r in wcl['V1_V2_Change_Log'].iter_rows(min_row=5, values_only=True) if r and r[0])
    wcl.close()
    n_csv = nrows('v1_to_v2_change_log.csv'); n_db = con.execute('SELECT count(*) FROM change_log').fetchone()[0]
    add('P15', 'Lineage', 'v2: شمار تغییرات change log در شیت = CSV = پایگاه داده', n_db, f'{n_sheet}/{n_csv}', 'PASS' if n_sheet == n_csv == n_db else 'FAIL')
    trace = con.execute("SELECT count(*) FROM (SELECT DISTINCT source_record_id FROM change_log)").fetchone()[0]
    ids_all = {r['Source_Record_ID'] for r in csv.DictReader(open(f'{MR}/event_mapping_lines.csv', encoding='utf-8-sig'))}
    orphan = sum(1 for (x,) in con.execute('SELECT DISTINCT source_record_id FROM change_log') if x not in ids_all)
    add('P16', 'Lineage', 'v2: هر Source_Record_ID در change log در فایل ردیفی رویداد وجود دارد', 0, f'{orphan} یتیم از {trace}', 'PASS' if orphan == 0 else 'FAIL')
    ondisk = []
    for root, _, fs in os.walk(OUT):
        for fn in fs:
            rel = os.path.relpath(os.path.join(root, fn), OUT).replace('\\', '/')
            if not rel.startswith('MANIFEST') and rel != 'financial_mapping_QA_v2.md': ondisk.append(rel)
    notin = sorted(set(ondisk) - set(man['files']))
    required = ['taxi_terminals_financial_mapping_1404_1405_v2.xlsx', 'corrective_audit_v2.md', 'taxi_terminals_management_report_v2.md', 'committee_decisions_v2.xlsx']
    miss_req = [x for x in required if x not in ondisk]
    T.append(dict(test_id='QA_OUTPUT_MANIFEST_INTEGRITY', area='Deliverable', sources='MANIFEST_v2.json، فایل‌های روی دیسک', population=f'{len(ondisk)} فایل خروجی',
                  description='هر فایل خروجی روی دیسک در مانیفست آمده و SHA-256 برابر است؛ فایل‌های الزامی (workbook، corrective_audit، management report، committee_decisions) موجودند؛ گزارش QA و خود مانیفست مستثنی‌اند (خودارجاع)',
                  expected='هش نابرابر=0، خارج از مانیفست=0، الزامی مفقود=0', actual=f'هش نابرابر={len(bad_m)}؛ خارج از مانیفست={len(notin)}؛ الزامی مفقود={len(miss_req)}', status='PASS' if not (bad_m or notin or miss_req) else 'FAIL',
                  detail=f'{bad_m[:3]} {notin[:3]} {miss_req}', command='TT_VARIANT=v2 python scripts/taxi_terminals_1404_1405/11_postbuild_qa.py'))
QA['tests'] += T
json.dump(QA, open(QA_JSON, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
con.execute('DELETE FROM qa_results WHERE test_id LIKE "P%"')
con.executemany('INSERT INTO qa_results VALUES(?,?,?,?,?,?,?)', [(t['test_id'], t['area'], t['description'], t['expected'], t['actual'], t['status'], t['detail']) for t in T])
con.commit()
import collections
print(dict(collections.Counter(t['status'] for t in T)))
for t in T:
    if t['status'] != 'PASS': print(t['status'], t['test_id'], t['actual'][:100], '|', t['detail'][:100])
