"""v2 deliverable documents.  mode 'docs' (default): corrective_audit_v2.md, taxi_terminals_management_report_v2.md, committee_decisions_v2.xlsx, CD-01 memo, MANIFEST_v2.json
                                   mode 'qa'  : financial_mapping_QA_v2.md from the final qa_results_v2.json, then re-hash MANIFEST_v2.json (adds the QA report).
"""
import sqlite3, sys, os, json, hashlib, collections, datetime
import xlsxwriter
sys.path.insert(0, os.path.dirname(__file__))
from common import *
from rules import EVENT_REVIEW, TT_EVENTS, TT_EVENTS_V1
from decisions_v2 import CC_AUDIT, build_decisions, COLS as DEC_COLS
assert VARIANT == 'v2'
MODE = sys.argv[1] if len(sys.argv) > 1 else 'docs'
con = sqlite3.connect(DB, timeout=300); con.execute(f"ATTACH DATABASE '{WORK}/tt.sqlite' AS v1")
cur = con.cursor()
q = lambda s, *a: cur.execute(s, a).fetchall()
def one(s, *a):
    r = cur.execute(s, a).fetchone(); return r[0] if r and r[0] is not None else 0
QA = json.load(open(QA_JSON, encoding='utf8'))
ORGFA = {'Taxi': 'سازمان تاکسیرانی', 'Terminals': 'سازمان پایانه‌ها'}
f = lambda x: f'{x:,}' if isinstance(x, (int, float)) and x == int(x) else (f'{x:,.4f}' if isinstance(x, float) else str(x))
pct = lambda a, b: f'{(a / b):.1%}' if b else '—'
def md(h, rows):
    out = ['| ' + ' | '.join(h) + ' |', '|' + '|'.join(['---'] * len(h)) + '|']
    for r in rows: out.append('| ' + ' | '.join(str(x).replace('|', '/').replace('\n', ' ') for x in r) + ' |')
    return '\n'.join(out)
NOW = datetime.datetime.now().strftime('%Y-%m-%d')
RELOUT = 'data/deliverables/taxi_terminals_1404_1405/revisions/v2'

def stats():
    S = {}
    S['docs'] = {o: one('SELECT count(*) FROM doc_class WHERE org=?', o) for o in ORGS}
    S['lines'] = {o: one('SELECT count(*) FROM sanad WHERE org=?', o) for o in ORGS}
    S['doc_out'] = {(v, o): dict(q(f"SELECT outcome,count(*) FROM {'v1.' if v == 'v1' else ''}doc_class WHERE org=? GROUP BY 1", o)) for v in ('v1', 'v2') for o in ORGS}
    S['cov'] = {(r[0], r[1]): r for r in q("SELECT version,org,sum(eligible_lines),sum(selected_lines),sum(multiple_lines),sum(insufficient_lines),sum(eligible_value),sum(selected_value),sum(multiple_value),sum(insufficient_value) FROM cc_coverage WHERE fy='ALL' GROUP BY 1,2")}
    S['fe_v1'] = one("SELECT count(DISTINCT own_event) FROM v1.line_event WHERE own_event LIKE 'FE-%' AND role IN ('DRIVER','SETTLEMENT')")
    S['fe_v2'] = one("SELECT count(DISTINCT own_event) FROM line_event WHERE own_event LIKE 'FE-%' AND role IN ('DRIVER','SETTLEMENT')")
    S['tt_v2'] = [e for e in TT_EVENTS]
    S['res'] = {(r[0], r[1]): (r[2], r[3]) for r in q('SELECT org,resolution,count(*),sum(net_value) FROM cc_resolution GROUP BY 1,2')}
    S['v1_unres'] = {o: one('SELECT count(*) FROM cc_resolution WHERE org=?', o) for o in ORGS}
    S['kpi_status'] = {(o, v): dict(q(f"SELECT calc_status,count(*) FROM {'v1.' if v == 'v1' else ''}kpi_catalogue WHERE org=? GROUP BY 1", o)) for o in ORGS for v in ('v1', 'v2')}
    S['qa'] = collections.Counter(t['status'] for t in QA['tests'])
    S['qa_named'] = [t for t in QA['tests'] if t['test_id'].startswith('QA_')]
    S['qa_generic'] = collections.Counter(t['status'] for t in QA['tests'] if not t['test_id'].startswith('QA_') and not t['test_id'].startswith('P'))
    S['qa_post'] = collections.Counter(t['status'] for t in QA['tests'] if t['test_id'].startswith('P'))
    return S
S = stats()

def event_table():
    rows = []
    for r in q('SELECT v1_id,v1_title,review_outcome,v2_id,lifecycle_attribute,v1_docs,v1_driver_lines,v2_lines,v2_status FROM event_review ORDER BY v1_id'):
        rows.append((r[0], r[1][:60], r[2], r[3] + (f' [{r[4]}]' if r[4] else ''), f(r[5]), f(r[6]), f(r[7]), r[8]))
    return rows
OUTCOME_COUNT = collections.Counter(v[0] for v in EVENT_REVIEW.values())

def cc_rows():
    rows = []
    for o in ORGS:
        for v in ('v1', 'v2'):
            c = S['cov'][(v, o)]
            rows.append((ORGFA[o], v, f(c[2]), f(c[3]), pct(c[3], c[2]), f(c[4]), f(c[5]), f(c[6]), f(c[7]), pct(c[7], c[6])))
    return rows

def kpi_rows():
    rows = []
    for r in q('SELECT kpi_id,org,fy,window,v1_value,v2_value,independent_value,v1_status,v2_status,verdict FROM kpi_v1_v2 ORDER BY kpi_id,fy,window'):
        rows.append((r[0], r[2], r[3], f(r[4]) if r[4] is not None else '—', f(r[5]) if r[5] is not None else '—', f(r[6]) if r[6] is not None else '—', r[8], r[9]))
    return rows

def kpi_status_table():
    rows = []
    for r in q('SELECT kpi_id,org,title_fa,basis_type,v1_status,calc_status,v2_verdict FROM kpi_catalogue ORDER BY org,kpi_id'):
        rows.append((r[0], r[2][:70], r[3], r[4], r[5], r[6]))
    return rows

def res_table():
    rows = []
    for o in ORGS:
        tot = S['v1_unres'][o]
        a = S['res'].get((o, 'RESOLVED_PROVISIONALLY'), (0, 0)); b = S['res'].get((o, 'STILL_UNRESOLVED'), (0, 0)); c = S['res'].get((o, 'NO_LONGER_ELIGIBLE'), (0, 0))
        rows.append((ORGFA[o], f(tot), f(a[0]), f(b[0]), f(c[0]), f(a[1]), f(b[1])))
    return rows

def doc_trans():
    return [(r[0], r[1], f(r[2]), f(r[3])) for r in q('SELECT v1_outcome,v2_outcome,docs,bed_total FROM doc_transitions ORDER BY docs DESC')]

def qa_table(tests):
    return md(['Test ID', 'حوزه', 'جمعیت', 'مورد انتظار', 'واقعی', 'نتیجه'], [(t['test_id'], t['area'], (t.get('population') or '')[:60], t['expected'][:70], t['actual'][:140], t['status']) for t in tests])

# ===================================================================================================================== docs
def write(path, text):
    open(f'{OUT}/{path}', 'w', encoding='utf8', newline='\n').write(text)

def corrective_audit():
    e1 = event_table()
    c1 = {m: (g[0], g[1]) for m, g in [(r[0], (r[1], r[2])) for r in q("SELECT metric,value_lines,value_net FROM cc_proposal_recon WHERE version='v1' AND cc_id='TTCC-P-01'")]}
    t = []
    t.append('# Corrective Audit v2 — تاکسیرانی و پایانه‌ها، سال‌های مالی ۱۴۰۴–۱۴۰۵\n')
    t.append(f'تاریخ تولید: {NOW}. وضعیت: **Audited / Reconciled / Decision-Ready — هیچ موردی APPROVED نیست؛ `activate_in_production = NO`**. v1 دست‌نخورده است (`data/deliverables/taxi_terminals_1404_1405/`).\n')
    t.append('لایه‌ها: **A = شاهد مشاهده‌شده، B = پیشنهاد مدل، C = تأیید مرجع (هیچ ردیفی در C نیست).**\n')
    t.append('## ۱. روش\n')
    t.append('- بازمحاسبه مستقل KPI از فایل‌های اکسل منبع با کد جدا (`13_kpi_independent.py`: بدون SQLite، بدون موتور طبقه‌بندی).\n- بازتولید خطای TTCC-P-01 با پایگاه v1 (`14_v2_audit.py`)، بازبینی مفهومی ۲۸ کاندید (`rules.EVENT_REVIEW`)، crosswalk ردیف‌به‌ردیف و change log.\n- تأیید محتوای RAR با 7-Zip 23.01 (`machine_readable/rar_verification.json`).\n- مقایسه شیت‌به‌شیت v7 و v7.1 (`machine_readable/v71_vs_v7_sheets.json`).\n')
    t.append('## ۲. نواقص تأییدشده v1، ریشه، اصلاح، شاهد و وضعیت\n')
    D = [
     ('D-01', 'TTCC-P-01 در v1: «۶۴۴ ردیف مستقیم» در برابر ۵۳۲ ردیف NEW_CC_CANDIDATE', f"شمارش بر اساس ستون cc_id بود؛ ردیف‌های MULTIPLE_CC_CANDIDATES نامزد اول را در cc_id نگه می‌داشتند: ۱۱۲ ردیف (۱۸ سند، فعالیت منبع ۱۲۰، {f(c1.get('REPORTED_V1', (0, 0))[1] - c1.get('DIRECT', (0, 0))[1])} واحد)", 'ردیف MULTIPLE مرکز انتخاب‌شده ندارد؛ سه شمارنده جدا Direct/Ambiguous/Evidence_Support', 'QA_NEW_CC_PROPOSAL_RECONCILIATION-V1 (FAIL بازتولیدشده)، New_CC_Proposals v2', 'اصلاح‌شده'),
     ('D-02', 'TTCC-P-02 با شواهد ضعیف و هم‌پوشان با CC-406', '۹ ردیف فقط با شرح کل سند (Des) تطبیق خورده بود؛ ممیزی خدمات ۱۴۰۵ این خدمت را به CC-406 با HIGH نگاشت کرده است', 'ادغام در CC-406؛ جریان عاملیتی هزینه نیست', 'ممیزی ۱۴۰۵ (ردیف «خدمات تاکسیرانی و سرویس مدارس»)', 'اصلاح‌شده؛ نیازمند تأیید'),
     ('D-03', 'TTCC-P-03 مرکز کاندید بدون ردیف مستقیم', '۱٬۶۴۳ ردیف MULTIPLE و ۱٬۲۵۹ ردیف PROVISIONAL فقط چون پیشنهاد در فهرست نامزدها بود', 'زیرفعالیت CC-403 + بُعد منبع درآمد برای اجاره/عوارض', 'cc_proposal_recon (v1: DIRECT=0)', 'اصلاح‌شده؛ نیازمند تأیید'),
     ('D-04', 'قواعد متنی مرکز هزینه تاکسیرانی از شرح کل سند استفاده می‌کردند', 'یک شرح سند می‌توانست به همه ردیف‌های سند منتقل شود', 'فقط شرح خود ردیف؛ ۱۴۸ از ۱۵۷ ردیف P-02 با شرح ردیف تطبیق داشت', 'cc_proposal_moves', 'اصلاح‌شده'),
     ('D-05', 'TT-NE-19 («بستن حساب») چند ماهیت نامرتبط را یکجا گرفته بود', 'قاعده بر عبارت «بستن حساب» بود', 'تفکیک: پاداش بستن حساب (FE-50)، بستن پیش‌دریافت مدارس (TT-NE-05)، بستن سود و زیان (CLOSING_TEMPORARY)، تهاتر شهرداری (فقط TERM-1405-217/480)', 'TAXI-1405-440/562/444، TERM-1404-1171', 'اصلاح‌شده'),
     ('D-06', 'خطوط INSUFFICIENT پایانه‌ها فرضاً تنخواه بود', 'قواعد متنی اجزای حقوق، حواله انبار و فاکتور فروشندگان را نمی‌شناخت', 'قواعد جدید: اجزای حقوق (FE-44/45/46)، حواله مواد مصرفی (TT-NE-21)، ارزش افزوده (FE-11)', 'cc_unresolved_resolution.csv', 'بخشی اصلاح؛ باقی‌مانده در بخش ۶'),
     ('D-07', 'کاندیدهای TT-NE به‌صورت مفهومی بازبینی نشده بودند', 'چرخه‌عمر، مولفه ثبت و ادغام‌ها دیده نشده بود', f'۲۸ نتیجه بازبینی: {dict(OUTCOME_COUNT)}', 'QA_Semantic_Events، Event_Crosswalk_v1_v2', 'اصلاح‌شده؛ نیازمند تأیید کمیته'),
     ('D-08', 'KPI: درآمد خدمات تاکسیرانی شامل اجاره ۴۱۳-۸ بود؛ مخرج TX-K02 ناهمگون', 'تعریف شاخص پایه T_REV_SERVICE', 'T_REV_SERVICE = فقط ۴۱۳-۱؛ T_REV_RENT جدا؛ TX-K02 = جریمه ÷ (۴۱۳-۱ + جریمه)', 'QA_KPI_FORMULA_RECALCULATION، KPI_V1_V2', 'اصلاح‌شده'),
     ('D-09', 'اثر نوع سند اشتباه روی KPI ۱۴۰۵ (درآمد پنجره ۱۵۲٫۶ میلیارد v1 در برابر ۱۷۵٫۹ مستقل)', 'پاداش بستن حساب و بستن پیش‌دریافت به‌عنوان بستن حساب طبقه‌بندی شده بود', 'اصلاح نوع سند؛ مقدار پایپ‌لاین = مستقل', 'kpi_verification (۰ اختلاف)', 'اصلاح‌شده'),
     ('D-10', 'KPIهای پایانه (TM-K01/K05/K14) درآمد/هزینه سازمان فرض شده بودند', 'ماهیت حسابداری سازمان نامشخص است', 'وضعیت CALCULATED_BUT_ACCOUNTING_POLICY_PENDING؛ برچسب «مطالبه»/«هزینه تحمیل‌شده»', 'Terminal_Agency_Evidence، CD-01', 'اصلاح؛ نیازمند تصمیم مرجع'),
     ('D-11', 'TM-K04 «نرخ وصول» نبود', 'وصول دوره شامل مطالبات دوره‌های قبل و پیش‌دریافت است', 'برچسب «نسبت گردش وصول به مطالبه در دوره»؛ PARTIALLY_CALCULABLE', 'KPI_Catalogue v2', 'اصلاح‌شده'),
     ('D-12', 'منشأ RAR تأییدنشده (SOURCE_ARCHIVE_CONTENT_NOT_FULLY_VERIFIED)', 'ابزار tar با نام‌های فارسی شکست خورد', '7-Zip 23.01: `7z t` سالم؛ هر ۸ فایل از نظر SHA-256 یکسان', 'QA_RAR_SOURCE_VERIFICATION', 'حل‌شده با محدودیت (بخش ۸)'),
     ('D-13', 'هش v7.1 روی دیسک با هش مانیفست متفاوت بود و ثبت نشده بود', 'فایل پس از مانیفست ذخیره شده است (docProps 2026-09-24)', 'مقایسه شیت‌به‌شیت: شیت‌های مورد استفاده (فرهنگ رویداد، ماتریس شواهد، …) یکسان؛ تفاوت فقط در شیت‌های QA/خلاصه', 'QA_BASELINE_V71_PROVENANCE', 'ثبت‌شده/محدود؛ REVIEW'),
     ('D-14', 'TT-NE-34 (واریزی بانکی نامشخص) رویداد درآمدی فرض شده بود', 'بستانکار موقت ۲۱۱-۱-۵ هنوز درآمد نیست', 'EXC-01: صف تعلیق، نه رویداد و نه درآمد', 'QA_REVENUE_RECOGNITION_BASIS', 'اصلاح‌شده'),
     ('D-15', 'QA بدون منبع/جمعیت/روش و با فرمول cached بدون برچسب', 'قالب ساده QA', 'ستون‌های Test ID، منبع، جمعیت، روش، مورد انتظار، واقعی، نتیجه، استثنا، دستور بازتولید؛ برچسب cached', 'QA_Reconciliation v2', 'اصلاح‌شده'),
    ]
    t.append(md(['ID', 'مشکل', 'ریشه', 'اصلاح', 'شاهد', 'وضعیت'], D)); t.append('')
    t.append('## ۳. رویدادهای مالی — بازبینی ۲۸ کاندید v1\n')
    t.append(md(['v1', 'عنوان', 'نتیجه بازبینی', 'مقصد v2 [چرخه‌عمر]', 'اسناد v1', 'ردیف محرک v1', 'ردیف محرک v2 (همان شناسه)', 'وضعیت v2'], e1)); t.append('')
    t.append(f"نتیجه: ۲۸ کاندید → **{len(TT_EVENTS)} کاندید v2** ({sum(1 for v in EVENT_STATUS_V2_.values() if v == 'RETAINED_CANDIDATE')} کاندید باقی‌مانده + {sum(1 for v in EVENT_STATUS_V2_.values() if v != 'RETAINED_CANDIDATE')} در انتظار شواهد) و یک نوع استثنا (EXC-01). رویدادهای FE v7.1 به‌کاررفته: v1 = {S['fe_v1']}، v2 = {S['fe_v2']} (FE-70 به‌عنوان مولفه ثبت/ادغام افزوده شد). FE-xx بازتعریف نشد.\n")
    t.append('### تغییر نتیجه طبقه‌بندی اسناد\n')
    t.append(md(['v1', 'v2', 'اسناد', 'جمع بدهکار'], doc_trans())); t.append('')
    t.append('## ۴. مراکز هزینه\n')
    t.append(md(['سازمان', 'نسخه', 'ردیف واجد شرایط', 'با مرکز انتخاب‌شده', '٪', 'MULTIPLE', 'INSUFFICIENT', 'ارزش خالص واجد شرایط', 'ارزش انتخاب‌شده', '٪ ارزش'], cc_rows())); t.append('')
    t.append('ارزش = Σ(بدهکار−بستانکار) ردیف‌های هزینه‌ای/سرمایه‌ای واجد شرایط. جمعیت واجد شرایط v1 و v2 یکسان نیست (نقش ردیف و ردیف‌های VAT/تبعی اصلاح شد)، پس مقایسه نسبت‌ها بر مبنای جمعیت خودشان است.\n')
    for cid, a in CC_AUDIT.items():
        t.append(f"### {cid} → {a['recommendation']}\n\n{a['title_v2']}\n\n{a['reasoning']}\n")
        t.append(md(['شاخص', 'v1 ردیف', 'v1 خالص', 'v2 ردیف', 'v2 خالص'], [(m, f(*q("SELECT coalesce(value_lines,0) FROM cc_proposal_recon WHERE version='v1' AND cc_id=? AND metric=?", cid, m)[0]) if q("SELECT value_lines FROM cc_proposal_recon WHERE version='v1' AND cc_id=? AND metric=?", cid, m) else '—',
                 f(*q("SELECT coalesce(value_net,0) FROM cc_proposal_recon WHERE version='v1' AND cc_id=? AND metric=?", cid, m)[0]) if q("SELECT value_net FROM cc_proposal_recon WHERE version='v1' AND cc_id=? AND metric=?", cid, m) else '—',
                 f(*q("SELECT coalesce(value_lines,0) FROM cc_proposal_recon WHERE version='v2' AND cc_id=? AND metric=?", cid, m)[0]) if q("SELECT value_lines FROM cc_proposal_recon WHERE version='v2' AND cc_id=? AND metric=?", cid, m) else '—',
                 f(*q("SELECT coalesce(value_net,0) FROM cc_proposal_recon WHERE version='v2' AND cc_id=? AND metric=?", cid, m)[0]) if q("SELECT value_net FROM cc_proposal_recon WHERE version='v2' AND cc_id=? AND metric=?", cid, m) else '—') for m in ('DIRECT', 'AMBIGUOUS', 'EVIDENCE_SUPPORT', 'REPORTED_V1', 'ALT_OF_SELECTED')])); t.append('')
    t.append('## ۵. KPI\n')
    t.append(md(['KPI', 'سال', 'پنجره', 'v1', 'v2', 'مستقل', 'وضعیت v2', 'قضاوت'], kpi_rows())); t.append('')
    t.append(md(['KPI', 'عنوان', 'مبنا', 'وضعیت v1', 'وضعیت v2', 'قضاوت'], kpi_status_table())); t.append('')
    t.append('## ۶. مسائل حل‌نشده پس از v2\n')
    t.append(md(['سازمان', 'ردیف حل‌نشده v1', 'حل‌شده (موقت)', 'هنوز حل‌نشده', 'خارج از جمعیت واجد شرایط', 'ارزش حل‌شده', 'ارزش باقی‌مانده'], res_table())); t.append('')
    for o in ORGS:
        d1, d2 = S['doc_out'][('v1', o)], S['doc_out'][('v2', o)]
        t.append(f"- {ORGFA[o]}: اسناد مبهم/ترکیبی/در انتظار شناسایی v1 = {d1.get('AMBIGUOUS_EVENT', 0) + d1.get('COMPOSITE_TRANSACTION', 0)}؛ v2 = {d2.get('AMBIGUOUS_EVENT', 0) + d2.get('COMPOSITE_TRANSACTION', 0)} + {d2.get('PENDING_IDENTIFICATION', 0)} سند EXC-01.")
    t.append('\nمواردی که عمداً حل نشدند: ردیف‌های تنخواه/سند بدون شرح ماهیت و بدون کد فعالیت (INSUFFICIENT)، ردیف‌های ۱۱۸/۱۲۰ تاکسیرانی (MULTIPLE تا تصمیم CD-04/CD-08)، خدمات برون‌سپاری بدون شرح فعالیت.\n')
    t.append('## ۷. نتایج QA جدید (بدون سرکوب)\n')
    t.append(f"شمار کل: PASS={S['qa']['PASS']} / REVIEW={S['qa']['REVIEW']} / FAIL={S['qa']['FAIL']}. تست‌های نام‌دار (حوزه V1_ARTIFACT بازتولید نقص v1 است و FAIL آن عمدی و حفظ‌شده است):\n")
    t.append(qa_table(S['qa_named'])); t.append('')
    t.append('## ۸. یادداشت‌های صداقت و محدودیت‌ها\n')
    t.append('- در حین ساخت v2 دو اشکال پیاده‌سازی کشف و اصلاح شد: (۱) واژه «پایانه» در متن باعث نگاشت ۹۱۲ ردیف پایانه‌ها به CC-403 می‌شد (قاعده‌های سرمایه‌ای/ناوگان شهرداری مستثنی شد)؛ (۲) تغییر شناسه قاعده برای صورت‌وضعیت خدمات پایانه ۴۵۶ ردیف (۱٫۷۶ هزار میلیارد) را از جمعیت واجد شرایط مرکز هزینه خارج کرده بود (پیشوند TX-)؛ پس از آشکار شدن در مقایسه v1/v2 اصلاح شد.\n- 7-Zip از 7-zip.org با `curl --ssl-no-revoke` (بدون بررسی ابطال گواهی) دانلود و با `msiexec /a` بسته‌گشایی شد؛ هش 7z.exe در گزارش تأیید ثبت است. نام پوشه‌های فارسی در خروجی کنسول 7z به‌صورت خط‌زیر دیده شد؛ پس نام پوشه سازمان مستقل تأیید نشد (محتوای فایل‌ها بایت‌به‌بایت تأیید شد).\n- بازمحاسبه مستقل KPI از همان فایل‌های منبع است، اما فرض‌های تعریف (نوع سند، فیلتر حساب) را با پایپ‌لاین به‌اشتراک می‌گذارد؛ تأیید ریاضی است نه تأیید سیاست حسابداری.\n- مقدار ذخیره‌شده فرمول‌های QA_Reconciliation محاسبه‌شده توسط اسکریپت (cached) است.\n- واحد پول منبع تأیید نشده است؛ مبالغ بدون تبدیل.\n')
    return '\n'.join(t)

def management_report():
    t = ['# گزارش مدیریتی v2 — تاکسیرانی و پایانه‌ها، سال‌های مالی ۱۴۰۴ و ۱۴۰۵ (نیمه‌اول)\n', f'تاریخ: {NOW}. وضعیت: **حسابرسی‌شده و تطبیق‌داده‌شده، آمادهٔ تصمیم؛ هیچ موردی مصوب نیست؛ هیچ تغییری در سامانه عملیاتی اعمال نشده است.**\n']
    t.append('## خلاصه\n')
    t.append(f"- منبع: ۸ فایل اکسل (حساب و سند هر دو سازمان در دو سال)، {f(S['lines']['Taxi'] + S['lines']['Terminals'])} ردیف سند در {f(S['docs']['Taxi'] + S['docs']['Terminals'])} سند. محتوای هر دو آرشیو RAR با 7-Zip استخراج و فایل‌ها بایت‌به‌بایت با نسخهٔ تحلیل‌شده یکسان است.\n- رویدادهای مالی: ۲۸ کاندید رویداد جدید بازبینی مفهومی شد؛ {len(TT_EVENTS)} کاندید باقی ماند (۷ مورد به رویداد موجود یا چرخهٔ عمر ادغام شد).\n- مراکز هزینه: از سه مرکز پیشنهادی فقط TTCC-P-01 با دامنه‌ای بازتعریف‌شده باقی ماند؛ TTCC-P-02 با CC-406 ادغام شد؛ TTCC-P-03 زیرفعالیت CC-403 و بُعد منبع درآمد شد.\n")
    t.append('## پوشش مراکز هزینه\n'); t.append(md(['سازمان', 'نسخه', 'ردیف واجد شرایط', 'با مرکز', '٪', 'چندمرکزی', 'ناکافی', 'ارزش واجد شرایط', 'ارزش با مرکز', '٪ ارزش'], cc_rows())); t.append('')
    t.append('ردیف‌های «چندمرکزی» و «ناکافی» عمداً به مرکز نگاشت نشده‌اند.\n')
    t.append('## KPIهای قابل اتکا\n')
    k = q("SELECT kpi_id,fy,window,value,numerator,denominator FROM kpi_results WHERE org='Taxi' AND status='CALCULATED_AND_VERIFIED' AND fy='1404' AND window='FULL_YEAR' ORDER BY kpi_id")
    t.append(md(['KPI', 'عنوان', 'مقدار (سال کامل ۱۴۰۴)', 'وضعیت'], [(r[0], q('SELECT title_fa FROM kpi_catalogue WHERE kpi_id=?', r[0])[0][0][:60], f(r[3]) if r[3] is not None else f(r[4]), 'تأیید با بازمحاسبه مستقل') for r in k])); t.append('')
    t.append('وضعیت همه ۳۱ KPI: ' + '؛ '.join(f"{ORGFA[o]}: " + ' ، '.join(f'{k_}={v}' for k_, v in sorted(S['kpi_status'][(o, 'v2')].items())) for o in ORGS) + '\n')
    t.append('KPIهای پایانه‌ها (مطالبه، هزینه تحمیل‌شده) تا تصمیم دربارهٔ ماهیت حسابداری سازمان «وابسته به سیاست حسابداری» هستند؛ مبلغ مطالبه ۱۴۰۴ و وصول با بازمحاسبه مستقل تأیید شد، اما اینکه درآمد متعلق به سازمان است یا شهرداری تصمیمی بیرونی است.\n')
    t.append('## آنچه باید خارج از سیستم تصمیم گرفته شود\n')
    dec = build_decisions(q, one)
    t.append(md(['شناسه', 'سازمان', 'موضوع', 'مرجع', 'مسدودکننده؟', 'وضعیت'], [(d[0], d[1], d[2][:70], d[8][:50], d[10], d[11]) for d in dec if d[11] == 'REQUIRES_AUTHORITY_DECISION' and not d[0].startswith('CD-EV')])); t.append('')
    t.append('کاندیدهای رویداد (CD-EV-*) با وضعیت «مدل‌سازی موقت» نیاز به بازبینی کمیته رویداد دارند و مسدودکنندهٔ تحویل موقت نیستند.\n')
    t.append('## وضعیت نهایی هر سازمان\n')
    for o in ORGS:
        c = S['cov'][('v2', o)]
        t.append(f"### {ORGFA[o]}\n- پوشش مرکز هزینه: {f(c[3])} از {f(c[2])} ردیف ({pct(c[3], c[2])})؛ چندمرکزی {f(c[4])}، ناکافی {f(c[5])}.")
    t.append('- تاکسیرانی: **آماده برای تحویل موقت** (به‌شرط وضعیت PROPOSED)؛ نیازمند تأیید رسمی کارشناسان (CD-04، CD-07، CD-08 و کاندیدهای رویداد)؛ داده تکمیلی لازم برای KPIهای عملیاتی و بودجه‌ای و برای کامل‌بودن ۱۴۰۵.')
    t.append('- پایانه‌ها: **آماده برای تحویل موقت نگاشت‌های دفتری**؛ KPIهای مالی **مسدود تا CD-01**؛ بخشی از ردیف‌ها از نظر فنی حل‌نشده (فهرست در Exceptions)؛ داده تکمیلی عملیاتی لازم است.\n')
    t.append('جزئیات فنی: `corrective_audit_v2.md`، تصمیم‌ها: `committee_decisions_v2.xlsx`، کنترل کیفیت: `financial_mapping_QA_v2.md`.\n')
    return '\n'.join(t)

def memo_cd01():
    ex = q("""SELECT s.doc_key,s.date,s.hcode,coalesce(a.title,''),s.bed,s.bes FROM sanad s LEFT JOIN account_dictionary a ON a.org=s.org AND a.fy=s.fy AND a.hcode=s.hcode
              WHERE s.doc_key IN ('TERMINALS-1404-76','TERM-1404-76','TERM-1404-207','TERM-1405-422','TERM-1405-217','TERM-1405-480') ORDER BY s.doc_key,s.src_row""")
    _by = collections.defaultdict(list)
    for r_ in ex: _by[r_[0]].append(r_)
    ex = [r_ for k_ in sorted(_by) for r_ in sorted(_by[k_], key=lambda x: -max(x[4] or 0, x[5] or 0))[:10]]
    ta = q("SELECT section,fy,doc_kind,account_group,account_title,debit,credit FROM terminal_agency WHERE section='FLOWS' ORDER BY fy,debit DESC LIMIT 14") if one("SELECT count(*) FROM terminal_agency WHERE section='FLOWS'") else q('SELECT section,fy,doc_kind,account_group,account_title,debit,credit FROM terminal_agency ORDER BY section,fy,debit DESC LIMIT 14')
    t = ['# یادداشت کارشناسی CD-01 — ماهیت حسابداری سازمان پایانه‌ها\n', f'تاریخ: {NOW}. وضعیت: **REQUIRES_AUTHORITY_DECISION — مسدودکننده برای KPIهای مالی پایانه‌ها.**\n']
    t.append('## پرسش\nآیا سازمان پایانه‌ها در این دفاتر نقش «عامل شهرداری» (هزینه به حساب شهرداری و درآمد برای شهرداری) دارد، یا واحد مستقلی است که درآمد و هزینهٔ خود را شناسایی می‌کند؟\n')
    t.append('## شواهد مشاهده‌شده (لایه A)\n')
    t.append('- حساب‌های ۱۱۳-۱-۱ (طلب از شهرداری مرکزی) و ۲۱۱-۱-۱ (بدهی به شهرداری): مانده افتتاحیه و اختتامیه هر دو سال **صفر** است؛ طی سال گردش بزرگ دارند و پایان دوره با اسناد تهاتر (INTERNAL_SETTLEMENT، ۱۴۰۵) یا سند بستن حساب موقت (CLOSING_TEMPORARY، ۱۴۰۴) صفر می‌شوند.\n- بدهکار ۱۱۳-۱-۱ = هزینهٔ تحمیل‌شده به شهرداری؛ بستانکار ۲۱۱-۱-۱ = مطالبهٔ درآمد برای شهرداری.\n- مطالبه صادرشده از بهره‌برداران: ۱۱۳-۱-۴ و ۱۱۳-۱-۸ (سهم ۵٪ بلیط) با وصول در بانک؛ ودایع ۲۱۲-۶ مانده دارند.\n')
    t.append(md(['بخش', 'سال', 'نوع سند', 'گروه حساب', 'عنوان حساب', 'بدهکار', 'بستانکار'], [(r[0], r[1], r[2], r[3], r[4], f(r[5]), f(r[6])) for r in ta])); t.append('')
    t.append('### نمونه اسناد (بدون شرح متنی)\n')
    t.append(md(['سند', 'تاریخ', 'کد حساب', 'عنوان حساب', 'بدهکار', 'بستانکار'], [(r[0], r[1], r[2], r[3][:40], f(r[4]), f(r[5])) for r in ex])); t.append('')
    t.append('## تفسیرها\n| تفسیر | پیامد برای رویدادها | پیامد برای KPI |\n|---|---|---|\n| الف) عامل شهرداری | مطالبه/هزینه تحمیل‌شده «جریان عاملیتی» است نه درآمد/هزینه سازمان | TM-K01/K05/K14 به جریان‌های عاملیتی تغییر هویت می‌دهند؛ درآمد/هزینه فقط حق‌الزحمه سازمان |\n| ب) واحد مستقل | درآمد = مطالبه صادرشده؛ هزینه تحمیل‌شده = هزینه سازمان با طلب از شهرداری | KPIها همان‌اند ولی طلب از شهرداری باید جدا بررسی شود |\n| ج) واحد ستادی با تسهیم | تسهیم هزینه ستادی | KPI بازتعریف می‌شود |\n')
    t.append('## توصیه مدل (غیرالزام‌آور)\nتا تعیین تکلیف: مطالبه را «مطالبه صادرشده (assessment)» و هزینه را «هزینه تحمیل‌شده» بنامید و KPIهای وابسته را در وضعیت `CALCULATED_BUT_ACCOUNTING_POLICY_PENDING` نگه دارید. نتیجه‌گیری حقوقی از دفاتر ممکن نیست.\n')
    t.append('## مدارک لازم از مرجع\n- اساسنامه/مصوبهٔ تشکیل و آیین‌نامه مالی سازمان؛ تفاهم‌نامه تسهیم درآمد؛ نحوه ثبت در صورت‌های مالی شهرداری؛ سیاست شناسایی درآمد و هزینه.\n')
    return '\n'.join(t)

def committee_xlsx():
    wbk = xlsxwriter.Workbook(f'{OUT}/committee_decisions_v2.xlsx')
    H = wbk.add_format({'bold': True, 'bg_color': '#1F3864', 'font_color': 'white', 'text_wrap': True, 'border': 1, 'align': 'center', 'valign': 'vcenter', 'reading_order': 2})
    T = wbk.add_format({'text_wrap': True, 'valign': 'top', 'border': 1, 'reading_order': 2}); N = wbk.add_format({'num_format': '#,##0', 'valign': 'top', 'border': 1})
    TT_ = wbk.add_format({'bold': True, 'font_size': 14, 'reading_order': 2})
    dec = build_decisions(q, one)
    ws = wbk.add_worksheet('Decisions'); ws.right_to_left(); ws.write(0, 0, 'ماتریس تصمیم کمیته — v2 (هیچ تصمیمی اتخاذ‌شده نیست؛ ستون وضعیت = آمادگی)', TT_)
    HD = ['Decision ID', 'Organization', 'Subject', 'Current evidence', 'Model recommendation', 'Alternative options', 'Financial / operational impact', 'Relevant source examples', 'Expert responsible', 'Required approval', 'Blocking / non-blocking', 'Decision status', 'Recommended next action']
    for j, h in enumerate(HD): ws.write(2, j, h, H); ws.set_column(j, j, 34 if j in (2, 3, 4, 12) else 22)
    for i, r in enumerate(dec):
        for j, v in enumerate(r): ws.write(3 + i, j, v, T)
    ws.freeze_panes(3, 1); ws.autofilter(2, 0, 2 + len(dec), len(HD) - 1)
    # supporting examples: real documents (no narration), selected by evidence class
    ws2 = wbk.add_worksheet('Supporting_Examples'); ws2.right_to_left(); ws2.write(0, 0, 'نمونه‌های واقعی از اسناد منبع (شناسه سند، حساب‌ها و مبالغ؛ بدون شرح متنی)', TT_)
    for j, h in enumerate(['Decision', 'Evidence class', 'doc_key', 'date', 'account', 'account title', 'debit', 'credit', 'v2 event', 'role', 'v2 CC status', 'v2 CC']): ws2.write(2, j, h, H); ws2.set_column(j, j, 18)
    picks = []
    def docs_for(cond, n=2, org=None):
        return [r[0] for r in q(f"SELECT e.doc_key,sum(e.amount_dr+e.amount_cr) a FROM line_event e {cond} GROUP BY 1 ORDER BY a DESC LIMIT {n}")]
    for did, cls, cond in (('CD-01', 'مطالبه/وصول پایانه', "WHERE e.org='Terminals' AND e.own_event IN ('TT-NE-15','TT-NE-01') AND e.role='DRIVER'"), ('CD-01', 'تهاتر با شهرداری TT-NE-19', "WHERE e.own_event='TT-NE-19' AND e.role='DRIVER'"),
                           ('CD-04', 'تاکسیرانی: انتخاب‌شده TTCC-P-01', "JOIN line_cc c ON c.sid=e.sid WHERE c.cc_id='TTCC-P-01' AND e.role='DRIVER'"), ('CD-04', 'تاکسیرانی: ابهام ۱۲۰ (MULTIPLE)', "JOIN line_cc c ON c.sid=e.sid WHERE c.source_markaz='120' AND c.cc_status='MULTIPLE_CC_CANDIDATES'"),
                           ('CD-05', 'سرویس مدارس: دریافت امانی TT-NE-03', "WHERE e.own_event='TT-NE-03' AND e.role='DRIVER'"), ('CD-05', 'سرویس مدارس: پرداخت TT-NE-04', "WHERE e.own_event='TT-NE-04' AND e.role='DRIVER'"), ('CD-05', 'سهم نگهداشته TT-NE-05', "WHERE e.own_event='TT-NE-05' AND e.role='DRIVER'"),
                           ('CD-06', 'هزینه پایانه → CC-403', "JOIN line_cc c ON c.sid=e.sid WHERE c.cc_id='CC-403' AND e.org='Terminals'"), ('CD-08', 'حقوق پایانه → CC-1301', "JOIN line_cc c ON c.sid=e.sid WHERE c.cc_id='CC-1301' AND e.org='Terminals'"),
                           ('CD-EV-13', 'چرخه‌عمر چک TT-NE-13', "WHERE e.own_event='TT-NE-13' AND e.lifecycle_action='RETURN_DISHONOURED'"), ('CD-EXC01', 'واریزی نامشخص EXC-01', "WHERE e.own_event='EXC-01'"), ('CD-FE60', 'FE-60 تاکسیرانی', "WHERE e.own_event='FE-60' AND e.org='Taxi' AND e.role='DRIVER'"),
                           ('CD-FE60', 'FE-60 پایانه', "WHERE e.own_event='FE-60' AND e.org='Terminals' AND e.role='DRIVER'")):
        for dk in docs_for(cond): picks.append((did, cls, dk))
    r = 3
    for did, cls, dk in picks:
        for row in q("""SELECT s.doc_key,s.date,s.hcode,coalesce(a.title,''),s.bed,s.bes,coalesce(e.own_event,''),e.role,coalesce(c.cc_status,''),coalesce(c.cc_id,'') FROM sanad s JOIN line_event e ON e.sid=s.sid JOIN line_cc c ON c.sid=s.sid
                        LEFT JOIN account_dictionary a ON a.org=s.org AND a.fy=s.fy AND a.hcode=s.hcode WHERE s.doc_key=? ORDER BY s.src_row LIMIT 14""", dk):
            vals = [did, cls] + list(row[:4]) + [row[4], row[5]] + list(row[6:])
            for j, v in enumerate(vals): (ws2.write_number(r, j, v, N) if j in (6, 7) and isinstance(v, (int, float)) else ws2.write(r, j, '' if v is None else str(v), T))
            r += 1
    ws2.freeze_panes(3, 0)
    ws3 = wbk.add_worksheet('CD-01_Memo'); ws3.right_to_left(); ws3.set_column(0, 0, 150)
    for i, ln in enumerate(memo_cd01().split('\n')): ws3.write(i, 0, ln, T if ln.strip() else None)
    ws4 = wbk.add_worksheet('README'); ws4.right_to_left(); ws4.set_column(0, 0, 130)
    for i, ln in enumerate(['این فایل مشتق از Decision_Readiness در کتاب کار v2 است. هیچ تصمیم یا مصوبه‌ای ثبت نشده است؛ ستون «Decision status» وضعیت آمادگی است (TECHNICALLY_VERIFIED / PROVISIONALLY_MODELED / REQUIRES_AUTHORITY_DECISION).',
                            'نمونه‌ها از اسناد واقعی منبع انتخاب شده‌اند (بزرگ‌ترین مبلغ برای هر دسته)؛ شرح متنی اسناد عمداً نیامده است.']): ws4.write(i, 0, ln, T)
    wbk.close()

def manifest(extra_qa=False):
    man = {}
    for root, _, fs in os.walk(OUT):
        for fn in sorted(fs):
            p = os.path.join(root, fn); rel = os.path.relpath(p, OUT).replace('\\', '/')
            if rel.startswith('MANIFEST'): continue
            if rel == 'financial_mapping_QA_v2.md' and not extra_qa: continue
            man[rel] = dict(bytes=os.path.getsize(p), sha256=hashlib.sha256(open(p, 'rb').read()).hexdigest())
    base = f'{ROOT}/data/deliverables/financial_event_discovery/revisions/1404-r20260922-canonical-events-v7.1/financial_event_discovery_1404-r20260922_canonical-events_v7.1.xlsx'
    m = dict(generated_for='Taxi/Terminals FY1404-1405 v2 (Audited, Reconciled, Decision-Ready)', generated_on=NOW, activate_in_production='NO', approved_items=0,
             v1_preserved_at='data/deliverables/taxi_terminals_1404_1405/', baseline_v71_sha256_current=hashlib.sha256(open(base, 'rb').read()).hexdigest(), baseline_v71_sha256_recorded_in_its_manifest='3561b9817df949b3d3175a74ccc40e7f01cb2fa932bebc03fadb7ace6c6449fa',
             self_referential_exclusions=['MANIFEST_v2.json'] + ([] if extra_qa else ['financial_mapping_QA_v2.md']), files=man)
    json.dump(m, open(f'{OUT}/MANIFEST_v2.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)

from rules import EVENT_STATUS_V2 as EVENT_STATUS_V2_
if MODE == 'docs':
    write('corrective_audit_v2.md', corrective_audit())
    write('taxi_terminals_management_report_v2.md', management_report())
    write('CD-01_terminal_agency_expert_memo.md', memo_cd01())
    committee_xlsx()
    manifest(False)
    print('docs written')
else:
    S = stats()
    t = ['# financial_mapping_QA_v2 — کنترل کیفیت v2\n', f'تاریخ: {NOW}. جمع: PASS={S["qa"]["PASS"]} / REVIEW={S["qa"]["REVIEW"]} / FAIL={S["qa"]["FAIL"]} (هیچ شمارشی هدف نبوده؛ FAIL با حوزه V1_ARTIFACT بازتولید نقص v1 است و عمداً حفظ شده).\n']
    t.append('مقادیر ذخیره‌شده فرمول‌های کتاب کار (cached) توسط اسکریپت محاسبه شده‌اند و بازمحاسبه زنده توسط موتور اکسل نیستند؛ بازمحاسبه مستقل در اسکریپت‌های زیر انجام می‌شود.\n')
    t.append(f"- تست‌های عمومی (Q01–Q45): {dict(S['qa_generic'])}\n- تست‌های نام‌دار v2: {dict(collections.Counter(x['status'] for x in S['qa_named']))}\n- تست‌های خروجی (P*): {dict(S['qa_post'])}\n")
    t.append('## تست‌های نام‌دار v2\n')
    for x in S['qa_named']:
        t.append(f"### {x['test_id']} — {x['status']}\n- منابع: {x.get('sources', '')}\n- جمعیت ورودی: {x.get('population', '')}\n- روش: {x['description']}\n- مورد انتظار: {x['expected']}\n- واقعی: {x['actual']}\n- جزئیات استثنا: {x['detail']}\n- بازتولید: `{x.get('command', '')}`\n")
    t.append('## سایر تست‌ها (وضعیت غیر PASS)\n')
    t.append(md(['ID', 'حوزه', 'شرح', 'واقعی', 'وضعیت', 'جزئیات'], [(x['test_id'], x['area'], x['description'][:90], x['actual'][:80], x['status'], x['detail'][:120]) for x in QA['tests'] if not x['test_id'].startswith('QA_') and x['status'] != 'PASS'])); t.append('')
    t.append('## بازتولید\n```\ncd municipality_demo/scripts/taxi_terminals_1404_1405\nset TT_VARIANT=v2\ncopy ..\\..\\data\\work\\taxi_terminals\\tt.sqlite ..\\..\\data\\work\\taxi_terminals\\tt_v2.sqlite   (یا اجرای مجدد 01..03,06)\npython 04_classify_events.py\npython 05_classify_cost_centers.py\npython 07_kpi_comparison.py\npython 09_qa.py\npython 13_kpi_independent.py\npython 14_v2_audit.py\npython 15_kpi_qa_v2.py\npython 08_build_outputs.py\npython 16_reports_v2.py docs\npython 11_postbuild_qa.py\npython 16_reports_v2.py qa\n```\nآزمون‌ها: `python -m pytest tests/test_taxi_terminals_mapping.py`.\n')
    write('financial_mapping_QA_v2.md', '\n'.join(t))
    manifest(True)
    print('qa report written')
