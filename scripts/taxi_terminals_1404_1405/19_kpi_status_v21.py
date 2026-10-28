"""v2.1 — KPI status model.  Separates five concepts that v2 collapsed into one field:
   Definition_Status    – a KPI definition exists (unique KPI id)
   Calculation_Status   – can it be calculated from the delivered sources (and for which periods)
   Verification_Status  – has the NUMERICAL result been independently recomputed from the original workbooks (EXACT match)
   Governance_Status    – is the ACCOUNTING INTERPRETATION approved (never in v2.1; CD-01 for Terminal flows)
   status (legacy label) – combined label kept identical in KPI_Catalogue and KPI_Results (the TX-K01 results row used to be stale)
Run after 13_kpi_independent.py and 15_kpi_qa_v2.py.
"""
import sqlite3, sys, os, json, collections
sys.path.insert(0, os.path.dirname(__file__))
from common import *
assert VARIANT == 'v21'
con = sqlite3.connect(DB, timeout=300); cur = con.cursor()
q = lambda s, *a: cur.execute(s, a).fetchall()
def one(s, *a):
    r = cur.execute(s, a).fetchone(); return r[0] if r and r[0] is not None else 0
for col in ('definition_status', 'calculation_status', 'verification_status', 'governance_status', 'verification_basis'):
    try: cur.execute(f'ALTER TABLE kpi_catalogue ADD COLUMN {col}')
    except sqlite3.OperationalError: pass
for col in ('calculation_status', 'verification_status'):
    try: cur.execute(f'ALTER TABLE kpi_results ADD COLUMN {col}')
    except sqlite3.OperationalError: pass

VER = collections.defaultdict(set)      # (org,fy,window) -> verified metric ids
BAD = set()
for m, o, fy, w, verdict in q('SELECT metric_id,org,fy,window,verdict FROM kpi_verification'):
    (VER[(o, fy, w)].add(m) if verdict == 'EXACT_MATCH' else BAD.add((m, o, fy, w)))
CALC = {'CALCULATED_AND_VERIFIED': 'CALCULABLE_FROM_SOURCE', 'CALCULATED_BUT_ACCOUNTING_POLICY_PENDING': 'CALCULABLE_FROM_SOURCE', 'PARTIALLY_CALCULABLE': 'PARTIALLY_CALCULABLE',
        'REQUIRES_OPERATIONAL_DATA': 'NOT_CALCULABLE_OPERATIONAL_DATA_MISSING', 'REQUIRES_BUDGET_DATA': 'NOT_CALCULABLE_BUDGET_DATA_MISSING', 'REQUIRES_EXPERT_DEFINITION': 'NOT_CALCULABLE_DEFINITION_PENDING'}
cat = {r[0]: r for r in q('SELECT kpi_id,org,calc_status,metrics FROM kpi_catalogue')}
# TM-K02 (assessed amount by terminal) had its values only in billed_by_terminal; add one total row per period so every calculated KPI has result rows
if not one("SELECT count(*) FROM kpi_results WHERE kpi_id='TM-K02'"):
    for fy, w, tot, nfac in q("SELECT fy,window,sum(billed),count(*) FROM billed_by_terminal GROUP BY 1,2 ORDER BY 1,2"):
        cur.execute('INSERT INTO kpi_results VALUES(?,?,?,?,?,?,?,?,?,?,?,?,NULL,NULL)', ('TM-K02', 'Terminals', fy, w, 'مطالبه صادرشده (جمع بخش‌های اول CodeVahed)', tot, '—', None, tot, 'RIAL?', 'CALCULATED_AND_VERIFIED', f'تفکیک {nfac} پایانه/واحد: KPI_Terminal_Breakdown (مطالبه = assessment، نه درآمد قطعی)'))
res = q('SELECT rowid,kpi_id,org,fy,window,value,numerator,denominator FROM kpi_results')

INFORMATIONAL = {'T_BANKFEE_LINES', 'T_SCHOOL_RECEIPTS'}     # line counts / auxiliary items that do not enter the KPI value
def period_verified(kid, org, fy, w):
    mets = [m for m in (cat[kid][3] or '').split(',') if m and m not in INFORMATIONAL]
    if not mets: return False
    return all(m in VER[(org, fy, w)] for m in mets)

# result rows: status label follows the catalogue; calculation/verification are per period
per_kpi = collections.defaultdict(list)
for rid, kid, org, fy, w, val, num, den in res:
    cs = cat[kid][2]
    has_value = (val is not None) or (num is not None)
    calc = CALC[cs] if has_value else CALC.get(cs, 'NOT_CALCULATED')
    ver = ('INDEPENDENTLY_VERIFIED' if period_verified(kid, org, fy, w) else 'NOT_INDEPENDENTLY_VERIFIED') if CALC[cs] == 'CALCULABLE_FROM_SOURCE' else 'NOT_APPLICABLE'
    cur.execute('UPDATE kpi_results SET status=?, calculation_status=?, verification_status=? WHERE rowid=?', (cs, calc, ver, rid))
    per_kpi[kid].append((fy, w, has_value, ver))

BASIS = {'INDEPENDENTLY_VERIFIED': 'بازمحاسبه مستقل شاخص‌های پایه از فایل‌های اکسل منبع (13_kpi_independent.py): برابری دقیق در همه دوره‌های گزارش‌شده',
         'NOT_INDEPENDENTLY_VERIFIED': 'شاخص پایه به طبقه‌بندی رویداد (قواعد TX-*) وابسته است و بازمحاسبه مستقل حسابی ندارد؛ پل تطبیق با ۱۱۳-۱-۱ در kpi_recharge_bridge',
         'NOT_APPLICABLE': 'قابل محاسبه از منبع نیست'}
for kid, (k, org, cs, mets) in cat.items():
    rows = per_kpi.get(kid, [])
    vers = {r[3] for r in rows if r[2]}
    ver = 'NOT_APPLICABLE' if CALC[cs] != 'CALCULABLE_FROM_SOURCE' else ('INDEPENDENTLY_VERIFIED' if vers == {'INDEPENDENTLY_VERIFIED'} else 'NOT_INDEPENDENTLY_VERIFIED')
    gov = 'ACCOUNTING_POLICY_PENDING (CD-01)' if cs == 'CALCULATED_BUT_ACCOUNTING_POLICY_PENDING' else 'PROPOSED_NOT_APPROVED'
    cur.execute('UPDATE kpi_catalogue SET definition_status=?, calculation_status=?, verification_status=?, governance_status=?, verification_basis=? WHERE kpi_id=?',
                ('DEFINED', CALC[cs], ver, gov, BASIS[ver], kid))

# --------------------------------------------------------------- consistency + counts tables
cur.execute('DROP TABLE IF EXISTS kpi_status_consistency')
cur.execute('''CREATE TABLE kpi_status_consistency(kpi_id, org, catalogue_status, distinct_result_statuses, result_rows, rows_with_value, rows_independently_verified, definition_status, calculation_status, verification_status, governance_status, consistent)''')
for kid, (k, org, cs, mets) in cat.items():
    st = [r[0] for r in q('SELECT DISTINCT status FROM kpi_results WHERE kpi_id=?', kid)]
    rr = per_kpi.get(kid, [])
    d = q('SELECT definition_status,calculation_status,verification_status,governance_status FROM kpi_catalogue WHERE kpi_id=?', kid)[0]
    cur.execute('INSERT INTO kpi_status_consistency VALUES(?,?,?,?,?,?,?,?,?,?,?,?)', (kid, org, cs, ' / '.join(st), len(rr), sum(1 for r in rr if r[2]), sum(1 for r in rr if r[3] == 'INDEPENDENTLY_VERIFIED'), *d, 'YES' if st == [cs] or (not st) else 'NO'))
cur.execute('DROP TABLE IF EXISTS kpi_counts')
cur.execute('CREATE TABLE kpi_counts(organization, metric, value, definition)')
def put(o, m, v, d): cur.execute('INSERT INTO kpi_counts VALUES(?,?,?,?)', (o, m, v, d))
for o in list(ORGS) + ['ALL']:
    w = '' if o == 'ALL' else ' AND org=?'; a = () if o == 'ALL' else (o,)
    put(o, 'unique_kpi_definitions', one(f'SELECT count(DISTINCT kpi_id) FROM kpi_catalogue WHERE 1=1{w}', *a), 'شمار kpi_id یکتا در KPI_Catalogue')
    put(o, 'catalogue_rows', one(f'SELECT count(*) FROM kpi_catalogue WHERE 1=1{w}', *a), 'شمار ردیف‌های کاتالوگ (باید برابر یکتا باشد)')
    put(o, 'calculable_from_source_definitions', one(f"SELECT count(*) FROM kpi_catalogue WHERE calculation_status='CALCULABLE_FROM_SOURCE'{w}", *a), 'تعریف‌های قابل محاسبه از منبع')
    put(o, 'independently_verified_definitions', one(f"SELECT count(*) FROM kpi_catalogue WHERE verification_status='INDEPENDENTLY_VERIFIED'{w}", *a), 'تعریف‌هایی که همه دوره‌هایشان با بازمحاسبه مستقل برابر است')
    put(o, 'verified_and_not_policy_pending_definitions', one(f"SELECT count(*) FROM kpi_catalogue WHERE verification_status='INDEPENDENTLY_VERIFIED' AND calc_status='CALCULATED_AND_VERIFIED'{w}", *a), 'تأییدشده عددی و بدون وابستگی به سیاست حسابداری')
    put(o, 'policy_pending_definitions', one(f"SELECT count(*) FROM kpi_catalogue WHERE calc_status='CALCULATED_BUT_ACCOUNTING_POLICY_PENDING'{w}", *a), 'محاسبه‌شده ولی وابسته به تصمیم حسابداری')
    put(o, 'partially_calculable_definitions', one(f"SELECT count(*) FROM kpi_catalogue WHERE calc_status='PARTIALLY_CALCULABLE'{w}", *a), 'جزئی')
    put(o, 'not_calculable_definitions', one(f"SELECT count(*) FROM kpi_catalogue WHERE calc_status LIKE 'REQUIRES_%'{w}", *a), 'نیازمند داده/تعریف')
    put(o, 'result_rows_total', one(f'SELECT count(*) FROM kpi_results WHERE 1=1{w}', *a), 'ردیف‌های نتیجه (KPI × سال × پنجره)')
    put(o, 'result_rows_with_value', one(f'SELECT count(*) FROM kpi_results WHERE (value IS NOT NULL OR numerator IS NOT NULL){w}', *a), 'ردیف‌های دارای مقدار')
    put(o, 'verified_kpi_period_observations', one(f"SELECT count(*) FROM kpi_results WHERE verification_status='INDEPENDENTLY_VERIFIED' AND (value IS NOT NULL OR numerator IS NOT NULL){w}", *a), 'مشاهدات KPI×دوره با بازمحاسبه مستقل')

# --------------------------------------------------------------- recharge bridge (why TM-K05/K14 are not independently verified)
cur.execute('DROP TABLE IF EXISTS kpi_recharge_bridge')
cur.execute('CREATE TABLE kpi_recharge_bridge(fy, window, step, description, lines, amount)')
for fy, w in (('1404', 'FULL_YEAR'), ('1405', 'ALL_AVAILABLE')):
    pipe = one("SELECT value FROM metric_values WHERE org='Terminals' AND fy=? AND window=? AND metric_id='M_RECHARGE'", fy, w)
    W = '' if w == 'FULL_YEAR' else ''
    a113 = q("SELECT count(*),sum(s.bed) FROM sanad s JOIN doc_class d ON d.doc_key=s.doc_key WHERE s.org='Terminals' AND s.fy=? AND s.kol='113' AND s.moeen='1' AND s.taf1='1' AND d.kind='REGULAR' AND s.bed>0", fy)[0]
    notin = q("SELECT count(*),sum(s.bed) FROM line_event e JOIN sanad s ON s.sid=e.sid JOIN doc_class d ON d.doc_key=e.doc_key WHERE e.org='Terminals' AND e.fy=? AND s.kol='113' AND s.moeen='1' AND s.taf1='1' AND d.kind='REGULAR' AND s.bed>0 AND NOT (e.role='DRIVER' AND e.rule_id LIKE 'TX-%')", fy)[0]
    other = q("SELECT count(*),sum(s.bed) FROM line_event e JOIN sanad s ON s.sid=e.sid WHERE e.org='Terminals' AND e.fy=? AND e.rule_id LIKE 'TX-%' AND e.role='DRIVER' AND NOT (s.kol='113' AND s.moeen='1' AND s.taf1='1')", fy)[0]
    recon = (a113[1] or 0) - (notin[1] or 0) + (other[1] or 0)
    for st, d, n, v in ((1, 'حساب‌محور: بدهکار ۱۱۳-۱-۱ در اسناد منظم', a113[0], a113[1]), (2, '− خطوط ۱۱۳-۱-۱ که در تعریف هزینه تحمیل‌شده نیستند (جزء/ارزش افزوده/جبران‌سازی؛ نقش COMPONENT یا قاعده غیر TX)', notin[0], -(notin[1] or 0)),
                        (3, '+ خطوط TX-* روی حساب‌های دیگر (۱۱۳-۱-۳، ۱۱۳-۱-۶ …)', other[0], other[1]), (4, '= بازسازی', None, recon), (5, 'M_RECHARGE خط‌لوله (metric_values)', None, pipe), (6, 'اختلاف', None, recon - pipe)):
        cur.execute('INSERT INTO kpi_recharge_bridge VALUES(?,?,?,?,?,?)', (fy, w, st, d, n, v))
con.commit()
for r in q('SELECT * FROM kpi_counts WHERE organization IN ("ALL","Terminals","Taxi") ORDER BY organization,metric'): print(r[:3])
print(q('SELECT kpi_id,catalogue_status,distinct_result_statuses,consistent,verification_status FROM kpi_status_consistency WHERE consistent<>"YES" OR verification_status="NOT_INDEPENDENTLY_VERIFIED"'))
for r in q('SELECT * FROM kpi_recharge_bridge'): print(r)
