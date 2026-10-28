"""Phase 2 — cost-center reconciliation (PROPOSED layer).

Reuse order (mandate §7): existing municipality cost center (cc_master.json = v3 baseline + CC-109 addendum, itself only 'PROPOSED')
→ MULTIPLE_CC_CANDIDATES → NEW_CC_CANDIDATE (provisional namespace TTCC-P-xx) → INSUFFICIENT_INFORMATION.
No approved authority exists for any crosswalk, therefore EXACT_EXISTING_CC and VALIDATED_EXISTING_CC are never assigned (count = 0 by
construction and reported as such).  The SOURCE activity code (CodeMarkaz) is evidence only and is never equated to a CC ID.
"""
import sqlite3, re, sys, os, json, collections
sys.path.insert(0, os.path.dirname(__file__))
from common import *
from rules import *

CC = json.load(open(f'{ROOT}/cc_master.json', encoding='utf8'))

# ----------------------------------------------------------------------------------------------- provisional new CC candidates
NEW_CC = {
 'TTCC-P-01': dict(title='ساماندهی، صدور مجوز و نظارت بر ناوگان و شرکت‌های حمل‌ونقل درون‌شهری (تاکسیرانی)', domain='حمل ونقل، ترافیک و مهندسی عبور و مرور', orgs='Taxi',
                  definition='فعالیت‌های صدور/تمدید/تعویض پروانه و مجوز تاکسیرانی، رتبه‌بندی و نظارت بر شرکت‌های حمل‌ونقل، بازرسی ناوگان، رسیدگی به تخلفات و شکایات و بایگانی پرونده ناوگان',
                  why_existing_insufficient='CC-406 «تأمین، نوسازی و حمایت از ناوگان» تأمین/حمایت ناوگان را می‌پوشاند نه تنظیم‌گری و صدور مجوز؛ ممیزی خدمات ۱۴۰۵ نیز ۱۰ خدمت مجوز/ساماندهی تاکسی را «فاقد مرکز / نیازمند بررسی کارگروه» ثبت کرده است',
                  alternatives='CC-406; CC-1502; CC-1305', owner='سازمان تاکسیرانی', overlap='CC-406 (حمایت ناوگان)؛ CC-1502 (شکایات مردمی)'),
 'TTCC-P-02': dict(title='حمل‌ونقل ویژه دانش‌آموزی و معلولین (سرویس مدارس، ایاب‌وذهاب دانش‌آموزان استثنایی، خودروهای ویژه)', domain='حمل ونقل، ترافیک و مهندسی عبور و مرور', orgs='Taxi',
                  definition='مدیریت سامانه سرویس مدارس (سفیر مهر)، نظارت بر شرکت‌های ارائه‌دهنده و پرداخت اعتبارات مصرف‌معین ایاب‌وذهاب دانش‌آموزان استثنایی و ون‌های ویژه معلولین',
                  why_existing_insufficient='«خدمات تاکسیرانی و سرویس مدارس» در ممیزی ۱۴۰۵ به CC-406 نگاشت شده، اما جریان مالی آن عاملیتی (پیش‌دریافت امانی/پرداخت به شرکت‌ها) و منبع تأمین مصرف‌معین دارد و با حمایت از ناوگان هم‌ماهیت نیست',
                  alternatives='CC-406; CC-904', owner='سازمان تاکسیرانی', overlap='CC-406؛ CC-904 (خدمات اجتماعی)'),
 'TTCC-P-03': dict(title='مدیریت، بهره‌برداری و اجاره‌دهی پایانه‌های مسافربری برون‌شهری (غرفات، عوارض، شرکت‌های مسافربری)', domain='حمل ونقل، ترافیک و مهندسی عبور و مرور', orgs='Terminals',
                  definition='اداره پایانه‌ها شامل واگذاری و اجاره غرفات و دفاتر، دریافت عوارض شرکت‌های مسافربری، صدور مجوز فعالیت در پایانه و خدمات رفاهی مسافران',
                  why_existing_insufficient='CC-403 «پایانه‌ها و ایستگاه‌های اتوبوس و BRT» زیرساخت/ایستگاه را می‌پوشاند؛ ممیزی ۱۴۰۵ «مدیریت پایانه‌های مسافربری برون‌شهری»، «صدور مجوز در پایانه» و «خدمات رفاهی در پایانه‌ها» را بدون مرکز و نیازمند بررسی ثبت کرده است',
                  alternatives='CC-403; CC-1201; CC-1301', owner='سازمان پایانه‌های مسافربری', overlap='CC-403؛ CC-1201 (وصول درآمد)؛ CC-1301 (حقوق)'),
}

# ----------------------------------------------------------------------------------------------- source activity (CodeMarkaz) crosswalk — Taxi
# code -> (activity_id, activity title, kind, [primary CC], [alt CCs], conf, note)
MZ = {
 '001': ('ACT-TX-01', 'تدوین آیین‌نامه و دستورالعمل‌های ناوگان', 'NEW', 'TTCC-P-01', [], 'MEDIUM', ''),
 '002': ('ACT-TX-02', 'تدوین آیین‌نامه رتبه‌بندی شرکت‌های حمل‌ونقل درون‌شهری', 'NEW', 'TTCC-P-01', [], 'MEDIUM', ''),
 '007': ('ACT-TX-03', 'جلسات هیئت مدیره و کمیته سوخت/بانک‌های عامل', 'NEW', 'TTCC-P-01', ['CC-1601'], 'LOW', 'مدیریتی؛ جایگزین CC-1601'),
 '010': ('ACT-TX-04', 'نشست با سازمان‌های تاکسیرانی کشور و نمایشگاه', 'OLD', 'CC-1503', ['TTCC-P-01'], 'LOW', 'تشریفات/مناسبت‌های رسمی'),
 '013': ('ACT-TX-05', 'کمیته امور شرکت‌های حمل‌ونقل', 'NEW', 'TTCC-P-01', [], 'MEDIUM', ''),
 '027': ('ACT-TX-06', 'اجرای نرم‌افزار جامع تاکسیرانی', 'OLD', 'CC-1101', ['TTCC-P-01'], 'MEDIUM', 'نرم‌افزار تخصصی حوزه؛ مالکیت مرکز هزینه نیازمند تصمیم'),
 '030': ('ACT-TX-06', 'اجرای نرم‌افزار جامع تاکسیرانی', 'OLD', 'CC-1101', ['TTCC-P-01'], 'MEDIUM', ''),
 '033': ('ACT-TX-07', 'اطلاع‌رسانی از طریق پنل پیامک', 'MULTI', 'CC-1103', ['CC-1501', 'TTCC-P-01'], 'LOW', 'اطلاع‌رسانی به ناوگان/شهروندان'),
 '037': ('ACT-TX-08', 'خرید/پشتیبانی سخت‌افزار و نرم‌افزار سازمان', 'OLD', 'CC-1102', [], 'MEDIUM', ''),
 '115': ('ACT-TX-08', 'خرید/پشتیبانی سخت‌افزار و نرم‌افزار سازمان', 'OLD', 'CC-1102', [], 'MEDIUM', ''),
 '046': ('ACT-TX-09', 'تعمیر و نگهداری خودروهای بازرسی و اداری', 'OLD', 'CC-1402', ['TTCC-P-01'], 'MEDIUM', 'خودروهای بازرسی ابزار تنظیم‌گری‌اند؛ مالکیت نیازمند تصمیم'),
 '054': ('ACT-TX-10', 'چاپ دفترچه نرخ کرایه و برچسب بازرسی', 'NEW', 'TTCC-P-01', [], 'MEDIUM', ''),
 '055': ('ACT-TX-09', 'کرایه خودروهای استیجاری و بازرسی', 'OLD', 'CC-1402', ['TTCC-P-01'], 'MEDIUM', ''),
 '069': ('ACT-TX-11', 'ساخت کلیپ و بسته تبلیغاتی/فرهنگی', 'OLD', 'CC-1501', [], 'MEDIUM', ''),
 '082': ('ACT-TX-12', 'خرید لباس بازرسان و پرسنل اداری', 'OLD', 'CC-1403', ['TTCC-P-01'], 'LOW', ''),
 '084': ('ACT-TX-13', 'ورزش و اعزام تیم‌های ورزشی', 'OLD', 'CC-1302', [], 'MEDIUM', 'رفاه/ورزش کارکنان'),
 '088': ('ACT-TX-14', 'تعمیرات و نگهداری ساختمان سازمان', 'OLD', 'CC-1404', ['CC-1401'], 'MEDIUM', 'نگهداری جاری؛ تعمیرات اساسی CC-1401'),
 '090': ('ACT-TX-15', 'خرید و تعمیر تجهیزات و ملزومات اداری', 'OLD', 'CC-1403', [], 'MEDIUM', ''),
 '092': ('ACT-TX-16', 'حسابرسی سازمان', 'OLD', 'CC-1203', [], 'HIGH', ''),
 '095': ('ACT-TX-17', 'چاپ سربرگ و فرم‌های اداری', 'OLD', 'CC-1403', [], 'MEDIUM', ''),
 '099': ('ACT-TX-18', 'حفظ و نگهداری فضای سبز سازمان', 'OLD', 'CC-1404', ['CC-201'], 'LOW', 'فضای سبز محوطه اداری'),
 '101': ('ACT-TX-19', 'هزینه مخابرات، برق، آب، اینترنت و گاز', 'OLD', 'CC-1404', ['CC-1403'], 'MEDIUM', ''),
 '102': ('ACT-TX-20', 'بکارگیری نیروهای پیمانکاری', 'OLD', 'CC-1301', ['TTCC-P-01'], 'MEDIUM', 'نیروی برون‌سپاری‌شده؛ مصرف‌کننده نهایی نیروها نیازمند تصمیم'),
 '103': ('ACT-TX-21', 'بازدید کارکنان از سازمان‌های تاکسیرانی کلان‌شهرها', 'OLD', 'CC-1303', [], 'MEDIUM', 'آموزش/ارتقای شایستگی'),
 '112': ('ACT-TX-22', 'انعکاس سیاست‌ها و عملکرد سازمان (روابط عمومی)', 'OLD', 'CC-1501', [], 'MEDIUM', ''),
 '113': ('ACT-TX-23', 'تهیه کارکرد ماهانه پرسنل و بررسی پرونده‌های پرسنلی', 'OLD', 'CC-1301', ['CC-1305'], 'MEDIUM', ''),
 '116': ('ACT-TX-24', 'تهیه اسناد حسابداری و کنترل درآمد و هزینه سازمان', 'OLD', 'CC-1202', [], 'HIGH', ''),
 '117': ('ACT-TX-25', 'کنترل و نظارت بر واحدهای زیرمجموعه معاونت', 'NEW', 'TTCC-P-01', ['CC-1601'], 'LOW', 'مدیریتی'),
 '118': ('ACT-TX-26', 'رسیدگی به شکایات مردمی و بازرسی سطح شهر', 'MULTI', 'CC-1502', ['TTCC-P-01'], 'MEDIUM', 'شکایات (CC-1502) و بازرسی ناوگان (TTCC-P-01) در یک کد منبع ترکیب شده‌اند'),
 '119': ('ACT-TX-27', 'صدور و تمدید و تعویض مجوزهای تاکسیرانی', 'NEW', 'TTCC-P-01', [], 'HIGH', ''),
 '120': ('ACT-TX-28', 'بایگانی و کنترل اسناد ناوگان', 'MULTI', 'TTCC-P-01', ['CC-1305'], 'MEDIUM', ''),
 '121': ('ACT-TX-29', 'نظارت و کنترل عملکرد شرکت‌های حمل‌ونقل درون‌شهری', 'NEW', 'TTCC-P-01', [], 'HIGH', ''),
 '133': ('ACT-TX-30', 'تخصیص بودجه و کدبندی هزینه‌ها بر اساس کدهای استراتژی', 'OLD', 'CC-1601', [], 'MEDIUM', ''),
}
MZ_CATCHALL = {'100'}   # 2,753 lines (incl. 1,7xx bank-fee lines) carry the title «خدمات رفاهی به پرسنل» — not a reliable activity

# event-based defaults when the source activity is unusable (catch-all 100 / blank)
EV_CC = {
 'TT-NE-08': ('CC-1202', [], 'HIGH', 'کارمزد بانکی ← خزانه‌داری (هم‌راستا با قاعده SUP_TREAS در مرکز هزینه فعالیت‌محور v4)'),
 'FE-44': ('CC-1301', [], 'MEDIUM', 'حقوق و مزایا'), 'FE-45': ('CC-1301', [], 'MEDIUM', 'کارکنان قراردادی/برون‌سپاری'),
 'FE-46': ('CC-1301', [], 'MEDIUM', ''), 'FE-47': ('CC-1301', [], 'MEDIUM', ''), 'FE-48': ('CC-1301', [], 'MEDIUM', ''),
 'FE-49': ('CC-1301', [], 'MEDIUM', ''), 'FE-50': ('CC-1301', [], 'MEDIUM', ''), 'FE-52': ('CC-1301', [], 'MEDIUM', ''),
 'FE-51': ('CC-1302', [], 'MEDIUM', 'رفاه کارکنان'), 'TT-NE-26': ('CC-1503', ['CC-1403'], 'LOW', 'پذیرایی/تشریفات'),
 'TT-NE-09': ('CC-406', ['TTCC-P-01'], 'LOW', 'کمک/رفاه رانندگان ناوگان تاکسی؛ مالکیت نیازمند تصمیم'),
 'FE-33': ('CC-1404', [], 'LOW', 'قبوض عمومی'), 'FE-34': ('CC-1404', ['CC-1102'], 'LOW', 'مخابرات'),
 'FE-35': ('CC-1403', [], 'LOW', 'اجاره'), 'FE-36': ('CC-1403', [], 'LOW', 'بیمه دارایی'),
 'FE-22': ('CC-1403', [], 'LOW', 'ملزومات'), 'FE-39': ('CC-1402', [], 'LOW', 'نگهداری خودرو'),
 'FE-41': ('CC-1404', ['CC-1401'], 'LOW', 'نگهداری ساختمان'), 'FE-29': ('CC-1203', ['CC-1003'], 'LOW', 'حق‌الزحمه/حسابرسی'),
 'FE-43': ('CC-1101', [], 'MEDIUM', 'نرم‌افزار'), 'TT-NE-12': (None, [], 'LOW', ''), 'TT-NE-23': (None, [], 'LOW', ''),
}

# text overrides (ordered)  → (cc, alts, conf, note, status)
TEXT_CC = [
 (re.compile(r'جایگاه شارژ خودرو|خودروهای برقی|خودرو برقی|ایستگاه شارژ'), ('CC-408', ['CC-1401'], 'MEDIUM', 'زیرساخت شارژ خودروهای برقی ناوگان', 'PROV')),
 (re.compile(r'ون معلولین|معلولین|همیار|ون وانا|دانش ?آموز|سفیر ?مهر|سرویس مدارس'), ('TTCC-P-02', ['CC-406', 'CC-904'], 'MEDIUM', 'سرویس ویژه دانش‌آموزی/معلولین', 'NEW')),
 (re.compile(r'آپارتمان مشهد|خرید آپارتمان'), ('CC-1302', ['CC-1401'], 'LOW', 'اقامتگاه رفاهی کارکنان؟ — نیازمند تصمیم مالکیت', 'MULTI')),
 (re.compile(r'ضلع غربی'), ('CC-1401', [], 'MEDIUM', 'ساختمان اداری سازمان (ضلع غربی)', 'PROV')),
]
ASSET_DEFAULT = {  # asset (event TT-NE-33 / FE-23) lines without a decisive text → by account
 'TT-NE-33': ('CC-1401', ['CC-1403'], 'LOW', 'ساختمان/ملک/پارکینگ/سایبان سازمان', 'PROV'),
 'FE-23': ('CC-1403', ['CC-1102'], 'LOW', 'تجهیزات و اثاثیه اداری', 'PROV'),
}

# Terminals: facility segment of CodeVahed (first 3-digit group) — verified against NameVahed (see QA)
T_FAC = {'001': 'کاوه', '002': 'صفه', '003': 'زاینده‌رود', '004': 'جی', '007': 'صمدیه', '010': 'اندیشه'}
T_CENTRAL = {'005': 'دفتر مرکزی', '006': 'انبار سازمان', '008': 'دفتر کار طالقانی'}

def terminal_cc(l, ev, text):
    if VARIANT == 'v2' and ev == 'FE-03': ev = 'TT-NE-12'   # v2: service statements (FE-03, provisional) use the same outsourced-service cost-center rules as v1's TT-NE-12
    seg = (l['vahed'] or '').split('-')[0] if l['vahed'] and l['vahed'] != 'NULL' else None
    if l['markaz'] == '008':
        return 'PROVISIONAL_EXISTING_CC', 'CC-403', [ 'TTCC-P-03' ], 'MEDIUM', 'کد فعالیت منبع 008 «بهبود نگهداری و تعمیرات و تجهیز پایانه‌ها»'
    fac = seg in T_FAC
    if ev in ('FE-33', 'FE-34', 'FE-41', 'FE-40', 'FE-39', 'FE-22', 'FE-36', 'TT-NE-21') and fac:
        return 'PROVISIONAL_EXISTING_CC', 'CC-403', ['TTCC-P-03'], 'LOW', f'هزینه تأسیسات/نگهداری در پایانه {T_FAC[seg]}؛ ارتباط با CC-403 معنایی است نه مصوب'
    if ev in ('FE-33', 'FE-34') and seg in T_CENTRAL:
        return 'PROVISIONAL_EXISTING_CC', 'CC-1404', ['CC-403'], 'LOW', 'قبوض ساختمان اداری/ستادی'
    if ev in ('FE-44', 'FE-45', 'FE-46', 'FE-47', 'FE-48', 'FE-49', 'FE-50', 'FE-51', 'FE-52'):
        return 'MULTIPLE_CC_CANDIDATES', 'CC-1301', ['CC-403', 'TTCC-P-03'], 'LOW', 'حقوق کارکنان: مرکز هزینه جبران خدمات یا مرکز هزینه فعالیت پایانه — نیازمند تصمیم'
    if ev == 'TT-NE-12' and re.search(r'انتظامات|حفاظت', text): return 'PROVISIONAL_EXISTING_CC', 'CC-1405', [], 'LOW', 'خدمات انتظامات'
    if ev == 'TT-NE-12' and re.search(r'نظافت|بازآفرینان|هنرکده|سپاهان وحید|تاسیسات', text): return 'MULTIPLE_CC_CANDIDATES', 'CC-403', ['CC-1404', 'TTCC-P-03'], 'LOW', 'خدمات تأسیسات/نظافت پایانه یا ساختمان ستادی'
    if ev == 'TT-NE-12': return 'MULTIPLE_CC_CANDIDATES', 'CC-403', ['CC-1403', 'TTCC-P-03'], 'LOW', 'خدمات برون‌سپاری‌شده بدون شرح فعالیت'
    if ev == 'TT-NE-08': return 'PROVISIONAL_EXISTING_CC', 'CC-1202', [], 'HIGH', 'کارمزد بانکی'
    if ev == 'FE-38' or ev is None:
        return 'INSUFFICIENT_INFORMATION', None, [], 'LOW', 'تسویه تنخواه/سند بدون شرح ماهیت هزینه و بدون کد فعالیت منبع'
    if ev == 'FE-51': return 'PROVISIONAL_EXISTING_CC', 'CC-1302', [], 'MEDIUM', 'رفاه کارکنان'
    return 'INSUFFICIENT_INFORMATION', None, [], 'LOW', 'رویداد بدون نگاشت مرکز هزینه'


# =====================================================================================================================
# v2 audit corrections (TT_VARIANT=v2)
#  * TTCC-P-02 retired -> CC-406 (1405 service audit: «خدمات تاکسیرانی و سرویس مدارس» -> CC-406, تطبیق مستقیم, HIGH)
#  * TTCC-P-03 is no longer a cost-center candidate: terminal operating cost -> CC-403, leasing/levy income = revenue dimension
#  * MULTIPLE_CC_CANDIDATES rows carry NO selected center (cc_id empty); all candidates live in alt_ccs  (v1 root cause of the TTCC-P-01 discrepancy)
#  * decisive text overrides use the LINE narration only (v1 also used the document-wide description)
#  * second pass for unresolved rows: payroll precedent (v4 PER_PAY -> CC-1301), warehouse-issue slips, municipal activity rules (v4 classify)
# =====================================================================================================================
V2 = os.environ.get('TT_VARIANT', 'v1') == 'v2'
if V2:
    sys.path.insert(0, f'{ROOT}/scripts/journal_1404_activity_cc_v4')
    from activity_rules import classify as _v4c
    # v4 rules were written for budget-row titles: organization/location words in invoice narratives are not activity evidence
    _LOC = re.compile(r'پایانه ?(?:ها|های)?|کاوه|صفه|زاینده ?رود|صمدیه|اندیشه|دفتر مرکزی|تاکسیرانی|تاکسی|ناوگان|سازمان')
    _V4_EXCL = {'CAP_BRT', 'CAP_FLEETPUB', 'INS_SHAHROKAR'}
    def v4_classify(text):
        v = _v4c(_LOC.sub(' ', text or ''))
        return None if (v is None or v['rule'] in _V4_EXCL) else v
    TEXT_CC[1] = (TEXT_CC[1][0], ('CC-406', ['CC-904'], 'MEDIUM', 'سرویس ویژه دانش‌آموزی/معلولین ← CC-406 (ممیزی خدمات ۱۴۰۵)', 'PROV'))
    EV_CC['TT-NE-09'] = ('CC-406', [], 'MEDIUM', 'حمایت از ناوگان تاکسی (عنوان CC-406)')
    NEW_CC.pop('TTCC-P-02', None); NEW_CC.pop('TTCC-P-03', None)
    PAYROLL_EVENTS = ('FE-44', 'FE-45', 'FE-46', 'FE-47', 'FE-48', 'FE-49', 'FE-50', 'FE-51', 'FE-52')
    V4_OK = ('op', 'cap', 'sup', 'per', 'CCONLY')

    def terminal_cc_v2(l, ev, text, has_consumable_issue):
        st, cc, alts, conf, basis = terminal_cc(l, ev, text)
        alts = [a for a in alts if a != 'TTCC-P-03']
        if ev in PAYROLL_EVENTS and l['markaz'] != '008':
            return 'PROVISIONAL_EXISTING_CC', 'CC-1301', [], 'MEDIUM', 'جبران خدمات کارکنان ← CC-1301 (قاعده PER_PAY مرکز هزینه فعالیت‌محور v4 شهرداری؛ تفکیک به فعالیت پایانه با منبع ممکن نیست)'
        if ev == 'TT-NE-21' and has_consumable_issue:
            return 'PROVISIONAL_EXISTING_CC', 'CC-1403', [], 'LOW', 'حواله خروج کالای مصرفی (۱۱۵-۵) ← تدارکات اداری و لوازم مصرفی؛ مصرف‌کننده نهایی در سند نیست'
        if st == 'PROVISIONAL_EXISTING_CC' and cc == 'CC-403' and conf == 'LOW' and not alts:
            basis += ' (TTCC-P-03 دیگر نامزد نیست)'
        if st in ('INSUFFICIENT_INFORMATION', 'MULTIPLE_CC_CANDIDATES'):
            v = v4_classify(text)
            if v and v['kind'] in V4_OK and v['cc']:
                if st == 'INSUFFICIENT_INFORMATION':
                    return 'PROVISIONAL_EXISTING_CC', v['cc'], [], 'LOW', f"قاعده فعالیت‌محور شهرداری {v['rule']} روی شرح سطر ({v['act']})؛ اطمینان پایین"
                if v['cc'] in ([cc] + alts):
                    return 'PROVISIONAL_EXISTING_CC', v['cc'], [a for a in [cc] + alts if a != v['cc']], 'LOW', f"ابهام با قاعده {v['rule']} روی شرح سطر رفع شد؛ اطمینان پایین"
        return st, cc, alts, conf, basis

con = sqlite3.connect(DB)
cur = con.cursor()
cur.execute('DROP TABLE IF EXISTS line_cc')
cur.execute('''CREATE TABLE line_cc(sid PRIMARY KEY, doc_key, org, fy, eligible INT, cc_status, cc_id, alt_ccs, activity_id, source_markaz, source_unit, conf, rule_id, basis, review INT)''')

rows = cur.execute('''SELECT e.sid,e.doc_key,e.org,e.fy,e.role,e.acat,e.event_id,e.outcome,s.kol,s.moeen,s.taf1,s.bed,s.bes,s.markaz,s.vahed,s.f1,s.des_norm,s.sharh_norm,s.name_vahed,e.rule_id
  FROM line_event e JOIN sanad s ON s.sid=e.sid''').fetchall()
out = []
cnt = collections.Counter()
DOCS_CONSUMABLE = {r[0] for r in cur.execute("SELECT DISTINCT doc_key FROM sanad WHERE org='Terminals' AND kol='115' AND moeen='5' AND bes>0")} if V2 else set()
from common import norm
for (sid, dk, org, fy, role, acat, ev, oc, kol, moe, t1, bed, bes, mz, vh, f1, des, sharh, nv, line_rule) in rows:
    text = norm(' '.join(x for x in (des, sharh, f1) if x))
    tsx = norm(sharh) if sharh else norm(des or '')
    eligible = 1 if (role == 'DRIVER' and oc != 'NOT_AN_OPERATIONAL_EVENT' and (acat in ('EXP', 'FIXED_ASSET') or (org == 'Terminals' and (line_rule or '').startswith('TX-')))) else 0
    mzv = None if mz in (None, 'NULL') else mz
    if not eligible:
        if role == 'MEMO' or oc == 'NOT_AN_OPERATIONAL_EVENT': why = 'سند/سطر غیرعملیاتی (افتتاحیه/اختتامیه/انتظامی)'
        elif role == 'CLOSING' or role == 'SETTLEMENT': why = 'سند افتتاحیه/اختتامیه/تهاتر'
        elif acat == 'PREPAY': why = 'پیش‌پرداخت/علی‌الحساب: مرکز هزینه هنگام تسویه با فاکتور تعیین می‌شود'
        elif acat in ('REV_OP', 'REV_NONOP') or (acat == 'AR' and t1 in ('4', '8')): why = 'درآمد: مرکز درآمد/جریان درآمدی جدا از مرکز هزینه است (تصمیم مدل داده)'
        else: why = 'سطر ترازنامه‌ای/تسویه/انتقال یا جزء سند؛ مرکز هزینه ندارد'
        out.append((sid, dk, org, fy, 0, 'CC_NOT_APPLICABLE', None, '', None, mzv, vh, 'HIGH', 'CC-NA', why, 0)); cnt[(org, fy, 'CC_NOT_APPLICABLE')] += 1
        continue
    status = cc = None; alts = []; act = None; conf = 'LOW'; basis = ''; rid = ''
    # 1) decisive text override (Taxi)
    if org == 'Taxi':
        for rx_, (c, al, cf, note, kind) in TEXT_CC:
            if rx_.search(tsx if V2 else text) and not (V2 and ev == 'TT-NE-08'):
                status = {'PROV': 'PROVISIONAL_EXISTING_CC', 'NEW': 'NEW_CC_CANDIDATE', 'MULTI': 'MULTIPLE_CC_CANDIDATES'}[kind]
                cc, alts, conf, basis, rid = c, al, cf, note + ' (شرح سند)', 'TXT-OVR'; break
        if status is None and mzv and mzv in MZ and mzv not in MZ_CATCHALL:
            a_id, a_t, kind, c, al, cf, note = MZ[mzv]
            status = {'OLD': 'PROVISIONAL_EXISTING_CC', 'NEW': 'NEW_CC_CANDIDATE', 'MULTI': 'MULTIPLE_CC_CANDIDATES'}[kind]
            cc, alts, conf, act = c, al, cf, a_id
            basis = f'کد فعالیت منبع {mzv} «{a_t}»' + (f' — {note}' if note else ''); rid = f'MZ-{mzv}'
        if status is None and acat == 'FIXED_ASSET' and ev in ASSET_DEFAULT:
            c, al, cf, note, kind = ASSET_DEFAULT[ev]
            status = 'PROVISIONAL_EXISTING_CC'; cc, alts, conf, basis, rid = c, al, cf, note, 'AST-DEF'
        if status is None:
            hit = EV_CC.get(ev)
            if hit and hit[0]:
                cc, alts, conf, note = hit
                status = 'PROVISIONAL_EXISTING_CC' if not alts else 'MULTIPLE_CC_CANDIDATES'
                basis = f'کد فعالیت منبع بی‌اعتبار/خالی ({mzv or "خالی"}{" — کد عمومی" if mzv in MZ_CATCHALL else ""}); مرکز از رویداد {ev}: {note}'; rid = 'EV-DEF'
                if ev == 'TT-NE-09' and not V2: status = 'MULTIPLE_CC_CANDIDATES'
            else:
                status, cc, alts, conf, basis, rid = 'INSUFFICIENT_INFORMATION', None, [], 'LOW', f'کد فعالیت منبع {mzv or "خالی"} عمومی است و رویداد {ev} مرکز مشخصی ندارد', 'EV-NONE'
    else:
        if V2: st, cc, alts, conf, basis = terminal_cc_v2(dict(markaz=mzv, vahed=vh), ev, tsx, dk in DOCS_CONSUMABLE)
        else: st, cc, alts, conf, basis = terminal_cc(dict(markaz=mzv, vahed=vh), ev, text)
        status = st; rid = 'TERM'; act = 'ACT-TM-01' if mzv == '008' else None
    if V2 and org == 'Taxi' and status in ('INSUFFICIENT_INFORMATION', 'MULTIPLE_CC_CANDIDATES') and ev not in ('FE-70',):
        v = v4_classify(tsx)
        if v and v['kind'] in V4_OK and v['cc'] and (status == 'INSUFFICIENT_INFORMATION' or v['cc'] in ([cc] + alts)):
            alts = [a for a in ([cc] + alts) if a and a != v['cc']] if status == 'MULTIPLE_CC_CANDIDATES' else []
            status, cc, conf, rid, basis = 'PROVISIONAL_EXISTING_CC', v['cc'], 'LOW', 'V4-' + v['rule'], f"قاعده فعالیت‌محور شهرداری {v['rule']} روی شرح سطر ({v['act']}) — اطمینان پایین"
    if V2 and ev == 'FE-70' and status == 'INSUFFICIENT_INFORMATION':
        basis = 'هزینه استهلاک/ذخیره پایان دوره: تخصیص به مرکز هزینه نیازمند ثبت دارایی/فعالیت است که در منبع نیست'
    if V2 and status == 'MULTIPLE_CC_CANDIDATES':       # no selected center for ambiguous rows: candidates only
        alts = [x for x in ([cc] + alts) if x]; cc = None
    cnt[(org, fy, status)] += 1
    out.append((sid, dk, org, fy, 1, status, cc, ';'.join(alts), act, mzv, vh, conf, rid, basis, 1))
cur.executemany('INSERT INTO line_cc VALUES(' + ','.join('?' * 15) + ')', out)
cur.execute('CREATE INDEX i_lc_cc ON line_cc(cc_id)')
con.commit()
for k, v in sorted(cnt.items()): print(k, v)
