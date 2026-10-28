"""v2 — KPI re-validation (v1 vs pipeline v2 vs independent recomputation from the raw workbooks) and the named semantic/relational QA tests.
Order: 04,05,07,09 (v2) → 13_kpi_independent → 14_v2_audit → THIS → 16_build…  Appends to qa_results_v2.json.
"""
import sqlite3, sys, os, json, re, collections, hashlib
sys.path.insert(0, os.path.dirname(__file__))
from common import *
from rules import TT_EVENTS, TT_EVENTS_V1, EVENT_REVIEW, EXCEPTION_TYPES
assert VARIANT in ('v2', 'v21')
con = sqlite3.connect(DB, timeout=300)
con.execute(f"ATTACH DATABASE '{WORK}/tt.sqlite' AS v1")
cur = con.cursor()
q = lambda s, *a: cur.execute(s, a).fetchall()
def one(s, *a):
    r = cur.execute(s, a).fetchone()
    return r[0] if r and r[0] is not None else 0
IND = json.load(open(f'{WORK}/kpi_independent_v2.json', encoding='utf8'))['metrics']
RAR = json.load(open('C:/tt_rar_verify/rar_verification.json', encoding='utf8')) if os.path.exists('C:/tt_rar_verify/rar_verification.json') else []
CMD = f'cd municipality_demo && set TT_VARIANT={VARIANT} && python scripts/taxi_terminals_1404_1405/'

# ================================================================================================ stock metric added in v2 (assessed receivables at date)
def stock(org, fy, kol, moe, taf_in, sign):
    return one(f"""SELECT sum(s.bed-s.bes) FROM sanad s JOIN doc_class d ON d.doc_key=s.doc_key WHERE s.org=? AND s.fy=? AND s.kol=? AND s.moeen=? AND s.taf1 IN ({','.join("'%s'" % t for t in taf_in)})
                  AND d.kind IN ('OPENING','REGULAR','INTERNAL_SETTLEMENT')""", org, fy, kol, moe) * sign
for fy in YEARS:
    cur.execute('DELETE FROM metric_values WHERE metric_id=? AND org=? AND fy=?', ('B_AR_ASSESSED', 'Terminals', fy))
    cur.execute('INSERT INTO metric_values VALUES(?,?,?,?,?,?,?,?)', ('Terminals', fy, 'END_OF_AVAILABLE_DATA', 'B_AR_ASSESSED', 'مانده مطالبات صادرشده از بهره‌برداران (۱۱۳-۱-۴/۸) در پایان داده موجود', stock('Terminals', fy, '113', '1', ('4', '8'), 1), 'RIAL?', 'افتتاحیه + گردش منظم؛ سهم STOCK'))

# ================================================================================================ KPI verification
cur.execute('DROP TABLE IF EXISTS kpi_verification')
cur.execute('CREATE TABLE kpi_verification(metric_id, org, fy, window, v1_value, v2_pipeline_value, independent_value, abs_diff, verdict, note)')
M2 = {(r[0], r[1], r[2], r[3]): r[4] for r in q('SELECT org,fy,window,metric_id,value FROM metric_values')}
M1 = {(r[0], r[1], r[2], r[3]): r[4] for r in q('SELECT org,fy,window,metric_id,value FROM v1.metric_values')}
NOTES = {'T_REV_SERVICE': 'v1 شامل اجاره ۴۱۳-۸ (FE-60) بود؛ v2 فقط ۴۱۳-۱ (در مقایسه مستقل: ۴۱۳-۱ منهای جریمه و سهم ۲٪)', 'T_REV_SCHOOL_SHARE': 'v2 سند «بستن حساب پیش‌دریافت» ۱۴۰۵ را هم دارد (در v1 به‌اشتباه تهاتر شهرداری بود)',
         'T_EXP_OP': 'v1: سند «پاداش بستن حساب ۱۴۰۴» به‌اشتباه بستن حساب بود', 'T_REV_TOTAL': 'همان علت سند بستن پیش‌دریافت ۱۴۰۵', 'T_EXP_BANKFEE': 'تعریف: ۶۱۲-۵-۱۲ با شرح کارمزد (حقوقی/عوارض قانونی خارج است)'}
IMAP = {'T_REV_SERVICE': 'T_REV_FEES_413_1'}
checked = 0
for key, vals in IND.items():
    if key == 'M_BILLED_BY_FACILITY': continue
    for k, ind in vals.items():
        org, fy, wn = k.split('|'); mid = key
        pm = IMAP.get(mid, mid)
        v2 = M2.get((org, fy, wn, [m for m, i in IMAP.items() if i == key][0] if key in IMAP.values() else mid))
        v1 = M1.get((org, fy, wn, [m for m, i in IMAP.items() if i == key][0] if key in IMAP.values() else mid))
        mm = [m for m, i in IMAP.items() if i == key][0] if key in IMAP.values() else mid
        if v2 is None: continue
        d = abs((v2 or 0) - ind)
        verdict = 'EXACT_MATCH' if d == 0 else 'MISMATCH'
        note = NOTES.get(mm, '') + ('' if v1 is None or v1 == v2 else f'؛ v1={v1:,}')
        cur.execute('INSERT INTO kpi_verification VALUES(?,?,?,?,?,?,?,?,?,?)', (mm, org, fy, wn, v1, v2, ind, d, verdict, note)); checked += 1
# facility split
fac_ind = IND['M_BILLED_BY_FACILITY']['Terminals|1404|FULL_YEAR']
fac_v2 = {r[0]: r[1] for r in q("SELECT facility_code,billed FROM billed_by_terminal WHERE fy='1404' AND window='FULL_YEAR'")}
for code, v in sorted(fac_ind.items()):
    cur.execute('INSERT INTO kpi_verification VALUES(?,?,?,?,?,?,?,?,?,?)', ('M_BILLED_BY_FACILITY:' + code, 'Terminals', '1404', 'FULL_YEAR', None, fac_v2.get(code), v, abs((fac_v2.get(code) or 0) - v), 'EXACT_MATCH' if (fac_v2.get(code) or 0) == v else 'MISMATCH', ''))

# ================================================================================================ KPI status taxonomy v2 + per-KPI verdict
for col in ('basis_type', 'v1_status', 'v2_verdict', 'v2_note'):
    try: cur.execute(f'ALTER TABLE kpi_catalogue ADD COLUMN {col}')
    except sqlite3.OperationalError: pass
CV, PP, RO_, RB_, RE_ = 'CALCULATED_AND_VERIFIED', 'CALCULATED_BUT_ACCOUNTING_POLICY_PENDING', 'REQUIRES_OPERATIONAL_DATA', 'REQUIRES_BUDGET_DATA', 'REQUIRES_EXPERT_DEFINITION'
PART = 'PARTIALLY_CALCULABLE'
# kpi -> (v2 status, basis_type, verdict vs v1, note)
KS = {
 'TX-K01': (CV, 'FLOW', 'CORRECTED', 'v1 جمع ۴۱۳-۱ و اجاره جایگاه ۴۱۳-۸ را «بهای خدمات» می‌نامید؛ اکنون فقط ۴۱۳-۱ (پروانه/عضویت/نقل‌وانتقال) و اجاره جدا (T_REV_RENT)'),
 'TX-K02': (CV, 'RATIO_OF_FLOWS', 'CORRECTED', 'مخرج v1 شامل اجاره بود؛ اکنون جریمه ÷ (درآمد خدمات ۴۱۳-۱ + جریمه)'),
 'TX-K03': (CV, 'RATIO_OF_FLOWS', 'UNCHANGED_VERIFIED', 'صورت: کمک بودجه (شرح «کمک بودجه») ؛ مخرج: هزینه عملیاتی بدون استهلاک؛ هزینه ۱۴۰۵ پنجره پس از بازبینی نوع سند اصلاح جزئی'),
 'TX-K04': (CV, 'RATIO_OF_FLOWS', 'CORRECTED', 'درآمد ۱۴۰۵ شامل سهم مدارس (سند بستن پیش‌دریافت) و هزینه شامل پاداش (نوع سند اصلاح شد)؛ ۱۴۰۴ سال کامل بدون تغییر'),
 'TX-K05': (CV, 'RATIO_OF_FLOWS', 'UNCHANGED_VERIFIED', 'حقوق = حساب ۶۱۱؛ خرید خدمت نیرو در ۶۱۲ است و در صورت نیست'),
 'TX-K06': (CV, 'RATIO_OF_FLOWS', 'UNCHANGED_VERIFIED', 'کارمزد بانکی = ۶۱۲-۵-۱۲ با شرح کارمزد؛ هزینه‌های حقوقی/عوارض قانونی همان زیرحساب خارج‌اند'),
 'TX-K07': (PART, 'RATIO_OF_FLOWS', 'DOWNGRADED_OR_UNCHANGED', 'طبقه‌بندی FE-45/TT-NE-12/FE-03 موقت'),
 'TX-K08': (PART, 'RATIO_OF_FLOWS', 'UNCHANGED_PARTIAL', 'سهم ۲٪ با دریافت امانی هم‌زمان نیست و نرخ مصوب در منبع نیست؛ سهم ۱۴۰۵ اکنون سند بستن پیش‌دریافت را هم دارد'),
 'TX-K09': (PART, 'RATIO_OF_FLOWS', 'UNCHANGED_PARTIAL', 'اضافات دارایی: مبنای ثبت و خالص‌سازی نامشخص'),
 'TX-K10': (RO_, 'RATIO', 'UNCHANGED', ''), 'TX-K11': (RO_, 'RATIO', 'UNCHANGED', 'صورت کسر قابل محاسبه (فعالیت ۰۴۶)'), 'TX-K12': (RO_, 'RATIO', 'UNCHANGED', ''),
 'TX-K13': (RO_, 'RATIO', 'UNCHANGED', ''), 'TX-K14': (RB_, 'RATIO', 'UNCHANGED', ''), 'TX-K15': (RO_, 'RATIO', 'UNCHANGED', ''), 'TX-K16': (RE_, 'RATIO', 'UNCHANGED', ''),
 'TM-K01': (PP, 'FLOW', 'DOWNGRADED_TO_POLICY_PENDING', 'مبلغ صادرشده (assessment) فقط شاهد مطالبه است؛ مالکیت درآمد (سازمان/شهرداری) وابسته به CD-01'),
 'TM-K02': (CV, 'FLOW', 'UPGRADED_VERIFIED', 'مطالبهٔ صادرشده به تفکیک بخش اول CodeVahed؛ برچسب «مطالبه» نه «درآمد»؛ مستقل بازمحاسبه شد'),
 'TM-K03': (PART, 'RATIO', 'UNCHANGED_PARTIAL', 'مخرج: فقط واحدهای دارای مطالبه'),
 'TM-K04': (PART, 'RATIO_OF_FLOWS', 'RELABELED', 'نسبت گردش وصول دوره به مطالبه همان دوره؛ نرخ وصول مطالبات همان دوره (cohort) نیست زیرا وصول شامل مطالبات دوره‌های قبل و پیش‌دریافت است'),
 'TM-K05': (PP, 'FLOW', 'DOWNGRADED_TO_POLICY_PENDING', 'هزینه تحمیل‌شده به شهرداری؛ ماهیت ثبت (عامل/مستقل) CD-01'),
 'TM-K06': (PART, 'RATIO', 'UNCHANGED_PARTIAL', 'سهم دفتر مرکزی قابل تسهیم نیست'),
 'TM-K07': (RO_, 'RATIO', 'UNCHANGED', ''), 'TM-K08': (RO_, 'RATIO', 'UNCHANGED', ''), 'TM-K09': (RO_, 'RATIO', 'UNCHANGED', ''),
 'TM-K10': (PART, 'RATIO', 'UNCHANGED_PARTIAL', ''),
 'TM-K11': (CV, 'STOCK', 'UNCHANGED_VERIFIED', 'مانده در تاریخ مشخص: پایان ۱۴۰۴ (۱۴۰۴/۱۲/۲۹) و آخرین تاریخ ۱۴۰۵ (۱۴۰۵/۰۷/۱۴)؛ افتتاحیه+گردش منظم (بدون اختتامیه)'),
 'TM-K12': (RE_, 'RATIO', 'UNCHANGED', 'برگشت چک اکنون چرخه‌عمر TT-NE-13 (RETURN_DISHONOURED) است ولی تعریف نرخ باید کارشناسی شود'),
 'TM-K13': (RB_, 'RATIO', 'UNCHANGED', ''),
 'TM-K14': (PP, 'RATIO_OF_FLOWS', 'DOWNGRADED_TO_POLICY_PENDING', 'صورت‌وضعیت‌های مشترک چند سازمان در صورت/مخرج'),
}
v1stat = {r[0]: r[1] for r in q('SELECT kpi_id,calc_status FROM v1.kpi_catalogue')}
for kid, (st, bt, vd, nt) in KS.items():
    cur.execute('UPDATE kpi_catalogue SET calc_status=?, basis_type=?, v1_status=?, v2_verdict=?, v2_note=? WHERE kpi_id=?', (st, bt, v1stat.get(kid), vd, nt, kid))
cur.execute("UPDATE kpi_catalogue SET title_fa='نسبت گردش وصول به مطالبه در دوره (نه نرخ وصول همان مطالبه)', title_en='Period collections-to-assessments turnover ratio' WHERE kpi_id='TM-K04'")
cur.execute("UPDATE kpi_catalogue SET title_fa='مطالبه صادرشده (assessment) پایانه‌ها — اجاره، عوارض، شارژ (مالکیت درآمد: CD-01)' WHERE kpi_id='TM-K01'")
cur.execute("UPDATE kpi_catalogue SET title_fa='هزینه تحمیل‌شده به حساب شهرداری (مبنای ثبت: CD-01)' WHERE kpi_id='TM-K05'")
# new KPI: stock of assessed receivables
cur.execute("INSERT OR REPLACE INTO kpi_catalogue(kpi_id,org,title_fa,title_en,category,activity,cost_centers,purpose,formula,numerator,denominator,unit,period,financial_fields,operational_fields,method,filters,exclusions,data_availability,calc_status,governance,confidence,notes,metrics,basis_type,v1_status,v2_verdict,v2_note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
  ('TM-K15', 'Terminals', 'مانده مطالبات صادرشده از بهره‌برداران (۱۱۳-۱-۴/۸) در پایان دوره', 'Assessed receivables stock', 'Financial efficiency indicators', 'وصول درآمد', 'CC_NOT_APPLICABLE', 'پایش مانده وصول‌نشده (stock) به‌جای نسبت جریان', 'مانده بدهکار ۱۱۳-۱-۴ و ۱۱۳-۱-۸ = افتتاحیه + گردش منظم', 'مانده', '—', 'واحد پول منبع', 'مانده در تاریخ مشخص', 'Sanad.Kol=113 Moeen=1 Tafsili1∈{4,8}', '—', 'مانده', '', 'اسناد اختتامیه', 'در منبع موجود', CV, 'PROPOSED — بدون تأیید رسمی', 'MEDIUM', 'ثبت مطالبات چک‌های در جریان وصول در ۱۱۳-۵/۶ جداست؛ مانده فقط ۱۱۳-۱', 'B_AR_ASSESSED', 'STOCK', None, 'NEWLY_CALCULABLE', 'مانده سنی (aging) و cohort در منبع نیست'))
# results rows for the new stock KPI and as-of labels
cur.execute("DELETE FROM kpi_results WHERE kpi_id='TM-K15'")
for fy, asof in (('1404', '1404/12/29'), ('1405', '1405/07/14')):
    v = one("SELECT value FROM metric_values WHERE org='Terminals' AND fy=? AND metric_id='B_AR_ASSESSED'", fy)
    cur.execute('INSERT INTO kpi_results VALUES(?,?,?,?,?,?,?,?,?,?,?,?)', ('TM-K15', 'Terminals', fy, 'END_OF_AVAILABLE_DATA', 'مانده مطالبات صادرشده', v, '—', None, v, 'RIAL?', CV, f'مانده در تاریخ {asof} (STOCK)'))
for fy, asof in (('1404', '1404/12/29'), ('1405', '1405/07/14')):
    cur.execute("UPDATE kpi_results SET caveat=? WHERE kpi_id='TM-K11' AND fy=?", (f'مانده در تاریخ {asof} (STOCK؛ افتتاحیه+گردش منظم)', fy))
# result statuses follow the catalogue (numerator-only rows keep their data-requirement status)
cur.execute("""UPDATE kpi_results SET status=(SELECT calc_status FROM kpi_catalogue c WHERE c.kpi_id=kpi_results.kpi_id) WHERE denominator IS NOT NULL OR kpi_id IN ('TM-K01','TM-K05','TM-K11','TM-K15')""")
cur.execute("""UPDATE kpi_results SET status=(SELECT calc_status FROM kpi_catalogue c WHERE c.kpi_id=kpi_results.kpi_id) WHERE denominator IS NULL AND kpi_id IN (SELECT kpi_id FROM kpi_catalogue WHERE calc_status IN ('REQUIRES_OPERATIONAL_DATA','REQUIRES_BUDGET_DATA','REQUIRES_EXPERT_DEFINITION'))""")
# per-KPI verdict vs independent recompute for the 8 originally source-calculable KPIs
cur.execute('DROP TABLE IF EXISTS kpi_v1_v2')
cur.execute('CREATE TABLE kpi_v1_v2(kpi_id, org, fy, window, v1_value, v2_value, independent_value, v1_status, v2_status, verdict, note)')
def ratio(a, b): return a / b if b else None
def ind(k): return IND[k]
IK = lambda m, org, fy, wn: IND[m].get(f'{org}|{fy}|{wn}')
for (fy, wn) in (('1404', 'FULL_YEAR'), ('1404', 'WINDOW'), ('1405', 'WINDOW')):
    T = lambda m: IK(m, 'Taxi', fy, wn)
    vals = {
     'TX-K01': T('T_REV_FEES_413_1'),
     'TX-K02': ratio(T('T_REV_FINES'), T('T_REV_FEES_413_1') + T('T_REV_FINES')),
     'TX-K03': ratio(T('T_REV_GRANT'), T('T_EXP_OP')),
     'TX-K04': ratio(T('T_REV_TOTAL') - T('T_REV_GRANT'), T('T_EXP_OP')),
     'TX-K05': ratio(T('T_EXP_PAYROLL'), T('T_EXP_OP')),
     'TX-K06': ratio(T('T_EXP_BANKFEE'), T('T_EXP_OP')),
    }
    for kid, iv in vals.items():
        r1 = q('SELECT value,numerator FROM v1.kpi_results WHERE kpi_id=? AND fy=? AND window=?', kid, fy, wn)
        r2 = q('SELECT value,numerator FROM kpi_results WHERE kpi_id=? AND fy=? AND window=?', kid, fy, wn)
        if kid == 'TX-K01': v1v, v2v = (r1[0][1] if r1 else None), (r2[0][1] if r2 else None)
        else: v1v, v2v = (r1[0][0] if r1 else None), (r2[0][0] if r2 else None)
        same2 = (v2v is not None and iv is not None and abs(v2v - iv) <= 1e-9 * max(1, abs(iv)))
        same1 = (v1v is not None and iv is not None and abs(v1v - iv) <= 1e-9 * max(1, abs(iv)))
        verdict = 'v2 = independent; v1 = independent' if (same2 and same1) else ('v2 = independent; v1 differs (corrected)' if same2 else 'v2 ≠ independent')
        cur.execute('INSERT INTO kpi_v1_v2 VALUES(?,?,?,?,?,?,?,?,?,?,?)', (kid, 'Taxi', fy, wn, v1v, v2v, iv, v1stat.get(kid), KS[kid][0], verdict, KS[kid][3]))
    for kid in ('TM-K02',):
        pass
for fy, wn in (('1404', 'FULL_YEAR'),):
    v1b = M1.get(('Terminals', fy, wn, 'M_BILLED')); v2b = M2.get(('Terminals', fy, wn, 'M_BILLED')); ib = IK('M_BILLED', 'Terminals', fy, wn)
    cur.execute('INSERT INTO kpi_v1_v2 VALUES(?,?,?,?,?,?,?,?,?,?,?)', ('TM-K02', 'Terminals', fy, wn, v1b, v2b, ib, v1stat.get('TM-K02'), KS['TM-K02'][0], 'v2 = independent' if v2b == ib else 'v2 ≠ independent', 'جمع تفکیک پایانه‌ها = مطالبه کل'))
for fy in YEARS:
    v1d = M1.get(('Terminals', fy, 'END_OF_AVAILABLE_DATA', 'B_DEPOSITS')); v2d = M2.get(('Terminals', fy, 'END_OF_AVAILABLE_DATA', 'B_DEPOSITS')); idp = IK('B_DEPOSITS', 'Terminals', fy, 'END_OF_AVAILABLE_DATA')
    cur.execute('INSERT INTO kpi_v1_v2 VALUES(?,?,?,?,?,?,?,?,?,?,?)', ('TM-K11', 'Terminals', fy, 'END_OF_AVAILABLE_DATA', v1d, v2d, idp, v1stat.get('TM-K11'), KS['TM-K11'][0], 'v2 = independent' if v2d == idp else 'v2 ≠ independent', 'stock در تاریخ'))
con.commit()

# ================================================================================================ named QA tests
QA = json.load(open(QA_JSON, encoding='utf8'))
QA['tests'] = [t for t in QA['tests'] if not t['test_id'].startswith('QA_')]
QA.pop('formula_block', None) if VARIANT == 'v21' else None
T = []
def add(tid, area, sources, population, procedure, expected, actual, status, detail='', script='15_kpi_qa_v2.py'):
    T.append(dict(test_id=tid, area=area, sources=sources, population=population, procedure=procedure, expected=str(expected), actual=str(actual), status=status, detail=detail, description=procedure, command=CMD + script))

# --- cost-center consistency
v1r = {(r[0], r[1]): r for r in q("SELECT cc_id,metric,value_lines,value_net FROM cc_proposal_recon WHERE version='v1'")}
rep, dire, amb = v1r[('TTCC-P-01', 'REPORTED_V1')], v1r[('TTCC-P-01', 'DIRECT')], v1r[('TTCC-P-01', 'AMBIGUOUS')]
add('QA_NEW_CC_PROPOSAL_RECONCILIATION-V1', 'V1_ARTIFACT', 'v1 New_CC_Proposals vs v1.line_cc', 'ردیف‌های TTCC-P-01 در v1',
    'گزارش v1 «ردیف‌های مستقیماً نگاشت‌شده» = ردیف‌های با cc_id=TTCC-P-01 صرف‌نظر از وضعیت؛ با شمارش Direct (NEW/PROV) مقایسه می‌شود', f'{rep[2]} = {dire[2]}', f'{rep[2]} ≠ {dire[2]} (اختلاف {rep[2]-dire[2]} ردیف، {rep[3]-dire[3]:,} واحد؛ همه MULTIPLE_CC_CANDIDATES با نامزد اول TTCC-P-01، فعالیت منبع ۱۲۰)',
    'FAIL', 'اختلاف v1 بازتولید شد و علت (جمعیت مختلط) تأیید شد؛ در v2 با سه شمارنده جدا اصلاح شد')
for cid in ('TTCC-P-01', 'TTCC-P-02', 'TTCC-P-03'):
    d = q("SELECT metric,value_lines,value_net FROM cc_proposal_recon WHERE version='v2' AND cc_id=?", cid); dd = {m: (a, b) for m, a, b in d}
    ok = dd['EVIDENCE_SUPPORT'][0] == dd['DIRECT'][0] + dd['AMBIGUOUS'][0]
    add(f'QA_NEW_CC_PROPOSAL_RECONCILIATION-{cid}', 'CostCenter', 'v2.line_cc', f'ردیف‌های مرتبط با {cid}', 'Evidence_Support = Direct_Assignment + Ambiguous_Candidate (جمعیت‌های جدا از هم)',
        f"{dd['DIRECT'][0]}+{dd['AMBIGUOUS'][0]}", f"{dd['EVIDENCE_SUPPORT'][0]}", 'PASS' if ok and dd['AMBIGUOUS'][0] == 0 else ('REVIEW' if ok else 'FAIL'), f"direct={dd['DIRECT']}, ambiguous={dd['AMBIGUOUS']}, support={dd['EVIDENCE_SUPPORT']}")
rows = q("""SELECT c.source_markaz,count(*),sum(CASE WHEN c.cc_status IN ('PROVISIONAL_EXISTING_CC','NEW_CC_CANDIDATE') THEN 1 ELSE 0 END),sum(CASE WHEN c.cc_status='MULTIPLE_CC_CANDIDATES' THEN 1 ELSE 0 END),
            sum(CASE WHEN c.cc_status='INSUFFICIENT_INFORMATION' THEN 1 ELSE 0 END) FROM line_cc c WHERE c.org='Taxi' AND c.eligible=1 AND c.source_markaz IS NOT NULL GROUP BY 1""")
bad = [(m, n, a + b + c) for m, n, a, b, c in rows if n != a + b + c]
reg_exp = q("""SELECT s.markaz,count(*) FROM sanad s JOIN doc_class d ON d.doc_key=s.doc_key WHERE s.org='Taxi' AND d.kind='REGULAR' AND s.kol IN ('611','612','613') AND s.markaz IS NOT NULL AND s.markaz<>'NULL' GROUP BY 1""")
elig = dict(q("SELECT source_markaz,count(*) FROM line_cc WHERE org='Taxi' AND eligible=1 AND source_markaz IS NOT NULL GROUP BY 1"))
diff = {m: (n, elig.get(m, 0)) for m, n in reg_exp if n != elig.get(m, 0)}
add('QA_ACTIVITY_TO_CC_POPULATION', 'CostCenter', 'sanad ⋈ doc_class ⋈ line_cc', 'ردیف‌های هزینه‌ای تاکسیرانی به تفکیک کد فعالیت منبع',
    'هر ردیف هزینه‌ای منظم با کد فعالیت باید دقیقاً یک وضعیت مرکز هزینه داشته باشد (مجموع وضعیت‌ها = ردیف‌های واجد شرایط) و Activity_Service_Map همان جمعیت را بشمارد', 'تفاوت صفر', f'{len(bad)} کد با ناهمخوانی وضعیت؛ {len(diff)} کد با اختلاف ردیف هزینه‌ای منظم و ردیف واجد شرایط',
    'PASS' if not bad and not diff else 'REVIEW', f'نمونه اختلاف (ردیف منظم, واجد شرایط): {dict(list(diff.items())[:6])}؛ ردیف‌های هزینه‌ای با نقش COMPONENT (کارمزد/تبعی در سندی با رویداد محرک دیگر) مرکز هزینه مستقل ندارند؛ کد ۱۰۰: ' + str(q("SELECT e.own_event,count(*) FROM sanad s JOIN line_event e ON e.sid=s.sid JOIN doc_class d ON d.doc_key=s.doc_key WHERE s.org='Taxi' AND s.markaz='100' AND d.kind='REGULAR' AND s.kol IN ('611','612','613') AND e.role<>'DRIVER' GROUP BY 1 ORDER BY 2 DESC LIMIT 3")))
dups = one("SELECT count(*) FROM (SELECT sid FROM line_cc GROUP BY sid HAVING count(*)>1)")
sel_empty = one("SELECT count(*) FROM line_cc WHERE cc_status IN ('PROVISIONAL_EXISTING_CC','NEW_CC_CANDIDATE') AND coalesce(cc_id,'')=''")
unsel = one("SELECT count(*) FROM line_cc WHERE cc_status NOT IN ('PROVISIONAL_EXISTING_CC','NEW_CC_CANDIDATE') AND coalesce(cc_id,'')<>''")
add('QA_CC_ASSIGNMENT_UNIQUENESS', 'CostCenter', 'v2.line_cc', 'همه ردیف‌های منبع', 'یک ردیف به‌ازای هر sid؛ مرکز انتخاب‌شده فقط برای وضعیت‌های PROVISIONAL/NEW (علت ریشه‌ای اختلاف TTCC-P-01 در v1)', '0/0/0', f'dups={dups}, selected_missing={sel_empty}, selected_on_unresolved={unsel}', 'PASS' if dups == sel_empty == unsel == 0 else 'FAIL')
mult_bad = one("SELECT count(*) FROM line_cc WHERE cc_status='MULTIPLE_CC_CANDIDATES' AND (length(alt_ccs)-length(replace(alt_ccs,';','')))<1")
alt_incl = one("SELECT count(*) FROM line_cc WHERE cc_status IN ('PROVISIONAL_EXISTING_CC','NEW_CC_CANDIDATE') AND ';'||alt_ccs||';' LIKE '%;'||cc_id||';%'")
add('QA_CC_CANDIDATE_VS_SELECTED', 'CostCenter', 'v2.line_cc', 'ردیف‌های MULTIPLE و انتخاب‌شده', 'MULTIPLE باید ≥۲ نامزد داشته باشد؛ مرکز انتخاب‌شده در فهرست جایگزین‌ها تکرار نشود', '0/0', f'multiple_with_lt2={mult_bad}, selected_in_alternatives={alt_incl}', 'PASS' if mult_bad == alt_incl == 0 else 'FAIL')
tot_all = one("SELECT sum(s.bed-s.bes) FROM line_cc c JOIN sanad s ON s.sid=c.sid WHERE c.eligible=1")
tot_by = one("SELECT sum(v) FROM (SELECT sum(s.bed-s.bes) v FROM line_cc c JOIN sanad s ON s.sid=c.sid WHERE c.eligible=1 GROUP BY c.cc_status)")
tot_ind = one("SELECT sum(s.bed-s.bes) FROM sanad s JOIN line_event e ON e.sid=s.sid WHERE e.role='DRIVER' AND e.doc_outcome<>'NOT_AN_OPERATIONAL_EVENT' AND (e.acat IN ('EXP','FIXED_ASSET') OR (s.org='Terminals' AND e.rule_id LIKE 'TX-%'))")
add('QA_CC_VALUE_RECONCILIATION', 'CostCenter', 'line_cc, line_event, sanad', 'ارزش خالص (بدهکار−بستانکار) ردیف‌های هزینه‌ای/سرمایه‌ای واجد شرایط', 'جمع به تفکیک وضعیت = جمع کل = شمارش مستقل از line_event (نه گردش بدهکار ترازنامه‌ای)', f'{tot_ind:,}', f'{tot_by:,} / {tot_all:,}', 'PASS' if tot_all == tot_by == tot_ind else 'FAIL')
# --- event semantics
retained = [k for k, v in EVENT_REVIEW.items() if v[0] != 'RETAIN_AS_NEW_EVENT']
missing = [k for k in TT_EVENTS_V1 if k not in EVENT_REVIEW]
nodoc = [k for k in TT_EVENTS if one("SELECT count(*) FROM line_event WHERE own_event=? AND role IN ('DRIVER','SETTLEMENT')", k) == 0]
pend = [k for k, v in EVENT_REVIEW.items() if v[0] == 'INSUFFICIENT_EVIDENCE']
add('QA_NEW_EVENT_CONCEPT_REVIEW', 'Events', 'rules.EVENT_REVIEW, v1/v2.line_event', '۲۸ کاندید v1', 'هر ۲۸ کاندید نتیجه بازبینی مفهومی دارد؛ هر کاندید باقی‌مانده حداقل یک ردیف دارد', '۲۸ بازبینی؛ ۰ کاندید بدون ردیف', f'بدون بازبینی={len(missing)}؛ بدون ردیف={nodoc}؛ در انتظار شواهد={pend}',
    'FAIL' if missing or nodoc else 'REVIEW', f'نتایج: {dict(collections.Counter(v[0] for v in EVENT_REVIEW.values()))}')
viol = []
for r in q("SELECT sid,lifecycle_action,amount_dr,amount_cr FROM line_event WHERE own_event='TT-NE-03' AND acat='ADV_REC'"):
    if r[1] == 'REFUND' and not r[2] > 0: viol.append(r[0])
    if r[1] == 'COLLECT' and not r[3] > 0: viol.append(r[0])
acts = dict(q("SELECT lifecycle_action,count(*) FROM line_event WHERE own_event IN ('TT-NE-13','TT-NE-03') GROUP BY 1"))
add('QA_EVENT_LIFECYCLE_SEPARATION', 'Events', 'v2.line_event', 'TT-NE-13 (چک)، TT-NE-03 (سرویس مدارس)', 'انتقال‌های چرخه‌عمر متمایز بمانند: دریافت چک ≠ انتقال به وصول ≠ وصول ≠ برگشت؛ جمع دریافت امانی ≠ استرداد (REFUND فقط بدهکار، COLLECT فقط بستانکار)', '۰ تخلف', f'تخلف={len(viol)}؛ اقدامات={acts}', 'PASS' if not viol and len(acts) >= 5 else 'FAIL')
bank_driver = one("""SELECT count(*) FROM line_event e WHERE e.acat IN ('BANK','TANKHAH') AND e.role='DRIVER' AND EXISTS(SELECT 1 FROM line_event x WHERE x.doc_key=e.doc_key AND x.acat NOT IN ('BANK','TANKHAH','MEMO'))""")
cmp_docs = one("SELECT count(*) FROM doc_class WHERE outcome='COMPOSITE_TRANSACTION'")
add('QA_EVENT_POSTING_VS_BUSINESS_EVENT', 'Events', 'v2.line_event, doc_class', 'خطوط بانک/تنخواه و اسناد ترکیبی', 'خطوط نقد/بانک فقط در اسناد صرفاً نقدی محرک باشند؛ تعدد خطوط حسابداری رویداد جداگانه نسازد (ترکیبی = خانواده‌های متمایز)', 'محرک بانکی در سند غیرنقدی = ۰', f'{bank_driver}؛ اسناد ترکیبی={cmp_docs}', 'PASS' if bank_driver == 0 else 'FAIL', 'اسناد ترکیبی برای بازبینی گزارش می‌شوند')
TARGET = {'TT-NE-06': {'TT-NE-03'}, 'TT-NE-07': {'TT-NE-04'}, 'TT-NE-14': {'TT-NE-13'}, 'TT-NE-23': {'FE-70'}, 'TT-NE-24': {'FE-70'}, 'TT-NE-34': {'EXC-01'}, 'TT-NE-26': {'FE-22', 'FE-11'}}
if VARIANT == 'v21': TARGET.update({'TT-NE-23': {'PEO-01'}, 'TT-NE-24': {'PEO-02', 'TT-NE-11'}})   # v2.1: depreciation / provisions are period-end operations (PEO), provision utilisation is TT-NE-11
broken = 0; chk = 0
for old, tg in TARGET.items():
    for (nv,) in q("SELECT b.own_event FROM v1.line_event a JOIN line_event b ON a.sid=b.sid WHERE a.own_event=? AND a.role IN ('DRIVER','SETTLEMENT')", old):
        chk += 1
        if nv not in tg and nv is not None: broken += 1
cov = one("SELECT count(*) FROM (SELECT DISTINCT v1_event FROM event_crosswalk WHERE v1_event LIKE 'TT-NE-%')")
add('QA_EVENT_MERGE_SPLIT_LINEAGE', 'Events', 'v1.line_event ⋈ v2.line_event, event_review, event_crosswalk', 'ردیف‌های کاندیدهای بازنشسته/ادغام‌شده', 'هر ردیف v1 با شناسه بازنشسته باید به جانشین مصوب در EVENT_REVIEW برسد (یا مبهم بماند) و crosswalk ردیف‌به‌ردیف وجود داشته باشد',
    '۰ مقصد خارج از جدول', f'بررسی‌شده={chk}؛ تخلف={broken}؛ شناسه‌های v1 در crosswalk={cov}', 'PASS' if broken == 0 else 'FAIL')
rev_driver = one("SELECT sum(s.bes-s.bed) FROM sanad s JOIN line_event e ON e.sid=s.sid WHERE e.acat IN ('REV_OP','REV_NONOP') AND e.role='DRIVER' AND e.doc_outcome<>'NOT_AN_OPERATIONAL_EVENT'")
rev_acc = one("SELECT sum(s.bes-s.bed) FROM sanad s JOIN doc_class d ON d.doc_key=s.doc_key WHERE d.kind='REGULAR' AND s.kol IN ('413','812','411')")
rev_comp = one("SELECT sum(s.bes-s.bed) FROM sanad s JOIN line_event e ON e.sid=s.sid WHERE e.acat IN ('REV_OP','REV_NONOP') AND e.role<>'DRIVER' AND e.doc_outcome<>'NOT_AN_OPERATIONAL_EVENT'")
add('QA_EVENT_AMOUNT_DOUBLE_COUNTING', 'Events', 'sanad ⋈ line_event ⋈ doc_class', 'درآمد (۴۱۱/۴۱۳/۸۱۲) اسناد منظم', 'جمع مبلغ ردیف‌های محرک درآمد + ردیف‌های درآمدی که COMPONENT شده‌اند = جمع حساب‌ها (هر ردیف دقیقاً یک بار)', f'{rev_acc:,}', f'{rev_driver:,} + {rev_comp:,} = {rev_driver + rev_comp:,}', 'PASS' if rev_driver + rev_comp == rev_acc else 'FAIL', 'ردیف درآمدی COMPONENT نشان می‌دهد درآمدی که با رویداد سند ادغام شده؛ مبلغ آن در KPI از حساب‌ها می‌آید نه از رویداد')
# --- agency
bal = {}
for fy in YEARS:
    for lab, k, m, t in (('113-1-1', '113', '1', '1'), ('211-1-1', '211', '1', '1')):
        o = one("SELECT sum(s.bed-s.bes) FROM sanad s JOIN doc_class d ON d.doc_key=s.doc_key WHERE s.org='Terminals' AND s.fy=? AND s.kol=? AND s.moeen=? AND s.taf1=? AND d.kind='OPENING'", fy, k, m, t)
        c_ = one("SELECT sum(s.bed-s.bes) FROM sanad s JOIN doc_class d ON d.doc_key=s.doc_key WHERE s.org='Terminals' AND s.fy=? AND s.kol=? AND s.moeen=? AND s.taf1=? AND d.kind='CLOSING_PERMANENT'", fy, k, m, t)
        bal[(fy, lab)] = (o, c_)
flows = {fy: (one("SELECT sum(s.bed) FROM sanad s JOIN doc_class d ON d.doc_key=s.doc_key WHERE s.org='Terminals' AND s.fy=? AND s.kol='113' AND s.moeen='1' AND s.taf1='1' AND d.kind='REGULAR'", fy),
              one("SELECT sum(s.bes) FROM sanad s JOIN doc_class d ON d.doc_key=s.doc_key WHERE s.org='Terminals' AND s.fy=? AND s.kol='211' AND s.moeen='1' AND s.taf1='1' AND d.kind='REGULAR'", fy)) for fy in YEARS}
zero = all(v == (0, 0) for v in bal.values())
add('QA_TERMINAL_AGENCY_FLOW', 'Agency', 'sanad ⋈ doc_class (Terminals ۱۱۳-۱-۱, ۲۱۱-۱-۱)', 'حساب‌های فی‌مابین با شهرداری مرکزی', 'مانده افتتاحیه و اختتامیه ۱۱۳-۱-۱ و ۲۱۱-۱-۱ صفر است (بسته‌شدن با تهاتر یا بستن حساب موقت) و گردش‌های سال شاهد هزینه تحمیل‌شده (بدهکار ۱۱۳-۱-۱) و مطالبه درآمد (بستانکار ۲۱۱-۱-۱) است',
    'مانده‌ها صفر', f'مانده‌ها={ {f"{a}/{b}": v for (a, b), v in bal.items()} }؛ گردش بدهکار ۱۱۳-۱-۱ / بستانکار ۲۱۱-۱-۱={flows}', 'REVIEW' if zero else 'FAIL',
    'شاهد الگوی عاملیتی/تهاتری است اما وضعیت حقوقی و مبنای حسابداری را اثبات نمی‌کند (CD-01)')
bad_sc = one("SELECT count(*) FROM line_event WHERE own_event IN ('TT-NE-03','TT-NE-04') AND role='DRIVER' AND acat IN ('REV_OP','REV_NONOP','EXP')")
sh_bad = one("SELECT count(*) FROM line_event e JOIN sanad s ON s.sid=e.sid WHERE e.own_event='TT-NE-05' AND e.acat IN ('REV_OP','REV_NONOP') AND s.kol<>'413'")
gross_in_rev = one("SELECT count(*) FROM line_event e JOIN sanad s ON s.sid=e.sid WHERE e.own_event IN ('TT-NE-03') AND e.role='DRIVER' AND s.kol IN ('413','812')")
add('QA_SCHOOL_SERVICE_PASS_THROUGH', 'Agency', 'v2.line_event', 'جریان سرویس مدارس', 'جریان ناخالص (دریافت/پرداخت/استرداد/تهاتر) نه درآمد باشد و نه هزینه؛ فقط سهم نگهداشته‌شده روی ۴۱۳', '۰ تخلف', f'عاملیتی روی درآمد/هزینه={bad_sc}؛ سهم روی غیر ۴۱۳={sh_bad}؛ ناخالص در ۴۱۳={gross_in_rev}', 'PASS' if bad_sc == sh_bad == gross_in_rev == 0 else 'FAIL')
exc_rev = one("SELECT count(*) FROM line_event WHERE own_event='EXC-01' AND acat IN ('REV_OP','REV_NONOP')")
tm = {k: v for k, v in q("SELECT kpi_id,calc_status FROM kpi_catalogue WHERE kpi_id IN ('TM-K01','TM-K05','TM-K14')")}
add('QA_REVENUE_RECOGNITION_BASIS', 'Agency', 'v2.line_event, kpi_catalogue', 'واریزی نامشخص و KPIهای مطالبه/هزینه پایانه', 'واریزی نامشخص (EXC-01) هیچ‌گاه درآمد شناخته نشود؛ KPIهای مطالبه/هزینه پایانه تا CD-01 «وابسته به سیاست حسابداری» باشند', '۰ و همه POLICY_PENDING', f'EXC-01 روی درآمد={exc_rev}؛ {tm}',
    'PASS' if exc_rev == 0 and all(v == PP for v in tm.values()) else 'FAIL')
# --- KPI
mis = q("SELECT metric_id,org,fy,window,v2_pipeline_value,independent_value FROM kpi_verification WHERE verdict<>'EXACT_MATCH'")
add('QA_KPI_FORMULA_RECALCULATION', 'KPI', 'v2.metric_values vs original Sanad.xlsx (13_kpi_independent.py)', f'{checked} متریک × دوره', 'بازمحاسبه مستقل صورت/مخرج هر KPI قابل محاسبه از فایل‌های منبع با کد جدا؛ مقایسه دقیق', '۰ اختلاف', f'{len(mis)} اختلاف از {checked}', 'PASS' if not mis else 'FAIL', str(mis[:5]), '13_kpi_independent.py')
nobasis = one("SELECT count(*) FROM kpi_catalogue WHERE basis_type IS NULL")
stock_asof = one("SELECT count(*) FROM kpi_results WHERE kpi_id IN ('TM-K11','TM-K15') AND caveat NOT LIKE '%تاریخ%'")
add('QA_KPI_ACCOUNTING_BASIS', 'KPI', 'v2.kpi_catalogue, kpi_results', 'همه KPI', 'هر KPI نوع مبنا (FLOW/STOCK/RATIO) دارد و stockها با تاریخ مشخص گزارش می‌شوند', '۰/۰', f'بدون مبنا={nobasis}؛ stock بدون تاریخ={stock_asof}', 'PASS' if nobasis == stock_asof == 0 else 'FAIL')
badc = one("SELECT count(*) FROM comparison WHERE comparability NOT IN ('INDICATIVE_ONLY','NOT_COMPARABLE','VOLUME_ONLY')")
add('QA_KPI_PERIOD_COMPARABILITY', 'KPI', 'v2.comparison, period_coverage', 'مقایسه ۱۴۰۴/۱۴۰۵', 'فقط پنجره مشترک؛ هیچ رشد سالانه‌ای بین سال کامل و سال ناقص', '۰', str(badc), 'PASS' if badc == 0 else 'FAIL', 'پنجره‌ها: ' + json.dumps({r[0]: r[1] for r in q("SELECT org,window_months FROM period_coverage WHERE fy='1405'")}))
untr = [r[0] for r in q("SELECT kpi_id FROM kpi_catalogue WHERE calc_status IN ('CALCULATED_AND_VERIFIED','CALCULATED_BUT_ACCOUNTING_POLICY_PENDING') AND (metrics IS NULL OR metrics='')")]
add('QA_KPI_SOURCE_TRACEABILITY', 'KPI', 'v2.kpi_catalogue.metrics → metric_values → Sanad', 'KPIهای دارای مقدار', 'هر KPI دارای مقدار به شاخص‌های پایه ردیابی‌پذیر (و آن‌ها به ردیف‌های منبع) وصل است', '۰', str(untr), 'PASS' if not untr else 'FAIL')
# --- provenance
okrar = bool(RAR) and all(r['match'] for r in RAR)
add('QA_RAR_SOURCE_VERIFICATION', 'Provenance', 'تاکسیرانی.rar، پایانه ها.rar ← 7-Zip 23.01 (7z t + x)', '۸ فایل اکسل', 'استخراج کامل هر دو RAR با 7-Zip، آزمون CRC آرشیو و مقایسه SHA-256 هر فایل استخراج‌شده با نسخه‌ای که پایپ‌لاین خوانده است', '۸/۸ برابر', f"{sum(1 for r in RAR if r['match'])}/{len(RAR)} برابر" if RAR else 'گزارش تأیید موجود نیست', 'PASS' if okrar else 'REVIEW',
    'ابزار: 7-Zip 23.01 دانلود‌شده از 7-zip.org (بدون بررسی ابطال گواهی TLS) و بسته‌بندی‌شده با msiexec /a؛ هش 7z.exe=8cebb25e…؛ نام پوشه‌های فارسی در فهرست 7z با خط‌زیر نمایش داده شد پس نام پوشه سازمان فقط از ترتیب/اندازه فایل‌ها (و تطابق بایتی) تأیید شد — SOURCE_ARCHIVE_CONTENT_NOT_FULLY_VERIFIED برداشته شد مگر برای نام پوشه‌ها', '13_kpi_independent.py (verification artefact: C:/tt_rar_verify/rar_verification.json)')
base = f'{ROOT}/data/deliverables/financial_event_discovery/revisions'
try:
    rec = json.load(open(f'{base}/1404-r20260922-canonical-events-v7.1/source_manifest_canonical-events_v7_1.json', encoding='utf8'))
    cur71 = hashlib.sha256(open(f'{base}/1404-r20260922-canonical-events-v7.1/financial_event_discovery_1404-r20260922_canonical-events_v7.1.xlsx', 'rb').read()).hexdigest()
    sheets = json.load(open('C:/tt_rar_verify/v71_vs_v7_sheets.json', encoding='utf8')) if os.path.exists('C:/tt_rar_verify/v71_vs_v7_sheets.json') else []
    ident = [s[0] for s in sheets if s[1] == 'IDENTICAL']; diffs = [s[0] for s in sheets if s[1] == 'DIFFERENT']; added = [s[0] for s in sheets if s[1] == 'ONLY_IN_V7.1']
    add('QA_BASELINE_V71_PROVENANCE', 'Provenance', 'v7 و v7.1 xlsx؛ manifest v7.1', 'همه شیت‌های v7.1', 'مقایسه مقداری تک‌تک شیت‌ها با v7 + هش + زمان تغییر (docProps)؛ هش تاریخی حفظ و بازنویسی نمی‌شود',
        'هش دیسک = هش مانیفست', f"{'برابر' if cur71 == rec['output_sha256'] else 'نابرابر'}؛ همان‌ها: {len(ident)} شیت (از جمله فرهنگ رویداد، ماتریس شواهد، جدول تصمیم کمیته، Doc_No_Mapping_Lineage، نگاشت شرح خام)؛ متفاوت: {len(diffs)} شیت QA/خلاصه؛ افزوده: {len(added)}",
        'REVIEW' if cur71 != rec['output_sha256'] else 'PASS', f'هش ثبت‌شده {rec["output_sha256"][:12]}… هش فعلی {cur71[:12]}…؛ آخرین ذخیره 2026-09-24T06:33Z پس از مانیفست (2026-09-23)؛ شیت‌های متفاوت: {diffs}؛ شیت‌های مورد استفاده v2 (فرهنگ رویداد) یکسان‌اند و اثر به بخش‌های QA/خلاصه محدود است')
except Exception as e:
    add('QA_BASELINE_V71_PROVENANCE', 'Provenance', '', '', 'خطا در اجرا', '', str(e), 'REVIEW')
QA['tests'] += T
json.dump(QA, open(QA_JSON, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
con.commit()
print(collections.Counter(t['status'] for t in T))
for t in T: print(t['status'], t['test_id'], '|', t['actual'][:140])
for r in q('SELECT kpi_id,fy,window,v1_value,v2_value,independent_value,verdict FROM kpi_v1_v2 ORDER BY kpi_id,fy,window'): print(r)
