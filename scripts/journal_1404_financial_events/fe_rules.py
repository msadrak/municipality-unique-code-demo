"""Provisional (UNAPPROVED) line-level financial-event rules for the 1404 journal.

Each journal line is first given an *accounting category* from the account hierarchy (new class/kol/moin; old
coding as fallback).  `line_rule` then returns the line's own event evidence:
    (event | [candidates] | None, kind, role, method, basis)
kind: DRIVER   – the line itself evidences the economic event (expense, revenue, prepayment, deposit, loan …)
      WITHHOLD – a deduction/withholding event that is a satellite of the document's main event (FE-02/07/09/11/48/49)
      COMPONENT– settlement/counter leg (bank, payable, inter-region account …); event is inherited from the document
Rules are evidence-based proposals for client approval, not ERP configuration.
"""
import re, sys
sys.path.insert(0, 'H:/Freelancing_Project/KalaniProject/municipality_demo/scripts/journal_1404_activity_cc_v4')
from activity_rules import norm, classify  # noqa: E402

# column indices of the journal main sheet (0-based; journal tuples are (excel_row,) + 43 cells)
C_DOCID, C_REG, C_REGN, C_DOCNO, C_ACC, C_OKOL, C_OMOIN, C_OTAF = 1, 2, 3, 4, 7, 8, 9, 10
C_KOLT, C_MOINT, C_TAFT, C_JOZT, C_DR, C_CR, C_DTYPE, C_DESC, C_BUD = 12, 13, 14, 15, 16, 17, 18, 19, 22
C_CLS, C_CLST, C_KOL, C_KOLN, C_MOIN, C_MOINN, C_ORG, C_ORGT = 23, 24, 25, 26, 27, 28, 29, 30
C_AF, C_AG, C_AH, C_AI, C_PER, C_PERT = 31, 32, 33, 34, 35, 36

def g(r, i): return r[1 + i]
def s(v): return '' if v is None else str(v).strip()
def num(v):
    try: return float(v or 0)
    except (TypeError, ValueError): return 0.0

# ------------------------------------------------------------------ gap register (NOT canonical events)
GAPS = {
 'GAP-01': ('ثبت (محاسبه) صورت‌وضعیت پیمانکار و شناسایی بدهی', 'پیمان و قرارداد', 'هزینه‌ای یا سرمایه‌ای / بدهی پیمانکار', 'شناسایی کارکرد',
            'فرهنگ v7.1 فقط «پرداخت» صورت‌وضعیت (FE-03) را دارد؛ اسناد «محاسبه صورت وضعیت پیمانکاران» شناسایی کارکرد و بدهی را بدون پرداخت ثبت می‌کنند. نزدیک‌ترین رویداد موجود: FE-03'),
 'GAP-02': ('شناسایی تعهدی درآمد (جدا از وصول)', 'درآمد و عوارض', 'درآمدی / مطالبات', 'شناسایی درآمد',
            'رویدادهای درآمدی v7.1 همگی «وصول» هستند. در دفتر ۱۴۰۴ درآمد هم‌زمان با دریافت وجه یا دریافت چک ثبت می‌شود (مبنای نقدی)، پس سطر جداگانه‌ای برای شناسایی تعهدی مشاهده نشد؛ فقط شکاف مدل ثبت می‌شود'),
 'GAP-03': ('وصول، واخواست و جابه‌جایی سررسید اسناد دریافتنی', 'درآمد و عوارض', 'ترازنامه‌ای / اسناد دریافتنی', 'وصول اسناد',
            'دریافت وجه چک‌های اقساطی، انتقال به واخواستی و جابه‌جایی سررسید در فرهنگ رویداد ندارد. نزدیک‌ترین: FE-57/FE-58 (وصول) که درآمد را در زمان دریافت چک شناسایی کرده‌اند'),
 'GAP-04': ('وصول سایر درآمدهای عمومی فاقد رویداد اختصاصی', 'درآمد و عوارض', 'درآمدی عمومی', 'وصول درآمد',
            'عوارض نقل‌وانتقال املاک، عوارض ماده ۹ قانون حمل‌ونقل ریلی، سود سپرده، کمک دولت و اعانات در فرهنگ v7.1 رویداد اختصاصی ندارند'),
 'GAP-05': ('پرداخت و تسویه مساعده و بدهی کارکنان', 'حقوق و دستمزد', 'ترازنامه‌ای / مطالبات از کارکنان', 'علی‌الحساب کارکنان',
            'پرداخت مساعده و کسر بدهی کارکنان از حقوق رویداد ندارد. نزدیک‌ترین: FE-44'),
 'GAP-06': ('تأمین مالی درون‌سازمانی صندوق ذخیره خزانه (اعطا/دریافت/بازپرداخت)', 'مالی و خزانه‌داری', 'ترازنامه‌ای / تسهیلات درون‌سازمانی', 'تأمین مالی داخلی',
            'تسهیلات صندوق ذخیره خزانه به مناطق و سازمان‌ها نه وام بانکی (FE-63/64) است نه انتقال ساده نقدینگی (FE-68)'),
 'GAP-07': ('پیش‌پرداخت و علی‌الحساب خرید کالا، خرید سرمایه‌ای و سایر پیش‌پرداخت‌ها', 'تدارکات و خرید', 'ترازنامه‌ای / پیش‌پرداخت', 'پیش‌پرداخت خرید',
            'FE-01 فقط پیش‌پرداخت پیمانکار است؛ پیش‌پرداخت خرید سیمان/قیر/کالا (معین 14002) و سایر پیش‌پرداخت‌ها (14003، 14005) رویداد ندارند'),
 'GAP-08': ('رسید و حواله کالا در انبار (مصرف موجودی)', 'تدارکات و خرید', 'ترازنامه‌ای / موجودی کالا', 'مصرف کالا',
            'خروج کالا از انبار و انتقال به هزینه/پروژه رویداد ندارد؛ FE-22 تا FE-28 خرید هستند نه مصرف'),
 'GAP-09': ('فروش، واگذاری و تهاتر اموال منقول و غیرمنقول', 'املاک و تملک', 'درآمدی / دارایی', 'واگذاری دارایی',
            'فروش املاک، واحدهای تجاری/مسکونی و اموال اسقاط رویداد ندارد. FE-56 فقط واگذاری معوض در توافق تملک است'),
 'GAP-10': ('پرداخت و تسویه حساب‌های پرداختنی عملیاتی (غیر از صورت‌وضعیت پیمانکار)', 'مالی و خزانه‌داری', 'ترازنامه‌ای / تسویه بدهی', 'تسویه بدهی',
            'پرداخت بدهی ثبت‌شده قبلی به تأمین‌کنندگان، سازمان‌های وابسته و سایر بستانکاران رویداد عمومی ندارد. FE-03 فقط پیمانکار و FE-67 فقط دیون سنواتی است'),
 'GAP-11': ('دریافت خدمات عمومی/برون‌سپاری فاقد رویداد اختصاصی', 'تدارکات و خرید', 'هزینه‌ای جاری', 'خرید خدمات',
            'حق‌الزحمه خدمات قراردادی عام، چاپ، تشریفات و خدمات برون‌سپاری‌شده شهری رویداد اختصاصی ندارند. FE-29 فقط مشاوره/طراحی است'),
 'GAP-12': ('سرمایه‌گذاری و مشارکت در سهام و پروژه‌های مشارکتی', 'مالی و خزانه‌داری', 'ترازنامه‌ای / سرمایه‌گذاری', 'سرمایه‌گذاری',
            'خرید سهام، مشارکت و سرمایه‌گذاری کوتاه‌مدت/بلندمدت رویداد ندارد'),
}

# ------------------------------------------------------------------ accounting category
def category(r):
    k, m = s(g(r, C_KOL)), s(g(r, C_MOIN))
    ok, om, ot = s(g(r, C_OKOL)), s(g(r, C_OMOIN)), s(g(r, C_OTAF))
    n = s(g(r, C_MOINT))
    if k == '110':
        return {'11009': 'IMPREST', '11007': 'CASHBOX', '11008': 'INTRANSIT'}.get(m, 'BANK')
    if k == '115':
        if m == '11513': return 'NOTES_REC'
        if ok == '630' and om == '001' and ot == '00006': return 'VAT_REC'
        if ok == '630' and om == '001' and ot in ('00100', '00101', '00001', '00005', '00014'): return 'INTER_REGION'
        if ok == '630' and om == '001' and ot in ('00200', '00201', '00002'): return 'REC_AFFIL'
        return 'REC_OTHER'
    if k == '120':
        return {'12001': 'STAFF_REC', '12003': 'DEP_GIVEN', '12004': 'TRANSFER_ADV', '12005': 'LOAN_GIVEN', '12006': 'BANK_FEE_REC'}.get(m, 'REC_OTHER')
    if k in ('125', '170'): return 'INVEST'
    if k == '130': return 'INVENTORY'
    if k == '140':
        return {'14001': 'PREPAY_PROJ', '14002': 'PREPAY_PURCH', '14003': 'PREPAY_CAPPURCH', '14004': 'PREPAY_COMP', '14005': 'PREPAY_OTHER'}.get(
            m, 'PREPAY_COMP' if 'غرامت' in n else 'PREPAY_OTHER')
    if k in ('150', '160'):
        if ok == '710' and om in ('005', '007'): return 'NOTES_LT'
        if ok == '710' and om in ('011', '012', '013', '014', '016'): return 'PROPERTY_STOCK'
        if ok == '710' and om == '003': return 'BANK_BLOCKED'
        if ok == '670': return 'FIXED_ASSET'
        return 'FIXED_OTHER'
    if k == '210':
        if m in ('21014', '21015'): return 'PAY_CONTRACTOR'
        if m in ('21010', '21011'): return 'PAY_COMP'
        if ok == '810' and om == '001':
            if ot == '00005': return 'PAY_STATUTORY'
            if ot == '00006': return 'PAY_SALARYBANK'
            if ot in ('00100', '00101', '00001', '00007'): return 'INTER_REGION'
            if ot in ('00200', '00201', '00002'): return 'PAY_AFFIL'
        return 'PAY_OTHER'
    if k == '220':
        return {'22001': 'PAY_STAFF', '22005': 'TRANSFER_RECEIPTS', '22008': 'LOAN_INTERNAL', '22011': 'VAT_PAY'}.get(m, 'PAY_OTHER')
    if k == '225':
        return {'22501': 'DEP_PERF', '22502': 'DEP_PERF', '22503': 'DEP_PERF', '22504': 'DEP_INS', '22505': 'DEP_TENDER', '22506': 'DEP_TENDER'}.get(m, 'DEP_OTHER')
    if k == '230':
        return 'PRE_RECEIPT_NOTES' if om == '004' else 'PRE_RECEIPT'
    if k == '235':
        return 'LOAN_INTERNAL' if ok == '820' or (ok == '860' and om == '003') else 'LOAN_BANK'
    if k == '250': return 'BONDS'
    if k == '310': return 'EQUITY'
    if k.startswith('4'): return 'REV'
    if k.startswith('6'): return 'EXP'
    if k == '710': return 'CLEARING'
    if k in ('810', '820'): return 'MEMO'
    return 'UNKNOWN'

CAT_FA = {
 'BANK': 'موجودی بانک', 'IMPREST': 'تنخواه‌گردان', 'CASHBOX': 'صندوق', 'INTRANSIT': 'وجوه بین‌راهی', 'NOTES_REC': 'اسناد دریافتنی عملیاتی',
 'VAT_REC': 'ارزش افزوده (اعتبار/دریافتنی)', 'INTER_REGION': 'حساب جاری بین مناطق/مدیریت‌ها', 'REC_AFFIL': 'مطالبات از سازمان‌های وابسته',
 'REC_OTHER': 'سایر دریافتنی‌ها', 'STAFF_REC': 'مطالبات از کارکنان', 'DEP_GIVEN': 'سپرده‌ها و ودایع پرداختی', 'TRANSFER_ADV': 'پرداخت‌های انتقالی (علی‌الحساب)',
 'LOAN_GIVEN': 'تسهیلات پرداختی (صندوق ذخیره)', 'BANK_FEE_REC': 'حساب‌های هزینه بانکی', 'INVEST': 'سرمایه‌گذاری', 'INVENTORY': 'موجودی مواد و کالا',
 'PREPAY_PROJ': 'پیش‌پرداخت پروژه‌ها', 'PREPAY_PURCH': 'پیش‌پرداخت خرید کالا و خدمات', 'PREPAY_CAPPURCH': 'پیش‌پرداخت خریدهای سرمایه‌ای',
 'PREPAY_COMP': 'پیش‌پرداخت غرامت تملکات', 'PREPAY_OTHER': 'سایر پیش‌پرداخت‌ها', 'NOTES_LT': 'اسناد دریافتنی بلندمدت/واخواستی',
 'PROPERTY_STOCK': 'املاک و اراضی آماده واگذاری', 'BANK_BLOCKED': 'وجوه مسدودشده بانکی', 'FIXED_ASSET': 'دارایی ثابت (اموال)', 'FIXED_OTHER': 'سایر دارایی‌های غیرجاری',
 'PAY_CONTRACTOR': 'بدهی به پیمانکاران', 'PAY_COMP': 'غرامت ملکی پرداختنی', 'PAY_STATUTORY': 'کسورات قانونی پرداختنی', 'PAY_SALARYBANK': 'بانک‌های پرداخت‌کننده حقوق',
 'PAY_AFFIL': 'بدهی به سازمان‌ها و شرکت‌های وابسته', 'PAY_OTHER': 'سایر حساب‌های پرداختنی', 'PAY_STAFF': 'بدهی به کارکنان', 'TRANSFER_RECEIPTS': 'دریافت‌های انتقالی',
 'LOAN_INTERNAL': 'تسهیلات دریافتی درون‌سازمانی', 'VAT_PAY': 'مالیات و عوارض ارزش افزوده پرداختنی', 'DEP_PERF': 'سپرده حسن انجام کار', 'DEP_INS': 'سپرده بیمه پیمانکاران',
 'DEP_TENDER': 'سپرده شرکت در مناقصه/مزایده', 'DEP_OTHER': 'سایر سپرده‌های پرداختنی', 'PRE_RECEIPT_NOTES': 'پیش‌دریافت (طرف اسناد دریافتنی بلندمدت)',
 'PRE_RECEIPT': 'پیش‌دریافت‌ها', 'LOAN_BANK': 'تسهیلات دریافتی از بانک‌ها', 'BONDS': 'اوراق مشارکت', 'EQUITY': 'ارزش خالص', 'REV': 'درآمد', 'EXP': 'هزینه',
 'CLEARING': 'حساب رابط تمرکز وجوه', 'MEMO': 'حساب انتظامی', 'UNKNOWN': 'نامشخص (#N/A)'}

NATURE = {'1': 'دارایی', '2': 'بدهی', '3': 'ارزش خالص', '4': 'درآمد', '6': 'هزینه', '7': 'حساب رابط', '8': 'انتظامی'}

def has(t, pat): return re.search(pat, t) is not None

# ------------------------------------------------------------------ expense line event (by moin + text)
def expense_event(r, t, statement_doc):
    m = s(g(r, C_MOIN))
    k = s(g(r, C_KOL))
    if k == '610':
        if has(t, r'اضافه ?کار|تعطیل ?کاری'): return 'FE-46', 'معین 610 + «اضافه‌کار»'
        if has(t, r'ماموریت|کارانه|پاداش|حق التحقیق'): return 'FE-47', 'معین 610 + «مأموریت/کارانه/پاداش»'
        if has(t, r'عیدی|سنوات|مرخصی|پایان خدمت'): return 'FE-50', 'معین 610 + «عیدی/سنوات»'
        if has(t, r'کارگر|قانون کار|روزمزد'): return 'FE-45', 'معین 610 + «کارگر/قانون کار»'
        return 'FE-44', 'معین 610 جبران خدمات کارکنان'
    if k == '611':
        if m == '61101': return 'FE-47', 'معین 61101 مأموریت'
        if m == '61107': return 'FE-65', 'معین 61107 هزینه‌های بانکی (کارمزد)'
        if m == '61108': return 'FE-33', 'معین 61108 آب، برق و سوخت'
        if m == '61110': return 'FE-29', 'معین 61110 مطالعاتی و تحقیقاتی'
        if m == '61104':
            if has(t, r'خودرو|ماشین|وسایط|وسائط|وسایل نقلیه|موتور|لاستیک|باطری|قطعات|ناوگان'): return 'FE-39', 'معین 61104 + «خودرو/ماشین‌آلات»'
            if has(t, r'ترافیک|دوربین|چراغ راهنما|چراغهای راهنمایی|کنترلر'): return 'FE-42', 'معین 61104 + «تجهیزات ترافیکی»'
            if has(t, r'نرم ?افزار|سامانه|سرور|رایانه|شبکه|سخت ?افزار'): return 'FE-43', 'معین 61104 + «نرم‌افزار/رایانه»'
            if has(t, r'پمپ|ترانس|چیلر|دیزل|ژنراتور|تاسیسات برقی|تاسیسات مکانیکی|موتورخانه'): return 'FE-40', 'معین 61104 + «تأسیسات/پمپ»'
            if has(t, r'ساختمان|ابنیه|آسانسور|اداری|مستحدثات|تاسیسات'): return 'FE-41', 'معین 61104 + «ساختمان/ابنیه»'
            return ['FE-39', 'FE-40', 'FE-41', 'FE-42', 'FE-43'], 'معین 61104 نگهداری دارایی ثابت بدون نوع دارایی مشخص'
        if m == '61109':
            return purchase_event(t, 'FE-22', 'معین 61109 مواد و لوازم مصرف‌شدنی')
        if m == '61111':
            if has(t, r'وسایط|وسائط|وسایل نقلیه|ماشین|خودرو|جرثقیل|لودر|کمپرسی|تانکر|کرایه'): return 'FE-32', 'معین 61111 + «کرایه ماشین/وسیله»'
            if has(t, r'ساختمان|ملک|اماکن|اجاره|مستغلات|محل'): return 'FE-35', 'معین 61111 + «اجاره ملک»'
            return ['FE-32', 'FE-35'], 'معین 61111 اجاره و کرایه بدون موضوع مشخص'
        if m == '61103':
            if has(t, r'تلفن|اینترنت|پست|مخابرات|پهنای باند|فاکس|ارتباطات'): return 'FE-34', 'معین 61103 + «تلفن/پست/اینترنت»'
            if has(t, r'حمل|باربری|کرایه|وسایط|وسائط|وسایل نقلیه|ایاب'): return 'FE-32', 'معین 61103 + «حمل/کرایه»'
            return ['FE-32', 'FE-34'], 'معین 61103 حمل‌ونقل و ارتباطات بدون موضوع مشخص'
        if m == '61102':
            if has(t, r'مشاور|طراحی|نظارت|مطالعه|مطالعات|محتوا|راهبری'): return 'FE-29', 'معین 61102 + «مشاوره/طراحی/نظارت»'
            if has(t, r'آزمایش|معاینات|ژئوتکنیک|کنترل کیفیت'): return 'FE-30', 'معین 61102 + «آزمایشگاه/معاینات»'
            if has(t, r'حق الوکاله|وکیل|وکالت|داوری|کارشناس رسمی|کارشناسی|دادرسی|ثبت اسناد|حقوقی'): return 'FE-31', 'معین 61102 + «حقوقی/کارشناسی»'
            if has(t, r'باربری|حمل|جرثقیل|تانکر|لودر|کمپرسی'): return 'FE-32', 'معین 61102 + «حمل/ماشین‌آلات»'
            if has(t, r'پشتیبانی|نرم ?افزار|سامانه|سرور'): return 'FE-43', 'معین 61102 + «پشتیبانی نرم‌افزار»'
            if has(t, r'شهروکار|تامین نیرو|نیروی انسانی|نیروی شرکتی|حجمی|خرید خدمت'): return 'FE-45', 'معین 61102 + «تأمین نیرو/حجمی»'
            return 'GAP-11', 'معین 61102 حق‌الزحمه خدمات قراردادی عام'
        if m in ('61105', '61106'): return 'GAP-11', f'معین {m} چاپ/تشریفات'
        return None, 'معین 611 نامشخص'
    if k == '613':
        if m == '61301': return 'FE-69', 'معین 61301 اعتبارات بودجه شورا'
        return ['FE-47', 'FE-51', 'FE-69'], 'معین 61305 هدایا و پرداخت‌های تشویقی (ذی‌نفع نامشخص)'
    if k == '614':
        if m == '61401': return 'FE-48', 'معین 61401 بازنشستگی سهم شهرداری'
        if has(t, r'بیمه تکمیلی|بیمه عمر|درمان'): return 'FE-51', f'معین {m} + «بیمه تکمیلی/درمان»'
        return 'FE-51', f'معین {m} رفاهی کارکنان/بازنشستگان'
    if k == '615':
        if m == '61501': return 'FE-29', 'معین 61501 مطالعه برای احداث'
        if statement_doc: return 'GAP-01', 'معین 615 ساختمان و مستحدثات در سند محاسبه صورت‌وضعیت'
        ev, why = purchase_event(t, None, 'معین 615 ساختمان و مستحدثات')
        if ev: return ev, why
        return ['GAP-01', 'FE-24', 'GAP-11'], 'معین 615 عملیات عمرانی خارج از سند صورت‌وضعیت؛ نوع اجرا (پیمانی/امانی/خرید) نامشخص'
    if k == '616':
        if m == '61602': return 'FE-23', 'معین 61602 تجهیزات اداری و رایانه‌ای'
        if m == '61603': return 'FE-28', 'معین 61603 تجهیزات حفاظتی و ارتباطی'
        if has(t, r'آتش|ایمنی|ترافیک|دوربین|علائم'): return 'FE-28', f'معین {m} + «ایمنی/ترافیکی/آتش‌نشانی»'
        if has(t, r'اداری|رایانه|اثاثیه|میز|صندلی'): return 'FE-23', f'معین {m} + «اداری»'
        return ['FE-23', 'FE-28'], f'معین {m} ماشین‌آلات و تجهیزات (نوع نامشخص)'
    if k == '617': return 'FE-43', 'معین 61701 سامانه‌های نرم‌افزاری'
    if k == '618': return 'FE-53', 'معین 61801 تملکات (زمین)'
    if k == '619': return 'FE-54', 'معین 61901 حقوق و امتیازات'
    if k == '620':
        if has(t, r'(^| )سود|کارمزد'): return 'FE-65', 'معین 62001 + «سود/کارمزد»'
        if has(t, r'(^| )اصل'): return 'FE-64', 'معین 62001 + «اصل»'
        return ['FE-64', 'FE-65'], 'معین 62001 بازپرداخت اصل و سود (تفکیک نشده)'
    if k == '630': return 'FE-69', f'معین {m} یارانه/پرداخت انتقالی'
    if k == '650':
        if m == '65101': return 'FE-50', 'معین 65101 پاداش پایان خدمت'
        return 'FE-67', 'معین 65001 دیون با محل'
    if k == '652': return 'FE-67', 'کل 652 تعهدات انتقالی سنواتی'
    return None, 'هزینه نامشخص'

def purchase_event(t, default, why):
    if has(t, r'قیر|آسفالت|بیندر|توپکا'): return 'FE-25', why + ' + «قیر/آسفالت»'
    if has(t, r'نهال|درخت|گل |گلکاری|چمن|خاک|بذر|کود'): return 'FE-26', why + ' + «نهال/گل/خاک»'
    if has(t, r'روشنایی|چراغ|لامپ|کابل|پروژکتور|برقی|الکتریکی'): return 'FE-27', why + ' + «روشنایی/برقی»'
    if has(t, r'ترافیک|علائم|تابلو|گاردریل|سرعت گیر|خط کشی|دوربین|آتش|ایمنی'): return 'FE-28', why + ' + «ترافیکی/ایمنی»'
    if has(t, r'مصالح|سیمان|شن|ماسه|میلگرد|آهن|لوله|بلوک|سنگ|موزاییک|جدول|کانیو|بتن'): return 'FE-24', why + ' + «مصالح»'
    return default, why

def revenue_event(r, t):
    m = s(g(r, C_MOIN))
    if has(t, r'کمیسیون ماده (100|صد|77)|ماده 100|ماده 77|جرائم کمیسیون'): return 'FE-61', 'عنوان حساب درآمد «جرائم کمیسیون ماده ۱۰۰/۷۷»'
    if has(t, r'اجاره|کرایه|غرفه|بهاء خدمات|بهای خدمات'): return 'FE-60', 'عنوان حساب درآمد «اجاره/بهای خدمات»'
    if has(t, r'زیربنا|تراکم|پروانه|پذیره|تفکیک|بالکن|پیش آمدگی|کسری پارکینگ|تغییر کاربری|ارزش افزوده ناشی|حذف پارکینگ|احداث|ساختمان|حصارکشی|ماده 101'):
        return 'FE-57', 'عنوان حساب درآمد «زیربنا/تراکم/پروانه»'
    if has(t, r'نوسازی|پسماند|خودرو|سالیانه'): return 'FE-58', 'عنوان حساب درآمد «نوسازی/پسماند/خودرو»'
    if has(t, r'کسب|پیشه|تابلو|ارزش افزوده|کالا و خدمات'): return 'FE-59', 'عنوان حساب درآمد «کسب‌وپیشه/ارزش افزوده»'
    if has(t, r'خسارت|جریمه|جرائم'): return 'GAP-04', 'عنوان حساب درآمد «خسارت/جریمه» (غیر از کمیسیون ماده ۱۰۰/۷۷)'
    if m == '41006': return 'FE-57', 'معین 41006 عوارض زیربنا'
    if has(t, r'ضبط'): return 'FE-19', 'عنوان حساب «ضبط سپرده/ضمانت»'
    if m in ('41101', '41201', '41204', '41301') or s(g(r, C_KOL)) in ('411', '412'):
        return 'FE-60', f'معین {m} بهای خدمات/کرایه اماکن'
    if m in ('41601', '41701') or s(g(r, C_KOL)) in ('416', '417'): return 'GAP-09', f'معین {m} فروش اموال'
    return 'GAP-04', f'معین {m or s(g(r, C_KOL))} درآمد فاقد رویداد اختصاصی'

def deposit_text_event(t, credit):
    if has(t, r'حسن انجام'): return ('FE-07' if credit else 'FE-08')
    if has(t, r'بیمه'): return ('FE-09' if credit else 'FE-10')
    if has(t, r'مناقصه|مزایده'): return ('FE-17' if credit else 'FE-18')
    return None

def guarantee_event(t, receive):
    if has(t, r'مناقصه|مزایده|شرکت در'): return 'FE-13' if receive else 'FE-14'
    if has(t, r'انجام تعهدات|حسن انجام|قرارداد|پیش پرداخت'): return 'FE-15' if receive else 'FE-16'
    return ['FE-13', 'FE-15'] if receive else ['FE-14', 'FE-16']

CLOSE_DESC = re.compile(r'اختتامیه|افتتاحیه|بستن حساب')
WITHHOLD_EVENTS = {'FE-02', 'FE-07', 'FE-09', 'FE-11', 'FE-12', 'FE-48', 'FE-49'}

def line_rule(r, cat, side, dtype, ctx):
    """Return (event|list|None, kind, role, method, basis)."""
    t = norm(' '.join(s(g(r, i)) for i in (C_TAFT, C_JOZT)))
    tn = norm(s(g(r, C_MOINT)) + ' ' + t)
    desc = norm(g(r, C_DESC))
    D = side == 'D'
    stmt = 'صورت وضعیت' in dtype
    acct = f"{s(g(r, C_KOL))}/{s(g(r, C_MOIN))} {s(g(r, C_MOINN))}"
    # ---- document-type overrides: closing / opening / correction
    if 'پایان دوره مالی' in dtype or CLOSE_DESC.search(desc):
        what = 'افتتاحیه (انتقال مانده)' if 'افتتاحیه' in desc else ('اختتامیه/بستن حساب' if desc and desc != 'عادی' else 'عملیات پایان دوره مالی')
        return 'FE-70', 'DRIVER', f'بستن/افتتاح حساب — {what}', 'قاعده نوع سند/شرح سند', f'نوع سند «{dtype}»؛ شرح «{desc}»'
    # ---- by category
    if cat == 'CLEARING':
        return 'FE-68', 'DRIVER', 'حساب رابط تمرکز وجوه (انتقال بین حساب‌ها/مناطق)', 'قاعده حساب', f'کل 710 حساب رابط: {s(g(r, C_MOINT))}'
    if cat == 'BANK':
        if 'جابجایی وجه بین حسابهای بانکی' in dtype or 'جابجایی حساب' in dtype:
            return 'FE-68', 'DRIVER', 'جابه‌جایی وجه بانکی', 'قاعده نوع سند', f'نوع سند «{dtype}»'
        return None, 'COMPONENT', 'دریافت وجه — طرف بانکی' if D else 'پرداخت وجه — طرف بانکی', 'وراثت از رویداد سند', f'حساب بانک {acct}'
    if cat in ('CASHBOX', 'INTRANSIT', 'BANK_BLOCKED', 'BANK_FEE_REC'):
        if cat == 'BANK_FEE_REC': return 'FE-65', 'DRIVER', 'هزینه/کارمزد بانکی', 'قاعده حساب', acct
        return None, 'COMPONENT', 'طرف نقدی (صندوق/بین‌راهی/مسدود)', 'وراثت از رویداد سند', acct
    if cat == 'IMPREST':
        if D: return 'FE-37', 'DRIVER', 'شارژ تنخواه‌گردان', 'قاعده حساب و جهت', f'بدهکار معین 11009 تنخواه‌گردان ({s(g(r, C_TAFT))})'
        return 'FE-38', 'DRIVER', 'تسویه تنخواه به هزینه', 'قاعده حساب و جهت', f'بستانکار معین 11009 تنخواه‌گردان ({s(g(r, C_TAFT))})'
    if cat == 'NOTES_REC':
        if ctx['has_rev_c'] and D: return None, 'COMPONENT', 'دریافت چک/سند اقساطی در قبال درآمد', 'وراثت از رویداد سند', acct
        if ctx['has_rev_d'] and not D: return None, 'COMPONENT', 'ابطال/استرداد سند دریافتنی در قبال برگشت درآمد', 'وراثت از رویداد سند', acct
        return 'GAP-03', 'DRIVER', ('وصول وجه سند دریافتنی' if ctx['has_bank_d'] and not D else 'جابه‌جایی/واخواست سند دریافتنی'), 'قاعده حساب', acct
    if cat in ('NOTES_LT', 'PRE_RECEIPT_NOTES'):
        if ctx['has_rev_c'] or ctx['has_rev_d']: return None, 'COMPONENT', 'سند دریافتنی بلندمدت/طرف آن در قبال درآمد', 'وراثت از رویداد سند', acct
        return 'GAP-03', 'DRIVER', 'جابه‌جایی سررسید/واخواست اسناد دریافتنی', 'قاعده حساب', acct
    if cat == 'VAT_REC' or cat == 'VAT_PAY':
        return 'FE-11', 'WITHHOLD', 'مالیات بر ارزش افزوده', 'قاعده حساب', acct + f' / {s(g(r, C_TAFT))}'
    if cat == 'PAY_STATUTORY':
        payroll = 'حقوق' in dtype or ctx['has_610']
        if payroll:
            if has(tn, r'بیمه|تامین اجتماعی|بازنشستگی|صندوق'): return 'FE-48', 'WITHHOLD', 'کسور بیمه کارکنان', 'قاعده حساب + سند حقوق', acct + f' / {s(g(r, C_TAFT))}'
            if has(tn, r'مالیات|دارائی|دارایی'): return 'FE-49', 'WITHHOLD', 'کسور مالیات حقوق', 'قاعده حساب + سند حقوق', acct + f' / {s(g(r, C_TAFT))}'
            return ['FE-48', 'FE-49'], 'WITHHOLD', 'کسور قانونی حقوق (نوع نامشخص)', 'قاعده حساب + سند حقوق', acct
        if has(tn, r'بیمه|تامین اجتماعی'): return 'FE-09', 'WITHHOLD', 'کسور بیمه (قانونی)', 'قاعده حساب', acct + f' / {s(g(r, C_TAFT))}'
        return 'FE-11', 'WITHHOLD', 'کسور مالیات/ارزش افزوده' + (' — واریز به سازمان' if D else ''), 'قاعده حساب', acct + f' / {s(g(r, C_TAFT))}'
    if cat == 'PAY_SALARYBANK' or cat == 'PAY_STAFF':
        return None, 'COMPONENT', 'بدهی حقوق به کارکنان/بانک عامل', 'وراثت از رویداد سند', acct
    if cat in ('INTER_REGION',):
        if ctx.get('cash_only'):
            return 'FE-68', 'DRIVER', 'انتقال وجه بین مناطق/مدیریت‌ها (حساب جاری)', 'قاعده حساب + سند صرفاً نقدی/بین‌منطقه‌ای', acct + f' / {s(g(r, C_TAFT))}'
        return None, 'COMPONENT', 'حساب جاری بین مناطق/مدیریت‌ها', 'وراثت از رویداد سند', acct + f' / {s(g(r, C_TAFT))}'
    if cat in ('REC_AFFIL', 'REC_OTHER', 'TRANSFER_RECEIPTS', 'DEP_GIVEN', 'FIXED_OTHER', 'PRE_RECEIPT'):
        return None, 'COMPONENT', CAT_FA[cat], 'وراثت از رویداد سند', acct + f' / {s(g(r, C_TAFT))}'
    if cat in ('PAY_AFFIL', 'PAY_OTHER'):
        if D and dtype.startswith('پیش پرداخت') and ctx['has_bank_c']:
            return 'GAP-07', 'DRIVER', 'پرداخت علی‌الحساب به طرف حساب (بدهکار کردن حساب پرداختنی)', 'قاعده حساب + نوع سند پیش‌پرداخت و علی‌الحساب', acct + f' / {s(g(r, C_TAFT))}'
        if D and ctx['has_bank_c'] and not ctx['drivers_other']:
            return 'GAP-10', 'DRIVER', 'تسویه بدهی ثبت‌شده — طرف بدهکار', 'قاعده حساب + سند پرداخت', acct + f' / {s(g(r, C_TAFT))}'
        return None, 'COMPONENT', ('بدهی ثبت‌شده (طرف بستانکار رویداد)' if not D else 'کاهش بدهی (طرف بدهکار)'), 'وراثت از رویداد سند', acct + f' / {s(g(r, C_TAFT))}'
    if cat == 'PAY_CONTRACTOR':
        if not D:
            if stmt: return None, 'COMPONENT', 'خالص بدهی پیمانکار بابت صورت‌وضعیت', 'وراثت از رویداد سند', acct
            return None, 'COMPONENT', 'بدهی پیمانکار (طرف بستانکار)', 'وراثت از رویداد سند', acct
        if dtype.startswith('پیش پرداخت'):
            return 'FE-01', 'DRIVER', 'پرداخت علی‌الحساب پیمانکار (بدهکار کردن حساب پیمانکار)', 'قاعده حساب + نوع سند پیش‌پرداخت و علی‌الحساب', acct + f' / {s(g(r, C_TAFT))[:60]}'
        if ctx['has_bank_c'] or 'پرداخت' in dtype:
            return 'FE-03', 'DRIVER', 'پرداخت مطالبات صورت‌وضعیت پیمانکار', 'قاعده حساب + سند پرداخت', acct + f' / {s(g(r, C_TAFT))[:60]}'
        return None, 'COMPONENT', 'کاهش بدهی پیمانکار (تهاتر/کسور)', 'وراثت از رویداد سند', acct
    if cat == 'PAY_COMP' or cat == 'PREPAY_COMP':
        role = ('پیش‌پرداخت غرامت تملک' if cat == 'PREPAY_COMP' and D else 'تسویه پیش‌پرداخت غرامت' if cat == 'PREPAY_COMP'
                else 'شناسایی غرامت ملکی پرداختنی' if not D else 'پرداخت غرامت ملکی')
        return 'FE-53', 'DRIVER', role, 'قاعده حساب', acct + f' / {s(g(r, C_TAFT))}'
    if cat == 'PREPAY_PROJ':
        if D: return 'FE-01', 'DRIVER', 'پرداخت پیش‌پرداخت/علی‌الحساب پیمانکار', 'قاعده حساب و جهت', acct + f' / {s(g(r, C_TAFT))}'
        return 'FE-02', 'WITHHOLD', 'استهلاک/کسر پیش‌پرداخت', 'قاعده حساب و جهت', acct + f' / {s(g(r, C_TAFT))}'
    if cat in ('PREPAY_PURCH', 'PREPAY_CAPPURCH', 'PREPAY_OTHER'):
        if cat == 'PREPAY_OTHER' and has(tn, r'حقوق|کارکنان|پرسنل'): return 'GAP-05', 'DRIVER', 'پیش‌پرداخت حقوق کارکنان', 'قاعده حساب + متن', acct
        return 'GAP-07', 'DRIVER', ('پرداخت پیش‌پرداخت/علی‌الحساب خرید' if D else 'تسویه پیش‌پرداخت خرید'), 'قاعده حساب و جهت', acct + f' / {s(g(r, C_TAFT))}'
    if cat == 'STAFF_REC':
        return 'GAP-05', 'DRIVER', ('پرداخت مساعده/ایجاد بدهی کارکنان' if D else 'کسر/تسویه بدهی کارکنان'), 'قاعده حساب و جهت', acct
    if cat == 'TRANSFER_ADV':
        return 'FE-69', 'DRIVER', ('علی‌الحساب پرداخت انتقالی به سازمان' if D else 'تسویه پرداخت انتقالی'), 'قاعده حساب', acct + f' / {s(g(r, C_TAFT))}'
    if cat == 'LOAN_GIVEN' or cat == 'LOAN_INTERNAL':
        return 'GAP-06', 'DRIVER', ('اعطا/بازپرداخت تسهیلات درون‌سازمانی'), 'قاعده حساب', acct + f' / {s(g(r, C_TAFT))}'
    if cat == 'LOAN_BANK':
        return ('FE-63', 'DRIVER', 'دریافت تسهیلات بانکی', 'قاعده حساب و جهت', acct + f' / {s(g(r, C_TAFT))}') if not D else \
               ('FE-64', 'DRIVER', 'بازپرداخت اصل تسهیلات', 'قاعده حساب و جهت', acct + f' / {s(g(r, C_TAFT))}')
    if cat == 'BONDS': return 'FE-66', 'DRIVER', 'اوراق مشارکت', 'قاعده حساب', acct
    if cat == 'EQUITY': return 'FE-70', 'DRIVER', 'ارزش خالص (بستن/انتقال مانده)', 'قاعده حساب', acct
    if cat == 'INVEST': return 'GAP-12', 'DRIVER', 'سرمایه‌گذاری/مشارکت', 'قاعده حساب', acct + f' / {s(g(r, C_TAFT))}'
    if cat == 'INVENTORY':
        if D:
            ev, why = purchase_event(tn, 'FE-22', 'رسید کالا به انبار')
            if ctx['has_inv_c'] and not ctx['has_pay_c'] and not ctx['has_bank_c']:
                return 'GAP-08', 'DRIVER', 'جابه‌جایی کالا بین انبارها/رسید داخلی', 'قاعده حساب', acct + f' / {s(g(r, C_TAFT))}'
            return ev, 'DRIVER', 'خرید و رسید کالا به انبار', why, acct + f' / {s(g(r, C_TAFT))}'
        return 'GAP-08', 'DRIVER', 'حواله/خروج کالا از انبار', 'قاعده حساب و جهت', acct + f' / {s(g(r, C_TAFT))}'
    if cat == 'PROPERTY_STOCK':
        if 'تملک' in dtype and D: return 'FE-53', 'DRIVER', 'تملک ملک', 'قاعده نوع سند', acct
        if ('واگذاری' in dtype or 'استرداد اموال' in dtype) and not D: return 'GAP-09', 'DRIVER', 'واگذاری ملک', 'قاعده نوع سند', acct
        return None, 'COMPONENT', 'املاک آماده واگذاری', 'وراثت از رویداد سند', acct + f' / {s(g(r, C_TAFT))}'
    if cat == 'FIXED_ASSET':
        if D:
            ev, why = purchase_event(tn, 'FE-23', 'ثبت دارایی ثابت')
            return ev, 'DRIVER', 'ثبت خرید/تحصیل دارایی ثابت', why, acct + f' / {s(g(r, C_TAFT))}'
        return 'GAP-09', 'DRIVER', 'خروج/واگذاری دارایی ثابت', 'قاعده حساب و جهت', acct
    if cat in ('DEP_PERF', 'DEP_INS', 'DEP_TENDER', 'DEP_OTHER'):
        credit = not D
        if not credit and ctx['has_rev415_c']: return 'FE-19', 'DRIVER', 'ضبط سپرده به نفع شهرداری', 'قاعده حساب + درآمد ضبط سپرده در سند', acct
        ev = {'DEP_PERF': ('FE-07', 'FE-08'), 'DEP_INS': ('FE-09', 'FE-10'), 'DEP_TENDER': ('FE-17', 'FE-18')}.get(cat)
        ev = (ev[0] if credit else ev[1]) if ev else deposit_text_event(tn, credit)
        if ev is None: return (['FE-07', 'FE-17'] if credit else ['FE-08', 'FE-18']), 'DRIVER', 'سایر سپرده‌ها (نوع نامشخص)', 'قاعده حساب', acct + f' / {s(g(r, C_TAFT))}'
        kind = 'WITHHOLD' if ev in WITHHOLD_EVENTS else 'DRIVER'
        role = {'FE-07': 'کسر سپرده حسن انجام کار', 'FE-08': 'استرداد سپرده حسن انجام کار', 'FE-09': 'کسر سپرده بیمه', 'FE-10': 'استرداد سپرده بیمه',
                'FE-17': 'دریافت سپرده مناقصه/مزایده', 'FE-18': 'استرداد سپرده مناقصه/مزایده'}[ev]
        return ev, kind, role, 'قاعده حساب و جهت', acct
    if cat == 'MEMO':
        ok = s(g(r, C_OKOL)); om = s(g(r, C_OMOIN)); ot = s(g(r, C_OTAF))
        if om == '001' and ot == '00002':   # guarantees of others held by municipality
            receive = (D if ok == '720' else not D)
            return guarantee_event(tn + ' ' + desc, receive), 'DRIVER', ('دریافت ضمانت‌نامه/سند تضمینی' if receive else 'استرداد ضمانت‌نامه/سند تضمینی'), 'قاعده حساب انتظامی و جهت', acct + f' / {s(g(r, C_TAFT))}'
        return None, 'COMPONENT', 'حساب انتظامی (ثبت یادداشتی)', 'وراثت از رویداد سند', acct + f' / {s(g(r, C_TAFT))}'
    if cat == 'REV':
        ev, why = revenue_event(r, tn)
        if D:
            if 'استرداد' in dtype or ctx['has_bank_c'] or ctx['has_notes_c']:
                return 'FE-62', 'DRIVER', 'استرداد/برگشت درآمد', 'قاعده جهت + نوع سند', why + f'؛ نوع سند «{dtype}»'
            return 'FE-70', 'DRIVER', 'اصلاح/برگشت درآمد', 'قاعده جهت + نوع سند', why + f'؛ نوع سند «{dtype}»'
        return ev, 'DRIVER', 'وصول/شناسایی درآمد', why, acct + f' / {s(g(r, C_TAFT))[:60]}'
    if cat == 'EXP':
        if not D:
            if 'برگشت از هزینه' in dtype or 'اصلاحی' in dtype: return 'FE-70', 'DRIVER', 'برگشت/اصلاح هزینه', 'قاعده جهت + نوع سند', acct
            return None, 'COMPONENT', 'کسر/برگشت هزینه (طرف بستانکار)', 'وراثت از رویداد سند', acct
        ev, why = expense_event(r, tn, stmt)
        if stmt and ev not in ('FE-67', 'GAP-01'):
            why = f'سند محاسبه صورت‌وضعیت؛ ماهیت هزینه: {ev if isinstance(ev, str) else "/".join(ev or [])} ({why})'
            ev = 'GAP-01'
        role = 'ثبت کارکرد صورت‌وضعیت (هزینه/سرمایه‌ای)' if ev == 'GAP-01' else ('شناسایی هزینه / مخارج سرمایه‌ای' if s(g(r, C_KOL)) != '652' else 'شناسایی/تسویه تعهد سنوات قبل')
        return ev, 'DRIVER', role, 'قاعده معین + متن حساب', why + f' | {acct}'
    return None, 'COMPONENT', CAT_FA.get(cat, cat), 'وراثت از رویداد سند', acct

# ------------------------------------------------------------------ dimension applicability per event (proposals)
R_, C_, O_, N_, U_ = 'REQUIRED_CANDIDATE', 'CONDITIONAL_CANDIDATE', 'OPTIONAL_CANDIDATE', 'NOT_APPLICABLE_CANDIDATE', 'UNKNOWN'
# cc, contract, bank, project, person, org
def dims(ev):
    n = int(ev[3:]) if ev.startswith('FE-') else None
    if ev == 'GAP-01': return (R_, R_, N_, C_, R_, O_)
    if ev in ('GAP-02',): return (N_, N_, N_, N_, C_, O_)
    if ev in ('GAP-03',): return (N_, N_, C_, N_, C_, O_)
    if ev in ('GAP-04',): return (N_, N_, R_, N_, C_, O_)
    if ev == 'GAP-05': return (C_, N_, C_, N_, R_, O_)
    if ev == 'GAP-06': return (N_, C_, R_, N_, R_, C_)
    if ev == 'GAP-07': return (C_, C_, C_, C_, R_, O_)
    if ev == 'GAP-08': return (R_, N_, N_, C_, O_, O_)
    if ev == 'GAP-09': return (N_, C_, C_, N_, R_, O_)
    if ev == 'GAP-10': return (C_, C_, R_, C_, R_, O_)
    if ev == 'GAP-11': return (R_, C_, C_, C_, R_, O_)
    if ev == 'GAP-12': return (N_, C_, C_, C_, R_, O_)
    if n in (1, 3, 4, 5, 6): return (R_ if n != 1 else C_, R_, R_, C_, R_, O_)
    if n in (2, 20, 21): return (C_, R_, N_, C_, R_, O_)
    if n in (7, 9, 11, 12): return (C_, R_ if n != 11 else C_, N_, C_, R_, O_)
    if n in (8, 10): return (C_, R_, R_, C_, R_, O_)
    if n in (13, 14, 15, 16): return (N_, C_ if n in (13, 14) else R_, C_, C_, R_, O_)
    if n in (17, 18, 19): return (N_, C_, C_ if n != 19 else N_, N_, R_, O_)
    if 22 <= n <= 36 or 39 <= n <= 43: return (R_, C_, C_, C_, R_, O_)
    if n == 37: return (C_, N_, R_, N_, R_, R_)
    if n == 38: return (R_, N_, N_, C_, R_, R_)
    if 44 <= n <= 52: return (R_, C_ if n == 45 else N_, C_, N_, C_, R_)
    if 53 <= n <= 56: return (R_, C_, C_, R_, R_, O_)
    if 57 <= n <= 61: return (N_, C_ if n == 60 else N_, R_, N_, C_, O_)
    if n == 62: return (N_, N_, C_, N_, R_, O_)
    if n in (63, 64, 65): return (N_, R_, R_, N_, R_, O_)
    if n == 66: return (N_, C_, R_, C_, R_, O_)
    if n == 67: return (C_, C_, C_, C_, R_, O_)
    if n == 68: return (N_, N_, R_, N_, N_, C_)
    if n == 69: return (R_, C_, C_, C_, R_, O_)
    if n == 70: return (C_, C_, C_, C_, C_, C_)
    return (U_,) * 6

# events whose execution in the same document moves cash (bank expected when paid in the same document)
CASH_EVENTS = {'FE-01', 'FE-03', 'FE-04', 'FE-05', 'FE-06', 'FE-08', 'FE-10', 'FE-18', 'FE-37', 'FE-44', 'FE-45', 'FE-57', 'FE-58', 'FE-59',
               'FE-60', 'FE-61', 'FE-62', 'FE-63', 'FE-64', 'FE-65', 'FE-66', 'FE-68', 'GAP-04', 'GAP-10'}

# ------------------------------------------------------------------ contract / bank evidence
FA_DIG = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')
RX_CONTRACT = [
    re.compile(r'قرارداد(?:\s*(?:شماره|ش|به شماره|بشماره|شمار))?\s*[:.]?\s*([0-9]+(?:\s*/\s*[0-9]+){1,3})'),
    re.compile(r'(?:^|[^\w])ق\s*\.?\s*([0-9]{1,4}\s*/\s*[0-9]{1,6}(?:\s*/\s*[0-9]+)?)'),
    re.compile(r'(?:شماره|ش)\s*([0-9]{1,3}/[0-9]{1,3}/[0-9]{1,5})'),
]
RX_CONTRACT_WORD = re.compile(r'قرارداد|پیمان(?!کار)')

def contract_in(text):
    t = (text or '').translate(FA_DIG)
    for rx in RX_CONTRACT:
        m = rx.search(t)
        if m: return re.sub(r'\s+', '', m.group(1))
    return None

RX_ACCNO = re.compile(r'([0-9][0-9\-/\.]{5,}[0-9])')
def bank_account(r):
    t = s(g(r, C_JOZT)); o = s(g(r, C_TAFT)); n = s(g(r, C_MOINT))
    m = RX_ACCNO.search(t.translate(FA_DIG))
    bank = o if 'بانک' in o or 'بانك' in o else n
    return (f'{bank} | {t}' if t and t != 'NULL' else bank), (m.group(1) if m else None)
