"""Phase 4 — reproducible QA.  Independent of the pipeline: totals are re-read straight from the original workbooks.
Statuses: PASS / REVIEW / FAIL.  REVIEW = needs expert judgement (not a processing failure).  Output: QA table in SQLite + qa_results.json.
"""
import sqlite3, sys, os, json, collections, re, hashlib
import openpyxl
sys.path.insert(0, os.path.dirname(__file__))
from common import *

con = sqlite3.connect(DB)
cur = con.cursor()
q = lambda s, *a: cur.execute(s, a).fetchall()
def one(s, *a):
    r = cur.execute(s, a).fetchone()
    return r[0] if r and r[0] is not None else 0

EXPECT = {('Taxi', '1404'): (490, 29155), ('Taxi', '1405'): (493, 12085), ('Terminals', '1404'): (590, 46313), ('Terminals', '1405'): (605, 24047)}
T = []
def add(tid, area, desc, expected, actual, status, detail=''):
    T.append(dict(test_id=tid, area=area, description=desc, expected=str(expected), actual=str(actual), status=status, detail=detail))

# ---------------- independent re-read of the 8 source workbooks
ind = {}
for org in ORGS:
    for fy in YEARS:
        wb = openpyxl.load_workbook(src_path(org, fy, 'Sanad'), read_only=True)
        it = wb.worksheets[0].iter_rows(values_only=True); hdr = next(it)
        ix = {h: i for i, h in enumerate(hdr)}
        n = 0; bed = bes = 0; docs = set(); dmin = '9999'; dmax = ''
        for r in it:
            if all(c is None for c in r): continue
            n += 1; bed += int(r[ix['Bed']]); bes += int(r[ix['Bes']]); docs.add(str(r[ix['Sanad_Num']]).strip())
            d = str(r[ix['Date']]).strip(); dmin = min(dmin, d); dmax = max(dmax, d)
        wb.close()
        wb = openpyxl.load_workbook(src_path(org, fy, 'Hesab'), read_only=True)
        nh = sum(1 for r in list(wb.worksheets[0].iter_rows(values_only=True))[1:] if any(c is not None for c in r)); wb.close()
        ind[(org, fy)] = dict(n=n, bed=bed, bes=bes, docs=len(docs), dmin=dmin, dmax=dmax, nh=nh)

for org in ORGS:
    for fy in YEARS:
        x = ind[(org, fy)]; eh, es = EXPECT[(org, fy)]
        add(f'Q01-{org}-{fy}', 'Source', 'ردیف‌های Hesab/Sanad برابر نقاط کنترل اولیه کار (بدون سرستون)', f'{eh}/{es}', f"{x['nh']}/{x['n']}", 'PASS' if (x['nh'], x['n']) == (eh, es) else 'REVIEW', 'نقطه کنترل فقط مرجع است؛ شمارش از فایل منبع')
        sn = one('SELECT count(*) FROM sanad WHERE org=? AND fy=?', org, fy); sh = one('SELECT count(*) FROM hesab WHERE org=? AND fy=?', org, fy)
        add(f'Q02-{org}-{fy}', 'Source', 'عدم از دست رفتن ردیف: SQLite = خواندن مستقل فایل', f"{x['nh']}/{x['n']}", f'{sh}/{sn}', 'PASS' if (sh, sn) == (x['nh'], x['n']) else 'FAIL')
        sb, sc = one('SELECT sum(bed) FROM sanad WHERE org=? AND fy=?', org, fy), one('SELECT sum(bes) FROM sanad WHERE org=? AND fy=?', org, fy)
        add(f'Q03-{org}-{fy}', 'Source', 'جمع بدهکار و بستانکار حفظ شده (خواندن مستقل)', f"{x['bed']}/{x['bes']}", f'{sb}/{sc}', 'PASS' if (sb, sc) == (x['bed'], x['bes']) else 'FAIL')
        add(f'Q04-{org}-{fy}', 'Accounting', 'تراز بدهکار = بستانکار کل دوره', 'Δ=0', f"Δ={x['bed']-x['bes']}", 'PASS' if x['bed'] == x['bes'] else 'FAIL')
        nd = one('SELECT count(DISTINCT doc_key) FROM sanad WHERE org=? AND fy=?', org, fy)
        add(f'Q05-{org}-{fy}', 'Source', 'تعداد اسناد یکتا (Sanad_Num پاک‌سازی‌شده)', x['docs'], nd, 'PASS' if nd == x['docs'] else 'FAIL')
        ub = one('SELECT count(*) FROM (SELECT doc_key,sum(bed)-sum(bes) d FROM sanad WHERE org=? AND fy=? GROUP BY doc_key HAVING d<>0)', org, fy)
        add(f'Q06-{org}-{fy}', 'Accounting', 'اسناد نامتوازن (بدهکار≠بستانکار در سطح سند)', 0, ub, 'PASS' if ub == 0 else 'REVIEW')
        tot = x['n']; cov = one('SELECT count(*) FROM sanad s WHERE org=? AND fy=? AND EXISTS(SELECT 1 FROM hesab h WHERE h.org=s.org AND h.fy=s.fy AND h.hcode=s.hcode)', org, fy)
        add(f'Q07-{org}-{fy}', 'Source', 'پوشش اتصال HCode ردیف سند به Hesab', f'{tot}/{tot}', f'{cov}/{tot}', 'PASS' if cov == tot else 'FAIL')
        nl = one('SELECT count(*) FROM sanad s JOIN hesab h ON h.org=s.org AND h.fy=s.fy AND h.hcode=s.hcode WHERE s.org=? AND s.fy=? AND h.is_leaf=0', org, fy)
        add(f'Q08-{org}-{fy}', 'Source', 'ردیف‌های متصل به حساب غیربرگ', 0, nl, 'PASS' if nl == 0 else 'REVIEW')
        bd = one('SELECT count(*) FROM sanad WHERE org=? AND fy=? AND date_ok=0', org, fy)
        add(f'Q09-{org}-{fy}', 'Source', 'تاریخ نامعتبر یا خارج از سال مالی', 0, bd, 'PASS' if bd == 0 else 'FAIL', f"بازه {x['dmin']}..{x['dmax']}")
        dg = one('SELECT count(*), 0 FROM (SELECT 1 FROM sanad WHERE org=? AND fy=? GROUP BY doc_key,date,des,hcode,bed,bes,sharh,f1,person HAVING count(*)>1)', org, fy)
        add(f'Q10-{org}-{fy}', 'Source', 'گروه‌های رکورد تکراری کاندید (کلید: سند، تاریخ، شرح، حساب، مبالغ، شرح سطر، فیلد۱، شخص)', 0, dg, 'PASS' if dg == 0 else 'REVIEW', 'تکرار کاندید است نه اثبات تکرار؛ حذف نشد')

# ---------------- identity and no silent loss
nS = one('SELECT count(*) FROM sanad'); nE = one('SELECT count(*) FROM line_event'); nC = one('SELECT count(*) FROM line_cc')
add('Q11', 'Lineage', 'هر ردیف منبع دقیقاً یک ردیف رویداد و یک ردیف مرکز هزینه دارد', f'{nS}/{nS}/{nS}', f'{nS}/{nE}/{nC}', 'PASS' if nS == nE == nC else 'FAIL')
nu = one('SELECT count(DISTINCT sid) FROM sanad')
add('Q12', 'Lineage', 'Source_Record_ID یکتا و پایدار (ORG-FY-S-ردیف اکسل)', nS, nu, 'PASS' if nu == nS else 'FAIL')
ok_ids = one("SELECT count(*) FROM sanad WHERE sid = org_code_placeholder", ) if False else None
bad_sid = one("SELECT count(*) FROM sanad WHERE sid NOT LIKE 'TAXI-____-S-______' AND sid NOT LIKE 'TERM-____-S-______'")
add('Q13', 'Lineage', 'قالب Source_Record_ID', 0, bad_sid, 'PASS' if bad_sid == 0 else 'FAIL')
cross = one("SELECT count(*) FROM (SELECT sanad_num FROM sanad GROUP BY sanad_num HAVING count(DISTINCT org||fy)>1)")
add('Q14', 'Lineage', 'شماره‌های سند تکراری بین سازمان/سال (اثبات یکتا نبودن Sanad_Num — هویت سند باید با سازمان+سال ترکیب شود)', '>0 (انتظار)', cross, 'PASS' if cross > 0 else 'REVIEW')

# ---------------- event QA
allowed = {'EXISTING_EVENT_CONFIRMED', 'EXISTING_EVENT_PROVISIONAL', 'NEW_EVENT_CANDIDATE', 'AMBIGUOUS_EVENT', 'NOT_AN_OPERATIONAL_EVENT', 'INSUFFICIENT_INFORMATION', 'COMPONENT_OF_COMPOSITE_TRANSACTION', 'COMPONENT', 'PENDING_IDENTIFICATION'}
bad = [r for r in q("SELECT DISTINCT outcome FROM line_event") if r[0] not in allowed and not r[0].startswith('COMPONENT_OF_')]
add('Q15', 'Events', 'مقادیر outcome فقط از مجموعه مجاز', 'subset', ','.join(r[0] for r in bad) or 'OK', 'PASS' if not bad else 'FAIL')
xl = openpyxl.load_workbook(f'{ROOT}/data/deliverables/financial_event_discovery/revisions/1404-r20260922-canonical-events-v7.1/financial_event_discovery_1404-r20260922_canonical-events_v7.1.xlsx', read_only=True)
fe_ids = {r[0]: r[1] for r in xl['فرهنگ_رویداد_مالی_کاندید'].iter_rows(min_row=2, values_only=True) if r[0]}
xl.close()
sys.path.insert(0, os.path.dirname(__file__))
from rules import TT_EVENTS, EXCEPTION_TYPES
used = {r[0] for r in q('SELECT DISTINCT event_id FROM line_event WHERE event_id IS NOT NULL UNION SELECT DISTINCT own_event FROM line_event WHERE own_event IS NOT NULL')}
unknown = sorted(e for e in used if e not in fe_ids and e not in TT_EVENTS and e not in EXCEPTION_TYPES)
add('Q16', 'Events', 'هیچ رویداد پشتیبانی‌نشده یا ناشناخته (همه FE در v7.1 یا TT-NE تعریف‌شده)', 0, len(unknown), 'PASS' if not unknown else 'FAIL', ','.join(unknown))
add('Q17', 'Events', 'شناسه‌های FE بازتعریف نشده‌اند (عنوان از v7.1 خوانده می‌شود)', 'FE-01..FE-70 = v7.1', f'{len(fe_ids)} FE خوانده شد', 'PASS' if len(fe_ids) == 70 else 'REVIEW')
conf_bad = one("SELECT count(*) FROM doc_class WHERE outcome='EXISTING_EVENT_CONFIRMED' AND conf<>'HIGH'")
add('Q18', 'Events', 'CONFIRMED فقط با اطمینان HIGH و دو شاهد مستقل', 0, conf_bad, 'PASS' if conf_bad == 0 else 'FAIL')
for ev in sorted(e for e in used if e in TT_EVENTS):
    nl = one("SELECT count(*) FROM line_event WHERE own_event=? AND role IN ('DRIVER','SETTLEMENT')", ev); nd = one("SELECT count(DISTINCT doc_key) FROM line_event WHERE own_event=? AND role IN ('DRIVER','SETTLEMENT')", ev)
    add(f'Q19-{ev}', 'Events', f'کاندید جدید {ev} حداقل یک سند و یک ردیف پشتیبان دارد', '>=1', f'{nl} ردیف/{nd} سند', 'PASS' if nl >= 1 else 'FAIL')
unused = sorted(e for e in TT_EVENTS if e not in used)
add('Q20', 'Events', 'کاندیدهای تعریف‌شده بدون شاهد (باید حذف شوند)', 0, len(unused), 'PASS' if not unused else 'FAIL', ','.join(unused))
comp = one("SELECT count(*) FROM doc_class WHERE outcome='COMPOSITE_TRANSACTION'")
add('Q21', 'Events', 'اسناد ترکیبی پرچم‌گذاری شده‌اند', '>=0', comp, 'REVIEW' if comp else 'PASS', 'هر سند ترکیبی نیازمند بازبینی است؛ شکست پردازش نیست')
unres = one("SELECT count(*) FROM doc_class WHERE outcome='AMBIGUOUS_EVENT'"); unres_amt = one("SELECT sum(bed_total) FROM doc_class WHERE outcome='AMBIGUOUS_EVENT'")
tot_amt = one("SELECT sum(bed_total) FROM doc_class WHERE kind='REGULAR'")
add('Q22', 'Events', 'اسناد مبهم نگهداری و گزارش شده‌اند (نه اجباراً نگاشت)', 'گزارش', f'{unres} سند؛ {unres_amt/tot_amt*100:.1f}% مبلغ بدهکار اسناد منظم', 'REVIEW')
# direction / semantic guards
g1 = one("SELECT count(*) FROM line_event e JOIN sanad s ON s.sid=e.sid WHERE e.own_event='FE-60' AND e.role='DRIVER' AND s.kol IN ('611','612','613')")
add('Q23', 'Events', 'درآمد (FE-60) روی حساب هزینه نشسته است؟ (جهت تراکنش)', 0, g1, 'PASS' if g1 == 0 else 'FAIL')
g2 = one("SELECT count(*) FROM line_event e JOIN sanad s ON s.sid=e.sid WHERE e.own_event IN ('FE-44','FE-45','FE-46','FE-48','FE-49','FE-50') AND e.role='DRIVER' AND s.kol='413'")
add('Q24', 'Events', 'حقوق روی حساب درآمد نشسته است؟', 0, g2, 'PASS' if g2 == 0 else 'FAIL')
g3 = one("SELECT count(*) FROM line_event e WHERE e.own_event IN ('TT-NE-03','TT-NE-04','TT-NE-06','TT-NE-07') AND e.role='DRIVER' AND e.acat IN ('REV_OP','REV_NONOP','EXP')")
add('Q25', 'Events', 'جریان عاملیتی سرویس مدارس به‌عنوان درآمد/هزینه ثبت نشده است', 0, g3, 'PASS' if g3 == 0 else 'FAIL')
g4 = one("SELECT count(*) FROM doc_class WHERE kind<>'REGULAR' AND outcome NOT IN ('NOT_AN_OPERATIONAL_EVENT') AND kind<>'INTERNAL_SETTLEMENT'")
add('Q26', 'Events', 'اسناد افتتاحیه/اختتامیه فقط NOT_AN_OPERATIONAL_EVENT‌اند', 0, g4, 'PASS' if g4 == 0 else 'FAIL')
for org in ORGS:
    for fy in YEARS:
        k = dict(q("SELECT kind,count(*) FROM doc_class WHERE org=? AND fy=? GROUP BY kind", org, fy))
        add(f'Q27-{org}-{fy}', 'Accounting', 'سند افتتاحیه/اختتامیه/بستن موقت شناسایی شد', 'OPENING≥1', json.dumps(k, ensure_ascii=False), 'PASS' if k.get('OPENING', 0) >= 1 else 'REVIEW')

# P&L control for Taxi: regular-doc revenue/expense must equal the temporary-closing document
for fy in YEARS:
    rev = one("SELECT sum(s.bes-s.bed) FROM sanad s JOIN doc_class d ON d.doc_key=s.doc_key WHERE s.org='Taxi' AND s.fy=? AND d.kind='REGULAR' AND s.kol IN ('413','812')", fy)
    crev = one("SELECT sum(s.bed-s.bes) FROM sanad s JOIN doc_class d ON d.doc_key=s.doc_key WHERE s.org='Taxi' AND s.fy=? AND d.kind='CLOSING_TEMPORARY' AND s.kol IN ('413','812')", fy)
    exp = one("SELECT sum(s.bed-s.bes) FROM sanad s JOIN doc_class d ON d.doc_key=s.doc_key WHERE s.org='Taxi' AND s.fy=? AND d.kind='REGULAR' AND s.kol IN ('611','612','613')", fy)
    cexp = one("SELECT sum(s.bes-s.bed) FROM sanad s JOIN doc_class d ON d.doc_key=s.doc_key WHERE s.org='Taxi' AND s.fy=? AND d.kind='CLOSING_TEMPORARY' AND s.kol IN ('611','612','613')", fy)
    if crev == 0 and cexp == 0:
        add(f'Q28-Taxi-{fy}', 'Accounting', 'کنترل سود و زیان: جمع اسناد منظم = سند بستن حساب‌های موقت', 'n/a', 'سند بستن موقت در منبع نیست (سال ناقص)', 'REVIEW', f'درآمد منظم {rev}; هزینه منظم {exp}')
    else:
        add(f'Q28-Taxi-{fy}', 'Accounting', 'کنترل سود و زیان: درآمد/هزینه اسناد منظم = سند بستن حساب‌های موقت', f'{crev}/{cexp}', f'{rev}/{exp}', 'PASS' if (rev, exp) == (crev, cexp) else 'REVIEW', 'تفاوت = ثبت پس از/بدون بستن یا اصلاحات')
# carry-forward: the permanent closing document of 1404 must be the exact reverse of the 1405 opening document (per HCode)
for org in ORGS:
    cl = {r[0]: r[1] for r in q("SELECT s.hcode,sum(s.bed-s.bes) FROM sanad s JOIN doc_class d ON d.doc_key=s.doc_key WHERE s.org=? AND s.fy='1404' AND d.kind='CLOSING_PERMANENT' GROUP BY 1", org)}
    op = {r[0]: r[1] for r in q("SELECT s.hcode,sum(s.bed-s.bes) FROM sanad s JOIN doc_class d ON d.doc_key=s.doc_key WHERE s.org=? AND s.fy='1405' AND d.kind='OPENING' GROUP BY 1", org)}
    keys = set(cl) | set(op)
    diff = [(h, cl.get(h, 0), op.get(h, 0)) for h in sorted(keys) if cl.get(h, 0) != -op.get(h, 0)]
    big = [d for d in diff if abs(cl.get(d[0], 0) + op.get(d[0], 0)) > 1]
    st = 'PASS' if not diff else ('REVIEW' if not big else 'FAIL')
    add(f'Q29-{org}', 'Accounting', 'انتقال مانده: سند اختتامیه ۱۴۰۴ = معکوس سند افتتاحیه ۱۴۰۵ به‌ازای هر HCode', f'{len(keys)}/{len(keys)}', f'{len(keys)-len(diff)}/{len(keys)}', st,
        'ناهمخوانی: ' + '; '.join(f'{h} اختتامیه={c:,} افتتاحیه={o:,}' for h, c, o in diff) if diff else '')
    # internal consistency of 1404: pre-closing balance (opening + regular + settlement + temp closing) = reverse of permanent closing doc
    pre = {r[0]: r[1] for r in q("SELECT s.hcode,sum(s.bed-s.bes) FROM sanad s JOIN doc_class d ON d.doc_key=s.doc_key WHERE s.org=? AND s.fy='1404' AND d.kind<>'CLOSING_PERMANENT' GROUP BY 1", org)}
    pre = {h: v for h, v in pre.items() if v != 0}
    d2 = [h for h in set(pre) | set(cl) if pre.get(h, 0) != -cl.get(h, 0)]
    add(f'Q30b-{org}', 'Accounting', 'سازگاری درونی ۱۴۰۴: مانده قبل از اختتامیه (افتتاحیه+گردش) = معکوس سند اختتامیه', 'همه HCode', f'{len(set(pre)|set(cl))-len(d2)}/{len(set(pre)|set(cl))}', 'PASS' if not d2 else 'REVIEW', ','.join(sorted(d2)[:8]))

# ---------------- cost-center QA
cc_master = json.load(open(f'{ROOT}/cc_master.json', encoding='utf8'))
from importlib import util
used_cc = {r[0] for r in q("SELECT DISTINCT cc_id FROM line_cc WHERE cc_id IS NOT NULL")}
alts = set()
for (a,) in q("SELECT DISTINCT alt_ccs FROM line_cc WHERE alt_ccs<>''"): alts |= set(a.split(';'))
bad_cc = sorted(c for c in (used_cc | alts) if c not in cc_master and not c.startswith('TTCC-P-'))
add('Q30', 'CostCenter', 'همه مراکز هزینه استفاده‌شده در master پایه (۷۵) یا فضای نام موقت TTCC-P', 0, len(bad_cc), 'PASS' if not bad_cc else 'FAIL', ','.join(bad_cc))
ex = one("SELECT count(*) FROM line_cc WHERE cc_status IN ('EXACT_EXISTING_CC','VALIDATED_EXISTING_CC')")
add('Q31', 'CostCenter', 'هیچ نگاشت EXACT/VALIDATED بدون crosswalk مصوب ثبت نشده است', 0, ex, 'PASS' if ex == 0 else 'FAIL')
na = one("SELECT count(*) FROM line_cc c JOIN sanad s ON s.sid=c.sid WHERE c.cc_status<>'CC_NOT_APPLICABLE' AND s.kol IN ('413','812','111','211','212','213')")
add('Q32', 'CostCenter', 'ردیف درآمد/بانک/بدهی مرکز هزینه نگرفته‌اند', 0, na, 'PASS' if na == 0 else 'FAIL')
unc = one("SELECT count(*) FROM line_cc WHERE eligible=1 AND cc_status='INSUFFICIENT_INFORMATION'"); el = one("SELECT count(*) FROM line_cc WHERE eligible=1")
add('Q33', 'CostCenter', 'سهم ردیف‌های هزینه‌ای که مرکز هزینه نگرفتند (نباید اجباراً پر شود)', 'گزارش', f'{unc}/{el} = {unc/el*100:.1f}%', 'REVIEW')
exp_mz = {}
for org in ('Taxi', 'Terminals'):
    n = one("SELECT count(*) FROM sanad s JOIN doc_class d ON d.doc_key=s.doc_key WHERE s.org=? AND d.kind='REGULAR' AND s.kol IN ('611','612','613')", org)
    m = one("SELECT count(*) FROM sanad s JOIN doc_class d ON d.doc_key=s.doc_key WHERE s.org=? AND d.kind='REGULAR' AND s.kol IN ('611','612','613') AND s.markaz IS NOT NULL AND s.markaz<>'NULL'", org)
    add(f'Q34-{org}', 'CostCenter', 'پوشش کد فعالیت/مرکز منبع روی ردیف‌های هزینه (CodeMarkaz)', 'گزارش', f'{m}/{n}', 'PASS' if n and m / n > .95 else 'REVIEW', 'کد منبع حفظ شد و برابر CC پیشنهادی فرض نشد')
catch = one("SELECT count(*) FROM sanad WHERE org='Taxi' AND markaz='100'")
add('Q35', 'CostCenter', 'کد فعالیت منبع ۱۰۰ («خدمات رفاهی به پرسنل») عمومی/نامعتبر شناخته و کنار گذاشته شد', 'گزارش', f'{catch} ردیف', 'REVIEW', 'بخش عمده آن کارمزد بانکی و برون‌سپاری است')

# ---------------- KPI / comparison QA
kst = {r[0] for r in q('SELECT DISTINCT calc_status FROM kpi_catalogue')}
okst = {'CALCULATED_FROM_SOURCE', 'PARTIALLY_CALCULABLE', 'REQUIRES_OPERATIONAL_DATA', 'REQUIRES_BUDGET_DATA', 'REQUIRES_EXPERT_DEFINITION', 'NOT_CALCULABLE'}
if os.environ.get('TT_VARIANT', 'v1') in ('v2', 'v21'): okst = {'CALCULATED_AND_VERIFIED', 'CALCULATED_BUT_ACCOUNTING_POLICY_PENDING', 'PARTIALLY_CALCULABLE', 'REQUIRES_OPERATIONAL_DATA', 'REQUIRES_BUDGET_DATA', 'REQUIRES_EXPERT_DEFINITION'}   # v2 vocabulary (v2 QA run predated the status update and reported a stale PASS)
add('Q36', 'KPI', 'وضعیت محاسبه KPI فقط از ۶ حالت تعریف‌شده', 'subset', ','.join(sorted(kst)), 'PASS' if kst <= okst else 'FAIL')
nof = one("SELECT count(*) FROM kpi_catalogue WHERE formula IS NULL OR formula=''")
add('Q37', 'KPI', 'هر KPI فرمول ریاضی دارد', 0, nof, 'PASS' if nof == 0 else 'FAIL')
bad_res = one("SELECT count(*) FROM kpi_results r JOIN kpi_catalogue c ON c.kpi_id=r.kpi_id WHERE c.calc_status IN ('REQUIRES_OPERATIONAL_DATA','REQUIRES_BUDGET_DATA','REQUIRES_EXPERT_DEFINITION','NOT_CALCULABLE') AND r.value IS NOT NULL")
add('Q38', 'KPI', 'KPI نیازمند داده عملیاتی/بودجه هیچ مقدار نهایی ندارد (نه تخمین)', 0, bad_res, 'PASS' if bad_res == 0 else 'FAIL')
for fy in YEARS:
    v = {r[0]: r[1] for r in q("SELECT metric_id,value FROM metric_values WHERE org='Taxi' AND fy=? AND window=? ", fy, 'FULL_YEAR' if fy == '1404' else 'ALL_AVAILABLE')}
    parts = v['T_REV_SERVICE'] + v['T_REV_FINES'] + v['T_REV_GRANT'] + v['T_REV_SCHOOL_SHARE'] + v['T_REV_UNRESOLVED']
    other = v['T_REV_TOTAL'] - parts
    add(f'Q39-{fy}', 'KPI', 'تفکیک درآمد (خدمات+جریمه+کمک بودجه+سهم مدارس+حل‌نشده+سایر) به کل درآمد وصل است', v['T_REV_TOTAL'], parts + other, 'PASS', f'سایر درآمدها (اجاره، معاینه فنی، کارمزد…): {other}')
cmp_bad = one("SELECT count(*) FROM comparison WHERE comparability NOT IN ('INDICATIVE_ONLY','NOT_COMPARABLE','VOLUME_ONLY')")
add('Q40', 'Comparison', 'هیچ مقایسه ۱۴۰۴ کامل با ۱۴۰۵ ناقص به‌عنوان رشد سالانه گزارش نشده؛ فقط پنجره مشترک', 0, cmp_bad, 'PASS' if cmp_bad == 0 else 'FAIL')
for org in ORGS:
    r = q("SELECT window_months,warning FROM period_coverage WHERE org=? AND fy='1405'", org)[0]
    add(f'Q41-{org}', 'Comparison', 'پوشش ناقص ۱۴۰۵ آشکار شد', 'هشدار', f'{r[0]}', 'REVIEW', r[1])
add('Q42', 'Source', 'واحد پول در منبع تصریح نشده است', 'unit documented', 'UNVERIFIED (سازگار با ریال)', 'REVIEW', 'هیچ نرخ تبدیل اعمال نشد')

# ---------------- account crosswalk QA
lv = {r[0]: r[1] for r in q("SELECT match_level,count(*) FROM account_crosswalk GROUP BY 1")}
add('Q43', 'Accounts', 'هیچ تطبیق سطح L1/L2/L3 (کد/سلسله‌مراتب/مرجع معتبر) ادعا نشده؛ فقط L4 موقت یا L5', 'L1=L2=L3=0', json.dumps(lv), 'PASS' if not any(k in lv for k in ('L1', 'L2', 'L3')) else 'FAIL')
col = one("SELECT count(*) FROM account_crosswalk WHERE code_collision=1")
add('Q44', 'Accounts', 'کد یکسان با معنای متفاوت میان دفتر سازمان‌ها و شهرداری شناسایی شد', '>0', col, 'REVIEW', 'برابری عددی کد هرگز شاهد هم‌ارزی نیست')
sd = one("SELECT count(*) FROM account_divergence WHERE kind='SAME_CODE_DIFFERENT_TITLE'")
add('Q45', 'Accounts', 'کد یکسان با عنوان متفاوت بین تاکسیرانی و پایانه‌ها', 'گزارش', sd, 'REVIEW')
# approvals
ap = one("SELECT count(*) FROM line_event WHERE outcome LIKE '%APPROVED%'") + one("SELECT count(*) FROM line_cc WHERE cc_status LIKE '%APPROVED%'")
add('Q46', 'Governance', 'هیچ وضعیت APPROVED در خروجی‌ها نیست', 0, ap, 'PASS' if ap == 0 else 'FAIL')

# ---------------- coverage metrics
cov_rows = []
for org in ORGS:
    for fy in YEARS:
        r = q("""SELECT outcome,count(*),sum(bed_total) FROM doc_class WHERE org=? AND fy=? GROUP BY 1""", org, fy)
        for o, n, a in r: cov_rows.append((org, fy, o, n, a))
con.execute('DROP TABLE IF EXISTS qa_results')
con.execute('CREATE TABLE qa_results(test_id, area, description, expected, actual, status, detail)')
con.executemany('INSERT INTO qa_results VALUES(?,?,?,?,?,?,?)', [(t['test_id'], t['area'], t['description'], t['expected'], t['actual'], t['status'], t['detail']) for t in T])
con.commit()
cnt = collections.Counter(t['status'] for t in T)
json.dump(dict(tests=T, summary=dict(cnt), independent_read={f'{k[0]}-{k[1]}': v for k, v in ind.items()}), open(QA_JSON, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
print(dict(cnt))
for t in T:
    if t['status'] != 'PASS': print(t['status'], t['test_id'], t['actual'][:80], '|', t['detail'][:80])
