"""v2.1 pre-build acceptance tests (DB level).  Appends to qa_results_v21.json (idempotent).  Run after 17, 09, 15, 19."""
import sqlite3, sys, os, json, re, collections
sys.path.insert(0, os.path.dirname(__file__))
from common import *
assert VARIANT == 'v21'
con = sqlite3.connect(DB, timeout=300)
con.execute(f"ATTACH DATABASE '{WORK}/tt_v2.sqlite' AS v2"); con.execute(f"ATTACH DATABASE '{WORK}/tt.sqlite' AS v1")
cur = con.cursor()
q = lambda s, *a: cur.execute(s, a).fetchall()
def one(s, *a):
    r = cur.execute(s, a).fetchone(); return r[0] if r and r[0] is not None else 0
QA = json.load(open(QA_JSON, encoding='utf8'))
T = []
CMD = f'cd municipality_demo && set TT_VARIANT=v21 && python scripts/taxi_terminals_1404_1405/18_qa_v21.py'
def add(tid, area, sources, population, procedure, expected, actual, status, detail=''):
    T.append(dict(test_id=tid, area=area, sources=sources, population=population, description=procedure, expected=str(expected), actual=str(actual), status=status, detail=detail, command=CMD))

# 1 completeness of the LOW audit population (independently rebuilt from v1/v2 line_cc, not from cc_resolution)
ind = {r[0] for r in q("SELECT a.sid FROM v1.line_cc a JOIN v2.line_cc b ON a.sid=b.sid WHERE a.cc_status IN ('MULTIPLE_CC_CANDIDATES','INSUFFICIENT_INFORMATION') AND b.cc_status IN ('PROVISIONAL_EXISTING_CC','NEW_CC_CANDIDATE') AND b.conf='LOW' AND b.eligible=1")}
aud = {r[0] for r in q('SELECT source_record_id FROM low_audit')}
ALLOWED = {'RETAIN_LOW_CONFIDENCE', 'UPGRADE_TO_MEDIUM_WITH_EVIDENCE', 'UPGRADE_TO_HIGH_WITH_EVIDENCE', 'RECLASSIFY_TO_MULTIPLE_CANDIDATES', 'RECLASSIFY_TO_INSUFFICIENT_INFORMATION', 'REASSIGN_TO_DIFFERENT_CC', 'CC_NOT_APPLICABLE', 'REQUIRES_EXPERT_DECISION'}
bad_dec = one(f"SELECT count(*) FROM low_audit WHERE audit_decision NOT IN ({','.join(repr(x) for x in ALLOWED)})")
by_org = dict(q("SELECT organization,count(*) FROM low_audit GROUP BY 1"))
add('QA_LOW_CONFIDENCE_AUDIT_COMPLETENESS', 'CostCenter', 'v1.line_cc ⋈ v2.line_cc ⋈ low_audit', 'ردیف‌های حل‌نشده v1 که v2 با اطمینان LOW به مرکز نگاشت کرد', 'جمعیت از line_cc نسخه‌های v1/v2 بازسازی می‌شود (نه از cc_resolution) و باید برابر مجموعه ردیف‌های ممیزی‌شده باشد؛ هر ردیف تصمیم معتبر دارد',
    '1016 = جمعیت مستقل؛ تصمیم نامعتبر 0', f'{len(aud)} / مستقل {len(ind)}؛ تفاوت مجموعه {len(ind ^ aud)}؛ تصمیم نامعتبر {bad_dec}؛ سازمان‌ها {by_org}', 'PASS' if ind == aud and bad_dec == 0 and len(aud) == 1016 else 'FAIL')
# 2 evidence for confidence upgrades
up = q("SELECT source_record_id,v2_confidence,v21_confidence,audit_evidence,audit_reason FROM low_audit WHERE v21_confidence<>v2_confidence")
no_ev = [r[0] for r in up if not (r[3] and r[4])]
rank = {'LOW': 0, 'MEDIUM': 1, 'HIGH': 2}
high_up = [r[0] for r in up if r[2] == 'HIGH']
mismatch = one("SELECT count(*) FROM low_audit a JOIN line_cc c ON c.sid=a.source_record_id WHERE c.conf<>a.v21_confidence OR coalesce(c.cc_id,'')<>coalesce(a.v21_cc,'') OR c.cc_status<>a.v21_status")
conf_up_outside = one("SELECT count(*) FROM v2.line_cc a JOIN line_cc b ON a.sid=b.sid WHERE a.conf<>b.conf AND a.sid NOT IN (SELECT source_record_id FROM low_audit)")
add('QA_CC_UPGRADE_EVIDENCE', 'CostCenter', 'low_audit, line_cc', 'ردیف‌های با تغییر اطمینان', 'هر ارتقای اطمینان دارای شاهد و دلیل ثبت‌شده است؛ هیچ HIGH بدون شاهد؛ line_cc با جدول ممیزی هم‌خوان؛ هیچ تغییر اطمینان خارج از جمعیت ممیزی',
    '0 / 0 / 0 / 0', f'ارتقا بدون شاهد={len(no_ev)}؛ HIGH={len(high_up)}؛ ناهمخوانی line_cc={mismatch}؛ تغییر خارج از جمعیت={conf_up_outside}', 'PASS' if not no_ev and not high_up and mismatch == 0 and conf_up_outside == 0 else 'FAIL',
    f'ارتقاها: {collections.Counter((r[1], r[2]) for r in up)}')
# 3 population bridge
tot = one('SELECT sum(lines) FROM cc_bridge_v2_v21'); diff_elig = one('SELECT sum(lines) FROM cc_bridge_v2_v21 WHERE v2_eligible<>v21_eligible')
chg = {r[0] for r in q('SELECT a.sid FROM v2.line_cc a JOIN line_cc b ON a.sid=b.sid WHERE a.cc_status<>b.cc_status OR coalesce(a.cc_id,\'\')<>coalesce(b.cc_id,\'\') OR a.conf<>b.conf OR a.alt_ccs<>b.alt_ccs')}
val_all = one('SELECT sum(s.bed-s.bes) FROM line_cc c JOIN sanad s ON s.sid=c.sid WHERE c.eligible=1'); val_v2 = one('SELECT sum(s.bed-s.bes) FROM v2.line_cc c JOIN sanad s ON s.sid=c.sid WHERE c.eligible=1')
add('QA_CC_BRIDGE_V2_V21', 'CostCenter', 'v2.line_cc ⋈ line_cc ⋈ cc_bridge_v2_v21', 'همه ۱۱۱٬۶۰۰ ردیف منبع', 'هر ردیف دقیقاً در یک سلول پل v2→v2.1 است؛ جمعیت واجد شرایط بدون تغییر؛ فقط ردیف‌های ممیزی‌شده تغییر کرده‌اند؛ ارزش واجد شرایط ثابت',
    f'111600؛ تغییر اهلیت 0؛ تغییر خارج از ممیزی 0؛ ارزش برابر', f'{tot}؛ تغییر اهلیت {diff_elig}؛ تغییرکرده {len(chg)} که خارج از ممیزی {len(chg - aud)}؛ ارزش {val_v2:,} → {val_all:,}',
    'PASS' if tot == 111600 and diff_elig == 0 and not (chg - aud) and val_all == val_v2 else 'FAIL', f'انتقال‌ها: {q("SELECT v2_status,v21_status,sum(lines) FROM cc_bridge_v2_v21 WHERE v2_status<>v21_status GROUP BY 1,2")}')
# 4 change-log parity
st_changed = one('SELECT count(*) FROM low_audit WHERE v21_status<>v2_status'); log_st = one("SELECT count(*) FROM change_log_v21 WHERE affected_component='line_cc.cc_status'")
cc_changed = one("SELECT count(*) FROM low_audit WHERE coalesce(v21_cc,'')<>coalesce(v2_cc,'')"); log_cc = one("SELECT count(*) FROM change_log_v21 WHERE affected_component='line_cc.cc_id_selected'")
conf_changed = one('SELECT count(*) FROM low_audit WHERE v21_confidence<>v2_confidence'); log_conf = one("SELECT count(*) FROM change_log_v21 WHERE affected_component='line_cc.confidence'")
add('QA_LOW_AUDIT_CHANGELOG_PARITY', 'Lineage', 'low_audit ↔ change_log_v21', 'تغییرات مرکز هزینه v2→v2.1', 'تعداد تغییر وضعیت/مرکز/اطمینان در جدول ممیزی = تعداد ردیف‌های change log متناظر', f'{st_changed}/{cc_changed}/{conf_changed}', f'{log_st}/{log_cc}/{log_conf}', 'PASS' if (st_changed, cc_changed, conf_changed) == (log_st, log_cc, log_conf) else 'FAIL')
# 5 sample review
rv = dict(q('SELECT reviewer_verdict,count(*) FROM low_sample GROUP BY 1')); pf = dict(q('SELECT reviewer_verdict,count(*) FROM low_postfix_changes GROUP BY 1'))
r1 = dict(q('SELECT reviewer_verdict,count(*) FROM low_sample_round1 GROUP BY 1'))
nyr = rv.get('NOT_YET_REVIEWED', 0) + pf.get('NOT_YET_REVIEWED', 0)
nonagree = sum(v for k, v in rv.items() if k not in ('AGREE',))
add('QA_LOW_SAMPLE_REVIEW', 'CostCenter', 'low_sample, low_sample_round1, low_postfix_changes', 'نمونه طبقه‌ای ۵۴ ردیفی (دور ۲) + ۵۶ ردیف دور ۱ + ردیف‌های متأثر از اصلاح قاعده', 'همه ردیف‌های نمونه با بازبینی دستی (شرح ردیف + عنوان حساب) قضاوت شده‌اند؛ مخالفت‌ها به اصلاح قاعده و بازبینی همه ردیف‌های متأثر منجر شده است',
    'NOT_YET_REVIEWED = 0', f'دور۱ {r1}؛ دور۲ {rv}؛ ردیف‌های متأثر از اصلاح {pf}', 'FAIL' if nyr else ('REVIEW' if nonagree else 'PASS'),
    'دور ۱: ۲ مخالفت (ناوگان معاینه فنی؛ نرم‌افزار) و ۳ نظر جزئی → قواعد اصلاح و ۱۲۸ بازتخصیص INSUFFICIENT به‌طور کامل بازبینی شد؛ دور ۲: ۱ مخالفت (تبلیغات پروژه) → قاعده اصلاح و ۴ ردیف متأثر بازبینی؛ نمونه‌برداری استنباط اعتبار برای ردیف‌های نمونه‌نشده نیست')
# 6 FE-70
dep_left = one("SELECT count(*) FROM line_event WHERE own_event='FE-70' AND lifecycle_action IN ('DEPRECIATION','PROVISION_OR_ACCRUAL')")
fe_drv = q("SELECT s.kol,count(*) FROM line_event e JOIN sanad s ON s.sid=e.sid WHERE e.own_event='FE-70' AND e.role='DRIVER' GROUP BY 1")
bad_kol = [k for k, n in fe_drv if k not in ('316', '120', '121', '122', '812')]
cons = q("SELECT sum(debit),sum(credit) FROM fe70_review")[0]; v2c = q("SELECT sum(s.bed),sum(s.bes) FROM v2.line_event e JOIN sanad s ON s.sid=e.sid WHERE e.own_event='FE-70' AND e.lifecycle_action IN ('DEPRECIATION','PROVISION_OR_ACCRUAL')")[0]
dep_wrong = one("SELECT count(*) FROM line_event e JOIN sanad s ON s.sid=e.sid WHERE e.own_event='PEO-01' AND NOT (e.acat IN ('EXP','ACC_DEPR'))")
settle_wrong = one("SELECT count(*) FROM line_event e JOIN sanad s ON s.sid=e.sid WHERE e.lifecycle_action='SETTLE_ACCRUED_LIABILITY' AND NOT (s.bed>s.bes)")
recog_wrong = one("SELECT count(*) FROM line_event e JOIN sanad s ON s.sid=e.sid WHERE e.lifecycle_action='PROVISION_ACCRUAL_RECOGNITION' AND NOT (s.bes>s.bed)")
add('QA_FE70_SEMANTICS', 'Events', 'line_event, fe70_review, v2.line_event, v7.1 dictionary (FE-70 «اصلاح سند، بستن حساب‌ها و جابه‌جایی حسابداری»)', 'خطوط FE-70 در v2', 'در v2.1 هیچ خط استهلاک/ذخیره زیر FE-70 نیست؛ خطوط باقی‌مانده FE-70 فقط بستن حساب موقت/انتقال دارایی/اصلاح سنواتی‌اند؛ جمع بدهکار و بستانکار بازتخصیص‌ها حفظ شده؛ جهت بدهکار/بستانکار با نوع رویداد سازگار',
    '0 / ∅ / برابر', f'استهلاک-ذخیره زیر FE-70={dep_left}؛ کل‌های ناهمخوان={bad_kol}؛ جمع {tuple(cons)} در برابر v2 {tuple(v2c)}؛ PEO-01 با حساب نامرتبط={dep_wrong}؛ تسویه با جهت نادرست={settle_wrong}؛ شناسایی با جهت نادرست={recog_wrong}',
    'PASS' if dep_left == 0 and not bad_kol and tuple(cons) == tuple(v2c) and dep_wrong == settle_wrong == recog_wrong == 0 else 'FAIL', f'باقی‌مانده FE-70 (کل: خط): {dict(fe_drv)}')
# 7 source totals
s_n = one('SELECT count(*) FROM sanad'); s_b, s_c = q('SELECT sum(bed),sum(bes) FROM sanad')[0]; v_b, v_c = q('SELECT sum(bed),sum(bes) FROM v2.sanad')[0]
r_b, r_c = q('SELECT sum(Bed),sum(Bes) FROM sanad_raw')[0] if one("SELECT count(*) FROM pragma_table_info('sanad_raw') WHERE name='Bed'") else (None, None)
docs = one('SELECT count(*) FROM doc_class'); le = one('SELECT count(*) FROM line_event'); lc = one('SELECT count(*) FROM line_cc')
add('QA_SOURCE_TOTALS_UNCHANGED', 'Totals', 'sanad ↔ v2.sanad ↔ sanad_raw', 'همه ردیف‌های Sanad', 'تعداد ردیف، اسناد، جمع بدهکار/بستانکار (و برابری بدهکار=بستانکار) نسبت به v2 و منبع خام بدون تغییر؛ line_event و line_cc یک‌به‌یک',
    '111600 / 4512 / بدهکار=بستانکار=v2', f'{s_n}/{docs}؛ Σبدهکار={s_b:,} Σبستانکار={s_c:,}؛ v2: {v_b:,}/{v_c:,}؛ خام: {r_b}/{r_c}؛ line_event={le} line_cc={lc}',
    'PASS' if s_n == 111600 and docs == 4512 and s_b == s_c == v_b == v_c and le == lc == 111600 and (r_b is None or (r_b == s_b and r_c == s_c)) else 'FAIL')
# 8 event lineage
chg_ev = {r[0] for r in q("SELECT sid FROM line_event WHERE coalesce(v2_event,'')<>coalesce(own_event,'') OR coalesce(v2_lifecycle,'')<>coalesce(lifecycle_action,'')")}
fe_s = {r[0] for r in q('SELECT sid FROM fe70_review')}
log_ev = one("SELECT count(*) FROM change_log_v21 WHERE affected_component='line_event.assigned_event'")
add('QA_EVENT_LINEAGE_V2_V21', 'Events', 'line_event.v2_event, fe70_review, change_log_v21, event_crosswalk_v2_v21', 'ردیف‌های با رویداد تغییرکرده', 'هر ردیف با رویداد تغییرکرده در v2.1 در fe70_review و change log آمده و crosswalk v2→v2.1 همان را می‌شمارد؛ هیچ شناسهٔ FE بازتعریف نشده',
    f'{len(fe_s)} = {len(chg_ev)} = {len(fe_s)}', f'{len(chg_ev)} تغییرکرده؛ در fe70_review {len(chg_ev & fe_s)}؛ change log {log_ev}؛ crosswalk {one("SELECT sum(lines) FROM event_crosswalk_v2_v21")}', 'PASS' if chg_ev == fe_s and log_ev == len(fe_s) and one('SELECT sum(lines) FROM event_crosswalk_v2_v21') == len(fe_s) else 'FAIL')
# 9-13 KPI
ncat, ndist = one('SELECT count(*) FROM kpi_catalogue'), one('SELECT count(DISTINCT kpi_id) FROM kpi_catalogue'); dupres = one('SELECT count(*) FROM (SELECT 1 FROM kpi_results GROUP BY kpi_id,fy,window HAVING count(*)>1)')
idx = one("SELECT count(*) FROM sqlite_master WHERE type='index' AND name='u_kpi_catalogue'"); orphan = one('SELECT count(*) FROM kpi_results WHERE kpi_id NOT IN (SELECT kpi_id FROM kpi_catalogue)')
add('QA_KPI_UNIQUE_IDENTITY', 'KPI', 'kpi_catalogue, kpi_results', '۳۱ تعریف KPI', 'هر kpi_id دقیقاً یک ردیف کاتالوگ دارد (کلید یکتا)؛ هر نتیجه یک KPI و یک دوره؛ نتیجهٔ یتیم نیست', '31 / 31 / 0 / 0', f'{ncat} ردیف / {ndist} یکتا؛ نتیجهٔ تکراری {dupres}؛ یتیم {orphan}؛ شاخص یکتا={idx}', 'PASS' if ncat == ndist == 31 and dupres == 0 and orphan == 0 and idx == 1 else 'FAIL', 'علت v2: ردیف تکراری TM-K15')
inc = q("SELECT kpi_id,catalogue_status,distinct_result_statuses FROM kpi_status_consistency WHERE consistent<>'YES'"); noresult = [r[0] for r in q("SELECT kpi_id FROM kpi_status_consistency WHERE result_rows=0 AND catalogue_status IN ('CALCULATED_AND_VERIFIED','CALCULATED_BUT_ACCOUNTING_POLICY_PENDING')")]
add('QA_KPI_STATUS_CONSISTENCY', 'KPI', 'kpi_status_consistency', '۳۱ KPI', 'وضعیت ردیف‌های KPI_Results با KPI_Catalogue یکسان است؛ هر KPI محاسبه‌شده ردیف نتیجه دارد؛ وضعیت تعریف/محاسبه/راستی‌آزمایی/حاکمیت جدا و ثبت شده', '0 ناسازگار؛ 0 بدون نتیجه', f'ناسازگار={inc}؛ محاسبه‌شده بدون نتیجه={noresult}', 'PASS' if not inc and not noresult else 'FAIL', 'v2: TX-K01 در نتایج CALCULATED_FROM_SOURCE مانده بود؛ TM-K02 ردیف نتیجه نداشت')
kc = dict(((o, m), v) for o, m, v in q('SELECT organization,metric,value FROM kpi_counts'))
calc = {o: one("SELECT count(*) FROM kpi_catalogue WHERE calc_status IN ('CALCULATED_AND_VERIFIED','CALCULATED_BUT_ACCOUNTING_POLICY_PENDING') AND org=?", o) for o in ORGS}
vrf = {o: one("SELECT count(*) FROM kpi_catalogue WHERE verification_status='INDEPENDENTLY_VERIFIED' AND org=?", o) for o in ORGS}
ok_cnt = all(kc[(o, 'calculable_from_source_definitions')] == calc[o] and kc[(o, 'independently_verified_definitions')] == vrf[o] for o in ORGS) and kc[('ALL', 'unique_kpi_definitions')] == 31
add('QA_KPI_COUNT_RECONCILIATION', 'KPI', 'kpi_counts ↔ kpi_catalogue ↔ kpi_results', 'شمارش‌های KPI', 'تعریف یکتا، تعریف تأییدشده و مشاهدات KPI×دوره سه شمارش جدا هستند و از جدول یک‌منبعی kpi_counts می‌آیند',
    'برابر با بازشمارش مستقل', f'یکتا {kc[("ALL","unique_kpi_definitions")]}؛ تأییدشده تعریف {dict(vrf)} (جمع {sum(vrf.values())})؛ مشاهدات تأییدشده {kc[("ALL","verified_kpi_period_observations")]} از {kc[("ALL","result_rows_with_value")]}', 'PASS' if ok_cnt else 'FAIL')
nv = one("SELECT count(*) FROM kpi_verification WHERE metric_id NOT LIKE 'M_BILLED_BY_FACILITY:%'"); nmis = one("SELECT count(*) FROM kpi_verification WHERE verdict<>'EXACT_MATCH'")
add('QA_KPI_46_COMPARISONS_RERUN', 'KPI', 'kpi_verification (13_kpi_independent.py از xlsx منبع)', 'شاخص‌های پایه × دوره', 'بازاجرای بازمحاسبه مستقل؛ ۴۶ مقایسهٔ v2 بدون اختلاف تکرار می‌شود و مقدار هیچ KPI با اصلاح برچسب تغییر نکرده است', '≥46 مقایسه؛ 0 اختلاف', f'{nv} مقایسه شاخص + تفکیک پایانه؛ اختلاف {nmis}', 'PASS' if nv >= 46 and nmis == 0 else 'FAIL', 'مقادیر عددی KPI بین v2 و v2.1 تغییر نکرده‌اند (تفاوت فقط در برچسب/ساختار وضعیت)')
rb = q("SELECT fy,window,amount FROM kpi_recharge_bridge WHERE step=6")
add('QA_KPI_RECHARGE_BRIDGE', 'KPI', 'kpi_recharge_bridge', 'هزینه تحمیل‌شده (M_RECHARGE) پایانه‌ها', 'پل تطبیق حساب‌محور (بدهکار ۱۱۳-۱-۱) با شاخص خط‌لوله (قواعد TX-*) بسته می‌شود؛ شاخص وابسته به طبقه‌بندی است و بازمحاسبهٔ مستقل حسابی ندارد (TM-K05/K14 «تأییدنشده مستقل»)',
    'اختلاف 0', f'{rb}', 'REVIEW' if all(r[2] == 0 for r in rb) else 'FAIL', 'پل بسته می‌شود اما تأیید مستقل KPI نیست؛ و ماهیت حسابداری (CD-01) باز است')
# 14 privacy masking
leak = sum(one(f"SELECT count(*) FROM {t} WHERE {c} GLOB '*[0-9][0-9][0-9][0-9][0-9][0-9]*' OR {c} LIKE '%IR__ %' ") for t, c in (('account_dictionary', 'title'), ('account_crosswalk', 'org_title'), ('account_divergence', 'title_a'), ('account_divergence', 'title_b')))
nrestr = one('SELECT count(*) FROM account_dictionary_restricted')
add('QA_PRIVACY_MASKING_TITLES', 'Privacy', 'account_dictionary, account_crosswalk, account_divergence, account_dictionary_restricted', 'عنوان حساب‌ها', 'عنوان حساب‌ها در خروجی‌های غیرمحدود شمارهٔ حساب بانکی/شبا (≥۶ رقم) ندارند؛ اصل در جدول محدود نگه داشته شده؛ کد سلسله‌مراتبی ماسک نمی‌شود', '0', f'نشت={leak}؛ ردیف‌های محدود={nrestr}', 'PASS' if leak == 0 and nrestr > 0 else 'FAIL')
# 15 coverage by confidence
cc = {(r[0], r[1]): r for r in q('SELECT * FROM cc_confidence_coverage')}
okc = True; det = []
for (v, o), r in cc.items():
    sel = r[10]; okc &= (r[4] + r[6] + r[8] == sel) and (r[12] <= sel) and (sel + r[14] + r[16] == r[2])
cur_sel = {o: one("SELECT count(*) FROM line_cc WHERE eligible=1 AND org=? AND cc_status IN ('PROVISIONAL_EXISTING_CC','NEW_CC_CANDIDATE')", o) for o in ORGS}
okc &= all(cc[('v2.1', o)][10] == cur_sel[o] for o in ORGS)
add('QA_CC_CONFIDENCE_COVERAGE', 'CostCenter', 'cc_confidence_coverage ↔ line_cc', 'پوشش مرکز هزینه v2 و v2.1', 'پوشش تحلیلی موقت (همه انتخاب‌شده) و پوشش «پشتیبانی‌شده با شاهد» (MEDIUM+HIGH) جدا گزارش می‌شوند؛ HIGH+MEDIUM+LOW = انتخاب‌شده؛ انتخاب‌شده + چندمرکزی + ناکافی = واجد شرایط',
    'برابر', '؛ '.join(f'{v} {o}: تحلیلی {r[10]:,}/{r[2]:,} ({r[10]/r[2]:.1%})، شاهدی {r[12]:,} ({r[12]/r[2]:.1%})، LOW {r[8]:,}' for (v, o), r in sorted(cc.items(), key=lambda x: (x[0][1], x[0][0]))), 'PASS' if okc else 'FAIL')
# 16 approval flags
appr = one("SELECT count(*) FROM line_event WHERE outcome LIKE '%APPROVED%'") + one("SELECT count(*) FROM line_cc WHERE cc_status IN ('EXACT_EXISTING_CC','VALIDATED_EXISTING_CC')")
add('QA_NO_APPROVED_ITEMS', 'Governance', 'line_event, line_cc', 'همه خطوط', 'هیچ رویداد یا مرکز هزینه‌ای با وضعیت APPROVED/EXACT/VALIDATED نیست (approved_items = 0)', '0', str(appr), 'PASS' if appr == 0 else 'FAIL')

ids = {t['test_id'] for t in T}
QA['tests'] = [t for t in QA['tests'] if t['test_id'] not in ids] + T
json.dump(QA, open(QA_JSON, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
print(collections.Counter(t['status'] for t in T))
for t in T: print(t['status'], t['test_id'], '|', t['actual'][:170])
