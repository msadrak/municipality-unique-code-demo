"""Phase 3 — period coverage, source-derived metrics, KPI catalogue/results and the 1404 vs 1405 comparison.

Only regular documents (doc kind REGULAR) feed financial metrics: opening / closing / temporary-closing / netting documents are excluded
so nothing is double counted.  Values are in the SOURCE monetary unit (not stated in the files; consistent with rial — UNVERIFIED).
Window rule (reproducible): for each org the comparable window is the longest contiguous prefix of 1405 months m1..mk such that the number
of regular documents posted in month m of 1405 is >= 50% of those posted in month m of 1404 AND month m is not the month containing the
latest source date.  This is a posting-density heuristic, NOT a proof of completeness.
"""
import sqlite3, sys, os, json, collections
sys.path.insert(0, os.path.dirname(__file__))
from common import *

con = sqlite3.connect(DB)
cur = con.cursor()
q = lambda s, *a: cur.execute(s, a).fetchall()
def one(s, *a):
    r = cur.execute(s, a).fetchone()
    return (r[0] or 0) if r else 0

for t in ('period_coverage', 'monthly_series', 'metric_values', 'kpi_catalogue', 'kpi_results', 'comparison'):
    cur.execute(f'DROP TABLE IF EXISTS {t}')
cur.execute('CREATE TABLE period_coverage(org, fy, first_date, last_date, last_month, n_docs INT, n_lines INT, window_months, window_rule, warning)')
cur.execute('CREATE TABLE monthly_series(org, fy, month, n_docs_regular INT, n_lines INT, revenue_own INT, expense_own INT, billed INT, collected INT, density_vs_1404)')
cur.execute('CREATE TABLE metric_values(org, fy, window, metric_id, title_fa, value, unit, basis)')

REG = "d.kind='REGULAR'"
BASE = "FROM sanad s JOIN doc_class d ON d.doc_key=s.doc_key JOIN line_event e ON e.sid=s.sid"
def val(org, fy, m_from, m_to, cond, expr):
    return one(f"SELECT sum({expr}) {BASE} WHERE s.org=? AND s.fy=? AND {REG} AND substr(s.date,6,2) BETWEEN ? AND ? AND ({cond})", org, fy, m_from, m_to)
def cnt(org, fy, m_from, m_to, cond, what='count(*)'):
    return one(f"SELECT {what} {BASE} WHERE s.org=? AND s.fy=? AND {REG} AND substr(s.date,6,2) BETWEEN ? AND ? AND ({cond})", org, fy, m_from, m_to)

# ------------------------------------------------------------------------------------------ coverage + window
cover = {}
for org in ORGS:
    dens = {}
    for fy in YEARS:
        r = q('SELECT min(date),max(date),count(distinct doc_key),count(*) FROM sanad WHERE org=? AND fy=?', org, fy)[0]
        cover[(org, fy)] = dict(first=r[0], last=r[1], docs=r[2], lines=r[3])
        for m in range(1, 13):
            mm = f'{m:02d}'
            nd = one(f"SELECT count(DISTINCT s.doc_key) {BASE} WHERE s.org=? AND s.fy=? AND {REG} AND substr(s.date,6,2)=?", org, fy, mm)
            dens[(fy, m)] = nd
    last_m = int(cover[(org, '1405')]['last'][5:7])
    k = 0
    for m in range(1, 13):
        if m >= last_m: break
        a, b = dens[('1404', m)], dens[('1405', m)]
        if a > 0 and b >= 0.5 * a: k = m
        else: break
    cover[(org, 'window_k')] = k
    for fy in YEARS:
        c = cover[(org, fy)]
        partial = fy == '1405'
        warn = ('سال ۱۴۰۵ ناقص است: آخرین تاریخ منبع %s؛ مقایسه سالانه با ۱۴۰۴ کامل مجاز نیست. پنجره مقایسه‌پذیر: ماه ۱ تا %d (قاعده تراکم ثبت).' % (c['last'], k)) if partial else 'سال کامل تا ' + c['last']
        cur.execute('INSERT INTO period_coverage VALUES(?,?,?,?,?,?,?,?,?,?)', (org, fy, c['first'], c['last'], int(c['last'][5:7]), c['docs'], c['lines'], f'01..{k:02d}' if partial else '01..12',
                    'ratio(docs1405_m/docs1404_m)>=0.5 contiguous, month < last-source month' if partial else 'full year', warn))
    for fy in YEARS:
        for m in range(1, 13):
            mm = f'{m:02d}'
            nd = dens[(fy, m)]
            nl = one(f"SELECT count(*) {BASE} WHERE s.org=? AND s.fy=? AND {REG} AND substr(s.date,6,2)=?", org, fy, mm)
            if nd == 0 and fy == '1405' and m > last_m: continue
            rev = val(org, fy, mm, mm, "s.kol IN ('413','812')", 's.bes-s.bed')
            exp = val(org, fy, mm, mm, "s.kol IN ('611','612','613') AND NOT (s.kol='613' AND s.moeen='20')", 's.bed-s.bes')
            bil = val(org, fy, mm, mm, "s.org='Terminals' AND s.kol='113' AND s.moeen='1' AND s.taf1 IN ('4','8')", 's.bed')
            col = val(org, fy, mm, mm, "s.org='Terminals' AND s.kol='113' AND s.moeen='1' AND s.taf1 IN ('4','8')", 's.bes')
            ratio = (nd / dens[('1404', m)]) if (fy == '1405' and dens[('1404', m)]) else None
            cur.execute('INSERT INTO monthly_series VALUES(?,?,?,?,?,?,?,?,?,?)', (org, fy, mm, nd, nl, rev, exp, bil, col, ratio))

# ------------------------------------------------------------------------------------------ metrics
EXP_OP = "s.kol IN ('611','612','613') AND NOT (s.kol='613' AND s.moeen='20')"
MET = {
 'Taxi': [
  ('T_REV_TOTAL', 'درآمد کل شناسایی‌شده (۴۱۳ و ۸۱۲)', "s.kol IN ('413','812')", 's.bes-s.bed', 'RIAL?', 'خالص بستانکار−بدهکار؛ بدون اسناد افتتاحیه/اختتامیه'),
  ('T_REV_SERVICE', 'درآمد بهای خدمات (پروانه، حق عضویت، نقل‌وانتقال، …) — FE-60 موقت', "s.kol='413' AND e.own_event='FE-60'", 's.bes-s.bed', 'RIAL?', ''),
  ('T_REV_FINES', 'درآمد جریمه تخلفات — TT-NE-01', "e.own_event='TT-NE-01'", 's.bes-s.bed', 'RIAL?', ''),
  ('T_REV_GRANT', 'کمک بودجه دریافتی از شهرداری — TT-NE-02', "e.own_event='TT-NE-02'", 's.bes-s.bed', 'RIAL?', ''),
  ('T_REV_SCHOOL_SHARE', 'سهم ۲٪ سرویس مدارس — TT-NE-05', "e.own_event='TT-NE-05' AND s.kol='413'", 's.bes-s.bed', 'RIAL?', ''),
  ('T_REV_UNRESOLVED', 'درآمد با رویداد حل‌نشده', "s.kol IN ('413','812') AND e.own_event IS NULL", 's.bes-s.bed', 'RIAL?', ''),
  ('T_EXP_OP', 'هزینه عملیاتی (۶۱۱–۶۱۳ بدون استهلاک)', EXP_OP, 's.bed-s.bes', 'RIAL?', 'مبنای تعهدی؛ شامل هزینه‌های ثبت‌شده در حساب پرداختنی'),
  ('T_EXP_DEP', 'هزینه استهلاک (۶۱۳-۲۰)', "s.kol='613' AND s.moeen='20'", 's.bed-s.bes', 'RIAL?', 'سند تعدیلی پایان دوره؛ هزینه غیرنقدی'),
  ('T_EXP_PAYROLL', 'حقوق و مزایا (۶۱۱)', "s.kol='611'", 's.bed-s.bes', 'RIAL?', ''),
  ('T_EXP_BANKFEE', 'کارمزد خدمات بانکی — TT-NE-08', "e.own_event='TT-NE-08' AND s.kol='612'", 's.bed-s.bes', 'RIAL?', ''),
  ('T_EXP_OUTSRC', 'خدمات برون‌سپاری‌شده و نیروی پیمانکاری (FE-45 + TT-NE-12)', "e.own_event IN ('FE-45','TT-NE-12') AND s.kol IN ('611','612','613')", 's.bed-s.bes', 'RIAL?', ''),
  ('T_EXP_WELFARE', 'رفاه کارکنان (FE-51)', "e.own_event='FE-51' AND s.kol IN ('611','612','613')", 's.bed-s.bes', 'RIAL?', ''),
  ('T_EXP_DRIVER_SUPPORT', 'کمک/رفاه رانندگان ناوگان — TT-NE-09', "e.own_event='TT-NE-09' AND s.kol='613'", 's.bed-s.bes', 'RIAL?', ''),
  ('T_EXP_VEHICLE', 'نگهداری و سوخت خودروهای بازرسی (فعالیت منبع ۰۴۶)', "s.markaz='046' AND s.kol IN ('612')", 's.bed-s.bes', 'RIAL?', 'کد فعالیت منبع؛ نه مرکز هزینه مصوب'),
  ('T_EXP_COMPLAINT', 'هزینه رسیدگی به شکایات و بازرسی (فعالیت منبع ۱۱۸)', "s.markaz='118' AND s.kol IN ('611','612')", 's.bed-s.bes', 'RIAL?', ''),
  ('T_CAPEX', 'اضافات دارایی ثابت (۱۲۰/۱۲۱/۱۲۳ بدهکار؛ بدون اصلاح سند)', "s.kol IN ('120','121','123') AND e.own_event IN ('FE-23','TT-NE-33')", 's.bed', 'RIAL?', 'ناخالص اضافات؛ تحویل نقدی یا تعهدی نامشخص'),
  ('T_SCHOOL_RECEIPTS', 'وجوه دریافتی سرویس مدارس (پیش‌دریافت امانی) — TT-NE-03', "e.own_event='TT-NE-03' AND s.kol='213'", 's.bes-s.bed', 'RIAL?', 'جریان عاملیتی؛ درآمد نیست'),
  ('T_SCHOOL_PAYOUT', 'پرداخت به شرکت‌های سرویس مدارس — TT-NE-04', "e.own_event='TT-NE-04' AND s.kol='113'", 's.bed-s.bes', 'RIAL?', 'ثبت در بدهکار حساب دریافتنی ۱۱۳ — ماهیت حسابداری نیازمند تأیید'),
  ('T_SCHOOL_REFUND', 'استرداد وجه انصرافی سرویس مدارس — TT-NE-06', "e.own_event='TT-NE-06' AND s.kol='213'", 's.bed-s.bes', 'RIAL?', ''),
  ('T_DOCS', 'تعداد اسناد منظم', 'd.kind=\'REGULAR\'', 'distinct', 'count', ''),
  ('T_BANKFEE_LINES', 'تعداد ردیف کارمزد بانکی', "e.own_event='TT-NE-08' AND s.kol='612'", 'count', 'count', ''),
 ],
 'Terminals': [
  ('M_BILLED', 'مطالبه درآمد صادرشده (بدهکار ۱۱۳-۱-۴ و ۱۱۳-۱-۸) — TT-NE-15', "s.kol='113' AND s.moeen='1' AND s.taf1 IN ('4','8')", 's.bed', 'RIAL?', 'مبنای صدور مطالبه؛ درآمد متعلق به شهرداری و بستانکاری ۲۱۱-۱ است'),
  ('M_COLLECTED', 'وصول مطالبات درآمدی (بستانکار ۱۱۳-۱-۴ و ۱۱۳-۱-۸) — FE-60 موقت', "s.kol='113' AND s.moeen='1' AND s.taf1 IN ('4','8')", 's.bes', 'RIAL?', 'شامل تسویه چک‌های وصول‌شده'),
  ('M_RECHARGE', 'هزینه تحمیل‌شده به شهرداری/شرکت‌ها (بدهکار ۱۱۳-۱ غیردرآمدی، بدون تسویه بین‌سازمانی)', "e.rule_id LIKE 'TX-%' AND e.role='DRIVER'", 's.bed', 'RIAL?', 'ماهیت: هزینه پرداخت‌شده توسط سازمان به حساب مطالبه از شهرداری؛ مبنای نقدی/عاملیتی — نیازمند تأیید حسابداری'),
  ('M_RECHARGE_PAYROLL', 'بخش حقوق و مزایا از هزینه تحمیل‌شده (FE-44..FE-51)', "e.rule_id LIKE 'TX-%' AND e.role='DRIVER' AND e.own_event IN ('FE-44','FE-48','FE-49','FE-50','FE-51')", 's.bed', 'RIAL?', ''),
  ('M_RECHARGE_OUTSRC', 'بخش برون‌سپاری (انتظامات/تأسیسات/نظافت) از هزینه تحمیل‌شده — TT-NE-12', "e.rule_id LIKE 'TX-%' AND e.role='DRIVER' AND e.own_event='TT-NE-12'", 's.bed', 'RIAL?', 'شامل صورت‌وضعیت‌های مشترک چند سازمان؛ تفکیک سهم پایانه‌ها ممکن نیست'),
  ('M_RECHARGE_UTIL', 'بخش قبوض و تعمیرات پایانه‌ها (FE-33/34/40/41)', "e.rule_id LIKE 'TX-%' AND e.role='DRIVER' AND e.own_event IN ('FE-33','FE-34','FE-41','FE-40','FE-39')", 's.bed', 'RIAL?', ''),
  ('M_EXP_OWN', 'هزینه در حساب‌های هزینه ۶۱۱–۶۱۳ (بدون استهلاک)', EXP_OP, 's.bed-s.bes', 'RIAL?', 'بسیار اندک: اکثر هزینه‌ها در حساب‌های دریافتنی ثبت می‌شود'),
  ('M_EXP_FACILITY_ACT', 'هزینه فعالیت منبع ۰۰۸ «بهبود نگهداری و تعمیرات و تجهیز پایانه‌ها»', "s.markaz='008' AND s.kol IN ('611','612','613') AND NOT (s.kol='613' AND s.moeen='20')", 's.bed-s.bes', 'RIAL?', ''),
  ('M_DEP', 'هزینه استهلاک (۶۱۳-۲۰)', "s.kol='613' AND s.moeen='20'", 's.bed-s.bes', 'RIAL?', ''),
  ('M_CHEQUES_RECEIVED', 'مبلغ چک‌های دریافتی اجاره/عوارض (بدهکار ۱۱۳-۵) — TT-NE-13', "s.kol='113' AND s.moeen='5' AND e.own_event='TT-NE-13'", 's.bed', 'RIAL?', ''),
  ('M_CAPEX', 'اضافات دارایی ثابت و زمین (بدهکار ۱۲۰/۱۲۱)', "s.kol IN ('120','121') AND s.bed>0 AND e.own_event IN ('FE-23','TT-NE-33')", 's.bed', 'RIAL?', ''),
  ('M_DOCS', 'تعداد اسناد منظم', "d.kind='REGULAR'", 'distinct', 'count', ''),
  ('M_BILLED_UNITS', 'تعداد واحد/غرفه‌ای که در دوره مطالبه برایش صادر شده (CodeVahed متمایز)', "s.kol='113' AND s.moeen='1' AND s.taf1 IN ('4','8') AND s.bed>0 AND s.vahed IS NOT NULL AND s.vahed<>'NULL'", 'distinct_vahed', 'count', 'فقط واحدهای دارای مطالبه؛ موجودی کل غرفات/مساحت در منبع نیست'),
 ],
}
V2 = VARIANT == 'v2'
if V2:   # audited metric definitions (see corrective_audit_v2.md §KPI): event ids and filters follow the v2 event dictionary
    def _patch(org, mid, cond=None, expr=None, title=None, insert_after=None, new=None):
        lst = MET[org]
        if new:
            i = [m[0] for m in lst].index(insert_after) + 1
            lst.insert(i, new); return
        i = [m[0] for m in lst].index(mid); m = lst[i]
        lst[i] = (m[0], title or m[1], cond or m[2], expr or m[3], m[4], m[5])
    _patch('Taxi', 'T_REV_SERVICE', cond="s.kol='413' AND s.moeen='1' AND e.own_event='FE-60'", title='درآمد بهای خدمات (پروانه، حق عضویت، نقل‌وانتقال؛ ۴۱۳-۱) — FE-60 موقت')
    _patch('Taxi', None, insert_after='T_REV_SERVICE', new=('T_REV_RENT', 'درآمد اجاره جایگاه/غرفه/فروشگاه (۴۱۳-۸) — FE-60 موقت', "s.kol='413' AND s.moeen='8' AND e.own_event='FE-60'", 's.bes-s.bed', 'RIAL?', 'در v1 داخل «درآمد بهای خدمات» شمرده شده بود'))
    _patch('Taxi', 'T_EXP_OUTSRC', cond="e.own_event IN ('FE-45','TT-NE-12','FE-03') AND s.kol IN ('611','612','613')", title='خدمات برون‌سپاری‌شده و نیروی پیمانکاری (FE-45 + TT-NE-12 + FE-03 صورت‌وضعیت خدمات)')
    _patch('Taxi', 'T_SCHOOL_RECEIPTS', cond="e.own_event='TT-NE-03' AND s.kol='213' AND e.lifecycle_action='COLLECT'")
    _patch('Taxi', 'T_SCHOOL_PAYOUT', cond="e.own_event='TT-NE-04' AND s.kol='113' AND e.lifecycle_action='PAYOUT'")
    _patch('Taxi', 'T_SCHOOL_REFUND', cond="e.own_event='TT-NE-03' AND s.kol='213' AND e.lifecycle_action='REFUND'")

windows = {}
for org in ORGS:
    k = cover[(org, 'window_k')]
    windows[org] = [('1404', 'FULL_YEAR', '01', '12'), ('1404', 'WINDOW', '01', f'{k:02d}'), ('1405', 'WINDOW', '01', f'{k:02d}'), ('1405', 'ALL_AVAILABLE', '01', '12')]
res = {}
for org, mets in MET.items():
    for fy, wn, a, b in windows[org]:
        for mid, title, cond, expr, unit, basis in mets:
            if expr == 'distinct':
                v = cnt(org, fy, a, b, cond, 'count(DISTINCT s.doc_key)')
            elif expr == 'distinct_vahed':
                v = cnt(org, fy, a, b, cond, 'count(DISTINCT s.vahed)')
            elif expr == 'count':
                v = cnt(org, fy, a, b, cond)
            else:
                v = val(org, fy, a, b, cond, expr)
            res[(org, fy, wn, mid)] = v
            cur.execute('INSERT INTO metric_values VALUES(?,?,?,?,?,?,?,?)', (org, fy, wn, mid, title, v, unit, basis))

# balance-type metrics (include opening documents, exclude closing documents): deposits held
def balance(org, fy, kol, moeen, upto_month):
    return one("""SELECT sum(s.bes-s.bed) FROM sanad s JOIN doc_class d ON d.doc_key=s.doc_key WHERE s.org=? AND s.fy=? AND s.kol=? AND s.moeen=?
                  AND d.kind IN ('OPENING','REGULAR','INTERNAL_SETTLEMENT') AND substr(s.date,6,2)<=?""", org, fy, kol, moeen, upto_month)
for org in ORGS:
    for fy in YEARS:
        for (kol, moe, mid, title) in (('212', '6', 'B_DEPOSITS', 'مانده سپرده‌های دیگران نزد ما (۲۱۲-۶) در پایان دوره'),):
            v = balance(org, fy, kol, moe, '12')
            cur.execute('INSERT INTO metric_values VALUES(?,?,?,?,?,?,?,?)', (org, fy, 'END_OF_AVAILABLE_DATA', mid, title, v, 'RIAL?', 'افتتاحیه + گردش منظم − بدون اسناد اختتامیه'))
            res[(org, fy, 'END_OF_AVAILABLE_DATA', mid)] = v
con.commit()

# ------------------------------------------------------------------------------------------ KPI catalogue
Y, Pn, RO, RB, RE, NC, CAL = 'CALCULATED_FROM_SOURCE', 'PARTIALLY_CALCULABLE', 'REQUIRES_OPERATIONAL_DATA', 'REQUIRES_BUDGET_DATA', 'REQUIRES_EXPERT_DEFINITION', 'NOT_CALCULABLE', 'CALCULATED_FROM_SOURCE'
K = []
def kpi(kid, org, fa, en, cat, activity, ccs, purpose, formula, num, den, unit, source_fin, source_op, method, filters, excl, avail, status, conf, notes, metrics=None):
    K.append(dict(kpi_id=kid, org=org, title_fa=fa, title_en=en, category=cat, activity=activity, cost_centers=ccs, purpose=purpose, formula=formula, numerator=num, denominator=den,
                  unit=unit, period='ماهانه/فصلی/سالانه؛ سال ۱۴۰۵ فقط پنجره مقایسه‌پذیر', financial_fields=source_fin, operational_fields=source_op, method=method, filters=filters,
                  exclusions=excl, data_availability=avail, calc_status=status, governance='PROPOSED — بدون تأیید رسمی', confidence=conf, notes=notes, metrics=metrics or ''))
GOV_EXCL = 'اسناد افتتاحیه/اختتامیه/بستن حساب موقت/تهاتر بین‌سازمانی؛ حساب‌های انتظامی ۹۱۸/۹۱۹'
# ---- Taxi
kpi('TX-K01', 'Taxi', 'درآمد بهای خدمات تاکسیرانی (پروانه، حق عضویت، نقل‌وانتقال)', 'Taxi service-fee revenue', 'Revenue indicators', 'ACT-TX-27 صدور و تمدید مجوز', 'مرکز هزینه ندارد (درآمد)', 'اندازه جریان درآمد خدمات سازمان', 'Σ(بستانکار−بدهکار ۴۱۳-۱ با رویداد FE-60)', 'درآمد خدمات', '—', 'واحد پول منبع', 'Sanad.Kol/Moeen/Tafsili1/Bed/Bes', '—', 'جمع در پنجره زمانی', 'اسناد منظم؛ kol=413', GOV_EXCL, 'در منبع موجود', Y, 'MEDIUM', 'نگاشت FE-60 موقت است', 'T_REV_SERVICE')
kpi('TX-K02', 'Taxi', 'سهم جریمه تخلفات از درآمد خدمات', 'Fines share of service revenue', 'Revenue indicators', 'ACT-TX-29 نظارت و کنترل', 'TTCC-P-01 (پیشنهادی)', 'پایش اتکا به جریمه', 'TT-NE-01 ÷ (FE-60 + TT-NE-01)', 'درآمد جریمه', 'درآمد خدمات + جریمه', 'درصد', 'Sanad.Sharh (نوع درآمد)', '—', 'نسبت', 'kol=413', GOV_EXCL, 'در منبع موجود', Y, 'MEDIUM', 'تفکیک با شرح سطر؛ ردیف‌های بدون شرح در FE-60 می‌مانند', 'T_REV_FINES,T_REV_SERVICE')
kpi('TX-K03', 'Taxi', 'وابستگی به کمک بودجه شهرداری', 'Municipal grant dependency', 'Financial sustainability indicators', 'کل سازمان', '—', 'سنجش خودتأمینی', 'TT-NE-02 ÷ (هزینه عملیاتی بدون استهلاک)', 'کمک بودجه دریافتی', 'هزینه عملیاتی', 'درصد', 'Sanad.Sharh «کمک بودجه»', '—', 'نسبت', 'kol 413-8', GOV_EXCL, 'در منبع موجود', Y, 'MEDIUM', 'ردیف‌های ۴۱۳-۸ بدون شرح نگاشت نمی‌شوند', 'T_REV_GRANT,T_EXP_OP')
kpi('TX-K04', 'Taxi', 'نسبت پوشش هزینه عملیاتی با درآمد (بدون کمک بودجه)', 'Operating cost-recovery ratio excl. grants', 'Financial sustainability indicators', 'کل سازمان', '—', 'سنجش توان پوشش هزینه', '(درآمد کل − کمک بودجه) ÷ هزینه عملیاتی', 'درآمد خدمات و سایر بدون کمک بودجه', 'هزینه عملیاتی بدون استهلاک', 'نسبت', 'Sanad.Kol 413/812/611-613', '—', 'نسبت', 'اسناد منظم', GOV_EXCL, 'در منبع موجود', Y, 'MEDIUM', 'مبنای تعهدی؛ درآمد ناشی از وجوه عاملیتی سرویس مدارس در صورت‌های سود و زیان وارد نیست', 'T_REV_TOTAL,T_REV_GRANT,T_EXP_OP')
kpi('TX-K05', 'Taxi', 'سهم هزینه حقوق و مزایا از هزینه عملیاتی', 'Payroll share of operating cost', 'Cost-efficiency indicators', 'ACT-TX-20/23 نیروی انسانی', 'CC-1301', 'کنترل ساختار هزینه', 'هزینه ۶۱۱ ÷ هزینه عملیاتی', 'حقوق و مزایا', 'هزینه عملیاتی', 'درصد', 'Sanad.Kol=611', '—', 'نسبت', 'kol 611–613', GOV_EXCL, 'در منبع موجود', Y, 'HIGH', 'خرید خدمات نیرو (۶۱۲) در صورت کسر نیست — مقایسه با TX-K11', 'T_EXP_PAYROLL,T_EXP_OP')
kpi('TX-K06', 'Taxi', 'بار کارمزد بانکی', 'Bank-fee burden', 'Financial efficiency indicators', 'ACT-TX-24 امور مالی', 'CC-1202', 'شناسایی اتلاف مالی ناشی از کارمزد', 'TT-NE-08 ÷ هزینه عملیاتی؛ تعداد ردیف کارمزد', 'کارمزد بانکی', 'هزینه عملیاتی', 'درصد/تعداد', 'Sanad.Kol=612-5-12', '—', 'نسبت', 'تفصیلی ۱۲', GOV_EXCL, 'در منبع موجود', Y, 'HIGH', '', 'T_EXP_BANKFEE,T_EXP_OP,T_BANKFEE_LINES')
kpi('TX-K07', 'Taxi', 'هزینه برون‌سپاری و نیروی پیمانکاری به هزینه عملیاتی', 'Outsourcing cost ratio', 'Cost-efficiency indicators', 'ACT-TX-20', 'CC-1301 / TTCC-P-01', 'سنجش اتکا به برون‌سپاری', '(FE-45 + TT-NE-12) ÷ هزینه عملیاتی', 'هزینه برون‌سپاری', 'هزینه عملیاتی', 'درصد', 'Sanad', '—', 'نسبت', '', GOV_EXCL, 'در منبع موجود', Pn, 'LOW', 'طبقه‌بندی رویداد برای ۶۱۲-۵-۱۴ موقت و کم‌اطمینان است', 'T_EXP_OUTSRC,T_EXP_OP')
kpi('TX-K08', 'Taxi', 'نرخ نگهداشت کارمزد سرویس مدارس (سهم ۲٪)', 'School-service retained-share rate', 'Service-output indicators', 'ACT-TX سرویس مدارس', 'TTCC-P-02 (پیشنهادی)', 'تطبیق سهم درآمد با وجوه عاملیتی', 'TT-NE-05 ÷ TT-NE-03', 'سهم شناسایی‌شده', 'وجوه دریافتی سامانه', 'درصد', 'Sanad (۲۱۳-۲-۵، ۴۱۳)', '—', 'نسبت', '', GOV_EXCL, 'در منبع موجود', Pn, 'LOW', 'زمان‌بندی شناسایی سهم با دریافت وجه یکسان نیست؛ نرخ مصوب در منبع نیست', 'T_REV_SCHOOL_SHARE,T_SCHOOL_RECEIPTS')
kpi('TX-K09', 'Taxi', 'سهم هزینه سرمایه‌ای از مجموع خروج منابع', 'Capital outlay share', 'Asset utilization indicators', 'ساختمان/جایگاه شارژ برقی', 'CC-1401 / CC-408', 'پایش سرمایه‌گذاری', 'اضافات دارایی ثابت ÷ (اضافات + هزینه عملیاتی)', 'اضافات دارایی ثابت', 'اضافات + هزینه عملیاتی', 'درصد', 'Sanad.Kol 120/121/123', '—', 'نسبت', '', GOV_EXCL, 'در منبع موجود', Pn, 'LOW', 'مبنای ثبت اضافات (نقدی/تعهدی) و خالص‌سازی تصحیحات روشن نیست', 'T_CAPEX,T_EXP_OP')
kpi('TX-K10', 'Taxi', 'هزینه به‌ازای هر تاکسی فعال', 'Cost per active taxi', 'Productivity indicators', 'کل ناوگان', 'CC-406 / TTCC-P-01', 'اثربخشی هزینه نسبت به اندازه ناوگان', 'هزینه عملیاتی ÷ تعداد تاکسی فعال', 'هزینه عملیاتی', 'تعداد تاکسی فعال', 'واحد پول/تاکسی', 'Sanad', 'ثبت ناوگان فعال (در منبع نیست)', '—', '', GOV_EXCL, 'مخرج در منبع نیست', RO, 'N/A', 'مخرج تخمین زده نشد')
kpi('TX-K11', 'Taxi', 'هزینه نگهداری به‌ازای هر خودروی بازرسی', 'Maintenance cost per inspection vehicle', 'Maintenance and reliability indicators', 'ACT-TX-09', 'CC-1402', 'کنترل هزینه نگهداری', 'هزینه فعالیت منبع ۰۴۶ ÷ تعداد خودروی بازرسی', 'T_EXP_VEHICLE', 'تعداد خودروی بازرسی', 'واحد پول/خودرو', 'Sanad.CodeMarkaz=046', 'تعداد خودرو (در منبع نیست)', '—', '', GOV_EXCL, 'صورت کسر در منبع؛ مخرج نیست', RO, 'N/A', 'صورت کسر قابل‌محاسبه است', 'T_EXP_VEHICLE')
kpi('TX-K12', 'Taxi', 'درآمد به‌ازای هر تراکنش خدمت (پروانه/نقل‌وانتقال)', 'Revenue per service transaction', 'Revenue indicators', 'ACT-TX-27', '—', 'بهره‌وری درآمد', 'درآمد بهای خدمات ÷ تعداد پروانه/درخواست پردازش‌شده', 'درآمد خدمات', 'تعداد تراکنش', 'واحد پول/تراکنش', 'Sanad', 'تعداد درخواست‌های پردازش‌شده', '—', '', GOV_EXCL, 'مخرج در منبع نیست (ردیف‌های دفتر خلاصه‌ی روزانه‌اند نه تراکنش)', RO, 'N/A', 'شمارش ردیف‌های دفتر جایگزین مخرج نیست')
kpi('TX-K13', 'Taxi', 'هزینه اداری به‌ازای هر درخواست پردازش‌شده', 'Administrative cost per processed request', 'Productivity indicators', 'ACT-TX-27/23/24', 'CC-1202 / CC-1301', 'کارایی اداری', 'هزینه فعالیت‌های اداری ÷ تعداد درخواست', 'هزینه اداری', 'تعداد درخواست', 'واحد پول/درخواست', 'Sanad.CodeMarkaz', 'تعداد درخواست', '—', '', GOV_EXCL, 'مخرج در منبع نیست', RO, 'N/A', '')
kpi('TX-K14', 'Taxi', 'هزینه واقعی نسبت به برنامه عملیاتی', 'Actual vs planned operating expenditure', 'Budget execution indicators', 'کل سازمان', '—', 'اجرای بودجه', 'هزینه واقعی ÷ بودجه مصوب', 'هزینه عملیاتی', 'بودجه مصوب سازمان', 'درصد', 'Sanad', 'بودجه مصوب سازمان (در منبع نیست)', '—', '', GOV_EXCL, 'بودجه سازمان در منبع نیست', RB, 'N/A', '')
kpi('TX-K15', 'Taxi', 'هزینه رسیدگی به شکایات به‌ازای هر شکایت', 'Complaint-handling cost per complaint', 'Service quality indicators', 'ACT-TX-26', 'CC-1502 / TTCC-P-01', 'کیفیت خدمت', 'هزینه فعالیت ۱۱۸ ÷ تعداد شکایت', 'T_EXP_COMPLAINT', 'تعداد شکایت', 'واحد پول/شکایت', 'Sanad.CodeMarkaz=118', 'تعداد شکایت', '—', '', GOV_EXCL, 'صورت کسر در منبع؛ مخرج نیست', RO, 'N/A', '', 'T_EXP_COMPLAINT')
kpi('TX-K16', 'Taxi', 'کمک و رفاه رانندگان به‌ازای هر راننده', 'Driver-support spend per driver', 'Service-output indicators', 'TT-NE-09', 'CC-406', 'پایش حمایت از ناوگان', 'TT-NE-09 ÷ تعداد رانندگان تحت پوشش', 'T_EXP_DRIVER_SUPPORT', 'تعداد رانندگان', 'واحد پول/راننده', 'Sanad', 'تعداد رانندگان (فقط نمونه‌هایی چون «۷۰۱ نفر انصرافی» در متن)', '—', '', GOV_EXCL, 'مخرج در منبع نیست', RE, 'N/A', 'تعریف «راننده تحت پوشش» باید توسط کارشناس مشخص شود', 'T_EXP_DRIVER_SUPPORT')
# ---- Terminals
kpi('TM-K01', 'Terminals', 'مطالبه درآمد صادرشده پایانه‌ها (اجاره، عوارض، شارژ)', 'Billed terminal revenue', 'Revenue indicators', 'مدیریت و اجاره‌دهی غرفات', 'CC_NOT_APPLICABLE (درآمد) — TTCC-P-03', 'اندازه درآمد قابل مطالبه', 'Σ بدهکار ۱۱۳-۱-۴ و ۱۱۳-۱-۸', 'مطالبه صادرشده', '—', 'واحد پول منبع', 'Sanad.Kol=113 Moeen=1 Tafsili1∈{4,8}', '—', 'جمع در پنجره', 'اسناد منظم', GOV_EXCL, 'در منبع موجود', Pn, 'MEDIUM', 'درآمد متعلق به شهرداری است (بستانکار ۲۱۱-۱)؛ فقط «مطالبه» است نه درآمد شناسایی‌شده سازمان', 'M_BILLED')
kpi('TM-K02', 'Terminals', 'مطالبه درآمد به تفکیک پایانه', 'Billed revenue by terminal', 'Revenue indicators', 'مدیریت پایانه‌ها', 'TTCC-P-03', 'مقایسه درون‌سازمانی پایانه‌ها', 'Σ مطالبه به تفکیک بخش اول CodeVahed', 'مطالبه هر پایانه', '—', 'واحد پول منبع', 'Sanad.CodeVahed', '—', 'گروه‌بندی', 'tafsili1∈{4,8}', GOV_EXCL, 'در منبع موجود', Y, 'MEDIUM', 'بخش اول CodeVahed: ۰۰۱ کاوه، ۰۰۲ صفه، ۰۰۳ زاینده‌رود، ۰۰۴ جی، ۰۰۷ صمدیه — از روی NameVahed راستی‌آزمایی شد', 'M_BILLED')
kpi('TM-K03', 'Terminals', 'درآمد به‌ازای هر واحد/غرفه دارای مطالبه', 'Revenue per billed unit', 'Revenue indicators', 'اجاره غرفات', 'TTCC-P-03', 'بهره‌وری درآمدی واحدها', 'مطالبه ÷ تعداد CodeVahed متمایز دارای مطالبه', 'M_BILLED', 'M_BILLED_UNITS', 'واحد پول/واحد', 'Sanad.CodeVahed', 'مساحت/تعداد کل غرفات (در منبع نیست)', 'نسبت', '', GOV_EXCL, 'مخرج جزئی: فقط واحدهای دارای مطالبه', Pn, 'LOW', 'غرفه‌های خالی یا بدون مطالبه در مخرج نیستند؛ مساحت موجود نیست', 'M_BILLED,M_BILLED_UNITS')
kpi('TM-K04', 'Terminals', 'نسبت وصول به مطالبه', 'Collection-to-billing ratio', 'Financial efficiency indicators', 'وصول درآمد', 'CC-1201', 'پایش وصول', 'M_COLLECTED ÷ M_BILLED', 'وصول', 'مطالبه', 'نسبت', 'Sanad.Kol=113', '—', 'نسبت', '', GOV_EXCL, 'در منبع موجود', Pn, 'LOW', 'وصول شامل تسویه مطالبات دوره‌های قبل است؛ نسبت دوره‌ای نه نرخ وصول همان دوره', 'M_COLLECTED,M_BILLED')
kpi('TM-K05', 'Terminals', 'هزینه تحمیل‌شده به شهرداری به تفکیک نوع (حقوق/برون‌سپاری/تأسیسات)', 'Recharged operating cost by type', 'Cost-efficiency indicators', 'اداره پایانه‌ها', 'CC-403 / CC-1301 / TTCC-P-03', 'شفافیت هزینه‌های پایانه‌ها', 'Σ بدهکار ۱۱۳-۱ غیردرآمدی', 'M_RECHARGE', '—', 'واحد پول منبع', 'Sanad.Kol=113 Tafsili1∉{4,8,7}', '—', 'جمع', '', GOV_EXCL, 'در منبع موجود', Pn, 'LOW', 'ماهیت مبنای ثبت (هزینه سازمان یا هزینه‌ای که شهرداری بازپرداخت می‌کند) باید تأیید شود؛ صورت‌وضعیت‌های مشترک چند سازمان', 'M_RECHARGE,M_RECHARGE_PAYROLL,M_RECHARGE_OUTSRC,M_RECHARGE_UTIL')
kpi('TM-K06', 'Terminals', 'هزینه عملیاتی به‌ازای هر پایانه', 'Operating cost per terminal', 'Cost-efficiency indicators', 'اداره پایانه‌ها', 'CC-403', 'مقایسه هزینه پایانه‌ها', 'هزینه تحمیل‌شده با CodeVahed پایانه ÷ تعداد پایانه', 'هزینه پایانه', 'تعداد پایانه (۶ مشاهده‌شده)', 'واحد پول/پایانه', 'Sanad.CodeVahed', 'مساحت/مسافر', '—', '', GOV_EXCL, 'صورت کسر ناقص: بخشی از هزینه با کد دفتر مرکزی ثبت شده است', Pn, 'LOW', 'سهم هزینه دفتر مرکزی بین پایانه‌ها قابل تسهیم نیست', 'M_RECHARGE')
kpi('TM-K07', 'Terminals', 'هزینه به‌ازای هر مسافر خدمت‌شده', 'Cost per passenger served', 'Productivity indicators', 'اداره پایانه‌ها', 'CC-403', 'بهره‌وری', 'هزینه ÷ تعداد مسافر', 'هزینه', 'تعداد مسافر', 'واحد پول/مسافر', 'Sanad', 'آمار مسافر (در منبع نیست)', '—', '', GOV_EXCL, 'مخرج در منبع نیست', RO, 'N/A', 'تخمین مسافر از عوارض ۵٪ بلیط انجام نشد (غیرمستند)')
kpi('TM-K08', 'Terminals', 'درآمد به‌ازای هر مسافر', 'Revenue per passenger', 'Revenue indicators', 'اداره پایانه‌ها', '—', 'بهره‌وری درآمدی', 'مطالبه ÷ تعداد مسافر', 'M_BILLED', 'تعداد مسافر', 'واحد پول/مسافر', 'Sanad', 'آمار مسافر', '—', '', GOV_EXCL, 'مخرج در منبع نیست', RO, 'N/A', '')
kpi('TM-K09', 'Terminals', 'هزینه نگهداری به‌ازای هر تأسیسات/مساحت پایانه', 'Maintenance cost per facility', 'Maintenance and reliability indicators', 'ACT-TM-01 نگهداری و تجهیز پایانه‌ها', 'CC-403', 'کنترل نگهداری', 'هزینه نگهداری و تأسیسات ÷ مساحت/تعداد تأسیسات', 'M_RECHARGE_UTIL', 'مساحت پایانه', 'واحد پول/متر', 'Sanad', 'مساحت/فهرست تأسیسات', '—', '', GOV_EXCL, 'صورت کسر در منبع؛ مخرج نیست', RO, 'N/A', '', 'M_RECHARGE_UTIL,M_EXP_FACILITY_ACT')
kpi('TM-K10', 'Terminals', 'سرمایه‌گذاری زیرساختی به‌ازای هر پایانه', 'Infrastructure investment per terminal', 'Asset utilization indicators', 'تجهیز پایانه‌ها', 'CC-403', 'پایش سرمایه‌گذاری', 'اضافات دارایی ثابت ÷ تعداد پایانه', 'M_CAPEX', 'تعداد پایانه', 'واحد پول/پایانه', 'Sanad.Kol 120/121', '—', '—', '', GOV_EXCL, 'اضافات در منبع (کم‌حجم) ؛ تخصیص به پایانه نیازمند CodeVahed دارایی', Pn, 'LOW', '', 'M_CAPEX')
kpi('TM-K11', 'Terminals', 'مانده سپرده غرفات و شرکت‌ها (تعهد استرداد)', 'Deposit liability held', 'Financial sustainability indicators', 'سپرده انجام تعهدات', 'CC_NOT_APPLICABLE', 'پایش تعهد استرداد', 'مانده بستانکار ۲۱۲-۶', 'مانده', '—', 'واحد پول منبع', 'Sanad.Kol=212 Moeen=6', '—', 'مانده (افتتاحیه + گردش)', '', 'اسناد اختتامیه', 'در منبع موجود', Y, 'MEDIUM', '', 'B_DEPOSITS')
kpi('TM-K12', 'Terminals', 'نرخ برگشت چک‌های دریافتی', 'Cheque dishonour rate', 'Financial efficiency indicators', 'وصول درآمد', 'CC-1201', 'ریسک وصول', 'مبلغ چک برگشتی ÷ مبلغ چک دریافتی', 'چک برگشتی', 'چک دریافتی', 'درصد', 'Sanad.Kol=113 Moeen=5/6/7', '—', '—', '', GOV_EXCL, 'برگشت چک در حساب ۱۱۳-۷ و واخواست جزئی؛ تعریف دقیق نیاز به تصمیم کارشناس دارد', RE, 'N/A', 'عدد منتشر نشد')
kpi('TM-K13', 'Terminals', 'هزینه واقعی نسبت به برنامه (فعالیت ۰۰۸)', 'Actual vs planned expenditure', 'Budget execution indicators', 'ACT-TM-01', 'CC-403', 'اجرای بودجه', 'هزینه واقعی ÷ بودجه مصوب', 'M_EXP_FACILITY_ACT', 'بودجه مصوب پایانه‌ها', 'درصد', 'Sanad.CodeMarkaz=008', 'بودجه مصوب (در منبع نیست)', '—', '', GOV_EXCL, 'بودجه در منبع نیست', RB, 'N/A', '', 'M_EXP_FACILITY_ACT')
kpi('TM-K14', 'Terminals', 'سهم برون‌سپاری از هزینه تحمیل‌شده', 'Outsourcing share of recharged cost', 'Cost-efficiency indicators', 'خدمات انتظامات/تأسیسات', 'CC-1405 / CC-403', 'سنجش اتکا به برون‌سپاری', 'M_RECHARGE_OUTSRC ÷ M_RECHARGE', 'برون‌سپاری', 'هزینه تحمیل‌شده', 'درصد', 'Sanad', '—', 'نسبت', '', GOV_EXCL, 'در منبع موجود', Pn, 'LOW', 'صورت‌وضعیت مشترک چند سازمان؛ احتمال جمع‌شدن اقلام غیرمرتبط', 'M_RECHARGE_OUTSRC,M_RECHARGE')
cur.execute('CREATE TABLE kpi_catalogue(kpi_id, org, title_fa, title_en, category, activity, cost_centers, purpose, formula, numerator, denominator, unit, period, financial_fields, operational_fields, method, filters, exclusions, data_availability, calc_status, governance, confidence, notes, metrics)')
for k in K:
    cur.execute('INSERT INTO kpi_catalogue VALUES(' + ','.join('?' * 24) + ')', tuple(k[c] for c in ('kpi_id', 'org', 'title_fa', 'title_en', 'category', 'activity', 'cost_centers', 'purpose', 'formula', 'numerator', 'denominator', 'unit', 'period', 'financial_fields', 'operational_fields', 'method', 'filters', 'exclusions', 'data_availability', 'calc_status', 'governance', 'confidence', 'notes', 'metrics')))

# ------------------------------------------------------------------------------------------ KPI results (only supportable)
cur.execute('CREATE TABLE kpi_results(kpi_id, org, fy, window, numerator_name, numerator, denominator_name, denominator, value, unit, status, caveat)')
def g(org, fy, wn, mid): return res.get((org, fy, wn, mid), 0)
def ratio(a, b): return (a / b) if b else None
for org in ORGS:
    for fy, wn, a, b in windows[org]:
        if org == 'Taxi':
            R = lambda m: g(org, fy, wn, m)
            rows = [
              ('TX-K01', 'درآمد بهای خدمات', R('T_REV_SERVICE'), '—', None, R('T_REV_SERVICE'), 'RIAL?', Y, ''),
              ('TX-K02', 'درآمد جریمه', R('T_REV_FINES'), 'درآمد خدمات + جریمه', R('T_REV_SERVICE') + R('T_REV_FINES'), ratio(R('T_REV_FINES'), R('T_REV_SERVICE') + R('T_REV_FINES')), 'نسبت', Y, ''),
              ('TX-K03', 'کمک بودجه', R('T_REV_GRANT'), 'هزینه عملیاتی', R('T_EXP_OP'), ratio(R('T_REV_GRANT'), R('T_EXP_OP')), 'نسبت', Y, ''),
              ('TX-K04', 'درآمد بدون کمک بودجه', R('T_REV_TOTAL') - R('T_REV_GRANT'), 'هزینه عملیاتی', R('T_EXP_OP'), ratio(R('T_REV_TOTAL') - R('T_REV_GRANT'), R('T_EXP_OP')), 'نسبت', Y, ''),
              ('TX-K05', 'حقوق و مزایا', R('T_EXP_PAYROLL'), 'هزینه عملیاتی', R('T_EXP_OP'), ratio(R('T_EXP_PAYROLL'), R('T_EXP_OP')), 'نسبت', Y, ''),
              ('TX-K06', 'کارمزد بانکی', R('T_EXP_BANKFEE'), 'هزینه عملیاتی', R('T_EXP_OP'), ratio(R('T_EXP_BANKFEE'), R('T_EXP_OP')), 'نسبت', Y, f"تعداد ردیف کارمزد: {R('T_BANKFEE_LINES')}"),
              ('TX-K07', 'برون‌سپاری', R('T_EXP_OUTSRC'), 'هزینه عملیاتی', R('T_EXP_OP'), ratio(R('T_EXP_OUTSRC'), R('T_EXP_OP')), 'نسبت', Pn, 'طبقه‌بندی موقت'),
              ('TX-K08', 'سهم ۲٪ شناسایی‌شده', R('T_REV_SCHOOL_SHARE'), 'وجوه دریافتی سامانه', R('T_SCHOOL_RECEIPTS'), ratio(R('T_REV_SCHOOL_SHARE'), R('T_SCHOOL_RECEIPTS')), 'نسبت', Pn, 'زمان‌بندی نابرابر؛ نرخ مصوب نامشخص'),
              ('TX-K09', 'اضافات دارایی ثابت', R('T_CAPEX'), 'اضافات + هزینه عملیاتی', R('T_CAPEX') + R('T_EXP_OP'), ratio(R('T_CAPEX'), R('T_CAPEX') + R('T_EXP_OP')), 'نسبت', Pn, ''),
              ('TX-K11', 'هزینه فعالیت ۰۴۶ (صورت کسر)', R('T_EXP_VEHICLE'), 'تعداد خودروی بازرسی', None, None, 'واحد پول/خودرو', RO, 'مخرج در منبع نیست'),
              ('TX-K15', 'هزینه فعالیت ۱۱۸ (صورت کسر)', R('T_EXP_COMPLAINT'), 'تعداد شکایت', None, None, 'واحد پول/شکایت', RO, 'مخرج در منبع نیست'),
              ('TX-K16', 'کمک/رفاه رانندگان (صورت کسر)', R('T_EXP_DRIVER_SUPPORT'), 'تعداد رانندگان', None, None, 'واحد پول/راننده', RE, 'تعریف مخرج نیاز به تصمیم'),
            ]
        else:
            R = lambda m: g(org, fy, wn, m)
            rows = [
              ('TM-K01', 'مطالبه صادرشده', R('M_BILLED'), '—', None, R('M_BILLED'), 'RIAL?', Pn, 'مطالبه عاملیتی؛ درآمد شهرداری'),
              ('TM-K03', 'مطالبه صادرشده', R('M_BILLED'), 'واحد دارای مطالبه', R('M_BILLED_UNITS'), ratio(R('M_BILLED'), R('M_BILLED_UNITS')), 'واحد پول/واحد', Pn, 'مخرج جزئی'),
              ('TM-K04', 'وصول', R('M_COLLECTED'), 'مطالبه', R('M_BILLED'), ratio(R('M_COLLECTED'), R('M_BILLED')), 'نسبت', Pn, 'نسبت دوره‌ای؛ وصول شامل دوره‌های قبل'),
              ('TM-K05', 'هزینه تحمیل‌شده', R('M_RECHARGE'), '—', None, R('M_RECHARGE'), 'RIAL?', Pn, 'مبنای ثبت نیازمند تأیید'),
              ('TM-K14', 'برون‌سپاری', R('M_RECHARGE_OUTSRC'), 'هزینه تحمیل‌شده', R('M_RECHARGE'), ratio(R('M_RECHARGE_OUTSRC'), R('M_RECHARGE')), 'نسبت', Pn, ''),
              ('TM-K13', 'هزینه فعالیت ۰۰۸ (صورت کسر)', R('M_EXP_FACILITY_ACT'), 'بودجه مصوب', None, None, 'درصد', RB, 'بودجه در منبع نیست'),
            ]
        for (kid, nn, nv, dn, dv, v, unit, st, cav) in rows:
            cur.execute('INSERT INTO kpi_results VALUES(?,?,?,?,?,?,?,?,?,?,?,?)', (kid, org, fy, wn, nn, nv, dn, dv, v, unit, st, cav))
    # TM-K11 deposits balance
    for fy in YEARS:
        cur.execute('INSERT INTO kpi_results VALUES(?,?,?,?,?,?,?,?,?,?,?,?)', ('TM-K11', 'Terminals', fy, 'END_OF_AVAILABLE_DATA', 'مانده سپرده', res[('Terminals', fy, 'END_OF_AVAILABLE_DATA', 'B_DEPOSITS')], '—', None, res[('Terminals', fy, 'END_OF_AVAILABLE_DATA', 'B_DEPOSITS')], 'RIAL?', Y, 'افتتاحیه+گردش') ) if org == 'Terminals' else None
# per-terminal billed revenue (TM-K02)
cur.execute('CREATE TABLE IF NOT EXISTS billed_by_terminal(fy, window, facility_code, facility_name, billed INT, collected INT, n_units INT)')
cur.execute('DELETE FROM billed_by_terminal')
FAC = {'001': 'کاوه', '002': 'صفه', '003': 'زاینده‌رود', '004': 'جی', '007': 'صمدیه', '005': 'دفتر مرکزی', '008': 'دفتر طالقانی', '010': 'اندیشه', '006': 'انبار'}
for fy, wn, a, b in windows['Terminals']:
    rows = q(f"""SELECT substr(coalesce(s.vahed,'NULL'),1,3) seg, sum(s.bed), sum(s.bes), count(DISTINCT s.vahed) {BASE} WHERE s.org='Terminals' AND s.fy=? AND {REG}
                 AND substr(s.date,6,2) BETWEEN ? AND ? AND s.kol='113' AND s.moeen='1' AND s.taf1 IN ('4','8') GROUP BY seg ORDER BY 2 DESC""", fy, a, b)
    for seg, bd, cr, nu in rows:
        cur.execute('INSERT INTO billed_by_terminal VALUES(?,?,?,?,?,?,?)', (fy, wn, seg, FAC.get(seg, 'نامشخص'), bd, cr, nu))
con.commit()

# ------------------------------------------------------------------------------------------ comparison table
cur.execute('CREATE TABLE comparison(org, metric_id, title_fa, v1404_full, v1404_window, v1405_window, v1405_all_available, window_months, change_pct_window, comparability, note)')
for org, mets in MET.items():
    k = cover[(org, 'window_k')]
    for mid, title, *_ in mets:
        f, w4, w5, al = (res[(org, '1404', 'FULL_YEAR', mid)], res[(org, '1404', 'WINDOW', mid)], res[(org, '1405', 'WINDOW', mid)], res[(org, '1405', 'ALL_AVAILABLE', mid)])
        chg = ((w5 - w4) / w4 * 100) if w4 else None
        if k == 0:
            comp = 'NOT_COMPARABLE'; note = 'هیچ ماهی از ۱۴۰۵ قاعده تراکم ثبت را ندارد'
        else:
            comp = 'INDICATIVE_ONLY'; note = f'پنجره ماه ۱ تا {k}؛ تغییر کدگذاری/ثبت و تأخیر ثبت ممکن است؛ رشد سالانه نیست'
        if mid in ('T_DOCS', 'M_DOCS'): comp = 'VOLUME_ONLY'
        cur.execute('INSERT INTO comparison VALUES(?,?,?,?,?,?,?,?,?,?,?)', (org, mid, title, f, w4, w5, al, f'01..{k:02d}', chg, comp, note))
con.commit()
print({k: v for k, v in cover.items() if isinstance(k[1], str) and k[1] == 'window_k'})
for r in q('SELECT org,fy,window,metric_id,value FROM metric_values WHERE window IN ("FULL_YEAR","WINDOW") AND metric_id IN ("T_REV_TOTAL","T_EXP_OP","M_BILLED","M_COLLECTED","M_RECHARGE") ORDER BY 1,4,2,3'): print(r)
for r in q('SELECT * FROM kpi_results WHERE window=? ORDER BY org,kpi_id,fy', 'WINDOW'): print(r)
