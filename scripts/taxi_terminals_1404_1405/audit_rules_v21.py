"""v2.1 — rule-level semantic audit of the 1,016 cost-center assignments that v2 made to previously unresolved rows with LOW confidence.

Findings of the review (all evidence is in the delivered audit workbook):
  * Group S  (Terminals warehouse issue slips -> CC-1403, 369 lines): the account sub-title (expense nature of the charged 113-1-1-xx account) separates consumables
              (consistent with an office-supplies center) from capital equipment / building parts (not consistent with CC-1403; consumer unknown).
  * Group E  (Taxi event-default FE-22 -> CC-1403, 266 lines): hospitality / ceremonies / gifts / staff-welfare vouchers are not "supplies".
  * Group K  (municipal v4 keyword classifier applied to line narration; Terminals + Taxi): single weak indicator; sample review found keyword collisions
              (wall plug vs plate, dent repair vs asphalt, 'smart system' damages vs software, security *office* vs physical guarding, 'advertising' as vendor name, ...).
  * Group F  (location-only evidence: line belongs to a terminal -> CC-403): location says WHERE, not WHAT.
Dispositions never force a single center for an ambiguous line; candidates are listed, keyword hints are kept only as hints.
"""
import re
from common import norm

N = lambda s: norm(s or '')
RX = lambda p: re.compile(p)

VEH = RX(r'وسائط نقلیه|وسایط نقلیه|وسایل نقلیه|لوازم یدکی|خودرو|وانت|مزدا|پژو|اگزوز|جلوبندی|سر ?سیلندر|صافکاری|اتومبیل|اتواسپرت|دور ?فرمان|داشبرد|روکش فابریک|لکه ?گیری و صافکاری')
BUILD_A = RX(r'جزیی ساختمان|تاسیسات|تعمیرات.*ساختمان|نگهداری و تعمیرات جزیی')
WELF_T = RX(r'پرسنل|کارکنان|بازنشسته')
WELF_K = RX(r'تفریح|استخر|ورزش|بن |کارت هدیه|هدیه|رفاه|پاداش|تولد|روز مادر|پس ?انداز|آپارتمان مشهد|جشن پرسنلی')
CEREM = RX(r'صنایع دستی|شکلات ?خوری|تراول ماگ|برگ بامبو|برگ بریده|رز |گل |گل$|گلدان|مراسم|تودیع|جشن|پذیرایی|پذیرائی|سوگواری|افطاری|مداح|خواننده|سخنرانی|حق ?القدم|میوه|شیرینی|آجیل|نشست خبری|کیک|آبمعدنی|سبد ?گل|شاخه گل|هدیه')
ACCEPT = {   # CC -> narration pattern that is SPECIFIC to the center's activity (not a bare keyword) ; (reject pattern or None)
    'CC-1101': (RX(r'نرم ?افزار|سامانه نظارت|ارتقا نرم|پشتیبانی نرم|استقرار سامانه'), RX(r'خسارت|عودت|تعزیرات')),
    'CC-1102': (RX(r'مرکز داده|مشاوره پشتیبانی'), None),
    'CC-401': (RX(r'ثبت تخلف|تجهیزات ترافیکی|دوربین'), None),
    'CC-1003': (RX(r'لایحه|خدمات قضایی'), None),
    'CC-1301': (RX(r'حقوق|پاداش|عیدی|مزایا|ماموران? به سازمان|مامور به سازمان'), RX(r'ماموریت|هزینه سفر|کارشناس رسمی')),
    'CC-201': (RX(r'نگهداری فضای سبز|قرارداد فضای سبز'), RX(r'خودرو|وانت|مزدا|اگزوز')),
    'CC-1302': (RX(r'بن |کارت هدیه|پس ?انداز|آپارتمان مشهد|استخر|مراکز تفریحی|رفاه|طب کار|معاینات|کارت تولد'), RX(r'سبد ?گل|شیشه تک گل|لوازم التحریر|ظرف پلاستیکی|ماموریت|سفر')),
    'CC-1501': (RX(r'هزینه تبلیغات|چاپ و تبلیغات|بنر استندی'), RX(r'ورزشی|ساک|نقطه|پرچم')),
    'CC-1405': (RX(r'نگهبان|انتظامات|حراست از سازمان|شیفت'), RX(r'خودرو|چاپ فرم|رله')),
    'CC-1402': (RX(r'بیمه ?نامه|شخص ثالث'), None),
    'CC-902': (RX(r'اجرای برنامه|برنامه دهه|تئاتر|برنامه گلستان شهدا|هفته اصفهان'), RX(r'کارکنان|پرسنلی|گل|سبد')),
    'CC-1003B': (None, None),
}
SOFT_A = RX(r'نرم ?افزار|فناوری اطلاعات|هوشمند')
SOFT_BAD = RX(r'خسارت|عودت|تعزیرات|لایحه|اظهارنامه|ثنا|اینماد|گرافیک')
LEGAL_T = RX(r'لایحه|اظهارنامه|دادگستری|کارشناس رسمی|سامانه عدل')
MISSION_A = RX(r'ماموریت|هزینه سفر')
FIRE_T = RX(r'کپسول|اطفاء|آتش ?نشانی')
SIGN_T = RX(r'تابلو|بنر|استیکر|آرم|حروف برجسته')
SPORT_T = RX(r'فوتسال|بازیکن|تیم|البسه ورزشی|کالای ورزشی')
OFFICE_A = RX(r'لوازم مصرفی اداری|تعمیر و نگهداری وسایل اداری|تعمیر و نگهداری وسایل')
PROG_A = RX(r'اجرای برنامه')
FLEET_T = RX(r'معاینه فنی|ناوگان')
MACH_A = RX(r'کرایه ماشین آلات')
COLLISION_CC = {'CC-602', 'CC-502', 'CC-102', 'CC-203', 'CC-605', 'CC-901', 'CC-904', 'CC-905', 'CC-1305'}
BANKFEE_T = RX(r'کارمزد|کارمزذ')
BANKFEE_A = RX(r'بانکی')

CAND_VEH = ['CC-1402']
CAND_BUILD = ['CC-1404', 'CC-403']
CAND_CEREM = ['CC-1503', 'CC-1403']
CAND_WELF = ['CC-1302']


def group_of(rec):
    b = rec['basis'] or ''
    if 'حواله خروج کالا' in b: return 'S'
    if rec['rule_id'] == 'EV-DEF': return 'E'
    if 'قاعده فعالیت' in b and 'شهرداری' in b: return 'K'
    if 'هزینه تأسیسات' in b and 'پایانه' in b: return 'F'
    return 'O'


def _mult(cc, extra):
    out = []
    drop_cc = cc in COLLISION_CC and len(set(extra)) >= 2     # keyword center known to collide in the sample review and the nature already yields >=2 candidates
    for c in list(extra) + ([cc] if cc and not drop_cc else []):
        if c and c not in out: out.append(c)
    return out


def _decide_raw(rec):
    """rec: dict(org, cc, T (norm line narration), A (norm account title), event, basis, rule_id).
    returns (decision, new_status, new_cc, new_conf, new_alts(list), reason, evidence)"""
    g = group_of(rec); T, A, cc = rec['T'], rec['A'], rec['cc']
    PROV, MULT, INSUF = 'PROVISIONAL_EXISTING_CC', 'MULTIPLE_CC_CANDIDATES', 'INSUFFICIENT_INFORMATION'
    if g == 'S':
        if 'لوازم مصرفی اداری' in A:
            return ('UPGRADE_TO_MEDIUM_WITH_EVIDENCE', PROV, cc, 'MEDIUM', [], 'حواله انبار روی حساب «لوازم مصرفی اداری» (طبیعت هزینه در سرفصل تفصیلی منبع) با کالای مصرفی هم‌خوان؛ مصرف‌کننده نهایی در سند نیست',
                    'عنوان حساب تفصیلی ۱۱۳-۱-۱ + نام کالا در خود ردیف (دو شاهد مستقل)')
        if 'سرمایه' in A and 'اثاثیه' in A:
            return ('RECLASSIFY_TO_MULTIPLE_CANDIDATES', MULT, None, 'LOW', ['CC-1403', 'CC-1102'], 'تجهیزات سرمایه‌ای (اثاثیه/منصوبات) خارج از دامنه «لوازم مصرفی»؛ مرکز مصرف‌کننده معلوم نیست', 'عنوان حساب «اثاثیه و منصوبات (سرمایه‌ای)»')
        if 'تاسیسات' in A and 'سرمایه' in A:
            return ('RECLASSIFY_TO_MULTIPLE_CANDIDATES', MULT, None, 'LOW', ['CC-403', 'CC-1404', 'CC-1403'], 'تجهیزات تأسیساتی سرمایه‌ای؛ مصرف‌کننده نامعلوم', 'عنوان حساب «تاسیسات و تجهیزات (سرمایه‌ای)»')
        if 'جزیی ساختمان' in A:
            return ('RECLASSIFY_TO_MULTIPLE_CANDIDATES', MULT, None, 'LOW', ['CC-1404', 'CC-403', 'CC-1403'], 'قطعات جزیی ساختمان/تأسیسات؛ ساختمان مقصد نامعلوم', 'عنوان حساب «لوازم جزیی ساختمان و تأسیسات»')
        return ('RECLASSIFY_TO_MULTIPLE_CANDIDATES', MULT, None, 'LOW', ['CC-1403', 'CC-403'], 'حواله انبار بدون طبیعت هزینه مشخص', 'فقط ماهیت حواله')
    if g == 'E':
        if FLEET_T.search(T) and not CEREM.search(T):
            return ('RECLASSIFY_TO_MULTIPLE_CANDIDATES', MULT, None, 'LOW', ['TTCC-P-01', 'CC-406'], 'خدمات مرتبط با ناوگان (معاینه فنی/نظارت): نامزدهای معنادار وجود دارد؛ «ملزومات» نیست', 'شرح ردیف: ناوگان/معاینه فنی')
        if re.search(r'رفاهی|تفریحی', A) or (WELF_T.search(T) and WELF_K.search(T)):
            return ('RECLASSIFY_TO_MULTIPLE_CANDIDATES', MULT, None, 'LOW', ['CC-1302', 'CC-1503'], 'رفاه/پذیرایی کارکنان یا میهمان؛ «ملزومات» (CC-1403) نیست', 'عنوان حساب + شرح ردیف')
        if re.search(r'جشن|پذیرایی|پذیرائی|سوگواری|افطاری', A) or CEREM.search(T) or re.search(r'تقدیر|کارت هدیه', T):
            return ('RECLASSIFY_TO_MULTIPLE_CANDIDATES', MULT, None, 'LOW', ['CC-1503', 'CC-1403', 'CC-902'], 'مراسم، پذیرایی و هدایا: تشریفات یا رویداد؛ پیش‌فرض رویداد FE-22 به «ملزومات» از نظر معنایی پشتیبانی نمی‌شود', 'عنوان حساب (جشن و پذیرایی/کمک) + شرح ردیف')
        return ('RECLASSIFY_TO_INSUFFICIENT_INFORMATION', INSUF, None, 'LOW', [cc] if cc else [], 'پیش‌فرض رویدادی بدون شاهد ماهیت', 'فقط پیش‌فرض رویداد')
    if g == 'K':
        if cc == 'CC-1202' and BANKFEE_T.search(T) and BANKFEE_A.search(A):
            return ('UPGRADE_TO_MEDIUM_WITH_EVIDENCE', PROV, cc, 'MEDIUM', [], 'کارمزد بانکی: عنوان حساب «هزینه‌های بانکی» و شرح «کارمزد» هم‌سو (همان منطق TT-NE-08 → CC-1202)', 'عنوان حساب + شرح ردیف')
        acc, rej = ACCEPT.get(cc, (None, None))
        if acc and acc.search(T) and not (rej and rej.search(T)):
            return ('RETAIN_LOW_CONFIDENCE', PROV, cc, 'LOW', [], 'عبارت اختصاصی فعالیت در شرح خود ردیف و بدون برخورد واژگانی در بازبینی؛ تک‌شاهد، اطمینان LOW حفظ شد', 'عبارت اختصاصی در شرح ردیف')
        if SOFT_A.search(A) and cc == 'CC-1101' and not SOFT_BAD.search(T):
            return ('RETAIN_LOW_CONFIDENCE', PROV, cc, 'LOW', [], 'حساب «نرم‌افزار/فناوری اطلاعات» و شرح سامانه/نرم‌افزار هم‌سو با CC-1101؛ تک‌خانواده، LOW حفظ شد', 'عنوان حساب + شرح ردیف')
        if SOFT_A.search(A) and cc != 'CC-1101' and not SOFT_BAD.search(T):
            return ('RECLASSIFY_TO_MULTIPLE_CANDIDATES', MULT, None, 'LOW', _mult(cc, ['CC-1101']), 'نرم‌افزار/سامانه؛ طبیعت حساب فناوری اطلاعات و مرکز کاربر هر دو نامزدند', 'عنوان حساب نرم‌افزار')
        if LEGAL_T.search(T):
            return ('RECLASSIFY_TO_MULTIPLE_CANDIDATES', MULT, None, 'LOW', _mult(cc, ['CC-1003']), 'خدمات حقوقی/قضایی؛ مرکز حقوقی نامزد معنادار است', 'شرح ردیف')
        if MISSION_A.search(A):
            return ('RECLASSIFY_TO_MULTIPLE_CANDIDATES', MULT, None, 'LOW', _mult(cc, ['CC-1302', 'CC-1301']), 'ماموریت/هزینه سفر کارکنان: پرداخت‌های حقوقی یا ایاب‌وذهاب/سفر؛ شاهد واژگانی کافی نیست', 'عنوان حساب ماموریت و سفر')
        if FIRE_T.search(T):
            return ('RECLASSIFY_TO_MULTIPLE_CANDIDATES', MULT, None, 'LOW', ['CC-801', 'CC-1404', 'CC-403'], 'شارژ کپسول آتش‌نشانی تأسیسات؛ ایمنی ساختمان یا عملیات آتش‌نشانی', 'شرح ردیف')
        if SIGN_T.search(T) and cc == 'CC-402':
            return ('RECLASSIFY_TO_MULTIPLE_CANDIDATES', MULT, None, 'LOW', ['CC-402', 'CC-403'], 'تابلو/آرم پایانه: علائم ترافیکی یا تجهیز ساختمان؛ شاهد کافی برای یکی نیست', 'شرح ردیف')
        if SPORT_T.search(T):
            return ('RECLASSIFY_TO_MULTIPLE_CANDIDATES', MULT, None, 'LOW', ['CC-903', 'CC-1302'], 'تیم ورزشی سازمان: ورزش یا رفاه کارکنان', 'شرح ردیف')
        if MACH_A.search(A):
            return ('RECLASSIFY_TO_MULTIPLE_CANDIDATES', MULT, None, 'LOW', ['CC-1402', 'CC-403'], 'کرایه ماشین‌آلات سنگین/جرثقیل برای پایانه‌ها؛ ناوگان یا عمران', 'عنوان حساب کرایه ماشین‌آلات')
        if PROG_A.search(A) and cc != 'CC-902':
            return ('RECLASSIFY_TO_MULTIPLE_CANDIDATES', MULT, None, 'LOW', _mult(cc, ['CC-902']), 'اجرای برنامه فرهنگی/مذهبی؛ مرکز رویدادها یا مرکز واژهٔ کلیدی', 'عنوان حساب اجرای برنامه')
        if OFFICE_A.search(A) and cc != 'CC-1403':
            return ('RECLASSIFY_TO_MULTIPLE_CANDIDATES', MULT, None, 'LOW', _mult(cc, ['CC-1403']), 'حساب «لوازم مصرفی/تعمیر وسایل اداری» با واژهٔ کلیدی مرکز دیگر در شرح؛ طبیعت حساب به تدارکات اداری اشاره دارد', 'عنوان حساب')
        if VEH.search(A) or VEH.search(T):
            return ('RECLASSIFY_TO_MULTIPLE_CANDIDATES', MULT, None, 'LOW', _mult(cc, CAND_VEH), 'نگهداری/تعمیر وسیله نقلیه؛ واژه کلیدی مرکز دیگر مربوط به محل/استفاده‌کننده است نه ماهیت هزینه', 'عنوان حساب/شرح: وسیله نقلیه')
        if BUILD_A.search(A):
            return ('RECLASSIFY_TO_MULTIPLE_CANDIDATES', MULT, None, 'LOW', _mult(cc, CAND_BUILD), 'قطعات/تعمیرات جزیی ساختمان و تأسیسات؛ واژهٔ کلیدی ماهیت را تعیین نمی‌کند', 'عنوان حساب «تعمیرات/لوازم جزیی ساختمان»')
        if (WELF_T.search(T) and WELF_K.search(T)) or re.search(r'رفاهی|تفریحی', A):
            return ('RECLASSIFY_TO_MULTIPLE_CANDIDATES', MULT, None, 'LOW', _mult(cc, CAND_WELF), 'خدمات رفاهی کارکنان؛ مرکز رفاه (CC-1302) یا مرکز واژهٔ کلیدی', 'شرح ردیف: کارکنان + خدمت رفاهی')
        if CEREM.search(T):
            return ('RECLASSIFY_TO_MULTIPLE_CANDIDATES', MULT, None, 'LOW', _mult(cc, CAND_CEREM), 'مراسم/هدیه/گل؛ مرکز تشریفات یا مرکز واژهٔ کلیدی', 'شرح ردیف')
        return ('RECLASSIFY_TO_INSUFFICIENT_INFORMATION', INSUF, None, 'LOW', [cc] if cc else [], 'تنها یک واژهٔ کلیدی (قاعده v4 شهرداری روی شرح)؛ برخورد واژگانی در نمونه‌ها مشاهده شد؛ واژه فقط به‌عنوان راهنما نگه داشته شد', 'تک‌شاهد واژگانی')
    if g == 'F':
        if CEREM.search(T) or re.search(r'جشن|پذیرایی', A):
            return ('RECLASSIFY_TO_MULTIPLE_CANDIDATES', MULT, None, 'LOW', ['CC-1503', 'CC-1403'], 'پذیرایی/مراسم؛ محل (پایانه) ماهیت را تعیین نمی‌کند', 'شرح ردیف')
        if VEH.search(A) or VEH.search(T):
            return ('RECLASSIFY_TO_MULTIPLE_CANDIDATES', MULT, None, 'LOW', ['CC-1402', 'CC-403'], 'تعمیر وسیله نقلیه در پایانه؛ شاهد فقط محل است', 'عنوان حساب/شرح')
        return ('RETAIN_LOW_CONFIDENCE', PROV, cc, 'LOW', [], 'تجهیزات/نگهداری تأسیساتی در واحد پایانه؛ ماهیت و محل هر دو با CC-403 هم‌خوان (نمونه‌برداری)؛ LOW حفظ شد', 'محل + ماهیت تأسیسات')
    return ('REQUIRES_EXPERT_DECISION', PROV, cc, 'LOW', [], 'قاعدهٔ دیگر؛ بازبینی کارشناسی', '—')


def decide(rec):
    """public entry: _decide_raw + invariant that a MULTIPLE status never carries fewer than two candidates"""
    dec, nst, ncc, nconf, nalts, reason, evid = _decide_raw(rec)
    if nst == 'MULTIPLE_CC_CANDIDATES' and len(set(nalts)) < 2:
        if nalts and nalts[0] == rec['cc']: return ('RETAIN_LOW_CONFIDENCE', 'PROVISIONAL_EXISTING_CC', rec['cc'], 'LOW', [], reason, evid)
        return ('RECLASSIFY_TO_INSUFFICIENT_INFORMATION', 'INSUFFICIENT_INFORMATION', None, 'LOW', list(nalts), reason, evid)
    return dec, nst, ncc, nconf, nalts, reason, evid
