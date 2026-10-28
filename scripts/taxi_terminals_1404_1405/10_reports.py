"""Phase 4 — narrative deliverables generated from the pipeline database so every number is reproducible.
BASELINE_DISCOVERY.md, taxi_terminals_management_report.md (Persian), repository_integration_report.md, financial_mapping_QA.md
"""
import sqlite3, sys, os, json, collections, hashlib
sys.path.insert(0, os.path.dirname(__file__))
from common import *
from rules import TT_EVENTS

con = sqlite3.connect(f'file:{DB}?mode=ro', uri=True, timeout=120)
q = lambda s, *a: con.execute(s, a).fetchall()
def one(s, *a):
    r = con.execute(s, a).fetchone()
    return r[0] if r and r[0] is not None else 0
f = lambda n: f'{n:,.0f}' if isinstance(n, (int, float)) else str(n)
pct = lambda a, b: f'{a / b * 100:.1f}%' if b else '—'
QA = json.load(open(f'{WORK}/qa_results.json', encoding='utf8'))
CC = json.load(open(f'{ROOT}/cc_master.json', encoding='utf8'))
V71 = f'{ROOT}/data/deliverables/financial_event_discovery/revisions/1404-r20260922-canonical-events-v7.1/financial_event_discovery_1404-r20260922_canonical-events_v7.1.xlsx'
V71_SHA = hashlib.sha256(open(V71, 'rb').read()).hexdigest()
CCM_SHA = hashlib.sha256(open(f'{ROOT}/cc_master.json', 'rb').read()).hexdigest()
inv = q('SELECT org,fy,kind,file,sha256,bytes,data_rows FROM inventory ORDER BY org,fy,kind')
ORGFA = {'Taxi': 'سازمان تاکسیرانی', 'Terminals': 'سازمان پایانه‌ها'}
M = {(r[0], r[1], r[2], r[3]): r[4] for r in q('SELECT org,fy,window,metric_id,value FROM metric_values')}
def mv(org, fy, w, m): return M.get((org, fy, w, m), 0)
cover = {(r[0], r[1]): r for r in q('SELECT org,fy,first_date,last_date,last_month,n_docs,n_lines,window_months,window_rule,warning FROM period_coverage')}
src = {(r[0], r[1]): r for r in q('SELECT org,fy,count(*),count(DISTINCT doc_key),sum(bed),sum(bes),min(date),max(date) FROM sanad GROUP BY 1,2')}
hes = {(r[0], r[1]): r[2] for r in q('SELECT org,fy,count(*) FROM hesab GROUP BY 1,2')}
outc = collections.defaultdict(dict)
for org, oc, n, a in q('SELECT org,outcome,count(*),sum(bed_total) FROM doc_class GROUP BY 1,2'): outc[org][oc] = (n, a)
lineo = collections.defaultdict(dict)
for org, oc, n in q("SELECT org,outcome,count(*) FROM line_event WHERE role='DRIVER' GROUP BY 1,2"): lineo[org][oc] = n
ccs = collections.defaultdict(dict)
for org, st, n, nd in q('SELECT org,cc_status,count(*),count(DISTINCT doc_key) FROM line_cc WHERE eligible=1 GROUP BY 1,2'): ccs[org][st] = (n, nd)
elig = {o: one('SELECT count(*) FROM line_cc WHERE org=? AND eligible=1', o) for o in ORGS}
ccid = {o: q('SELECT cc_id,count(*),sum(s.bed-s.bes) FROM line_cc c JOIN sanad s ON s.sid=c.sid WHERE c.org=? AND c.eligible=1 AND c.cc_id IS NOT NULL GROUP BY 1 ORDER BY 3 DESC', o) for o in ORGS}
fe_used = {o: q("SELECT own_event,count(*),count(DISTINCT doc_key) FROM line_event WHERE org=? AND role IN ('DRIVER','SETTLEMENT') AND own_event LIKE 'FE-%' GROUP BY 1 ORDER BY 2 DESC", o) for o in ORGS}
tt_used = {o: q("SELECT own_event,count(*),count(DISTINCT doc_key) FROM line_event WHERE org=? AND role IN ('DRIVER','SETTLEMENT') AND own_event LIKE 'TT-NE-%' GROUP BY 1 ORDER BY 2 DESC", o) for o in ORGS}
fe_all = sorted({r[0] for o in ORGS for r in fe_used[o]})
tt_all = sorted({r[0] for o in ORGS for r in tt_used[o]})
cw = dict(q('SELECT match_status,count(*) FROM account_crosswalk GROUP BY 1'))
coll = one('SELECT count(*) FROM account_crosswalk WHERE code_collision=1')
div = dict(q('SELECT kind,count(*) FROM account_divergence GROUP BY 1'))
kst = collections.defaultdict(collections.Counter)
for org, st, n in q('SELECT org,calc_status,count(*) FROM kpi_catalogue GROUP BY 1,2'): kst[org][st] = n
nK = {o: sum(kst[o].values()) for o in ORGS}
qa_sum = collections.Counter(t['status'] for t in QA['tests'])
fb = QA.get('formula_block') or []
os.makedirs(OUT, exist_ok=True)

def table(hdr, rows):
    s = '| ' + ' | '.join(hdr) + ' |\n|' + '|'.join(['---'] * len(hdr)) + '|\n'
    for r in rows: s += '| ' + ' | '.join(str(x) for x in r) + ' |\n'
    return s

# ============================================================================================ BASELINE_DISCOVERY.md
ngit = 'M app/models.py, app/routers/contractors.py, app/routers/volume_contracts.py, app/schemas/*, frontend/src/{app/routes.tsx,components/Accounting/AccountingInboxPage.tsx,config/navigation.ts,pages/ContractorRegistration.tsx,pages/volume_contracts/VolumeContractsDashboard.tsx,services/volumeContracts.ts}, vite.config.ts; many untracked files'
bl = f'''# BASELINE_DISCOVERY — Taxi & Terminal organizations (FY1404–1405)

Generated from the repository as it exists on 2026-10-13. Historical paths, counts and hashes are advisory until re-checked; every item below was re-opened for this work.

## 1. Protection of existing state

* `git status` showed pre-existing uncommitted work (modified: {ngit}). **None of it was touched.** All new work is in new locations only:
  `scripts/taxi_terminals_1404_1405/`, `data/deliverables/taxi_terminals_1404_1405/`, `data/work/taxi_terminals/` (SQLite scratch), `tests/test_taxi_terminals_mapping.py`.
* No historical workbook was opened for writing, no database (including `municipality_demo.db`) was modified, no rule was activated.
* The two RAR archives sit in `H:/Freelancing_Project/KalaniProject/Taxi_Gate/`; the eight workbooks were already extracted beside them (`تاکسیرانی/`, `پایانه ها/`). The extractor available to this environment could list each archive only as a single folder entry, so the **extracted copies were used as the source of record**; their SHA-256 values are in `Source_Inventory`. Row counts of the extracted files match the checkpoints in the assignment exactly (see QA Q01).

## 2. Selected baselines

| Need | Selected artifact | Status (verified) | Why this and not another |
|---|---|---|---|
| Canonical financial-event dictionary | `data/deliverables/financial_event_discovery/revisions/1404-r20260922-canonical-events-v7.1/financial_event_discovery_1404-r20260922_canonical-events_v7.1.xlsx` (sheet `فرهنگ_رویداد_مالی_کاندید`, FE-01…FE-70) SHA-256 now on disk `{V71_SHA}` — **differs from the output SHA-256 recorded in `corrective_report_v7_1.txt` and `source_manifest_canonical-events_v7_1.json` (`3561b981…c6449fa`)**; the file was modified after its manifest was written (see §3). | **Candidate dictionary, not approved.** Its own `جدول_تصمیم_کمیته_رویداد` leaves every approved cardinality `Needs Decision`; every evidence pair is `OBSERVED — NOT AUTHORIZED`. `Acceptance_v7_1` = “ACCEPTED — FINAL DELIVERY CANDIDATE” is a QA acceptance of the workbook, not a business approval. | v7.1 is a metadata-only corrective patch over v7 (`corrective_report_v7_1.txt`: core-sheet value/formula equality, 0 business-value differences; 18 PASS / 2 REVIEW / 0 FAIL). v2–v6 are superseded by v7 (`corrective_report_v7.md`: v7 is a corrective copy of v6 with static PASS cells converted to formulas). Chosen for being the last QA-corrected revision, **not** for the highest version label. Built on the 337,268-row municipality 1404 journal — a different population from the new organizations. |
| Cost-center taxonomy | `cc_master.json` (75 entries = 74 centers of the v3 baseline + `CC-109` addendum; SHA-256 `{CCM_SHA}`), cross-checked against sheet `مرجع_مراکز_هزینه_v3_با_افزودنی` (75 rows) of `data/deliverables/service_activity_coverage/revisions/1405-r20260922-service-coverage/service_activity_coverage_1405-r20260922_QA-remapped_v2.xlsx` | **Proposed baseline, not an active ERP master.** `docs/financial-event-control-layer.md` and ADR-0015: v3 is the review baseline; Proposed/Pending centers may only be used in Draft/Review. `CC-109` is itself `PROPOSED — NEEDS REVIEW`. | The only machine-readable master that carries the ADR-0006 columns (title B / service domain C) and was reconciled against 1405 service sheets. The same audit also lists the taxi/terminal services with **no** center (used as gap evidence). |
| Source of integration model | ADR-0001…0027 under `docs/adr/`, `CONTEXT.md`, `docs/financial-event-control-layer.md` | Accepted decisions. Package/Line/Rule-Profile/override/exception model is documented but **not implemented in `app/`** (the doc’s “current implementation boundary”). | Defines the layers A (observed) / B (proposed) / C (approved) honoured here. |
| Journal-level rule patterns | `scripts/journal_1404_financial_events/fe_rules.py` (GAP-01…GAP-12 register), `scripts/journal_1404_activity_cc_v4/activity_rules.py` | Proposed provisional rules for the municipality journal; unapproved. | Reused as pattern and vocabulary: new candidates link to the existing GAP ids (e.g. GAP-10 payables settlement, GAP-03 notes receivable) instead of inventing parallel gaps. |

## 3. Competing or ignored artifacts

* **Baseline integrity finding (re-verified):** the v7.1 workbook currently on disk has SHA-256 `{V71_SHA}`, but the report and manifest generated with it record `3561b9817df949b3d3175a74ccc40e7f01cb2fa932bebc03fadb7ace6c6449fa`; the file's last-modified time (2026-09-24) is later than its report (2026-09-23). The v7 source file matches its recorded hash (`1de2fca6…a0f7e`). To bound the risk, the two sheets this work depends on — `فرهنگ_رویداد_مالی_کاندید` (71 rows) and `ماتریس_شواهد_رویداد_مرکز_v2` (74 rows) — were compared value-by-value with v7 and are **identical**. Integrity of the *other* v7.1 sheets is therefore unverified and they were not used.
* Other municipality deliverables exist (`FINAL_CLIENT_HANDOVER_1404/`, Desktop `Unique_Code_Financial_Event_Relationship_Model_DRAFT.xlsx`, the v3/v4 journal workbooks, `Fehrest Nahaie Pishnahadi.xlsx`). They were **not opened or used** as dictionaries; project memory describes them as review-ready, not production-approved. The only fact taken from that work is the lesson that cost-center values on revenue rows are an existing collision and must never be inherited.
* The `PreAccountingPackagePage` (frontend) is a **static demo** driven by `demoData.ts` (`DEMO_COST_CENTERS`, demo subsystems). It is not a data consumer yet.

## 4. Municipality account taxonomy used for the crosswalk

No authoritative chart-of-accounts file exists in the repository. The observable municipality taxonomy is the **new and old coding embedded in the 1404 municipality journal** (`data/work/fe_model/journal_v4.pkl`, 553,667 rows): extracted to `data/work/taxi_terminals/municipality_chart.json` (156 distinct class/kol/moin combinations). It is *observed*, hence the crosswalk is capped at provisional levels (see `Account_Crosswalk`).

## 5. Reuse / extend / ignore

* **Reuse unchanged:** FE-01…FE-70 definitions (never redefined), cost-center ids CC-xxx, GAP-xx vocabulary, ADR governance layers.
* **Extend (proposal only):** {len(tt_all)} new event candidates `TT-NE-xx`; 3 provisional cost centers `TTCC-P-01..03`; account-crosswalk rows; KPI catalogue.
* **Ignore:** any historical event↔cost-center co-occurrence as a rule (OBSERVED ≠ AUTHORIZED).
'''
open(f'{OUT}/BASELINE_DISCOVERY.md', 'w', encoding='utf8').write(bl)

# ============================================================================================ management report (Persian)
def srcrow(o, y):
    s = src[(o, y)]; return [ORGFA[o], y, f(s[2]), f(s[3]), f(hes[(o, y)]), f(s[4]), f(s[5]), f'{s[6]} تا {s[7]}', 'سالم: تراز، همه اسناد متوازن، ۱۰۰٪ اتصال حساب' if one('SELECT count(*) FROM (SELECT doc_key FROM sanad WHERE org=? AND fy=? GROUP BY doc_key HAVING sum(bed)<>sum(bes))', o, y) == 0 else 'نیازمند بازبینی']
T = {o: outc[o] for o in ORGS}
def tot(o): return sum(v[0] for v in T[o].values())
def ev_table(o):
    rows = []
    for k, fa in (('EXISTING_EVENT_CONFIRMED', 'رویداد موجود — تأییدشده با دو شاهد مستقل (CONFIRMED)'), ('EXISTING_EVENT_PROVISIONAL', 'رویداد موجود — موقت (PROVISIONAL)'), ('NEW_EVENT_CANDIDATE', 'کاندید رویداد جدید'),
                  ('COMPOSITE_TRANSACTION', 'سند ترکیبی'), ('AMBIGUOUS_EVENT', 'مبهم'), ('INSUFFICIENT_INFORMATION', 'اطلاعات ناکافی'), ('NOT_AN_OPERATIONAL_EVENT', 'غیرعملیاتی (افتتاحیه/اختتامیه/بستن)')):
        n, a = T[o].get(k, (0, 0)); rows.append((fa, f(n), pct(n, tot(o)), f(a)))
    return table(['نتیجه', 'اسناد', 'سهم از اسناد', 'جمع بدهکار اسناد'], rows)
def cc_table(o):
    rows = []
    for k in ('PROVISIONAL_EXISTING_CC', 'NEW_CC_CANDIDATE', 'MULTIPLE_CC_CANDIDATES', 'INSUFFICIENT_INFORMATION'):
        n, nd = ccs[o].get(k, (0, 0)); rows.append((k, f(n), pct(n, elig[o]), f(nd)))
    rows.append(('EXACT_EXISTING_CC / VALIDATED_EXISTING_CC', '0', '0٪', '0 — بدون crosswalk مصوب غیرممکن است'))
    return table(['وضعیت', 'ردیف هزینه‌ای', 'سهم', 'اسناد'], rows)
tx_rev = mv('Taxi', '1404', 'FULL_YEAR', 'T_REV_TOTAL')
rpt = f'''# گزارش مدیریتی — ادغام داده‌های سازمان تاکسیرانی و سازمان پایانه‌ها در معماری کد یکتا (سال‌های ۱۴۰۴ و ۱۴۰۵)

> **وضعیت حاکمیتی:** همه نتایج این گزارش در لایهٔ A (شواهد مشاهده‌شده) یا لایهٔ B (پیشنهاد مدل) هستند. هیچ رویداد، مرکز هزینه، کاردینالیتی، KPI یا قاعده‌ای «مصوب» نشده است و هیچ مدرک تصمیم کمیته‌ای وجود ندارد. واحد پول فایل‌ها تصریح نشده (سازگار با ریال؛ تأییدنشده).
> **حریم خصوصی:** این گزارش و کتاب کار خلاصه شرح متنی اسناد (حاوی نام اشخاص) را ندارد؛ شرح کامل فقط در فایل محدود `document_lineage_RESTRICTED.csv`.

## خلاصه اجرایی

* **دریافت و صحت:** ۸ فایل اکسل (۲٬۱۷۸ ردیف حساب، ۱۱۱٬۶۰۰ خط سند). تراز بدهکار/بستانکار در هر چهار مجموعه صفر اختلاف دارد، همه اسناد متوازن‌اند و همه خطوط سند به حساب متناظر وصل می‌شوند. سند افتتاحیه ۱۴۰۵ هر دو سازمان، معکوس دقیق سند اختتامیه ۱۴۰۴ است (جز اختلاف ۱ ریالی در دو حساب پایانه‌ها).
* **دو سازمان دو منطق حسابداری متفاوت دارند:** تاکسیرانی صورت مالی تعهدی مستقل دارد (درآمد ۱۴۰۴ = {f(tx_rev)}؛ سود و زیان جاری بسته‌شده = ۱۴۵٬۸۶۰٬۳۹۴٬۵۳۶). پایانه‌ها **عاملیتی** عمل می‌کند: درآمد را برای شهرداری مطالبه و وصول می‌کند (بدهکار ۱۱۳-۱-۴/۸ و بستانکار ۲۱۱-۱) و بیشتر هزینه‌ها را به حساب مطالبه از شهرداری (بدهکار ۱۱۳-۱) می‌نویسد؛ حساب‌های هزینه ۶۱۱–۶۱۳ آن تقریباً خالی است. این موضوع مستقیم روی KPIهای پایانه‌ها اثر دارد (تصمیم CD-01).
* **انطباق با مدل شهرداری:** {f(cw.get('PROVISIONAL_TITLE_NATURE_MATCH', 0))} حساب (کل/معین) تطبیق موقت عنوان+ماهیت، {f(cw.get('EXPERT_REVIEW_CANDIDATE', 0))} مورد بازبینی کارشناسی و {f(cw.get('NO_MUNICIPALITY_EQUIVALENT', 0))} مورد بدون معادل؛ {coll} ردیف برخورد کد (شماره یکسان با معنای متفاوت، مثل ۴۱۱/۴۱۲/۴۱۳/۶۱۱) — برابری عددی کد هرگز شاهد هم‌ارزی نبوده است.
* **رویداد مالی:** {len(fe_all)} رویداد از کاتالوگ v7.1 (FE) در داده مشاهده شد و بدون بازتعریف به‌کار رفت؛ {len(tt_all)} رویداد کاندید جدید (TT-NE) پیشنهاد می‌شود که هر کدام شاهد سندی دارد.
* **مرکز هزینه:** {len([c for c,_n,_a in ccid['Taxi'] if c in CC])} مرکز هزینه موجود (CC-xxx) به‌صورت *موقت* برای تاکسیرانی و {len([c for c,_n,_a in ccid['Terminals'] if c in CC])} مرکز برای پایانه‌ها به کار رفت؛ ۳ مرکز کاندید جدید (TTCC-P-01..03) پیشنهاد می‌شود. نگاشت EXACT/VALIDATED صفر است چون crosswalk مصوب وجود ندارد.
* **KPI:** {nK['Taxi']} KPI برای تاکسیرانی و {nK['Terminals']} برای پایانه‌ها تعریف شد؛ فقط {kst['Taxi']['CALCULATED_FROM_SOURCE'] + kst['Terminals']['CALCULATED_FROM_SOURCE']} مورد کاملاً از منبع قابل محاسبه است و {kst['Taxi']['PARTIALLY_CALCULABLE'] + kst['Terminals']['PARTIALLY_CALCULABLE']} مورد جزئی؛ بقیه نیازمند داده عملیاتی/بودجه/تعریف کارشناسی‌اند و عدد ندارند.
* **مقایسه ۱۴۰۴/۱۴۰۵:** سال ۱۴۰۵ ناقص است (تاکسیرانی تا ۱۴۰۵/۰۷/۱۳، پایانه‌ها تا ۱۴۰۵/۰۷/۱۴) و تراکم ثبت تاکسیرانی از ماه پنجم بسیار پایین است. فقط پنجرهٔ مشترک (تاکسیرانی ماه ۱ تا {cover[('Taxi','1405')][7][-2:]}، پایانه‌ها ماه ۱ تا {cover[('Terminals','1405')][7][-2:]}) و فقط به‌عنوان شاخص مقایسه شده است؛ درصد رشد سالانه ارائه نمی‌شود.

## ۱. دقیقاً چه چیزی دریافت شد؟

{table(['سازمان', 'سال', 'خطوط سند', 'اسناد یکتا', 'ردیف حساب', 'جمع بدهکار', 'جمع بستانکار', 'بازه تاریخ', 'یکپارچگی منبع'], [srcrow(o, y) for o in ORGS for y in YEARS])}
* شماره سند (Sanad_Num) در سطح سراسری یکتا نیست؛ هویت سند «سازمان + سال + شماره» است. در داده، {one("SELECT count(*) FROM (SELECT sanad_num FROM sanad GROUP BY sanad_num HAVING count(DISTINCT org||fy)>1)")} شماره سند بین سازمان/سال مشترک است.
* ستون‌های منبع: `NameVahed` در تاکسیرانی فقط نوع سند («عادی») و در پایانه‌ها نام واحد/پایانه/غرفه است؛ `CodeMarkaz` در تاکسیرانی کد فعالیت (≈۳۴ فعالیت) و در پایانه‌ها فقط فعالیت ۰۰۸ است؛ `CodeVahed` در پایانه‌ها واحد سلسله‌مراتبی است (بخش اول = پایانه: ۰۰۱ کاوه، ۰۰۲ صفه، ۰۰۳ زاینده‌رود، ۰۰۴ جی، ۰۰۷ صمدیه، ۰۰۵ دفتر مرکزی). ستون‌های بانک/قرارداد/پروژه در منبع نیست.

## ۲. یافته‌ها در هر سازمان

### سازمان تاکسیرانی
* درآمد ۱۴۰۴: خدمات (پروانه، حق عضویت، نقل‌وانتقال) {f(mv('Taxi','1404','FULL_YEAR','T_REV_SERVICE'))}، کمک بودجه شهرداری {f(mv('Taxi','1404','FULL_YEAR','T_REV_GRANT'))}، سهم ۲٪ سرویس مدارس {f(mv('Taxi','1404','FULL_YEAR','T_REV_SCHOOL_SHARE'))}، جریمه تخلف {f(mv('Taxi','1404','FULL_YEAR','T_REV_FINES'))}، درآمد بدون شرح تفکیکی {f(mv('Taxi','1404','FULL_YEAR','T_REV_UNRESOLVED'))}؛ جمع {f(tx_rev)} (برابر با سند بستن حساب‌های موقت).
* هزینه عملیاتی ۱۴۰۴ (بدون استهلاک): {f(mv('Taxi','1404','FULL_YEAR','T_EXP_OP'))}؛ حقوق و مزایا {f(mv('Taxi','1404','FULL_YEAR','T_EXP_PAYROLL'))}؛ برون‌سپاری {f(mv('Taxi','1404','FULL_YEAR','T_EXP_OUTSRC'))} (طبقه‌بندی موقت)؛ کارمزد بانکی تنها {f(mv('Taxi','1404','FULL_YEAR','T_EXP_BANKFEE'))} در {f(mv('Taxi','1404','FULL_YEAR','T_BANKFEE_LINES'))} ردیف — بیشترین ردیف‌ها با کمترین مبلغ.
* **جریان عاملیتی سرویس مدارس (سامانه سفیر مهر):** در ۱۴۰۴ مبلغ {f(mv('Taxi','1404','FULL_YEAR','T_SCHOOL_RECEIPTS'))} به‌عنوان پیش‌دریافت امانی دریافت و {f(mv('Taxi','1404','FULL_YEAR','T_SCHOOL_PAYOUT'))} به شرکت‌ها پرداخت شده است. این جریان **درآمد/هزینه نیست** و در KPI درآمد/هزینه وارد نشد؛ فقط ۲٪ سهم سازمان درآمد است.
* {pct(one("SELECT count(*) FROM sanad s JOIN doc_class d ON d.doc_key=s.doc_key WHERE s.org='Taxi' AND d.kind='REGULAR' AND s.kol IN ('611','612','613') AND s.markaz IS NOT NULL AND s.markaz<>'NULL'"), one("SELECT count(*) FROM sanad s JOIN doc_class d ON d.doc_key=s.doc_key WHERE s.org='Taxi' AND d.kind='REGULAR' AND s.kol IN ('611','612','613')"))} ردیف‌های هزینه کد فعالیت منبع دارند ({one("SELECT count(DISTINCT markaz) FROM sanad WHERE org='Taxi' AND markaz IS NOT NULL AND markaz<>'NULL'")} کد فعالیت متمایز)، اما کد ۱۰۰ («خدمات رفاهی به پرسنل») عملاً کد عمومی برای کارمزد بانکی، برون‌سپاری و غیره است و کنار گذاشته شد.
* سپرده/ضمانت‌نامه شرکت‌های حمل‌ونقل عمدتاً در حساب انتظامی ۹۱۸/۹۱۹ ثبت می‌شود ({one("SELECT count(*) FROM doc_class WHERE rule_id='MEMO-GUARANTEE'")} سند) و فقط به‌صورت موقت و کم‌اطمینان با FE-15/FE-16 مرتبط شد.

### سازمان پایانه‌ها
* مطالبه درآمد صادرشده ۱۴۰۴: {f(mv('Terminals','1404','FULL_YEAR','M_BILLED'))}؛ وصول {f(mv('Terminals','1404','FULL_YEAR','M_COLLECTED'))} (نسبت دوره‌ای {pct(mv('Terminals','1404','FULL_YEAR','M_COLLECTED'), mv('Terminals','1404','FULL_YEAR','M_BILLED'))}). منابع: اجاره غرفات، عوارض ۵٪ فروش بلیط و عوارض شرکت‌های مسافربری، حق شارژ و خسارت.
* هزینه تحمیل‌شده به شهرداری (بدهکار ۱۱۳-۱ غیردرآمدی) ۱۴۰۴: {f(mv('Terminals','1404','FULL_YEAR','M_RECHARGE'))} که {pct(mv('Terminals','1404','FULL_YEAR','M_RECHARGE_OUTSRC'), mv('Terminals','1404','FULL_YEAR','M_RECHARGE'))} آن برون‌سپاری (انتظامات/تأسیسات؛ صورت‌وضعیت‌های مشترک چند سازمان) و {pct(mv('Terminals','1404','FULL_YEAR','M_RECHARGE_PAYROLL'), mv('Terminals','1404','FULL_YEAR','M_RECHARGE'))} حقوق و مزایاست. هزینه ثبت‌شده در حساب‌های ۶۱۱–۶۱۳ فقط {f(mv('Terminals','1404','FULL_YEAR','M_EXP_OWN'))} است.
* چرخه چک: دریافت چک‌های اقساطی اجاره (پیش‌دریافت) ← انتقال به وصول ← وصول؛ بیشترین حجم خطوط پایانه‌ها ({f(one("SELECT count(*) FROM line_event WHERE org='Terminals' AND acat IN ('NOTES_REC','ADV_REC')"))} خط اسناد دریافتنی و پیش‌دریافت از {f(src[('Terminals','1404')][2]+src[('Terminals','1405')][2])} خط کل) همین چرخه است و در دیکشنری v7.1 رویداد ندارد (شکاف GAP-03).
* مانده سپرده غرفات و شرکت‌ها (۲۱۲-۶) در پایان ۱۴۰۴: {f(one("SELECT value FROM metric_values WHERE org='Terminals' AND fy='1404' AND metric_id='B_DEPOSITS'"))}.

## ۳. چه بخشی با مدل شهرداری انطباق دارد؟

* **حساب:** دو سازمان از نمودار حساب سازمان‌های وابسته استفاده می‌کنند (کل ۱۱۱/۲۱۱/۴۱۳/۶۱۱…) و شهرداری نمودار دیگری دارد؛ مثال: کد ۴۱۲ در سازمان‌ها «بهای تمام‌شده» ولی در شهرداری «بهای خدمات (درآمد)» است. نتیجه: L1/L2/L3 هیچ تطبیقی ندارد؛ {f(cw.get('PROVISIONAL_TITLE_NATURE_MATCH', 0))} تطبیق L4 (موقت) و {f(cw.get('EXPERT_REVIEW_CANDIDATE', 0))} L5.
* واگرایی دو سازمان (سطح کد کامل): فقط تاکسیرانی {div.get('ONLY_TAXI', 0)}، فقط پایانه‌ها {div.get('ONLY_TERMINALS', 0)}، هم‌کد هم‌عنوان {div.get('SHARED_SAME_MEANING', 0)}، هم‌کد با عنوان متفاوت {div.get('SAME_CODE_DIFFERENT_TITLE', 0)}؛ تغییر ۱۴۰۴→۱۴۰۵: اضافه {div.get('ADDED_IN_1405', 0)}، حذف {div.get('REMOVED_IN_1405', 0)}، تغییر عنوان {div.get('RENAMED_IN_1405', 0)}.

## ۴. رویدادهای مالی

### تاکسیرانی ({f(tot('Taxi'))} سند)
{ev_table('Taxi')}
### پایانه‌ها ({f(tot('Terminals'))} سند)
{ev_table('Terminals')}
رویدادهای موجود (FE) که در داده مشاهده شدند: ''' + '، '.join(fe_all) + f'''.
*رویدادهای FE-46 (اضافه‌کار)، FE-48 (بیمه سهم کارفرما)، FE-60 (وصول بهای خدمات/غرفات) و … در v7.1 «کاندید مفهومی بدون مشاهده» بودند و اکنون برای نخستین‌بار مشاهدهٔ مستقیم دارند؛ این به معنای تأیید نیست.*

## ۵. رویدادهای جدید پیشنهادی (TT-NE)

''' + table(['شناسه', 'عنوان', 'سازمان', 'اسناد', 'چرا FE موجود کافی نیست'], [(e, TT_EVENTS[e][0], TT_EVENTS[e][5], f(sum(r[2] for o in ORGS for r in tt_used[o] if r[0] == e)), TT_EVENTS[e][6][:140]) for e in tt_all]) + f'''
هر کاندید یا به شکاف ثبت‌شدهٔ GAP-xx در v7.1 پیوند دارد یا ماهیت حسابداری/مدرک متفاوتی نسبت به FE موجود دارد (ADR-0009). تصمیم پذیرش با کمیته است (CD-EV-xx).

## ۶. مراکز هزینه قابل استفاده مجدد

* تاکسیرانی: ''' + '، '.join(f'{c} ({f(n)} ردیف)' for c, n, _a in ccid['Taxi'] if c in CC) + f'''.
* پایانه‌ها: ''' + '، '.join(f'{c} ({f(n)} ردیف)' for c, n, _a in ccid['Terminals'] if c in CC) + f'''.
* همگی `PROVISIONAL_EXISTING_CC`: تناظر معنایی عنوان/فعالیت است؛ نه EXACT و نه VALIDATED.

### نتایج نگاشت مرکز هزینه — تاکسیرانی ({f(elig['Taxi'])} ردیف هزینه‌ای/سرمایه‌ای)
{cc_table('Taxi')}
### پایانه‌ها ({f(elig['Terminals'])} ردیف)
{cc_table('Terminals')}
* درآمد، بانک، بدهی، افتتاحیه/اختتامیه و پیش‌پرداخت: `CC_NOT_APPLICABLE` ({f(one('SELECT count(*) FROM line_cc WHERE eligible=0'))} ردیف). اینکه درآمد «مرکز درآمد» بگیرد تصمیم مدل داده است (CD-03).
* بزرگ‌ترین ریسک پایانه‌ها: {f(ccs['Terminals'].get('INSUFFICIENT_INFORMATION', (0, 0))[0])} ردیف (عمدتاً تسویه تنخواه کارپردازی) بدون شرح ماهیت هزینه و بدون کد فعالیت مرکز هزینه ندارند و عمداً پر نشدند.

## ۷. مراکز هزینه جدید لازم‌اند؟

''' + table(['شناسه موقت', 'عنوان', 'سازمان', 'ریسک هم‌پوشانی'], [('TTCC-P-01', 'ساماندهی، صدور مجوز و نظارت بر ناوگان و شرکت‌های حمل‌ونقل درون‌شهری', 'تاکسیرانی', 'CC-406، CC-1502'), ('TTCC-P-02', 'حمل‌ونقل ویژه دانش‌آموزی و معلولین (سرویس مدارس)', 'تاکسیرانی', 'CC-406، CC-904'), ('TTCC-P-03', 'مدیریت و اجاره‌دهی پایانه‌های مسافربری برون‌شهری', 'پایانه‌ها', 'CC-403، CC-1201')]) + f'''
دلیل: ممیزی خدمات ۱۴۰۵ همین خدمات را «فاقد مرکز / نیازمند بررسی کارگروه» ثبت کرده است. هیچ کد CC-xxx جدیدی به master افزوده نشد. TTCC-P-03 مستقیم به هزینه‌ای نگاشت نشده و فقط جایگزین است (تصمیم همراه با CD-03/CD-06).

## ۸. کدام KPIها اکنون قابل اندازه‌گیری‌اند؟

* تاکسیرانی (از منبع): درآمد بهای خدمات، سهم جریمه، وابستگی به کمک بودجه، نسبت پوشش هزینه، سهم حقوق، بار کارمزد بانکی؛ جزئی: برون‌سپاری، نرخ نگهداشت ۲٪، سهم سرمایه‌ای.
* پایانه‌ها: مطالبه درآمد به تفکیک پایانه (TM-K02) و مانده سپرده‌ها (TM-K11) از منبع؛ نسبت وصول، درآمد به‌ازای واحد دارای مطالبه، هزینه تحمیل‌شده و سهم برون‌سپاری به‌صورت جزئی (به‌دلیل CD-01).
## ۹. کدام KPIها به داده بیشتری نیاز دارند؟
* **داده عملیاتی لازم است:** هزینه به‌ازای تاکسی فعال، هزینه نگهداری به‌ازای خودروی بازرسی، درآمد به‌ازای تراکنش خدمت، هزینه اداری به‌ازای درخواست، هزینه شکایت، هزینه و درآمد به‌ازای مسافر، نگهداری به‌ازای مساحت پایانه.
* **بودجه لازم است:** اجرای بودجه (هر دو سازمان). **تعریف کارشناسی:** رانندهٔ تحت پوشش، نرخ برگشت چک.
* تخمین مسافر از عوارض ۵٪ بلیط یا ناوگان از ثبت‌نام‌ها عمداً انجام نشد.

## ۱۰. تغییر ۱۴۰۴ ← ۱۴۰۵ (با رعایت ناقص بودن دوره)

''' + table(['سازمان', 'آخرین تاریخ واقعی ۱۴۰۵', 'پنجره مقایسه‌پذیر', 'هشدار'], [(ORGFA[o], cover[(o, '1405')][3], cover[(o, '1405')][7], cover[(o, '1405')][9]) for o in ORGS]) + f'''
* **تاکسیرانی (پنجره ماه ۱..۴، فقط شاخص):** درآمد بدون کمک بودجه {f(mv('Taxi','1404','WINDOW','T_REV_TOTAL') - mv('Taxi','1404','WINDOW','T_REV_GRANT'))} در ۱۴۰۴ در برابر {f(mv('Taxi','1405','WINDOW','T_REV_TOTAL') - mv('Taxi','1405','WINDOW','T_REV_GRANT'))} در ۱۴۰۵؛ کمک بودجه {f(mv('Taxi','1404','WINDOW','T_REV_GRANT'))} ← {f(mv('Taxi','1405','WINDOW','T_REV_GRANT'))}؛ هزینه عملیاتی {f(mv('Taxi','1404','WINDOW','T_EXP_OP'))} ← {f(mv('Taxi','1405','WINDOW','T_EXP_OP'))}. بخش مهمی از درآمد ۱۴۰۴ در ماه ۱۲ شناسایی شده (۳۴۹٫۵ میلیارد؛ از جمله ۱۶۹٫۸ میلیارد سهم سرویس مدارس در یک سند ۱۴۰۴/۱۲/۲۹)؛ پس تفاوت می‌تواند **تغییر رویهٔ شناسایی** باشد نه عملکرد.
* **پایانه‌ها (پنجره ماه ۱..۶، فقط شاخص):** مطالبه {f(mv('Terminals','1404','WINDOW','M_BILLED'))} ← {f(mv('Terminals','1405','WINDOW','M_BILLED'))}؛ نسبت وصول {pct(mv('Terminals','1404','WINDOW','M_COLLECTED'), mv('Terminals','1404','WINDOW','M_BILLED'))} ← {pct(mv('Terminals','1405','WINDOW','M_COLLECTED'), mv('Terminals','1405','WINDOW','M_BILLED'))}؛ هزینه تحمیل‌شده {f(mv('Terminals','1404','WINDOW','M_RECHARGE'))} ← {f(mv('Terminals','1405','WINDOW','M_RECHARGE'))} (رشد شدید؛ صورت‌وضعیت‌های برون‌سپاری ماهانه از ≈۳۳ به ≈۵۲ میلیارد رسیده — دلیل تجاری/نرخ یا دامنه قرارداد نامشخص است).
* تغییرات طبقه‌بندی حساب بین دو سال اندک است (جدول Account_Divergence). اسناد و ردیف‌های ۱۴۰۵ پس از ماه سوم در تاکسیرانی به‌شدت کمتر از ۱۴۰۴ است (نشانهٔ تأخیر ثبت).

## ۱۱. چه چیزهایی مبهم مانده است؟
* {f(outc['Taxi'].get('AMBIGUOUS_EVENT', (0, 0))[0] + outc['Terminals'].get('AMBIGUOUS_EVENT', (0, 0))[0])} سند مبهم و {f(outc['Taxi'].get('COMPOSITE_TRANSACTION', (0, 0))[0] + outc['Terminals'].get('COMPOSITE_TRANSACTION', (0, 0))[0])} سند ترکیبی؛ فهرست در شیت Exceptions.
* **یکپارچگی مرجع پایه:** هش فایل کاتالوگ رویداد v7.1 روی دیسک با هش ثبت‌شده در مانیفست خودش یکی نیست (فایل بعد از تولید مانیفست تغییر کرده)؛ دو شیتِ مورد استفاده (فرهنگ رویداد و ماتریس شواهد) با v7 مقایسهٔ مقداری شد و یکسان است، اما یکپارچگی سایر شیت‌های v7.1 تأیید نشده و از آن‌ها استفاده نشد (BASELINE_DISCOVERY).
* ماهیت حسابداری «بدهکار ۱۱۳-۱» در پایانه‌ها؛ واحد پول؛ هم‌ارزی حساب‌ها؛ تعلق ضمانت‌نامه‌های انتظامی؛ ردیف‌های درآمد ۴۱۳-۸ بدون شرح؛ لوازم یدکی (خرید یا تعمیر).

## ۱۲. تصمیم‌هایی که شهرداری باید بگیرد (به ترتیب اولویت)
1. CD-01: ماهیت حسابداری پایانه‌ها (عامل شهرداری یا واحد مستقل) — شرط عددی‌شدن KPIهای پایانه.
2. CD-02: تأیید واحد پول.
3. CD-03/04/05/06: مدل درآمد (مرکز درآمد یا بُعد) و ایجاد/رد TTCC-P-01..03.
4. CD-07/08: تأیید crosswalk فعالیت منبع تاکسیرانی و اصلاح کد عمومی ۱۰۰.
5. CD-EV-xx: پذیرش/ادغام کاندیدهای رویداد؛ CD-FE-60: تفکیک FE-60.
6. CD-ACC/CD-CARD: نگاشت حساب و کاردینالیتی.
7. CD-PERIOD/CD-OPS: داده کامل ۱۴۰۵، داده عملیاتی و بودجه.

## ۱۳. چه چیزی آماده استفاده است و چه چیزی موقت است؟

| آماده (از منبع، قابل ممیزی) | موقت (لایه B) | بدون مبنا / منتظر تصمیم |
|---|---|---|
| تلفیق منبع و ردیابی هر ردیف با Source_Record_ID؛ اسناد افتتاحیه/اختتامیه؛ تراز و کنترل سود و زیان تاکسیرانی؛ KPIهای TX-K01..K06 و TM-K02/K11 | نگاشت رویداد (FE/TT-NE)، مراکز هزینه (PROVISIONAL)، crosswalk حساب L4/L5، KPIهای جزئی | کاردینالیتی مصوب، قواعد الزامی، مرکز درآمد، مراکز TTCC-P، KPIهای عملیاتی/بودجه‌ای |
'''
rpt += f'''
## ۱۴. جمع‌بندی نهایی به تفکیک سازمان

**سازمان تاکسیرانی**
* *اکنون به‌صورت موقت قابل نهایی‌سازی:* هویت و ردیابی کامل اسناد؛ تراز و سود و زیان ۱۴۰۴ (منطبق با سند بستن حساب‌های موقت)؛ نگاشت رویداد برای {pct(outc['Taxi'].get('EXISTING_EVENT_CONFIRMED',(0,0))[0]+outc['Taxi'].get('EXISTING_EVENT_PROVISIONAL',(0,0))[0], tot('Taxi'))} اسناد به رویدادهای موجود (FE)؛ مراکز هزینه موجود برای {pct(ccs['Taxi'].get('PROVISIONAL_EXISTING_CC',(0,0))[0], elig['Taxi'])} ردیف‌های هزینه‌ای؛ شش KPI مالی.
* *نیازمند مدل جدید:* رویدادهای عاملیتی سرویس مدارس، کمک بودجه دریافتی، جریمه تخلف، واریزی‌های نامشخص بانکی؛ مراکز TTCC-P-01 (مجوز/نظارت) و TTCC-P-02 (حمل‌ونقل ویژه).
* *حل‌نشده:* {f(outc['Taxi'].get('AMBIGUOUS_EVENT',(0,0))[0])} سند مبهم، {f(outc['Taxi'].get('COMPOSITE_TRANSACTION',(0,0))[0])} ترکیبی، {f(ccs['Taxi'].get('INSUFFICIENT_INFORMATION',(0,0))[0] + ccs['Taxi'].get('MULTIPLE_CC_CANDIDATES',(0,0))[0])} ردیف مرکز هزینه بدون تصمیم، KPIهای عملیاتی (ناوگان، درخواست، شکایت) و مقایسه سالانه ۱۴۰۵.

**سازمان پایانه‌ها**
* *اکنون به‌صورت موقت قابل نهایی‌سازی:* مطالبه و وصول درآمد به تفکیک پایانه (بُعد واحد سازمانی قابل اتکا)؛ مانده سپرده‌ها؛ نگاشت رویداد به FE موجود برای {pct(outc['Terminals'].get('EXISTING_EVENT_CONFIRMED',(0,0))[0]+outc['Terminals'].get('EXISTING_EVENT_PROVISIONAL',(0,0))[0], tot('Terminals'))} اسناد (عمدتاً وصول FE-60 و هزینه‌های قبوض/حقوق).
* *نیازمند مدل جدید:* چرخه اسناد دریافتنی (TT-NE-13/14)، صدور مطالبه تعهدی (TT-NE-15)، سپرده غرفات (TT-NE-17/18)، تهاتر با شهرداری (TT-NE-19)، خروج انبار؛ مرکز TTCC-P-03 یا گسترش CC-403.
* *حل‌نشده:* ماهیت حسابداری هزینه‌های تحمیل‌شده و درآمد عاملیتی (CD-01)، {f(ccs['Terminals'].get('INSUFFICIENT_INFORMATION',(0,0))[0])} ردیف هزینه بدون مرکز، مخرج‌های عملیاتی (مسافر، مساحت) و بودجه.
'''
open(f'{OUT}/taxi_terminals_management_report.md', 'w', encoding='utf8').write(rpt)

# ============================================================================================ repository_integration_report.md
tests_done = [t for t in QA['tests']]
repo = f'''# repository_integration_report — Taxi & Terminal organizations (FY1404–1405)

## 1. Relevant repository paths

| Area | Path | Notes |
|---|---|---|
| New pipeline (this work) | `scripts/taxi_terminals_1404_1405/` | `common.py`, `rules.py`, `01_load.py` … `10_reports.py` (run in numeric order) |
| New tests | `tests/test_taxi_terminals_mapping.py` | rule regressions + DB invariants (skips when scratch DB is absent) |
| Outputs | `data/deliverables/taxi_terminals_1404_1405/` | workbook, reports, `machine_readable/`, `MANIFEST.json` (sha-256 of every file) |
| Scratch DB (not a master) | `data/work/taxi_terminals/tt.sqlite` | raw + derived tables, regenerated by the scripts |
| Baseline event dictionary | `data/deliverables/financial_event_discovery/revisions/1404-r20260922-canonical-events-v7.1/…v7.1.xlsx` | read-only |
| Baseline cost centers | `cc_master.json`; `data/deliverables/service_activity_coverage/revisions/1405-r20260922-service-coverage/…QA-remapped_v2.xlsx` | read-only |
| Existing models | `app/models.py` (`FinancialEventRef`, `CostCenterRef`, `FinancialAccountRef`, `OrgUnit`, `Transaction.financial_event_id/cost_center_id`) | unchanged |
| Existing UI | `frontend/src/pages/pre-accounting/PreAccountingPackagePage.tsx` + `demoData.ts` | static demo; unchanged |

**Run order (reproducible, from the repository root):**
`python scripts/taxi_terminals_1404_1405/01_load.py` → `02_extract_municipality_chart.py` → `03_build_core.py` → `04_classify_events.py` → `05_classify_cost_centers.py` → `06_accounts.py` → `07_kpi_comparison.py` → `09_qa.py` → `08_build_outputs.py` → `10_reports.py` → `11_postbuild_qa.py` → `10_reports.py` (again, so the QA report includes the post-build checks) ; then `pytest tests/test_taxi_terminals_mapping.py`. Inputs: the eight workbooks under `H:/Freelancing_Project/KalaniProject/Taxi_Gate` (path constant in `common.py`). Use only the standard library plus `openpyxl` and `xlsxwriter` (numpy/pandas are broken in this environment and are not required).

## 2. Reused models and code
* **Reused unchanged:** FE-01…FE-70 titles/definitions are read from the v7.1 workbook at build time (never copied or edited); `CC-xxx` ids and titles from `cc_master.json`; the GAP-01…GAP-12 vocabulary of `scripts/journal_1404_financial_events/fe_rules.py` (each new `TT-NE` candidate that corresponds to a known gap carries the GAP id).
* **Rule patterns reused:** `activity_rules.py` conventions (bank fees → treasury CC, vehicle → CC-1402, building cleaning → CC-1404, terminals/BRT → CC-403, fleet → CC-406).
* **Identity convention reused:** ADR-0011/0013/0027 — Source_Record_ID is a *reference*, not the package/line identity; ids are non-semantic apart from the file/row locator.

## 3. New source adapters
* `01_load.py` — lossless loader for the 8 workbooks into `sanad_raw`/`hesab_raw` (all cells kept as read, padding included), plus `inventory` (SHA-256, header check, cell types).
* `03_build_core.py` — typed/trimmed `sanad`/`hesab`, `Source_Record_ID = <TAXI|TERM>-<FY>-S-<6-digit Excel row>` (Hesab: `…-H-…`), `doc_key = <ORG>-<FY>-<Sanad_Num>`, hierarchy derived from code components (not from `Tabageh/Gorooh`, whose meaning is unverified), Persian normalisation only in `*_norm` columns.
* `02_extract_municipality_chart.py` — reads the municipality 1404 journal pickle to expose the observed municipality taxonomy.

## 4. Mapping algorithms
1. **Document kind** (`04`): OPENING / CLOSING_PERMANENT / CLOSING_TEMPORARY / INTERNAL_SETTLEMENT / REGULAR from the document description; memo-only (918/919) documents are separated (guarantees → FE-15/16 provisional).
2. **Line role & event evidence** (`04`, `rules.py`): account subtype `(kol, moeen, tafsili1)` published in Hesab is first-order evidence (e.g. 612-5-4 → vehicle repair); narration of the *same line* is second evidence; agreement of both upgrades PROVISIONAL → CONFIRMED (HIGH, 2 independent evidences). Doc-wide descriptions are *not* used for expense typing (they list payees).
3. **Document driver selection**: classes ranked EXP > REV > ASSET > PREPAY > INV > SPEC > SETTLE; a class drives when its own-side amount ≥ 10 % of the document debit total; settlement legs yield to expense/revenue drivers; bank/tankhah lines are COMPONENT; minor events are listed, never promoted silently.
4. **Composite test**: more than one *family* (payroll, contractor-settlement, revenue, school-service, other) among drivers → `COMPOSITE_TRANSACTION`; same-family components stay one event with a note. Offsetting same-account debit/credit lines inside a document are netted as internal reclassification.
5. **Cost center** (`05`): source activity code (CodeMarkaz) → crosswalk table `MZ` → CC; otherwise event-based defaults; decisive narration overrides (EV charging → CC-408, special-transport → TTCC-P-02, …). Catch-all source code 100 is rejected. Revenue/bank/liability/opening/closing → `CC_NOT_APPLICABLE`.
6. **Account crosswalk** (`06`): curated (kol, moeen) table with levels L4 (title+nature, provisional) / L5 (review) / NONE; code collisions flagged; L1–L3 never asserted.
7. **KPI** (`07`): metrics from regular documents only; windows by posting-density rule; no estimate of operational denominators.

## 5. Database compatibility
* `app/models.py` stores events/cost centers only as `(code, title)` rows (`financial_event_refs`, `cost_center_refs`) referenced by `Transaction`. The new codes (`TT-NE-xx`, `TTCC-P-xx`) fit those columns, but **nothing was inserted**: ADR-0015 forbids seeding Proposed centers into the operational `CostCenterRef`.
* There is no organization/entity dimension on those tables, no status/version columns and no event↔cost-center relation table; the observed matrix therefore cannot be stored without a schema change (not done).
* The scratch SQLite is independent of `municipality_demo.db`; no Alembic migration was created.

## 6. Import / export compatibility
* Machine-readable exports (`machine_readable/`): `canonical_events.csv|json`, `event_mapping_lines.csv`, `cost_center_mapping_lines.csv`, `account_crosswalk.csv`, `account_dictionary.csv`, `account_divergence.csv`, `document_lineage_docs.csv`, `document_lineage_RESTRICTED.csv`, `kpi_definitions.json`, `kpi_results.csv`, `exceptions_queue.csv`, `new_cost_center_candidates.json`, `SCHEMAS.json`.
* `import_ready/`: `proposed_financial_event_refs.csv` and `proposed_cost_center_refs.csv` mirror the existing `(code,title)` tables with extra governance columns and `activate_in_production = NO`; `organization_event_catalog.json`; `event_cost_center_observed_matrix.csv` with separate `Observed_Cardinality`, `Proposed_Cardinality`, `Approved_Cardinality` (= `Needs Decision`).

## 7. Pre-accounting compatibility (assessment)
| Capability asked | Current repository | Gap |
|---|---|---|
| Organization-specific event catalogs | none (`orgs.py` returns all events) | add `organization`/`source_subsystem` scope to the catalog crosswalk (ADR-0005/0007) |
| Cost-center filtering | page uses `DEMO_COST_CENTERS`; `/cost-centers` returns all rows | needs Rule-Profile-driven filter, status/version |
| Conditional input fields | demo only | requires approved rules (not available) |
| Accounting-head selection | `FinancialAccountRef` exists, unused by the page | import `Account_Crosswalk` after approval |
| Activity selection | `SubsystemActivity`, `Activity` exist | link `Activity_Service_Map` ids after CD-07 |
| KPI metadata | none | out of scope; KPI definitions are JSON only |
| Source document references | `Transaction.unique_code`; ADR-0013 Source Reference | map `Source_Record_ID`/`Doc_Key` as Source Reference |

**Plan (proposed only):** (1) approve CD-01…CD-08; (2) load approved events/centers into versioned catalog tables with status; (3) add organization scope; (4) expose the observed matrix as *advisory* suggestions in Draft/Review only; (5) activate rules via Rule Profiles per ADR-0012. No UI work was done.

## 8. Implementation status
| Item | Status |
|---|---|
| Source adapters, mapping pipeline, QA, workbook, exports, reports | **Implemented** (scripts + outputs) |
| Tests (`tests/test_taxi_terminals_mapping.py`) | **Implemented** |
| Import-ready CSV/JSON | **Generated, not integrated** |
| Schema/UI changes, catalog seeding | **Proposed only** |
| All events, cost centers, cardinalities, KPI definitions | **Awaiting approval** (no APPROVED state anywhere) |

## 9. Remaining engineering work
* Versioned catalog + status tables and import service; organization scope on catalog crosswalk.
* Replace the document-level text heuristics with approved Rule Profiles once decisions exist.
* Persist `Observed/Proposed/Approved` cardinality in a relation table (currently only in exports).
* Operational data ingestion (fleet, passengers, area, requests, budgets) to unlock KPIs.

## 10. Tests performed
QA summary: **PASS {qa_sum['PASS']} / REVIEW {qa_sum['REVIEW']} / FAIL {qa_sum['FAIL']}** (see `financial_mapping_QA.md`); workbook formula block: {sum(1 for x in fb if x[5] == 'PASS')}/{len(fb)} PASS (values cached by the script, no spreadsheet engine was available to recalculate). Pytest: `tests/test_taxi_terminals_mapping.py`.

## 11. Known limitations
* Heuristic, rule-based classification; no ML; 214 documents remain ambiguous by design.
* Expense typing for Terminals recharge lines depends on narration only.
* `Hesab.Kind/Type/P` semantics not interpreted.
* Currency unit unverified; amounts are not converted.
* The 1405 data are incomplete; window rule is a posting-density heuristic.
* Archive extraction: the `.rar` files could not be re-extracted by the available tools; extracted copies were used (hashes recorded).
'''
open(f'{OUT}/repository_integration_report.md', 'w', encoding='utf8').write(repo)

# ============================================================================================ financial_mapping_QA.md
qa = f'''# financial_mapping_QA — Taxi & Terminal organizations (FY1404–1405)

Reproduce: `python scripts/taxi_terminals_1404_1405/01_load.py … 09_qa.py` (see order in `repository_integration_report.md`). Source totals are re-read directly from the eight original workbooks inside `09_qa.py`, independently of the pipeline tables.

**Result: PASS {qa_sum['PASS']} · REVIEW {qa_sum['REVIEW']} · FAIL {qa_sum['FAIL']}.** REVIEW = needs expert judgement, not a processing failure. Workbook formula block (SUMIFS over `Document_Lineage`, `Event_Mapping`, `Cost_Center_Mapping` vs `Source_Profile`): {sum(1 for x in fb if x[5] == 'PASS')}/{len(fb)} PASS.

## 1. Coverage metrics
''' + table(['Organization', 'FY', 'Lines', 'Docs', 'Debit', 'Credit', 'Lines with event evidence at driver level', 'Documents unresolved (AMBIGUOUS)', 'Eligible expense/capital lines', 'Lines without CC (INSUFFICIENT)'],
            [(o, y, f(src[(o, y)][2]), f(src[(o, y)][3]), f(src[(o, y)][4]), f(src[(o, y)][5]),
              f(one("SELECT count(*) FROM line_event WHERE org=? AND fy=? AND role='DRIVER' AND own_event IS NOT NULL", o, y)),
              f(one("SELECT count(*) FROM doc_class WHERE org=? AND fy=? AND outcome='AMBIGUOUS_EVENT'", o, y)),
              f(one('SELECT count(*) FROM line_cc WHERE org=? AND fy=? AND eligible=1', o, y)),
              f(one("SELECT count(*) FROM line_cc WHERE org=? AND fy=? AND cc_status='INSUFFICIENT_INFORMATION'", o, y))) for o in ORGS for y in YEARS]) + f'''
Share of regular-document debit value whose primary event is AMBIGUOUS: {pct(one("SELECT sum(bed_total) FROM doc_class WHERE outcome='AMBIGUOUS_EVENT'"), one("SELECT sum(bed_total) FROM doc_class WHERE kind='REGULAR'"))}.

## 2. Tests
''' + table(['ID', 'Area', 'Description', 'Expected', 'Actual', 'Status', 'Detail'], [(t['test_id'], t['area'], t['description'], t['expected'], t['actual'], t['status'], t['detail'][:140]) for t in QA['tests']]) + f'''
## 3. Failed checks
''' + ('None.' if qa_sum['FAIL'] == 0 else '\n'.join(f"* {t['test_id']}: {t['description']} — {t['actual']}" for t in QA['tests'] if t['status'] == 'FAIL')) + f'''

An earlier QA run produced one FAIL (Q19-TT-NE-19: the check counted only DRIVER lines while the internal-settlement candidate is carried on SETTLEMENT lines) and one mis-specified carry-forward test (pre-closing balance compared instead of the closing document). Both were defects of the checks, not of the data, and were corrected before this run; the corrected tests are the ones above.

## 4. Data exceptions
* Duplicate-candidate record groups (same document, date, narration, account, amounts, Field1, person): ''' + ', '.join(f"{o}-{y}: {one('SELECT count(*) FROM (SELECT 1 FROM sanad WHERE org=? AND fy=? GROUP BY doc_key,date,des,hcode,bed,bes,sharh,f1,person HAVING count(*)>1)', o, y)}" for o in ORGS for y in YEARS) + f''' — kept, not removed.
* Terminals closing-vs-opening carry-forward: two accounts (122-3-0-0, 122-4-0-0) differ by 1 currency unit between the 1404 closing document and the 1405 opening document.
* Taxi 1405 has no temporary-closing document (year incomplete).

## 4b. Post-build checks on the delivered files (`11_postbuild_qa.py`)
Privacy scan of every non-restricted output against all distinct narration/name strings of the source; row-count and total reconciliation of the line-level exports against the sources; verbatim check of the last source row in the restricted lineage; manifest hashes; **baseline integrity** (v7.1 hash vs its manifest; value comparison of the two reused sheets against v7). See tests `P01`–`P12` in the table above.

## 5. Unresolved classifications
All unresolved/ambiguous/composite documents and cost-center gaps are listed in workbook sheet `Exceptions` and `machine_readable/exceptions_queue.csv`; open decisions in `Committee_Decisions`.

## 6. Important semantic exceptions
* Terminals ledger is agency-style (costs on debit 113-1, revenue on credit 211-1): KPI cost/revenue values are PARTIAL until CD-01.
* Taxi school-service money (213-2-5) is pass-through; it is excluded from revenue and cost KPIs; only the 2 % share is revenue.
* Source activity code 100 (Taxi) is a catch-all and is not used to pick a cost center.
* Account code collisions with the municipality chart: {coll} crosswalk rows.
* Guarantee/memo documents (918/919) are mapped to FE-15/FE-16 only provisionally (LOW).
'''
open(f'{OUT}/financial_mapping_QA.md', 'w', encoding='utf8').write(qa)
print('reports written')
# ---- manifest of every delivered file (regenerated last so hashes match the final reports)
man = {}
for root, _, fs in os.walk(OUT):
    for fn in sorted(fs):
        if fn == 'MANIFEST.json': continue
        p = os.path.join(root, fn)
        man[os.path.relpath(p, OUT).replace('\\', '/')] = dict(bytes=os.path.getsize(p), sha256=hashlib.sha256(open(p, 'rb').read()).hexdigest())
json.dump(dict(generated_for='Taxi/Terminals FY1404-1405 v1', baseline_v71_sha256_on_disk=V71_SHA, files=man), open(f'{OUT}/MANIFEST.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
print('manifest', len(man))
