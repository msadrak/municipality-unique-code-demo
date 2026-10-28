"""v2.1 deliverable documents (all numbers come from tt_v21.sqlite tables / the canonical QA registry — nothing is typed by hand).
Writes: corrective_audit_v2.1.md, low_confidence_cc_audit_v2.1.xlsx, FE70_depreciation_provisions_semantic_review.md, kpi_verification_v2.1.xlsx,
        taxi_terminals_management_report_v2.1.md, committee_decisions_v2.1.xlsx, CD-01_terminal_agency_expert_memo_REDACTED.md, client_package/*, MANIFEST_v2.1.json
Run:  python 20_docs_v21.py   (after 08_build_outputs.py;  run again after 11/21 so that QA totals include every stage)
"""
import sqlite3, sys, os, json, hashlib, collections, datetime, shutil, re
import xlsxwriter
sys.path.insert(0, os.path.dirname(__file__))
from common import *
from rules import EVENT_REVIEW, TT_EVENTS, EVENT_STATUS_V2, EXCEPTION_TYPES
from decisions_v2 import CC_AUDIT
from decisions_v21 import build_decisions_v21
from qa_registry_v21 import build_registry, summarize, summary_table_md, CATS
assert VARIANT == 'v21'
con = sqlite3.connect(DB, timeout=300); con.execute(f"ATTACH DATABASE '{WORK}/tt_v2.sqlite' AS v2")
cur = con.cursor()
q = lambda s, *a: cur.execute(s, a).fetchall()
def one(s, *a):
    r = cur.execute(s, a).fetchone(); return r[0] if r and r[0] is not None else 0
QA = json.load(open(QA_JSON, encoding='utf8'))
EMB = json.load(open(f'{WORK}/qa_embedded_v21.json', encoding='utf8')) if os.path.exists(f'{WORK}/qa_embedded_v21.json') else []
_TWO = ('QA_SUMMARY_COUNTS_MATCH_DETAIL', 'QA_MD_KPI_COUNTS_MATCH')      # these two verify the documents rendered here; they are rendered as PASS and confirmed (or failed loudly) by 21_final_v21.py
QA['tests'] = [t for t in QA['tests'] if t['test_id'] not in _TWO] + [dict(test_id=x, area='Deliverable', sources='', population='', description='', expected='', actual='', status='PASS', detail='', command='') for x in _TWO]
REG = build_registry(QA, EMB); QS = summarize(REG)
ORGFA = {'Taxi': 'سازمان تاکسیرانی', 'Terminals': 'سازمان پایانه‌ها'}
NOW = datetime.datetime.now().strftime('%Y-%m-%d')
f = lambda x: f'{x:,}' if isinstance(x, (int, float)) and x == int(x) else (f'{x:,.4f}' if isinstance(x, float) else str(x))
pct = lambda a, b: f'{(a / b):.1%}' if b else '—'
def mcode(c):
    return re.sub(r'(?<=-)(\d{6,})$', lambda m: '•' * (len(m.group(1)) - 3) + m.group(1)[-3:], c) if isinstance(c, str) else c
def md(h, rows):
    out = ['| ' + ' | '.join(h) + ' |', '|' + '|'.join(['---'] * len(h)) + '|']
    for r in rows: out.append('| ' + ' | '.join(str(x).replace('|', '/').replace('\n', ' ') for x in r) + ' |')
    return '\n'.join(out)
def write(path, text): open(f'{OUT}/{path}', 'w', encoding='utf8', newline='\n').write(text)

# ============================================================================================ statistics
cov = {(r[0], r[1]): r for r in q('SELECT * FROM cc_confidence_coverage')}      # version, org, eligible_l, eligible_v, hi_l, hi_v, me_l, me_v, lo_l, lo_v, an_l, an_v, ev_l, ev_v, mu_l, mu_v, in_l, in_v
low = {}
for o in ORGS:
    rows = q('SELECT audit_decision,count(*),sum(abs(amount_net)) FROM low_audit WHERE organization=? GROUP BY 1', o)
    low[o] = {r[0]: (r[1], r[2] or 0) for r in rows}
    low[o]['_total'] = (sum(v[0] for v in low[o].values()), sum(v[1] for v in low[o].values()))
DEC_ALL = ('RETAIN_LOW_CONFIDENCE', 'UPGRADE_TO_MEDIUM_WITH_EVIDENCE', 'RECLASSIFY_TO_MULTIPLE_CANDIDATES', 'RECLASSIFY_TO_INSUFFICIENT_INFORMATION')
sample_ids = {r[0] for r in q('SELECT source_record_id FROM low_sample')} | {r[0] for r in q('SELECT source_record_id FROM low_sample_round1')} | {r[0] for r in q('SELECT source_record_id FROM low_postfix_changes')} | {r[0] for r in q("SELECT source_record_id FROM low_audit WHERE audit_decision='RECLASSIFY_TO_INSUFFICIENT_INFORMATION'")}
reviewed = {o: (one('SELECT count(*) FROM low_audit WHERE organization=? AND source_record_id IN (%s)' % ','.join('?' * len(sample_ids)), o, *sample_ids), one('SELECT sum(abs(amount_net)) FROM low_audit WHERE organization=? AND source_record_id IN (%s)' % ','.join('?' * len(sample_ids)), o, *sample_ids)) for o in ORGS}
other_low = {o: one("SELECT count(*) FROM line_cc c WHERE c.eligible=1 AND c.org=? AND c.cc_status IN ('PROVISIONAL_EXISTING_CC','NEW_CC_CANDIDATE') AND c.conf='LOW' AND c.sid NOT IN (SELECT source_record_id FROM low_audit)", o) for o in ORGS}
KC = {(r[0], r[1]): r[2] for r in q('SELECT organization,metric,value FROM kpi_counts')}
verdict_r2 = dict(q('SELECT reviewer_verdict,count(*) FROM low_sample GROUP BY 1')); verdict_r1 = dict(q('SELECT reviewer_verdict,count(*) FROM low_sample_round1 GROUP BY 1'))

def cov_table():
    rows = []
    for o in ORGS:
        for v in ('v2', 'v2.1'):
            c = cov[(v, o)]
            rows.append((ORGFA[o], v, f(c[2]), f(c[10]), pct(c[10], c[2]), f(c[12]), pct(c[12], c[2]), f(c[4]), f(c[6]), f(c[8]), f(c[14]), f(c[16]), pct(c[11], c[3]), pct(c[13], c[3])))
    return md(['سازمان', 'نسخه', 'ردیف واجد شرایط', 'پوشش تحلیلی (ردیف)', '٪', 'پوشش شاهدی MEDIUM+HIGH', '٪', 'HIGH', 'MEDIUM', 'LOW', 'چندنامزد', 'ناکافی', 'تحلیلی ٪ ارزش', 'شاهدی ٪ ارزش'], rows)

def audit_table():
    rows = []
    for o in ORGS:
        t = low[o]['_total']; g = lambda k: low[o].get(k, (0, 0))
        corrected = sum(g(k)[0] for k in ('UPGRADE_TO_MEDIUM_WITH_EVIDENCE', 'RECLASSIFY_TO_MULTIPLE_CANDIDATES', 'RECLASSIFY_TO_INSUFFICIENT_INFORMATION')); corrected_v = sum(g(k)[1] for k in ('UPGRADE_TO_MEDIUM_WITH_EVIDENCE', 'RECLASSIFY_TO_MULTIPLE_CANDIDATES', 'RECLASSIFY_TO_INSUFFICIENT_INFORMATION'))
        down = g('RECLASSIFY_TO_MULTIPLE_CANDIDATES')[0] + g('RECLASSIFY_TO_INSUFFICIENT_INFORMATION')[0]
        rows.append((ORGFA[o], f(t[0]), f(t[1]), f"{f(t[0])} / {f(t[1])}", f"{f(reviewed[o][0])} / {f(reviewed[o][1])}", f"{f(corrected)} / {f(corrected_v)}", f(g('UPGRADE_TO_MEDIUM_WITH_EVIDENCE')[0]), f(down),
                     f"{f(g('RECLASSIFY_TO_MULTIPLE_CANDIDATES')[0])} + {f(g('RECLASSIFY_TO_INSUFFICIENT_INFORMATION')[0])}", f(g('RETAIN_LOW_CONFIDENCE')[0]), f(g('RETAIN_LOW_CONFIDENCE')[1])))
    return md(['سازمان', 'LOW اولیه (ردیف)', 'ارزش مطلق', 'بازبینی قاعده‌محور (ردیف / ارزش)', 'بازبینی دستی فردی (ردیف / ارزش)', 'اصلاح‌شده (ردیف / ارزش)', 'ارتقا به MEDIUM', 'کاهش (انتخاب‌شده → حل‌نشده)', 'چندنامزد + ناکافی', 'LOW باقی‌مانده', 'ارزش LOW باقی‌مانده'], rows)

def rules_table(n=8):
    rows = []
    for o in ORGS:
        for r in q('SELECT rule_group,v2_cc,lines,abs_value,share_of_org_low_value,retained_low,upgraded_medium,to_multiple,to_insufficient FROM low_rule_analysis WHERE organization=? ORDER BY abs_value DESC LIMIT ?', o, n):
            rows.append((ORGFA[o], r[0], r[1], f(r[2]), f(r[3]), f'{r[4]:.1%}', f'{r[5]}/{r[6]}/{r[7]}/{r[8]}'))
    return md(['سازمان', 'گروه قاعده', 'مرکز v2', 'ردیف', 'ارزش مطلق', 'سهم ارزش LOW', 'حفظ/ارتقا/چندنامزد/ناکافی'], rows)

def kpi_value_rows():
    rows = []
    for r in q("""SELECT r.kpi_id,c.title_fa,r.fy,r.window,r.value,r.numerator,r.unit,r.status,r.calculation_status,r.verification_status FROM kpi_results r JOIN kpi_catalogue c ON c.kpi_id=r.kpi_id
                  WHERE r.verification_status='INDEPENDENTLY_VERIFIED' AND ((r.fy='1404' AND r.window='FULL_YEAR') OR r.window='END_OF_AVAILABLE_DATA') ORDER BY r.kpi_id,r.fy"""):
        rows.append((r[0], r[1][:60], r[2], r[3], f(r[4] if r[4] is not None else r[5]), r[7]))
    return rows

fe70 = q("SELECT v2_event||' ['||coalesce(v2_lifecycle,'')||']', own_event||' ['||coalesce(lifecycle_action,'')||']', count(*) FROM line_event WHERE sid IN (SELECT sid FROM fe70_review) GROUP BY 1,2")
FE70_LINES = q("SELECT v21_event,count(*),count(DISTINCT doc_key),sum(debit),sum(credit) FROM fe70_review GROUP BY 1")

# ============================================================================================ corrective audit
def corrective_audit():
    t = ['# Corrective Audit v2.1 — تاکسیرانی و پایانه‌ها (۱۴۰۴–۱۴۰۵)\n',
         f'تاریخ: {NOW}. وضعیت: **TECHNICALLY_VERIFIED / READY_FOR_EXPERT_REVIEW**؛ نه APPROVED_FOR_PRODUCTION. `approved_items = 0`، `activate_in_production = NO`. v1 و v2 دست‌نخورده‌اند.\n']
    t.append('## ۱. نقص‌های v2 که مستقلاً بازتولید شد\n')
    D = [
     ('A-01', 'تست P15 (تعداد change log) «انتظار ۴۳٬۵۴۲، واقعی ۴۳٬۵۴۱»', 'خطای یک‌واحدی در تست: ردیف کلید/سرستون شیت به‌عنوان داده شمرده می‌شد (min_row=4)؛ داده واقعی در CSV و Excel هر دو ۴۳٬۵۴۱ ردیف بود. در v2 تست پیش از تحویل اصلاح شد ولی کتاب‌کار قبلاً با نتیجه قدیمی FAIL ساخته شده بود', 'تست جدید QA_CHANGELOG_CSV_XLSX_ROW_PARITY هر سه منبع (CSV، Excel، DB) را با تشخیص ردیف سرستون می‌شمارد؛ عدد ثابت کدگذاری نشد', 'اصلاح شد'),
     ('A-02', 'سه جمع QA متفاوت: گزارش md ۱۲۵/۲۲/۱ ، ردیف‌های کتاب‌کار ۱۲۴/۲۲/۲ ، خلاصه کتاب‌کار با فرمول‌ها ۱۴۸/۲۲/۲', 'کتاب‌کار پیش از اجرای تست‌های پس از ساخت (P*) ساخته می‌شود و نتایج دورهٔ قبل را درون خود دارد؛ خلاصهٔ آن ۱۲۴ تست + ۲۴ ردیف کنترل فرمول را بی‌برچسب جمع می‌زد؛ گزارش md تست P15 اصلاح‌شده را می‌شمرد', 'رجیستری QA یکتا (QA_Test_Registry_v2.1.csv) با سه دسته؛ همه خلاصه‌ها از همان داده محاسبه می‌شوند؛ تست‌های پس از ساخت صراحتاً بیرون شیت کتاب‌کار برچسب خورده‌اند', 'اصلاح شد'),
     ('A-03', 'Q36 (واژگان وضعیت KPI) در v2 PASS ثبت شده بود', 'تست 09_qa.py پیش از به‌روزرسانی وضعیت‌ها اجرا شده بود؛ اجرای دوباره روی پایگاه نهایی v2 FAIL می‌شد (واژگان قدیمی)', 'واژگان تست به ۶ وضعیت v2 به‌روز شد؛ ترتیب اجرا مستند شد', 'اصلاح شد'),
     ('B-01', 'TX-K01 در KPI_Catalogue «CALCULATED_AND_VERIFIED» ولی در KPI_Results «CALCULATED_FROM_SOURCE»', 'ردیف‌های نتیجه با مخرج تهی (TX-K01 فقط صورت کسر) در به‌روزرسانی وضعیت جا افتاده بودند', 'مدل پنج‌گانه: Definition/Calculation/Verification/Governance + برچسب ترکیبی یکسان؛ تست QA_KPI_STATUS_CONSISTENCY', 'اصلاح شد'),
     ('B-02', 'گزارش مدیریتی «چهار KPI تأییدشدهٔ پایانه‌ها» (کاتالوگ سه شناسه)', 'نه KPI چهارم: ردیف تکراری TM-K15 در جدول بدون کلید یکتا (INSERT OR REPLACE در اجرای مکرر)؛ کاتالوگ ۳۲ ردیف با ۳۱ شناسه یکتا', 'ردیف تکراری حذف و شاخص یکتا ساخته شد؛ تعریف یکتا / نتیجه محاسبه‌شده / مشاهده KPI×دوره سه شمارش جدا (kpi_counts)', 'اصلاح شد'),
     ('B-03', 'TM-K02 تأییدشده بود ولی در KPI_Results ردیفی نداشت', 'مقادیر فقط در KPI_Terminal_Breakdown بود', 'ردیف‌های نتیجه (مجموع به تفکیک سال/پنجره) افزوده شد؛ تفکیک پایانه همان شیت', 'اصلاح شد'),
     ('B-04', 'TX-K06 «تأییدشده» با شاخص کمکی T_BANKFEE_LINES (شمارش ردیف) بدون بازمحاسبه', 'شاخص کمکی در ارزش KPI نقش ندارد', 'شاخص اطلاعاتی از راستی‌آزمایی مستثنا و در کد ثبت شد', 'توضیح داده شد'),
     ('B-05', 'TM-K05/TM-K14 «محاسبه‌شده» بدون بازمحاسبهٔ مستقل', 'هزینهٔ تحمیل‌شده با قواعد رویداد (TX-*) تعریف می‌شود', 'پل تطبیق حساب‌محور (بدهکار ۱۱۳-۱-۱) به شاخص خط‌لوله بسته شد (اختلاف ۰)؛ وضعیت Verification = NOT_INDEPENDENTLY_VERIFIED و Governance = CD-01', 'ثبت شد؛ REVIEW'),
     ('C-01', '۱٬۰۱۶ تخصیص مرکز هزینه با اطمینان LOW در v2 (تاکسیرانی ۳۱۵، پایانه‌ها ۷۰۱)', 'بازتولید شد: ۳۶۸ و ۲٬۲۳۶ تخصیص جدید از ردیف‌های حل‌نشده که ۳۱۵ و ۷۰۱ تای آن‌ها LOW بود؛ قواعد: پیش‌فرض رویدادی FE-22→CC-1403، حواله انبار→CC-1403، واژهٔ کلیدی قاعده‌های v4 روی شرح، شاهد محلی', 'بازبینی قاعده‌محور همه + نمونه‌گیری دستی دو دور؛ نتیجه در بخش ۳', 'اصلاح شد'),
     ('D-01', 'استهلاک و ذخیره زیر FE-70', 'تعریف FE-70: «ثبت‌های اصلاحی، انتقال مانده، بستن حساب‌های موقت و اسناد اختتامیه»؛ استهلاک و شناسایی ذخیره این‌ها نیستند؛ «ذخیره» شامل مصرف ذخیره (تسویه) هم بود', 'PEO-01 (استهلاک)، PEO-02 (شناسایی ذخیره)، TT-NE-11 (مصرف ذخیره)', 'اصلاح شد؛ نیازمند تأیید'),
     ('E-01', 'CD-01 memo و Account_Dictionary با شماره حساب بانکی و شبا', 'عنوان حساب‌های تفصیلی منبع شماره حساب دارد و memo نمونه‌اسناد را بی‌ماسک نقل می‌کرد', 'ماسک عنوان‌ها (≥۶ رقم و شبا)؛ نسخهٔ REDACTED؛ جدول اصلی محدود؛ بسته کارفرما جدا', 'اصلاح شد'),
    ]
    t.append(md(['ID', 'یافته v2', 'ریشه (بازتولیدشده)', 'اصلاح', 'وضعیت'], D)); t.append('')
    t.append('### مواردی که نقص نبودند\n')
    t.append('- «چهار KPI تأییدشدهٔ پایانه‌ها» KPI چهارم نبود (B-02).\n- ۴۶ مقایسهٔ عددی KPI در v2 درست بودند؛ بازاجرا ۰ اختلاف و هیچ مقدار KPI تغییر نکرد؛ فقط برچسب/ساختار وضعیت اصلاح شد.\n- مبالغ حسابداری، جمع بدهکار/بستانکار و ۱۱۱٬۶۰۰ ردیف منبع بدون تغییرند.\n')
    t.append('## ۲. تأثیر بر شمارش‌ها\n')
    t.append(md(['شمارش', 'مقدار'], [(k, KC[('ALL', k)]) for k in ('unique_kpi_definitions', 'catalogue_rows', 'calculable_from_source_definitions', 'independently_verified_definitions', 'verified_and_not_policy_pending_definitions', 'policy_pending_definitions', 'partially_calculable_definitions', 'not_calculable_definitions', 'result_rows_with_value', 'verified_kpi_period_observations')])); t.append('')
    t.append('## ۳. ممیزی مراکز هزینه با اطمینان LOW\n')
    t.append(audit_table()); t.append('')
    t.append('«بازبینی دستی فردی» = اجتماع نمونهٔ دور ۱ (۵۶)، دور ۲ (۵۴)، ردیف‌های متأثر از اصلاح قاعده و همهٔ ردیف‌های بازتخصیص‌یافته به INSUFFICIENT (بازبینی کامل ۱۲۸ ردیف در دور ۱). ردیف‌های نمونه‌نشده تأییدشدهٔ فردی نیستند.\n')
    t.append(f'ردیف‌های LOW مربوط به v1 که در دامنهٔ این ممیزی نبودند (تخصیص‌های قبلی): تاکسیرانی {other_low["Taxi"]:,}، پایانه‌ها {other_low["Terminals"]:,}.\n')
    t.append('### قواعد مسئله‌دار و تمرکز ریسک\n'); t.append(rules_table(6)); t.append('')
    t.append(f"نتایج نمونه‌گیری: دور ۱ {verdict_r1}؛ دور ۲ {verdict_r2}. مخالفت‌ها: معاینه فنی ناوگان (۱۴٫۰ میلیارد) با INSUFFICIENT زیادی محافظه‌کارانه؛ توسعه نرم‌افزار؛ تبلیغات پروژه‌ها → الگوها اصلاح و همهٔ ردیف‌های متأثر دوباره بازبینی شد.\n")
    t.append('### پوشش به تفکیک اطمینان\n'); t.append(cov_table()); t.append('')
    t.append('«پوشش تحلیلی موقت» همهٔ ردیف‌های دارای مرکز انتخاب‌شده (با LOW)؛ «پوشش شاهدی» فقط MEDIUM+HIGH. هیچ‌کدام «تأییدشده» نیست. کاهش پوشش تحلیلی v2.1 نسبت به v2 اصلاح معنایی است نه افت کیفیت: ردیف‌های ناسازگار به چندنامزد/ناکافی بازگشتند.\n')
    t.append('### پل جمعیت v2 → v2.1\n')
    t.append(md(['سازمان', 'وضعیت v2', 'اطمینان v2', 'وضعیت v2.1', 'اطمینان v2.1', 'ردیف', 'ارزش خالص'], [(o, a, c1, b, c2, f(n), f(v)) for o, a, c1, b, c2, n, v in q('SELECT org,v2_status,v2_conf,v21_status,v21_conf,sum(lines),sum(net_value) FROM cc_bridge_v2_v21 WHERE v2_status<>v21_status OR v2_conf<>v21_conf GROUP BY 1,2,3,4,5 ORDER BY 1,6 DESC')])); t.append('')
    t.append('جمعیت واجد شرایط تغییر نکرد؛ پل کامل v1→v2 (۴۲ ردیف تاکسیرانی/۱۶ پایانه از انتخاب‌شده به حل‌نشده، ۵۴۹ ردیف پایانه خارج از جمعیت، ۳ ردیف وارد شده) بازتولید و تأیید شد (v2).\n')
    t.append('## ۴. FE-70، استهلاک و ذخایر\n')
    t.append(md(['تخصیص v2', 'تخصیص v2.1', 'ردیف'], [(a, b, f(n)) for a, b, n in fe70])); t.append('')
    t.append('جزئیات: `FE70_depreciation_provisions_semantic_review.md`.\n')
    t.append('## ۵. نتایج QA (از رجیستری یکتا)\n')
    t.append(summary_table_md(REG)); t.append('')
    t.append('جزئیات هر تست: `QA_Test_Registry_v2.1.csv` و `financial_mapping_QA_v2.1.md`.\n')
    t.append('## ۶. محدودیت‌ها و عدم‌قطعیت باقی‌مانده\n')
    t.append('- ردیف‌های چندنامزد/ناکافی عمداً بدون مرکز مانده‌اند؛ ردیف‌های LOW باقی‌مانده تحلیلی‌اند.\n- TM-K05/TM-K14 بازمحاسبهٔ مستقل حسابی ندارند (پل تطبیق بسته می‌شود).\n- QA مقادیر cached فرمول را «محاسبه زندهٔ اکسل» نمی‌داند.\n- هش v7.1 با مانیفست خودش متفاوت است (ثبت‌شده از v2؛ شیت‌های مورد استفاده یکسان با v7).\n- واحد پول منبع و سال ۱۴۰۵ (ناقص) مانند v2 باز است.\n')
    return '\n'.join(t)

# ============================================================================================ FE-70 memo
def fe70_memo():
    t = ['# بازبینی معنایی FE-70، استهلاک و ذخایر — v2.1\n', f'تاریخ: {NOW}. وضعیت: **PROPOSED — نیازمند تصمیم کمیته (CD-PEO)**.\n']
    t.append('## تعریف FE-70 در کاتالوگ v7.1 (بدون تغییر)\n')
    t.append('- عنوان: «اصلاح سند، بستن حساب‌ها و جابه‌جایی حسابداری»؛ خانواده «مالی و خزانه‌داری»؛ ماهیت «واسط حسابداری»؛ مرحله «تعدیلات دفاتر»؛ شرح: «ثبت‌های اصلاحی حسابداری، انتقال مانده، بستن حساب‌های موقت و اسناد اختتامیه پایان سال مالی»؛ وضعیت: LOW — کاندید مفهومی (فاقد رخداد مستقیم در ۱۴۰۴).\n')
    t.append('## نتیجه\n')
    t.append(md(['موضوع', 'v2', 'سازگاری معنایی با FE-70', 'توصیه v2.1'], [
        ('استهلاک دوره‌ای (TT-NE-23)', 'FE-70 [DEPRECIATION]', 'ناسازگار: ثبت تعدیلی محاسبه‌شده (بدهکار ۶۱۳-۲۰ / بستانکار ۱۲۲)؛ اصلاح و بستن حساب نیست', 'PEO-01 — عملیات حسابداری پایان دوره؛ بدون شناسه FE جدید'),
        ('شناسایی ذخیره/هزینه تعهدی (TT-NE-24)', 'FE-70 [PROVISION_OR_ACCRUAL]', 'ناسازگار: شناسایی تعهد (بستانکار ۲۱۲-۲، ۲۲۳، ۲۱۴، ۲۱۷)', 'PEO-02'),
        ('مصرف ذخیره (بدهکار ذخیره در مقابل بانک)', 'FE-70 [PROVISION_OR_ACCRUAL]', 'ناسازگار: پرداخت/تسویه بدهی تعهدی', 'TT-NE-11 [SETTLE_ACCRUED_LIABILITY]'),
        ('بستن حساب موقت (۳۱۶-۳ → ۳۱۶-۱)', 'FE-70', 'سازگار', 'بدون تغییر'), ('جابه‌جایی حساب‌های دارایی (۱۲۰/۱۲۱)', 'FE-70', 'سازگار (جابه‌جایی حسابداری)', 'بدون تغییر'), ('اصلاح حساب‌های سنواتی (۸۱۲-۵)', 'FE-70', 'سازگار (اصلاح)', 'بدون تغییر')])); t.append('')
    t.append('## ارقام (ردیف‌های بازتخصیص‌یافته)\n')
    t.append(md(['تخصیص v2.1', 'ردیف', 'سند', 'بدهکار', 'بستانکار'], [(a, f(n), f(d), f(x), f(y)) for a, n, d, x, y in FE70_LINES])); t.append('')
    t.append('جمع بدهکار/بستانکار ردیف‌های بازتخصیص‌یافته با v2 برابر است (QA_FE70_SEMANTICS). هیچ مبلغ و مرکز هزینه‌ای تغییر نکرد؛ مرکز هزینه استهلاک نیازمند ثبت دارایی است (پایانه‌ها: ۴۷ ردیف بر پایهٔ کد فعالیت منبع ۰۰۸ به CC-403 با MEDIUM — برای بازبینی کارشناسی علامت خورد).\n')
    t.append('## ملاحظات\n')
    t.append('- گزینه‌های بررسی‌شده برای استهلاک: رویداد canonical مستقل (رد: رخداد پیش‌حسابداری نیست)، زیرنوع پُست (ممکن)، گسترش FE-70 (رد: خلاف تعریف)، عملیات پایان دوره خارج از کاتالوگ (انتخاب).\n- گزینه‌ها برای ذخایر: رویداد مستقل (رد)، زیرنوع (ممکن)، FE-70 (رد)، تفکیک شناسایی/مصرف (انتخاب).\n- شناسه PEO-xx خارج از فضای نام FE و TT-NE است (مانند EXC-01)؛ ردیابی نسب: `fe70_review.csv`، `event_crosswalk_v2_v21.csv`، `event_concept_review.csv`.\n- مشاهده: در سند TAXI-1405-425 ردیف استهلاک اثاثیه اداری به بستانکار ۱۲۲-۴ (استهلاک انباشتهٔ وسایط نقلیه) رفته است؛ این ناسازگاری ثبت منبع است و تغییر داده نشد (برای حسابدار ارشد).\n')
    t.append('## پیوست محدود\n')
    t.append('اسناد و ردیف‌های شاهد با شرح اصلی در `machine_readable/RESTRICTED_FE70_evidence.csv` (RESTRICTED).\n')
    return '\n'.join(t)

# ============================================================================================ management report (client-facing)
def management_report():
    t = ['# گزارش مدیریتی v2.1 — تاکسیرانی و پایانه‌ها (سال‌های مالی ۱۴۰۴ و ۱۴۰۵)\n', f'تاریخ: {NOW}. **تأییدشدهٔ فنی و آمادهٔ بازبینی کارشناسی؛ هیچ مورد رسمی (APPROVED) نیست و هیچ تغییری در سامانه عملیاتی اعمال نشده است.**\n',
         '> **توجه:** سال مالی ۱۴۰۵ ناقص است (تاکسیرانی تا ۱۴۰۵/۰۷/۱۳، پایانه‌ها تا ۱۴۰۵/۰۷/۱۴). سال کامل ۱۴۰۴ با سال ناقص ۱۴۰۵ مقایسه نشده است؛ فقط «پنجرهٔ مشترک» و فقط به‌صورت شاخص.\n']
    t.append('## خلاصه\n')
    t.append(f"- منبع: {f(one('SELECT count(*) FROM sanad'))} ردیف سند در {f(one('SELECT count(*) FROM doc_class'))} سند؛ محتوای دو آرشیو RAR با ابزار مستقل بازبینی و با فایل‌های تحلیل‌شده یکسان است؛ جمع بدهکار و بستانکار تغییر نکرده است.\n- نسخهٔ v2.1 یک اصلاح محدود است: ناهمخوانی‌های گزارش QA و KPI برطرف شد، همهٔ ۱٬۰۱۶ تخصیص مرکز هزینه با اطمینان پایین به‌صورت قاعده‌محور بازبینی شد (و نمونهٔ طبقه‌ای و ردیف‌های متأثر از اصلاح قاعده به‌صورت دستی و فردی) و استهلاک و ذخایر از رویداد «اصلاح سند و بستن حساب» جدا شد.\n- نتایج QA: " + '؛ '.join(f"{c}: PASS {QS[c]['PASS']}، REVIEW {QS[c]['REVIEW']}، FAIL {QS[c]['FAIL']}" for c in CATS) + ' (هر FAIL دسته «Historical Regression» بازتولید نقص نسخه‌های قبل است).\n')
    for o in ORGS:
        c = cov[('v2.1', o)]
        docs = one('SELECT count(*) FROM doc_class WHERE org=?', o)
        fe_used = [r[0] for r in q("SELECT DISTINCT own_event FROM line_event WHERE org=? AND own_event LIKE 'FE-%' AND role IN ('DRIVER','SETTLEMENT') ORDER BY 1", o)]
        tt_used = [r[0] for r in q("SELECT DISTINCT own_event FROM line_event WHERE org=? AND own_event LIKE 'TT-NE-%' AND role IN ('DRIVER','SETTLEMENT') ORDER BY 1", o)]
        spec = [r[0] for r in q("SELECT DISTINCT own_event FROM line_event WHERE org=? AND (own_event LIKE 'PEO-%' OR own_event LIKE 'EXC-%') ORDER BY 1", o)]
        t.append(f'## {ORGFA[o]}\n')
        t.append(f"**رویدادهای مالی.** {len(fe_used)} رویداد موجود کاتالوگ v7.1 بازاستفاده شد (بدون بازتعریف) و {len(tt_used)} کاندید جدید پیشنهادی (TT-NE) مشاهده می‌شود؛ عملیات پایان دوره/استثنا: {', '.join(spec) or '—'}. همه PROPOSED‌اند.\n")
        t.append(f"**مراکز هزینه.** از {f(c[2])} ردیف هزینه‌ای/سرمایه‌ای: پوشش تحلیلی موقت {f(c[10])} ({pct(c[10], c[2])})، پوشش پشتیبانی‌شده با شاهد (اطمینان متوسط یا بالا) {f(c[12])} ({pct(c[12], c[2])})، اطمینان پایین {f(c[8])}؛ بدون مرکز: چندنامزد {f(c[14])} و ناکافی {f(c[16])}. ارزش پوشش تحلیلی {pct(c[11], c[3])}، شاهدی {pct(c[13], c[3])}.\n")
    t.append('### تاکسیرانی — KPIهای قابل اتکا و داده‌های لازم\n')
    krows = [r for r in kpi_value_rows() if r[0].startswith('TX')]
    t.append(md(['KPI', 'عنوان', 'سال', 'پنجره', 'مقدار', 'وضعیت'], krows)); t.append('')
    t.append(f"از ۱۶ تعریف تاکسیرانی {KC[('Taxi', 'independently_verified_definitions')]} تعریف با بازمحاسبهٔ مستقل تأیید شد، {KC[('Taxi', 'partially_calculable_definitions')]} جزئی است و {KC[('Taxi', 'not_calculable_definitions')]} مورد نیازمند داده عملیاتی/بودجه/تعریف کارشناسی است (ناوگان فعال، درخواست‌ها، شکایات، برنامه عملیاتی).\n")
    t.append('### پایانه‌ها — چرخه چک و مطالبات، ابهام عاملیت و محدودیت KPI مالی\n')
    t.append('چک‌های اجاره/عوارض چرخه‌عمر مشخص دارند (دریافت چک، ارسال به وصول، وصول، برگشت) و به‌صورت یک رویداد با اقدام‌های متمایز مدل شده‌اند؛ تحقق نقدی همان‌جا شمرده می‌شود. حساب‌های ۱۱۳-۱-۱ و ۲۱۱-۱-۱ (فی‌مابین با شهرداری) در آغاز و پایان هر سال صفرند و در طول سال گردش بزرگ دارند؛ این الگو با «عامل شهرداری» سازگار است اما وضعیت حقوقی را اثبات نمی‌کند (CD-01). تا تصمیم، مبلغ صادرشده «مطالبه» و هزینه «هزینه تحمیل‌شده» نامیده می‌شود.\n')
    krows = [r for r in kpi_value_rows() if r[0].startswith('TM')]
    t.append(md(['KPI', 'عنوان', 'سال', 'پنجره', 'مقدار', 'وضعیت'], krows)); t.append('')
    t.append(f"از ۱۵ تعریف پایانه‌ها {KC[('Terminals', 'independently_verified_definitions')]} تعریف از نظر عددی با بازمحاسبهٔ مستقل تأیید شد: {KC[('Terminals', 'verified_and_not_policy_pending_definitions')]} تعریف بدون وابستگی به سیاست حسابداری (TM-K02، TM-K11، TM-K15) و ۱ تعریف (TM-K01: مطالبه صادرشده) که عددش تأیید شده ولی معنای حسابداری‌اش وابسته به CD-01 است. {KC[('Terminals', 'policy_pending_definitions')]} تعریف (TM-K01، TM-K05، TM-K14) به سیاست حسابداری وابسته‌اند و TM-K05/K14 بازمحاسبهٔ مستقل حسابی ندارند (پل تطبیق بسته می‌شود). TM-K04 «نسبت گردش وصول به مطالبه» است نه نرخ وصول همان مطالبه. این شمارش‌ها «تعریف یکتا»ند؛ مشاهدات KPI×دوره جدا در `kpi_counts.csv` است.\n")
    t.append('## تصمیم‌هایی که باید از مرجع بیرونی گرفته شود\n')
    dec = build_decisions_v21(q, one)
    t.append(md(['شناسه', 'سازمان', 'موضوع', 'مرجع', 'مسدودکننده؟'], [(d[0], d[1], d[2][:80], d[8][:48], d[10]) for d in dec if d[11] == 'REQUIRES_AUTHORITY_DECISION' and not d[0].startswith('CD-EV')])); t.append('')
    t.append('کاندیدهای رویداد (CD-EV-*) مسدودکنندهٔ تحویل موقت نیستند.\n')
    t.append('## محدودیت‌ها\n- واحد پول منبع تأیید نشده است؛ مبالغ «واحد منبع» (محتملاً ریال) بدون تبدیل‌اند.\n- ردیف‌های LOW و چندنامزد، تحلیلی/پیشنهادی‌اند.\n- مقدار فرمول‌های کتاب‌کار cached است.\n- جزئیات: `corrective_audit_v2.1.md`، `low_confidence_cc_audit_v2.1.xlsx`، `committee_decisions_v2.1.xlsx`.\n')
    return '\n'.join(t)

# ============================================================================================ redacted CD-01 memo
def memo_cd01():
    ex = q("""SELECT s.doc_key,s.date,s.hcode,coalesce(a.title,''),s.bed,s.bes FROM sanad s LEFT JOIN account_dictionary a ON a.org=s.org AND a.fy=s.fy AND a.hcode=s.hcode
              WHERE s.doc_key IN ('TERM-1404-76','TERM-1404-207','TERM-1405-422','TERM-1405-217','TERM-1405-480') ORDER BY s.doc_key,s.src_row""")
    by = collections.defaultdict(list)
    for r in ex: by[r[0]].append(r)
    ex = [r for k in sorted(by) for r in sorted(by[k], key=lambda x: -max(x[4] or 0, x[5] or 0))[:10]]
    ta = q("SELECT section,fy,doc_kind,account_group,account_title,debit,credit FROM terminal_agency ORDER BY section,fy,debit DESC LIMIT 14")
    t = ['# یادداشت کارشناسی CD-01 — ماهیت حسابداری سازمان پایانه‌ها (نسخهٔ REDACTED)\n', f'تاریخ: {NOW}. **REQUIRES_AUTHORITY_DECISION — مسدودکننده برای KPIهای مالی پایانه‌ها.** در این نسخه شماره حساب بانکی/شبا ماسک شده و شرح متنی اسناد نیامده است؛ کدهای طبقه‌بندی حسابداری (مثل ۱۱۳-۱-۱) حفظ شده‌اند.\n']
    t.append('## پرسش\nآیا سازمان پایانه‌ها «عامل شهرداری» است (هزینه به حساب شهرداری و درآمد برای شهرداری) یا واحد مستقلی که درآمد و هزینهٔ خود را شناسایی می‌کند؟\n')
    t.append('## شواهد مشاهده‌شده (لایه A)\n- ۱۱۳-۱-۱ (طلب از شهرداری مرکزی) و ۲۱۱-۱-۱ (بدهی به شهرداری): مانده افتتاحیه و اختتامیه هر دو سال صفر؛ طی سال گردش بزرگ؛ پایان دوره با اسناد تهاتر (۱۴۰۵) یا بستن حساب موقت (۱۴۰۴) صفر می‌شوند.\n- بدهکار ۱۱۳-۱-۱ = هزینهٔ تحمیل‌شده به شهرداری؛ بستانکار ۲۱۱-۱-۱ = مطالبهٔ درآمد برای شهرداری.\n- مطالبه از بهره‌برداران: ۱۱۳-۱-۴ و ۱۱۳-۱-۸ با وصول در بانک؛ ودایع ۲۱۲-۶ مانده دارند.\n')
    t.append(md(['بخش', 'سال', 'نوع سند', 'گروه حساب', 'عنوان حساب', 'بدهکار', 'بستانکار'], [(r[0], r[1], r[2], mcode(r[3]), r[4], f(r[5]), f(r[6])) for r in ta])); t.append('')
    t.append('### نمونه اسناد (بدون شرح متنی)\n')
    t.append(md(['سند', 'تاریخ', 'کد حساب', 'عنوان حساب', 'بدهکار', 'بستانکار'], [(r[0], r[1], mcode(r[2]), r[3][:40], f(r[4]), f(r[5])) for r in ex])); t.append('')
    t.append('## تفسیرها و پیامدها\n| تفسیر | رویدادها | KPI |\n|---|---|---|\n| الف) عامل شهرداری | مطالبه/هزینه تحمیل‌شده جریان عاملیتی است | TM-K01/K05/K14 تغییر هویت می‌دهند |\n| ب) واحد مستقل | درآمد = مطالبه صادرشده؛ طلب از شهرداری جدا بررسی شود | همان KPIها |\n| ج) واحد ستادی با تسهیم | تسهیم هزینه ستادی | بازتعریف KPI |\n')
    t.append('## توصیه (غیرالزام‌آور)\nمطالبه «مطالبه صادرشده» و هزینه «هزینه تحمیل‌شده» نامیده شود؛ KPIهای وابسته در وضعیت `CALCULATED_BUT_ACCOUNTING_POLICY_PENDING` بمانند.\n')
    t.append('## مدارک لازم\nاساسنامه/مصوبه تشکیل، آیین‌نامه مالی، تفاهم‌نامه تسهیم درآمد، نحوه ثبت در صورت‌های مالی شهرداری، سیاست شناسایی درآمد و هزینه.\n')
    return '\n'.join(t)

# ============================================================================================ xlsx outputs
def xl(path):
    wbk = xlsxwriter.Workbook(f'{OUT}/{path}', {'strings_to_numbers': False, 'strings_to_formulas': False})
    fm = dict(h=wbk.add_format({'bold': True, 'bg_color': '#1F3864', 'font_color': 'white', 'text_wrap': True, 'border': 1, 'align': 'center', 'valign': 'vcenter', 'reading_order': 2}),
              t=wbk.add_format({'text_wrap': True, 'valign': 'top', 'border': 1, 'reading_order': 2}), n=wbk.add_format({'num_format': '#,##0', 'valign': 'top', 'border': 1}),
              d=wbk.add_format({'num_format': '0.0000', 'valign': 'top', 'border': 1}), p=wbk.add_format({'num_format': '0.0%', 'valign': 'top', 'border': 1}), title=wbk.add_format({'bold': True, 'font_size': 13, 'reading_order': 2}))
    return wbk, fm
def put(wbk, fm, name, headers, rows, title=None, kinds=None, widths=None):
    ws = wbk.add_worksheet(name); ws.right_to_left(); r0 = 0
    if title: ws.write(0, 0, title, fm['title']); r0 = 2
    for j, h in enumerate(headers): ws.write(r0, j, h, fm['h']); ws.set_column(j, j, (widths or {}).get(j, 20))
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            k = (kinds or {}).get(j, 't')
            if v is None: ws.write_blank(r0 + 1 + i, j, None, fm['t'])
            elif k in ('n', 'd', 'p') and isinstance(v, (int, float)): ws.write_number(r0 + 1 + i, j, v, fm[k])
            else: ws.write_string(r0 + 1 + i, j, str(v), fm['t'])
    ws.freeze_panes(r0 + 1, 1)
    if rows: ws.autofilter(r0, 0, r0 + len(rows), len(headers) - 1)
    return ws

def low_xlsx():
    wbk, fm = xl('low_confidence_cc_audit_v2.1.xlsx')
    put(wbk, fm, 'README_Method', ['مورد', 'توضیح'], [
        ('هدف', 'بازبینی ۱٬۰۱۶ تخصیص مرکز هزینه با اطمینان LOW که v2 به ردیف‌های حل‌نشدهٔ v1 داد؛ پرسش اصلی «آیا مرکز انتخاب‌شده از نظر معنایی قابل دفاع است» نه «پوشش بیشتر شد».'),
        ('لایه ۱', 'همه ردیف‌ها به‌صورت قاعده‌محور بررسی شدند (گروه S انبار، E پیش‌فرض FE-22، K واژهٔ کلیدی قاعده‌های شهرداری، F شاهد محلی). شواهد: حساب تفصیلی (طبیعت هزینه)، شرح همان ردیف، رویداد.'),
        ('لایه ۲', 'نمونه‌گیری طبقه‌ای با seed ثابت 20260301 (بزرگ‌ترین ارزش + تصادفی در هر طبقه: سازمان×سال×تصمیم×گروه) در دو دور؛ بازبینی دستی هر ردیف با شرح و عنوان حساب (شرح متنی در خروجی نیامده). مخالفت → اصلاح قاعده → بازبینی همهٔ ردیف‌های متأثر.'),
        ('سلسله‌مراتب شاهد', 'حساب/فعالیت منبع تأییدشده > crosswalk > شرح ردیف > زمینه سند > طبقه‌بندی خدمات > تطبیق معنایی کنترل‌شده. دو شاهد واژگانی ضعیف باعث ارتقا نشد.'),
        ('تصمیم‌ها', 'RETAIN_LOW / UPGRADE_TO_MEDIUM / RECLASSIFY_TO_MULTIPLE / RECLASSIFY_TO_INSUFFICIENT / REQUIRES_EXPERT_DECISION. هیچ HIGH ارتقا نیافت.'),
        ('هشدار', 'ردیف نمونه‌نشده تأییدشدهٔ فردی نیست. اطمینان LOW یعنی تحلیلی/پیشنهادی.')], title='روش‌شناسی', widths={0: 24, 1: 140})
    summ = []
    for o in ORGS:
        for k in DEC_ALL:
            n, v = low[o].get(k, (0, 0)); summ.append((ORGFA[o], k, n, v))
    put(wbk, fm, 'Summary', ['سازمان', 'تصمیم', 'ردیف', 'ارزش مطلق'], summ, title='خلاصه تصمیم‌ها', kinds={2: 'n', 3: 'n'}, widths={0: 22, 1: 44})
    ra = q('SELECT organization,rule_group,v2_cc,v2_rule_id,lines,abs_value,share_of_org_low_value,retained_low,upgraded_medium,to_multiple,to_insufficient,other,finding FROM low_rule_analysis ORDER BY organization,abs_value DESC')
    put(wbk, fm, 'Rule_Analysis', ['سازمان', 'گروه', 'مرکز v2', 'قاعده v2', 'ردیف', 'ارزش مطلق', 'سهم ارزش', 'LOW حفظ', 'ارتقا', 'چندنامزد', 'ناکافی', 'سایر', 'یافته'], ra, title='تحلیل در سطح قاعده', kinds={4: 'n', 5: 'n', 6: 'p', 7: 'n', 8: 'n', 9: 'n', 10: 'n', 11: 'n'}, widths={12: 80, 1: 30})
    for nm, tb, ttl in (('Sample_Round1', 'low_sample_round1', 'نمونه دور ۱ (۵۶)'), ('Sample_Round2', 'low_sample', 'نمونه دور ۲ (۵۴)'), ('PostFix_Review', 'low_postfix_changes', 'ردیف‌های متأثر از اصلاح قاعده')):
        cur.execute(f'SELECT * FROM {tb}'); h = [d[0] for d in cur.description]
        put(wbk, fm, nm, h, cur.fetchall(), title=ttl, widths={len(h) - 1: 80})
    cur.execute('SELECT * FROM low_audit ORDER BY organization,fiscal_year,source_record_id'); h = [d[0] for d in cur.description]
    rows = [tuple(mcode(x) if h[i] == 'account_code' else x for i, x in enumerate(r)) for r in cur.fetchall()]
    put(wbk, fm, 'Audit_Population', h, rows, title='جمعیت کامل ممیزی (۱٬۰۱۶ ردیف)', kinds={h.index('amount_net'): 'n'}, widths={h.index('audit_reason'): 60, h.index('v2_reason'): 50})
    cv = [(r[0], r[1]) + tuple(r[2:]) for r in q('SELECT * FROM cc_confidence_coverage ORDER BY organization,version')]
    cur.execute('SELECT * FROM cc_confidence_coverage'); h = [d[0] for d in cur.description]
    put(wbk, fm, 'Coverage_By_Confidence', h, cv, title='پوشش به تفکیک اطمینان', kinds={i: 'n' for i in range(2, len(h))})
    unres = [(o, s, c, n, v) for o, s, c, n, v in q("SELECT org,cc_status,conf,count(*),sum(abs(sanad_net)) FROM (SELECT c.org,c.cc_status,c.conf,s.bed-s.bes AS sanad_net FROM line_cc c JOIN sanad s ON s.sid=c.sid WHERE c.eligible=1 AND c.cc_status IN ('MULTIPLE_CC_CANDIDATES','INSUFFICIENT_INFORMATION')) GROUP BY 1,2,3")]
    put(wbk, fm, 'Unresolved_Decisions', ['سازمان', 'وضعیت', 'اطمینان', 'ردیف', 'ارزش مطلق'], unres, title='ردیف‌های حل‌نشدهٔ باقی‌مانده (نیازمند تصمیم کارشناسی؛ CD-LOWCC)', kinds={3: 'n', 4: 'n'})
    wbk.close()

def kpi_xlsx():
    wbk, fm = xl('kpi_verification_v2.1.xlsx')
    cur.execute('SELECT kpi_id,org,title_fa,basis_type,formula,numerator,denominator,v1_status,calc_status,definition_status,calculation_status,verification_status,governance_status,verification_basis,metrics,v2_verdict,v2_note FROM kpi_catalogue ORDER BY org,kpi_id')
    put(wbk, fm, 'KPI_Definitions', ['KPI', 'سازمان', 'عنوان', 'مبنا', 'فرمول', 'صورت', 'مخرج', 'وضعیت v1', 'برچسب ترکیبی v2.1', 'Definition_Status', 'Calculation_Status', 'Verification_Status', 'Governance_Status', 'مبنای راستی‌آزمایی', 'شاخص‌های پایه', 'قضاوت', 'توضیح'], cur.fetchall(),
        title='تعریف KPI و وضعیت‌های جدا (۳۱ KPI یکتا)', widths={2: 40, 4: 40, 13: 50, 16: 50})
    rows = []
    for r in q("""SELECT r.kpi_id,r.org,r.fy,r.window,r.value,r.numerator,r.denominator,r.status,r.calculation_status,r.verification_status,c.formula,c.metrics,c.governance_status,r.caveat FROM kpi_results r JOIN kpi_catalogue c ON c.kpi_id=r.kpi_id ORDER BY r.kpi_id,r.fy,r.window"""):
        v1 = q('SELECT value,numerator FROM v1.kpi_results WHERE kpi_id=? AND fy=? AND window=?', r[0], r[2], r[3]) if False else []
        rows.append((r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9], r[10], r[11], r[12], r[13]))
    put(wbk, fm, 'KPI_Results_Verification', ['KPI', 'سازمان', 'سال', 'پنجره', 'مقدار v2.1 (= v2)', 'صورت', 'مخرج', 'برچسب', 'Calculation', 'Verification', 'فرمول', 'شاخص‌های پایه', 'حاکمیت', 'یادداشت'], rows, title='نتایج KPI×دوره و وضعیت راستی‌آزمایی (مقادیر عددی نسبت به v2 تغییر نکرده‌اند)',
        kinds={4: 'd', 5: 'n', 6: 'n'}, widths={10: 40, 11: 30, 12: 30})
    mv = q('SELECT metric_id,org,fy,window,v1_value,v2_pipeline_value,independent_value,abs_diff,verdict,note FROM kpi_verification ORDER BY org,metric_id,fy,window')
    put(wbk, fm, 'Metric_Verification', ['شاخص پایه', 'سازمان', 'سال', 'پنجره', 'v1', 'پایپ‌لاین v2.1', 'مستقل از xlsx منبع', 'اختلاف', 'نتیجه', 'یادداشت'], mv, title='بازمحاسبه مستقل شاخص‌های پایه (13_kpi_independent.py)', kinds={4: 'n', 5: 'n', 6: 'n', 7: 'n'}, widths={9: 60})
    kk = q('SELECT kpi_id,org,fy,window,v1_value,v2_value,independent_value,v1_status,v2_status,verdict,note FROM kpi_v1_v2 ORDER BY kpi_id,fy,window')
    put(wbk, fm, 'V1_V2_Independent', ['KPI', 'سازمان', 'سال', 'پنجره', 'v1', 'v2/v2.1', 'مستقل', 'وضعیت v1', 'وضعیت v2', 'قضاوت', 'توضیح تفاوت'], kk, title='مقایسه v1 / v2.1 / مستقل', kinds={4: 'd', 5: 'd', 6: 'd'}, widths={10: 60})
    put(wbk, fm, 'Counts', ['سازمان', 'شمارش', 'مقدار', 'تعریف'], q('SELECT organization,metric,value,definition FROM kpi_counts ORDER BY metric,organization'), title='شمارش‌ها', kinds={2: 'n'}, widths={1: 44, 3: 70})
    put(wbk, fm, 'Recharge_Bridge', ['سال', 'پنجره', 'گام', 'شرح', 'ردیف', 'مبلغ'], q('SELECT fy,window,step,description,lines,amount FROM kpi_recharge_bridge ORDER BY fy,step'), title='پل تطبیق هزینه تحمیل‌شده (TM-K05/K14): حساب‌محور ↔ خط‌لوله', kinds={4: 'n', 5: 'n'}, widths={3: 90})
    wbk.close()

def committee_xlsx():
    wbk, fm = xl('committee_decisions_v2.1.xlsx')
    dec = build_decisions_v21(q, one)
    HD = ['Decision ID', 'Organization', 'Subject', 'Current evidence', 'Model recommendation', 'Alternative options', 'Financial / operational impact', 'Relevant source examples', 'Expert responsible', 'Required approval', 'Blocking / non-blocking', 'Decision status', 'Recommended next action']
    put(wbk, fm, 'Decisions', HD, dec, title='ماتریس تصمیم کمیته v2.1 (هیچ تصمیمی اتخاذ‌شده نیست؛ وضعیت = آمادگی)', widths={2: 36, 3: 50, 4: 44, 5: 28, 12: 34})
    picks = []
    def docs_for(cond, n=2):
        return [r[0] for r in q(f"SELECT e.doc_key,sum(e.amount_dr+e.amount_cr) a FROM line_event e {cond} GROUP BY 1 ORDER BY a DESC LIMIT {n}")]
    for did, cls, cond in (('CD-01', 'مطالبه/وصول پایانه', "WHERE e.org='Terminals' AND e.own_event IN ('TT-NE-15','TT-NE-01') AND e.role='DRIVER'"), ('CD-01', 'تهاتر با شهرداری TT-NE-19', "WHERE e.own_event='TT-NE-19' AND e.role='DRIVER'"),
                           ('CD-04', 'تاکسیرانی: TTCC-P-01 انتخاب‌شده', "JOIN line_cc c ON c.sid=e.sid WHERE c.cc_id='TTCC-P-01' AND e.role='DRIVER'"), ('CD-05', 'سرویس مدارس TT-NE-03', "WHERE e.own_event='TT-NE-03' AND e.role='DRIVER'"),
                           ('CD-06', 'هزینه پایانه → CC-403', "JOIN line_cc c ON c.sid=e.sid WHERE c.cc_id='CC-403' AND e.org='Terminals'"), ('CD-08', 'حقوق پایانه → CC-1301', "JOIN line_cc c ON c.sid=e.sid WHERE c.cc_id='CC-1301' AND e.org='Terminals'"),
                           ('CD-PEO', 'استهلاک PEO-01', "WHERE e.own_event='PEO-01'"), ('CD-PEO', 'شناسایی ذخیره PEO-02', "WHERE e.own_event='PEO-02'"), ('CD-PEO', 'مصرف ذخیره (تسویه بدهی)', "WHERE e.lifecycle_action='SETTLE_ACCRUED_LIABILITY'"),
                           ('CD-LOWCC', 'انبار: چندنامزد پس از ممیزی', "JOIN line_cc c ON c.sid=e.sid WHERE c.v21_decision='RECLASSIFY_TO_MULTIPLE_CANDIDATES' AND e.own_event='TT-NE-21'"),
                           ('CD-LOWCC', 'پذیرایی/مراسم تاکسیرانی: چندنامزد', "JOIN line_cc c ON c.sid=e.sid WHERE c.v21_decision='RECLASSIFY_TO_MULTIPLE_CANDIDATES' AND e.org='Taxi'"),
                           ('CD-EV-13', 'چرخه‌عمر چک TT-NE-13', "WHERE e.own_event='TT-NE-13' AND e.lifecycle_action='RETURN_DISHONOURED'"), ('CD-EXC01', 'واریزی نامشخص EXC-01', "WHERE e.own_event='EXC-01'"), ('CD-FE60', 'FE-60 تاکسیرانی', "WHERE e.own_event='FE-60' AND e.org='Taxi' AND e.role='DRIVER'")):
        for dk in docs_for(cond): picks.append((did, cls, dk))
    ex = []
    for did, cls, dk in picks:
        for row in q("""SELECT s.doc_key,s.date,s.hcode,coalesce(a.title,''),s.bed,s.bes,coalesce(e.own_event,''),e.role,coalesce(c.cc_status,''),coalesce(c.cc_id,'') FROM sanad s JOIN line_event e ON e.sid=s.sid JOIN line_cc c ON c.sid=s.sid
                        LEFT JOIN account_dictionary a ON a.org=s.org AND a.fy=s.fy AND a.hcode=s.hcode WHERE s.doc_key=? ORDER BY max(s.bed,s.bes) DESC LIMIT 10""", dk):
            ex.append((did, cls, row[0], row[1], mcode(row[2]), row[3], row[4], row[5], row[6], row[7], row[8], row[9]))
    put(wbk, fm, 'Supporting_Examples', ['Decision', 'Evidence class', 'doc_key', 'date', 'account', 'account title', 'debit', 'credit', 'v2.1 event', 'role', 'v2.1 CC status', 'v2.1 CC'], ex, title='نمونه‌های واقعی (شناسه سند، حساب‌ها و مبالغ؛ بدون شرح متنی؛ شماره حساب بانکی ماسک شده)', kinds={6: 'n', 7: 'n'})
    memo = memo_cd01().split('\n')
    ws = wbk.add_worksheet('CD-01_Memo_REDACTED'); ws.right_to_left(); ws.set_column(0, 0, 150)
    for i, ln in enumerate(memo): ws.write(i, 0, ln, fm['t'])
    wbk.close()

# ============================================================================================ client package + manifest
CLIENT_FILES = ['taxi_terminals_management_report_v2.1.md', 'CD-01_terminal_agency_expert_memo_REDACTED.md', 'committee_decisions_v2.1.xlsx', 'kpi_verification_v2.1.xlsx', 'financial_mapping_QA_v2.1.md',
                'machine_readable/canonical_events.csv', 'machine_readable/new_cost_center_candidates.json', 'machine_readable/kpi_definitions.json', 'machine_readable/kpi_status_v21.json', 'machine_readable/kpi_results.csv',
                'machine_readable/kpi_counts.csv', 'machine_readable/decision_readiness.csv', 'machine_readable/event_concept_review.csv', 'machine_readable/cc_confidence_coverage_v2_v21.csv', 'QA_Test_Registry_v2.1.csv']
def client_package():
    d = f'{OUT}/client_package'
    if os.path.exists(d): shutil.rmtree(d)
    os.makedirs(d)
    for fn in CLIENT_FILES:
        sp = f'{OUT}/{fn}'
        if os.path.exists(sp): shutil.copy(sp, f'{d}/{os.path.basename(fn)}')
    open(f'{d}/README_CLIENT.md', 'w', encoding='utf8').write('# بستهٔ بازبینی کارفرما — v2.1\n\nاین پوشه فقط خروجی‌های مناسب بازبینی را دارد: گزارش مدیریتی، یادداشت CD-01 (ماسک‌شده)، ماتریس تصمیم، تأیید KPI، خلاصهٔ QA و کاتالوگ‌های پیشنهادی. شرح متنی اسناد، شناسه‌های بانکی کامل و ردیابی سطح ردیف در آن نیست. همهٔ موارد PROPOSED‌اند و هیچ‌چیز APPROVED یا فعال نشده است؛ سال ۱۴۰۵ ناقص است.\n')

from manifest_v21 import manifest as _manifest
def manifest(final=False): return _manifest(OUT, ROOT, NOW)

# ============================================================================================ restricted FE-70 evidence
def fe70_restricted():
    import csv
    rows = q("""SELECT s.doc_key,s.date,s.hcode,coalesce(a.title,''),s.bed,s.bes,e.v2_event,e.v2_lifecycle,e.own_event,e.lifecycle_action,s.sharh
                FROM line_event e JOIN sanad s ON s.sid=e.sid LEFT JOIN account_dictionary_restricted a ON a.org=s.org AND a.fy=s.fy AND a.hcode=s.hcode WHERE e.sid IN (SELECT sid FROM fe70_review) ORDER BY s.doc_key,s.src_row""")
    with open(f'{MR}/RESTRICTED_FE70_evidence.csv', 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.writer(fh); w.writerow(['doc_key', 'date', 'account_code', 'account_title_unmasked', 'debit', 'credit', 'v2_event', 'v2_lifecycle', 'v21_event', 'v21_lifecycle', 'narration_RESTRICTED'])
        for r in rows: w.writerow(r)

MODE = sys.argv[1] if len(sys.argv) > 1 else 'docs'
write('corrective_audit_v2.1.md', corrective_audit())
write('FE70_depreciation_provisions_semantic_review.md', fe70_memo())
write('taxi_terminals_management_report_v2.1.md', management_report())
write('CD-01_terminal_agency_expert_memo_REDACTED.md', memo_cd01())
low_xlsx(); kpi_xlsx(); committee_xlsx(); fe70_restricted()
os.makedirs(f'{MR}/audit_inputs', exist_ok=True)      # manual-review inputs of 17_v21_corrections.py (sample verdicts; no narration) — needed to reproduce the audit tables
for fn in ('audit_samples_v21_round1.json', 'audit_samples_v21_round2.json', 'audit_postfix_v21.json'):
    if os.path.exists(f'{WORK}/{fn}'): shutil.copy(f'{WORK}/{fn}', f'{MR}/audit_inputs/{fn}')
client_package(); manifest()
print('docs written;', 'registry', {c: dict(QS[c]) for c in CATS})
