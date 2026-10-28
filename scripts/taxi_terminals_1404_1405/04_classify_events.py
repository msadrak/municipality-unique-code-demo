"""Phase 2 — document-aware financial-event classification (PROPOSED layer; nothing here is approved).

Unit of reasoning = source-scoped document (doc_key = ORG-FY-Sanad_Num).  Each line receives a ROLE and a line-level event;
each document receives a primary event + outcome status.  Outcomes (per the mandate):
  EXISTING_EVENT_CONFIRMED  account-subtype evidence AND independent narration evidence agree on an FE-xx event
  EXISTING_EVENT_PROVISIONAL one evidence line supports an FE-xx event
  NEW_EVENT_CANDIDATE        evidence supports a reusable behaviour that FE-01..FE-70 does not have (TT-NE-xx)
  COMPOSITE_TRANSACTION      document legitimately carries >1 business event (components listed)
  AMBIGUOUS_EVENT            economic substance not decidable from source fields — never forced
  INSUFFICIENT_INFORMATION   no usable evidence
  NOT_AN_OPERATIONAL_EVENT   opening / closing / memo / internal netting
"""
import sqlite3, re, sys, os, json, collections
sys.path.insert(0, os.path.dirname(__file__))
from common import *
from rules import *

con = sqlite3.connect(DB)
cur = con.cursor()
for t in ('doc_class', 'line_event'):
    cur.execute(f'DROP TABLE IF EXISTS {t}')
cur.execute('''CREATE TABLE doc_class(doc_key PRIMARY KEY, org, fy, kind, n_lines INT, bed_total INT, date_first, date_last, primary_event, outcome,
  composite INT, driver_events, conf, rule_id, reason, review INT)''')
cur.execute('''CREATE TABLE line_event(sid PRIMARY KEY, doc_key, org, fy, role, acat, event_id, outcome, conf, rule_id, evidence_n INT, basis, doc_primary_event,
  doc_outcome, amount_dr INT, amount_cr INT, review INT)''')

# --------------------------------------------------------------------------------------------- account category
def acat(org, kol, moe, taf1):
    k, m = kol, moe
    if k in ('918', '919', '920'): return 'MEMO'
    if k == '111': return 'TANKHAH' if m == '3' else 'BANK'
    if k == '112': return 'INVEST'
    if k == '113':
        if m == '1': return 'AR'
        if m in ('5', '6', '7'): return 'NOTES_REC'
        return 'AR_OTHER'
    if k == '114':
        if m == '1': return 'STAFF_AR'
        if org == 'Taxi':
            return {'2': 'TREASURY', '9': 'VAT_PAID', '4': 'DEP_GIVEN'}.get(m, 'AR_OTHER')
        return {'9': 'TREASURY', '10': 'TREASURY', '4': 'DEP_GIVEN'}.get(m, 'AR_OTHER')
    if k == '115': return 'INVENTORY'
    if k == '116': return 'PREPAY'
    if k in ('120', '121', '123', '125'): return 'FIXED_ASSET'
    if k == '122': return 'ACC_DEPR'
    if k == '124': return 'INVEST'
    if k == '211': return 'AP_NOTES' if m == '5' else 'AP'
    if k == '212':
        return {'1': 'STAFF_AP', '2': 'ACCRUED', '3': 'TAX_WH', '4': 'INS_PAY', '6': 'DEPOSIT', '7': 'DEDUCTION', '8': 'OTHER_AP',
                '9': 'VAT_REC', '10': 'VAT_REC', '11': 'COMMIT', '12': 'COMMIT', '13': 'COMMIT', '14': 'COMMIT'}.get(m, 'OTHER_AP')
    if k == '213': return 'ADV_REC'
    if k in ('214', '217', '223', '224'): return 'PROV'
    if k in ('216', '222'): return 'LOAN'
    if k.startswith('3'): return 'EQUITY'
    if k in ('411', '413'): return 'REV_OP'
    if k == '812': return 'REV_NONOP'
    if k in ('611', '612', '613'): return 'EXP'
    return 'OTHER'

# --------------------------------------------------------------------------------------------- doc kind
R_OPEN = re.compile(r'افتتاح')
R_CLOSE = re.compile(r'اختتام')
R_CLOSE_TEMP = re.compile(r'بستن حساب\s?(?:ها|های|هاي)?\s?(?:ی |ي )?موقت')
R_ACC_CLOSE = re.compile(r'بستن حساب')

V2 = VARIANT == 'v2'
R_BONUS_CLOSE = re.compile(r'پاداش بستن حساب')
R_PL_TO_RE = re.compile(r'سود و زیان جاری به انباشته')
R_PREREC_CLOSE = re.compile(r'بستن حساب\s?(?:های|ها)?\s?پیش ?دریافت')

def doc_kind(descs):
    j = ' | '.join(descs)
    if R_OPEN.search(j): return 'OPENING'
    if R_CLOSE.search(j): return 'CLOSING_PERMANENT'
    if R_CLOSE_TEMP.search(j): return 'CLOSING_TEMPORARY'
    if V2:   # v1 treated every 'بستن حساب' text as inter-entity settlement; the audit found three unrelated populations
        if R_PL_TO_RE.search(j): return 'CLOSING_TEMPORARY'          # P&L result to retained earnings (closing step)
        if R_BONUS_CLOSE.search(j) or R_PREREC_CLOSE.search(j): return 'REGULAR'   # year-end bonus; school pre-receipt retained-share recognition
    if R_ACC_CLOSE.search(j): return 'INTERNAL_SETTLEMENT'
    return 'REGULAR'

# --------------------------------------------------------------------------------------------- text agreement (2nd evidence)
AGREE = {
 'FE-44': R_PAYROLL, 'FE-45': R_STAFFING, 'FE-48': R_INS_SOC, 'FE-50': R_EIDI, 'FE-51': re.compile(R_INS_COMP.pattern + '|' + R_GIFT.pattern + r'|رفاهی|ورزش|اردو'),
 'FE-33': R_UTIL, 'FE-34': R_TEL, 'FE-35': R_RENT, 'FE-39': re.compile(R_REPAIR.pattern + r'|وانت|خودرو|ون |موتور'), 'FE-41': R_REPAIR,
 'FE-36': re.compile(r'بیمه'), 'FE-43': R_IT, 'FE-29': R_AUDIT, 'FE-22': re.compile(r'خرید|لوازم|فاکتور|ملزومات'), 'FE-46': re.compile(r'اضافه ?کار|تعطیل'),
 'FE-47': re.compile(r'ماموریت'), 'FE-52': re.compile(r'بازنشست|مستمری|متوفی'),
}

def settle(ev, status, conf, ev_n, text):
    """upgrade PROVISIONAL → CONFIRMED when an independent narration pattern agrees"""
    if status == 'EXISTING_EVENT_PROVISIONAL' and ev in AGREE and AGREE[ev].search(text):
        return 'EXISTING_EVENT_CONFIRMED', 'HIGH', 2
    return status, conf, ev_n

# --------------------------------------------------------------------------------------------- line rules
def exp_line(org, l, t):
    k, m, t1 = l['kol'], l['moeeen'], l['taf1']
    # text-conditional overrides first
    if (k, m, t1) == ('612', '5', '14'):
        if R_STAFFING.search(t): return 'FE-45', 'EXISTING_EVENT_PROVISIONAL', 'LOW', 'EXP-612-5-14-STAFF', 1, 'خدمات پیمانکاری + تأمین نیرو/انتظامات'
        if re.search(r'ساختمان|احداث|اجرا|ایزوگام|سازه', t): return 'FE-03', 'EXISTING_EVENT_PROVISIONAL', 'LOW', 'EXP-612-5-14-WORKS', 1, 'خدمات پیمانکاری + عملیات اجرایی'
        return 'TT-NE-12', 'NEW_EVENT_CANDIDATE', 'MEDIUM', 'EXP-612-5-14-GEN', 1, 'خدمات پیمانکاری عام'
    if (k, m, t1) == ('612', '5', '7'):
        if R_INS_COMP.search(t) or R_GIFT.search(t): return 'FE-51', 'EXISTING_EVENT_PROVISIONAL', 'MEDIUM', 'EXP-612-5-7-GIFT', 2, 'رفاهی + هدیه/بن/بیمه تکمیل'
        if R_HOSPITALITY.search(t): return 'TT-NE-26', 'NEW_EVENT_CANDIDATE', 'LOW', 'EXP-612-5-7-HOSP', 2, 'رفاهی + پذیرایی/جشن'
    if (k, m, t1) == ('612', '5', '12') and not R_BANKFEE.search(t):
        return None, 'AMBIGUOUS_EVENT', 'LOW', 'EXP-612-5-12-X', 1, 'هزینه بانکی/حقوقی/عوارض قانونی بدون کارمزد'
    if (k, m, t1) == ('612', '4', '3'):
        if re.search(r'رانندگان استیجاری|کارکرد', t): return None, 'AMBIGUOUS_EVENT', 'LOW', 'EXP-612-4-3-DRV', 1, 'کارکرد رانندگان استیجاری: اجاره خودرو یا خدمات پیمانکاری؟'
        if re.search(r'جرثقیل|لیفتراک|کرایه|حمل|بیل|خاور|نیسان|پیک', t): return 'FE-32', 'EXISTING_EVENT_PROVISIONAL', 'LOW', 'EXP-612-4-3-HAUL', 2, 'کرایه حمل/ماشین‌آلات'
        return None, 'AMBIGUOUS_EVENT', 'LOW', 'EXP-612-4-3-X', 1, 'کرایه حمل‌ونقل نامشخص'
    if k == '613' and m == '20':
        return ('TT-NE-24', 'NEW_EVENT_CANDIDATE', 'MEDIUM', 'EXP-613-20-9', 1, 'مطالبات مشکوک‌الوصول') if t1 == '9' else \
               ('TT-NE-23', 'NEW_EVENT_CANDIDATE', 'HIGH', 'EXP-613-20', 2, 'هزینه استهلاک دوره')
    if k == '613' and m == '21':
        return ('FE-67', 'EXISTING_EVENT_PROVISIONAL', 'LOW', 'EXP-613-21', 1, 'هزینه سنوات قبل')
    hit = EXP_MAP.get((k, m, t1))
    if not hit:
        return None, 'AMBIGUOUS_EVENT', 'LOW', 'EXP-UNMAPPED', 0, f'زیرحساب {k}-{m}-{t1} در جدول نگاشت نیست'
    ev, st, conf, rid = hit
    if ev is None:
        note = SPARE_PARTS_NOTE if rid == 'EXP-612-7-3' else 'ابهام ذاتی زیرحساب'
        return None, st, conf, rid, 1, note
    ev_n = 1
    if st == 'EXISTING_EVENT_PROVISIONAL':
        st, conf, ev_n = settle(ev, st, conf, 1, t)
    return ev, st, conf, rid, ev_n, 'زیرحساب %s-%s-%s' % (k, m, t1)

def rev_line(org, l, t):
    k, m = l['kol'], l['moeeen']
    if k == '812':
        if m == '2': return 'TT-NE-28', 'NEW_EVENT_CANDIDATE', 'MEDIUM', 'REV-812-2', 1, 'سود سپرده بانکی'
        if m == '4': return 'FE-19', 'EXISTING_EVENT_PROVISIONAL', 'MEDIUM', 'REV-812-4', 1, 'ضبط سپرده معاملات'
        if m == '5': return 'FE-70', 'EXISTING_EVENT_PROVISIONAL', 'LOW', 'REV-812-5', 1, 'اصلاح حساب‌های سنواتی'
        return 'TT-NE-28', 'NEW_EVENT_CANDIDATE', 'LOW', 'REV-812-8', 1, 'درآمد متفرقه غیرعملیاتی'
    if m == '1':
        if R_SCHOOL_SHARE.search(t) and R_SCHOOL.search(t): return 'TT-NE-05', 'NEW_EVENT_CANDIDATE', 'HIGH', 'REV-413-SCHOOL', 2, 'سهم ۲٪ سرویس مدارس'
        if re.search(r'جریمه', t): return 'TT-NE-01', 'NEW_EVENT_CANDIDATE', 'MEDIUM', 'REV-413-FINE', 1, 'جریمه تخلف'
        if R_FEE_SERVICE.search(t): return 'FE-60', 'EXISTING_EVENT_PROVISIONAL', 'MEDIUM', 'REV-413-FEE', 2, 'درآمد بهای خدمات/حق عضویت/پروانه'
        return 'FE-60', 'EXISTING_EVENT_PROVISIONAL', 'LOW', 'REV-413-1-GEN', 1, 'درآمد خدمات عملیاتی با شرح عمومی'
    if m == '8' or True:
        if R_SCHOOL_SHARE.search(t) and R_SCHOOL.search(t): return 'TT-NE-05', 'NEW_EVENT_CANDIDATE', 'HIGH', 'REV-413-SCHOOL', 2, 'سهم ۲٪ سرویس مدارس'
        if R_GRANT.search(t): return 'TT-NE-02', 'NEW_EVENT_CANDIDATE', 'HIGH', 'REV-413-8-GRANT', 2, 'کمک بودجه از شهرداری'
        if R_RENT.search(t): return 'FE-60', 'EXISTING_EVENT_PROVISIONAL', 'MEDIUM', 'REV-413-8-RENT', 2, 'اجاره جایگاه/غرفه'
        return None, 'AMBIGUOUS_EVENT', 'LOW', 'REV-413-8-X', 1, 'سایر درآمدها بدون شرح تفکیک‌کننده'

def recharge_event(t):
    """Terminals: expenditure charged to the municipality / companies (Dr 113-1 not revenue).  Event comes from narration only."""
    if R_EIDI.search(t): return 'FE-50', 'HIGH', 'TX-EIDI'
    if R_TAX_SAL.search(t): return 'FE-49', 'MEDIUM', 'TX-TAX'
    if V2:
        if re.search(r'ش حواله|کالا:', t): return 'TT-NE-21', 'MEDIUM', 'TX-STORE2'
        if R_PAYCOMP.search(t) and not re.search(r'صورت ?وضعیت|پیمانکار|تامین نیرو|فاکتور|بیمه تکمیل', t):
            return ('FE-46' if re.search(r'تعطیل کاری|اضافه ?کار|نوبت کاری', t) else ('FE-45' if 'کارگر' in t else 'FE-44')), 'MEDIUM', 'TX-PAYCOMP'
        if re.search(r'ارزش افزوده', t): return 'FE-11', 'LOW', 'TX-VAT'
    if R_STORE_ISSUE.search(t): return 'TT-NE-21', 'MEDIUM', 'TX-STORE'
    if R_INS_COMP.search(t): return 'FE-51', 'MEDIUM', 'TX-INSCOMP'
    if R_PAYROLL.search(t) and not re.search(r'صورت ?وضعیت|پیمانکاری|تامین نیرو', t): return 'FE-44', 'MEDIUM', 'TX-PAYROLL'
    if R_INS_SOC.search(t): return 'FE-48', 'MEDIUM', 'TX-INS'
    if re.search(r'سپاهان وحید|صورت ?وضعیت|پیمانکاری|شهر ?و ?کار|انسانی|انتظامات|بازآفرینان|هنرکده', t): return 'TT-NE-12', 'LOW', 'TX-OUTSRC'
    if R_UTIL.search(t): return 'FE-33', 'MEDIUM', 'TX-UTIL'
    if R_TEL.search(t): return 'FE-34', 'MEDIUM', 'TX-TEL'
    if R_RENT.search(t): return 'FE-35', 'MEDIUM', 'TX-RENT'
    if R_REPAIR.search(t): return 'FE-41', 'LOW', 'TX-REPAIR'
    if re.search(r'بیمه', t): return 'FE-36', 'LOW', 'TX-INS-ASSET'
    if R_GIFT.search(t): return 'FE-51', 'MEDIUM', 'TX-GIFT'
    if re.search(r'غذا|ناهار|پرسنل', t) and R_HOSPITALITY.search(t): return 'FE-51', 'LOW', 'TX-STAFFFOOD'
    if R_HOSPITALITY.search(t): return 'TT-NE-26', 'LOW', 'TX-HOSP'
    if V2:
        if re.search(r'خرید (?:گل|نهال|سم|بذر)|گیاه ?پزشکی|خدمات کشاورزی', t): return 'FE-26', 'LOW', 'TX-PLANTS'
        if re.search(r'حق ?الزحمه|کارشناسی رسمی', t): return 'FE-29', 'LOW', 'TX-FEE'
        if re.search(r'رنگ|شیشه|مصالح|داربست|لوله|کابل|ایزوگام|آهن', t): return 'FE-24', 'LOW', 'TX-MATERIALS'
        if re.search(r'تابلو|تجهیزات ترافیکی', t): return 'FE-28', 'LOW', 'TX-SIGNS'
    if R_TANKHAH.search(t): return 'FE-38', 'LOW', 'TX-TANKHAH'
    return None, 'LOW', 'TX-X'

def spec_line(org, l, t, doc):
    """balance-sheet driven events.  Returns (class, event, outcome, conf, rule, ev_n, basis)."""
    a, k, m, t1 = l['acat'], l['kol'], l['moeeen'], l['taf1']
    dr, cr = l['bed'] > 0, l['bes'] > 0
    P_, N_, A_ = 'EXISTING_EVENT_PROVISIONAL', 'NEW_EVENT_CANDIDATE', 'AMBIGUOUS_EVENT'
    # school-service flows (Taxi)
    if org == 'Taxi' and (R_SCHOOL.search(t) or (k == '213' and t1 == '5') or k == '212' and m in ('11', '12', '13', '14')):
        if k == '212' and m == '14': return 'SPEC', 'TT-NE-09', N_, 'LOW', 'SCH-212-14', 1, 'تعهد بیمه تکمیل رانندگان'
        if R_SCHOOL_SHARE.search(t): return 'SPEC', 'TT-NE-05', N_, 'HIGH', 'SCH-SHARE', 2, 'سهم ۲٪ از پیش‌دریافت سامانه'
        if k == '212' or R_EXCEPTIONAL.search(t): return 'SPEC', 'TT-NE-07', N_, 'MEDIUM', 'SCH-EXCEP', 1, 'ایاب‌وذهاب دانش‌آموزان استثنایی/معلولین'
        if R_SCHOOL_REFUND.search(t) and dr: return 'SPEC', 'TT-NE-06', N_, 'MEDIUM', 'SCH-REFUND', 2, 'انصرافی سرویس مدارس'
        if R_SCHOOL_PAYOUT.search(t) or (a == 'AR' and dr): return 'SPEC', 'TT-NE-04', N_, 'MEDIUM', 'SCH-PAYOUT', 2, 'واریز به شرکت‌های سرویس مدارس'
        if a == 'ADV_REC' and cr: return 'SPEC', 'TT-NE-03', N_, 'HIGH', 'SCH-RECEIPT', 2, 'واریز سامانه سفیر مهر'
    if a == 'ADV_REC':
        if org == 'Terminals':
            if cr and R_CHEQUE_RECEIPT.search(t): return 'SPEC', 'TT-NE-13', N_, 'HIGH', 'ADV-CHQ', 2, 'دریافت چک اجاره/عوارض'
            return 'SPEC', 'TT-NE-13', N_, 'MEDIUM', 'ADV-T', 1, 'پیش‌دریافت خدمات پایانه'
        return 'SPEC', None, A_, 'LOW', 'ADV-X', 1, 'پیش‌دریافت خدمات بدون شرح سرویس مدارس'
    if a == 'NOTES_REC':
        if org == 'Terminals': return 'SPEC', 'TT-NE-14', N_, 'MEDIUM', 'NOTES-T', 1, 'تغییر وضعیت اسناد دریافتنی'
        return 'SPEC', None, A_, 'LOW', 'NOTES-X', 1, 'اسناد دریافتنی تاکسیرانی'
    if a == 'AR':
        if dr and any(x is not l and x['kol'] == k and x['moeeen'] == m and x['taf1'] == t1 and x['taf2'] == l['taf2'] and x['bes'] == l['bed'] for x in doc):
            return 'SETTLE', 'FE-68', P_, 'LOW', 'AR-OFFSET', 1, 'بدهکار هم‌مبلغ با بستانکار در همان حساب و همان سند (جابه‌جایی داخلی، خنثی)'
        if org == 'Terminals':
            if t1 == '7': return 'SPEC', 'TT-NE-32', N_, 'MEDIUM', 'AR-LOAN', 1, 'بازپرداخت وام خزانه (۱۱۳-۱-۷)'
            if t1 in ('4', '8'):
                if dr: return 'REV', 'TT-NE-15', N_, 'MEDIUM', 'AR-BILL', 2, 'مطالبه درآمد از بهره‌بردار/۵٪ فروش بلیط'
                return 'SPEC', 'FE-60', P_, 'MEDIUM', 'AR-COLLECT', 2, 'وصول مطالبه درآمدی'
            if dr:
                if R_INTERENT.search(l['ts']): return 'SETTLE', 'FE-68', P_, 'LOW', 'AR-INTERENT', 1, 'جابه‌جایی/تسویه حساب بین‌سازمانی (نه هزینه)'
                ev, conf, rid = recharge_event(l['ts'])
                return 'EXP', ev, ('EXISTING_EVENT_PROVISIONAL' if ev and ev.startswith('FE') else (N_ if ev else A_)), conf, rid, 1, 'هزینه تحمیل‌شده به شهرداری/شرکت‌ها (بدهکار ۱۱۳-۱-%s)' % t1
            return 'SETTLE', 'FE-68', P_, 'LOW', 'AR-OTHER-CR', 1, 'کاهش مطالبه (بازپرداخت/تسویه)'
        # Taxi
        if cr and re.search(r'واریزی|واریز', t): return 'SPEC', 'FE-68', P_, 'LOW', 'AR-T-RECEIPT', 1, 'واریزی شهرداری/سازمان‌ها (وصول مطالبه بین‌سازمانی)'
        return 'SPEC', None, A_, 'LOW', 'AR-T-X', 1, 'حساب دریافتنی بدون شرح تفکیک‌کننده'
    if a == 'AP':
        if org == 'Taxi' and t1 == '5' and cr: return 'SPEC', 'TT-NE-34', N_, 'MEDIUM', 'AP-UNIDENT', 2, 'بستانکاران افراد (نامشخص) — واریزی در انتظار شناسایی'
        if dr and not cr: return 'SPEC', 'TT-NE-11', N_, 'MEDIUM', 'AP-SETTLE', 1, 'تسویه حساب پرداختنی'
        return 'SPEC', None, A_, 'LOW', 'AP-X', 0, ''
    if a == 'STAFF_AR':
        return 'SPEC', 'TT-NE-10', N_, 'MEDIUM', 'STAFF-ADV', 2 if R_ADVANCE.search(t) else 1, 'مساعده/علی‌الحساب/کسر بدهی کارکنان'
    if a == 'TREASURY': return 'SPEC', 'FE-68', P_, 'MEDIUM', 'TREAS', 1, 'خزانه معین/انتقال وجه'
    if a == 'VAT_PAID' or a == 'VAT_REC': return 'SPEC', 'FE-11', P_, 'LOW', 'VAT', 1, 'مالیات بر ارزش افزوده'
    if a == 'TAX_WH':
        if R_PAYROLL.search(t) or R_TAX_SAL.search(t): return 'SPEC', 'FE-49', P_, 'MEDIUM', 'TAXWH-SAL', 2, 'مالیات حقوق'
        return 'SPEC', 'FE-11', P_, 'LOW', 'TAXWH', 1, 'مالیات تکلیفی'
    if a == 'INS_PAY':
        if R_INS_COMP.search(t): return 'SPEC', 'FE-51', P_, 'MEDIUM', 'INS-COMP', 2, 'بیمه تکمیل درمان'
        return 'SPEC', 'FE-48', P_, 'MEDIUM', 'INS-SOC', 1, 'حق بیمه پرداختنی'
    if a == 'DEDUCTION': return 'SPEC', 'TT-NE-30', N_, 'MEDIUM', 'DEDUCT', 1, 'کسورات حقوق'
    if a == 'STAFF_AP': return 'SPEC', 'FE-44', P_, 'MEDIUM', 'STAFF-AP', 2 if R_PAYROLL.search(t) else 1, 'بستانکار کارکنان (پرداخت حقوق)'
    if a == 'DEPOSIT':
        if t1 in ('1', '2'):
            if R_DEPOSIT_REFUND.search(t) or dr: return 'SPEC', 'FE-18', P_, 'MEDIUM', 'DEP-TENDER-R', 1, 'استرداد سپرده مناقصه/مزایده'
            return 'SPEC', 'FE-17', P_, 'MEDIUM', 'DEP-TENDER', 1, 'سپرده مناقصه/مزایده'
        if t1 == '3': return 'SPEC', ('FE-08' if dr else 'FE-07'), P_, 'MEDIUM', 'DEP-GOOD', 1, 'سپرده حسن انجام کار'
        if (org == 'Taxi' and t1 == '4') or (org == 'Terminals' and t1 == '6'):
            return 'SPEC', ('FE-10' if dr else 'FE-09'), P_, 'MEDIUM', 'DEP-INS', 1, 'سپرده بیمه'
        if org == 'Terminals' and t1 in ('5', '7'):
            return 'SPEC', ('TT-NE-18' if dr else 'TT-NE-17'), N_, 'MEDIUM', 'DEP-LEASE', 2 if R_DEPOSIT_REFUND.search(t) or not dr else 1, 'سپرده انجام تعهدات غرفات/شرکت‌ها'
        if org == 'Terminals' and t1 == '4': return 'SPEC', ('FE-08' if dr else 'FE-07'), P_, 'LOW', 'DEP-CONTR', 1, 'سپرده انجام تعهدات پیمانکاران'
        return 'SPEC', None, A_, 'LOW', 'DEP-X', 1, 'سایر سپرده‌ها'
    if a == 'PROV':
        if k == '223' and dr: return 'SPEC', 'FE-50', P_, 'MEDIUM', 'PROV-PAY', 1, 'پرداخت مزایای پایان خدمت از محل ذخیره'
        return 'SPEC', 'TT-NE-24', N_, 'MEDIUM', 'PROV', 1, 'ثبت ذخیره'
    if a == 'LOAN': return 'SPEC', 'TT-NE-32', N_, 'MEDIUM', 'LOAN-TRE', 1, 'تسهیلات خزانه'
    if a == 'OTHER_AP': return 'SPEC', None, A_, 'LOW', 'OTHER-AP', 0, 'سایر بستانکاران'
    if a == 'AR_OTHER': return 'SPEC', None, A_, 'LOW', 'AR-OTHER', 0, 'سایر بدهکاران/مطالبات'
    if a == 'DEP_GIVEN': return 'SPEC', None, A_, 'LOW', 'DEP-GIVEN', 0, 'سپرده نزد دیگران'
    if a == 'EQUITY': return 'SPEC', 'FE-70', P_, 'LOW', 'EQUITY', 1, 'حساب حقوق صاحبان سرمایه خارج از اسناد بستن'
    if a == 'ACC_DEPR': return 'SPEC', 'TT-NE-23', N_, 'MEDIUM', 'DEPR-ACC', 1, 'استهلاک انباشته'
    if a == 'INVEST': return 'SPEC', None, A_, 'LOW', 'INVEST', 0, 'سرمایه‌گذاری'
    if a == 'AP_NOTES': return 'SPEC', None, A_, 'LOW', 'AP-NOTES', 0, 'اسناد پرداختنی'
    if a == 'ACCRUED': return 'SPEC', 'TT-NE-24', N_, 'LOW', 'ACCRUED', 1, 'ذخیره هزینه پرداختنی'
    return 'SPEC', None, A_, 'LOW', 'SPEC-X', 0, 'ماهیت نامشخص'

def asset_line(org, l, t):
    k, m = l['kol'], l['moeeen']
    if re.search(r'اصلاح سند', t): return 'FE-70', 'EXISTING_EVENT_PROVISIONAL', 'LOW', 'AST-FIX', 1, 'اصلاح سند'
    if l['bed'] == 0 and l['bes'] > 0: return None, 'AMBIGUOUS_EVENT', 'LOW', 'AST-DISPOSE', 1, 'کاهش دارایی (فروش/اسقاط/ انتقال) — شکاف GAP-09'
    if k == '121' and m in ('3', '4', '5', '6', '7', '8', '10', '11'):
        return 'FE-23', 'EXISTING_EVENT_PROVISIONAL', 'MEDIUM', 'AST-EQUIP', 1, 'تجهیزات/اثاثیه/تأسیسات/وسیله نقلیه'
    if (k == '121' and m in ('1', '2', '9')) or k in ('120', '125'):
        return 'TT-NE-33', 'NEW_EVENT_CANDIDATE', 'MEDIUM', 'AST-PROP', 1, 'ملک/ساختمان/دارایی در جریان ساخت'
    return None, 'AMBIGUOUS_EVENT', 'LOW', 'AST-X', 0, 'دارایی نامشخص'

def prepay_line(org, l, t):
    if re.search(r'پیمانکار|قرارداد|صورت ?وضعیت', t): return 'FE-01', 'EXISTING_EVENT_PROVISIONAL', 'MEDIUM', 'PRE-CONTR', 1, 'پیش‌پرداخت پیمانکار'
    if R_TANKHAH.search(t) and l['kol'] == '116' and l['moeeen'] == '4': return 'FE-37', 'EXISTING_EVENT_PROVISIONAL', 'MEDIUM', 'PRE-TANKHAH', 1, 'تنخواه/علی‌الحساب کارپردازی'
    return 'TT-NE-29', 'NEW_EVENT_CANDIDATE', 'MEDIUM', 'PRE-GEN', 1, 'پیش‌پرداخت/علی‌الحساب/پیش‌فاکتور'

def inv_line(org, l, t):
    if l['bes'] > 0 or R_STORE_ISSUE.search(t): return 'TT-NE-21', 'NEW_EVENT_CANDIDATE', 'MEDIUM', 'INV-ISSUE', 1, 'خروج از انبار'
    if l['moeeen'] == '4': return 'FE-24', 'EXISTING_EVENT_PROVISIONAL', 'MEDIUM', 'INV-MAT', 1, 'خرید کالای اموالی/مصالح'
    return 'FE-22', 'EXISTING_EVENT_PROVISIONAL', 'MEDIUM', 'INV-CONS', 1, 'خرید کالای مصرفی'

# --------------------------------------------------------------------------------------------- engine
PRI = ['EXP', 'REV', 'ASSET', 'PREPAY', 'INV', 'SPEC', 'SETTLE', 'TRANSFER']
SAT = {'TT-NE-14', 'TT-NE-13', 'FE-11', 'TT-NE-23', 'TT-NE-08'}  # satellite postings that do not make a document composite on their own
PAYROLL_FAMILY = {'FE-44', 'FE-45', 'FE-46', 'FE-47', 'FE-48', 'FE-49', 'FE-50', 'FE-51', 'FE-52', 'TT-NE-30'}
SETTLE_EVENTS = {'TT-NE-11', 'FE-68', 'TT-NE-10', 'FE-11', 'FE-37'}   # payment/settlement legs: yield to any expense/revenue/asset driver
FAMILY = {}
for e in ('FE-44', 'FE-45', 'FE-46', 'FE-47', 'FE-48', 'FE-49', 'FE-50', 'FE-51', 'FE-52', 'TT-NE-30'): FAMILY[e] = 'PAYROLL'
for e in ('FE-03', 'TT-NE-12', 'FE-07', 'FE-08', 'FE-09', 'FE-10', 'FE-01', 'TT-NE-29'): FAMILY[e] = 'CONTRACTOR_SETTLEMENT'
for e in ('FE-60', 'TT-NE-01', 'TT-NE-05', 'TT-NE-15', 'FE-19', 'TT-NE-28', 'TT-NE-13', 'TT-NE-14', 'TT-NE-34'): FAMILY[e] = 'REVENUE'
for e in ('TT-NE-03', 'TT-NE-04', 'TT-NE-06', 'TT-NE-07'): FAMILY[e] = 'SCHOOL_SERVICE'
for e in ('FE-70',): FAMILY[e] = 'PERIOD_END'
FAMILY['EXC-01'] = 'REVENUE'
STRONG_SHARE = 0.10  # a class is a document driver when its own-side amount is >= 10% of the document's debit total
RANK = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
R_INTERENT = re.compile(r'جابجایی حساب|انتقال حساب|انتقال اقلام|تهاتر|ثبت واریزی|استرداد تنخواه|اصلاح سند')
R_GUAR = re.compile(r'ضمانت ?نامه|چک ضمانت|ضمانتنامه')
R_GUAR_END = re.compile(r'ابطال|عودت|استرداد|مسترد')

R_PAYCOMP = re.compile(r'کارمند|کارگر|فوق ?العاده|فوق الهاده|عائله|عایله|اولاد|هزینه مسکن|حق مسکن|ایاب|حق تاهل|مزد شغل|نوبت کاری|رده تحصیلی|برجستگی|خانوار|حق جذب|مامورین|تعطیل کاری|اضافه ?کار|مزایا')
R_MAT = re.compile(r'مصالح|شن|سیمان|آهن|میلگرد|ورق|نبشی|رنگ|گچ|بلوک|درب|پنجره|کابل|پنل|لوله|ایزوگام|فولاد|کاشی|لایت|برق|مخزن|پمپ')
R_CONTR = re.compile(r'پیمانکار|اجرا|سایبان|سقف|نصب|ساخت|جابجایی|تعمیر|ژنراتور')
R_CEREM = re.compile(r'جشن|مراسم|هدیه|بلیط|غذا|کیک|آبمیوه|خشکبار|نورپردازی|داربست|پذیرایی|اجرا|کلاه|کفش|چراغ|حمل')
R_PROP = re.compile(r'آپارتمان|زمین|ملک')
P2_, N2_ = 'EXISTING_EVENT_PROVISIONAL', 'NEW_EVENT_CANDIDATE'

def v2_adjust(org, i, lines, r):
    """Audited-event remap (v2).  Returns (res tuple, lifecycle_action).  See rules.EVENT_REVIEW for the rationale of each remap."""
    cls, ev, st, conf, rid, evn, basis = r
    l = lines[i]; a = l['acat']; ts = l['ts']; t = l['t']; dr = l['bed'] > 0; cr = l['bes'] > 0; act = None
    if ev == 'TT-NE-14' or (a == 'NOTES_REC' and ev == 'TT-NE-13'):
        ev = 'TT-NE-13'; m = l['moeeen']
        act = {'5': ('RECEIVE_INSTRUMENT' if dr else 'SEND_FOR_COLLECTION'), '6': ('SEND_FOR_COLLECTION' if dr else 'CLEAR_COLLECTED'), '7': 'RETURN_DISHONOURED'}.get(m, 'INSTRUMENT_POSTING')
    elif ev == 'TT-NE-13':
        act = 'RECEIVE_INSTRUMENT' if cr else 'APPLY_PREPAYMENT'
    if ev == 'TT-NE-06': ev = 'TT-NE-03'; act = 'REFUND'
    elif ev == 'TT-NE-03': act = 'COLLECT'
    elif ev == 'TT-NE-04': act = 'PAYOUT'
    elif ev == 'TT-NE-07': ev = 'TT-NE-04'; act = 'PAYOUT_EARMARKED'
    if org == 'Taxi' and a in ('ADV_REC', 'AR') and 'انتقال مانده' in t and (ev is None or ev in ('TT-NE-04',)):
        cls, ev, st, conf, rid, act = 'SPEC', 'TT-NE-04', N2_, 'MEDIUM', 'V2-AGENCY-OFFSET', 'OFFSET_AGENCY_BALANCE'; basis = 'تهاتر مانده حساب شرکت‌ها با پیش‌دریافت سامانه'
    if cls == 'REV' and org == 'Taxi' and R_PREREC_CLOSE.search(t):
        ev, st, conf, rid, act = 'TT-NE-05', N2_, 'MEDIUM', 'V2-RETAINED-SHARE', 'RETAINED_SHARE_RECOGNITION'; basis = 'بستن پیش‌دریافت سامانه به درآمد (سهم سازمان)'
    if ev == 'TT-NE-12':
        stmt = any(x['acat'] in ('INS_PAY', 'DEPOSIT') for x in lines) or re.search(r'صورت ?وضعیت|صورتحساب', ts)
        if stmt: ev, st, conf, act = 'FE-03', P2_, 'LOW', 'SERVICE_STATEMENT'   # rule id kept (Terminals cost-center eligibility keys on the TX- prefix)
        else: act = 'GENERIC_SERVICE'
    if ev in ('TT-NE-23', 'TT-NE-24'):
        act = 'DEPRECIATION' if ev == 'TT-NE-23' else 'PROVISION_OR_ACCRUAL'; ev, st, conf = 'FE-70', P2_, 'LOW'
    if ev == 'TT-NE-26': ev, st, conf, act = 'FE-22', P2_, 'LOW', 'HOSPITALITY'
    if ev == 'TT-NE-09':
        if re.search(r'سامانه هوشمند|تعزیرات|عودت', ts): ev, st, conf, act = None, 'AMBIGUOUS_EVENT', 'LOW', 'DAMAGES_OR_REFUND'
        elif R_CEREM.search(ts) and not re.search(r'بیمه', ts): ev, st, conf, act = 'FE-22', P2_, 'LOW', 'CEREMONY'
        else: act = 'INSURANCE_SUPPORT'
    if ev == 'TT-NE-34': ev, st, conf, act = 'EXC-01', 'PENDING_IDENTIFICATION', 'MEDIUM', 'SUSPENSE_RECEIPT'
    if cls == 'PREPAY':
        if cr and not dr: cls, ev, st, conf, act = 'WEAK', None, 'COMPONENT', 'MEDIUM', 'SETTLE_ADVANCE'
        elif dr and R_PROP.search(ts): ev, st, conf, act = 'TT-NE-33', N2_, 'MEDIUM', 'ADVANCE_FOR_PROPERTY'
        elif dr: act = 'ISSUE_ADVANCE'
    if cls == 'ASSET' and ev == 'TT-NE-33':
        if l['kol'] == '120' or (l['kol'] == '121' and l['moeeen'] == '1') or R_PROP.search(ts): act = 'PROPERTY_ACQUISITION'
        elif R_MAT.search(ts): ev, st, conf, act = 'FE-24', P2_, 'LOW', 'CAPITALIZED_MATERIALS'
        elif R_CONTR.search(ts): ev, st, conf, act = 'FE-03', P2_, 'LOW', 'CAPITALIZED_CONTRACTOR_WORK'
        else: ev, st, conf, act = None, 'AMBIGUOUS_EVENT', 'LOW', 'CAPITALIZED_UNSPECIFIED'
    if ev == 'FE-11' and cls == 'EXP': cls = 'SETTLE'
    if ev == 'TT-NE-10': act = 'ISSUE' if dr else 'RECOVER'
    if ev == 'TT-NE-17': act = 'RECEIVE_DEPOSIT'
    if ev == 'TT-NE-18': act = 'REFUND_DEPOSIT'
    if ev == 'TT-NE-11': act = 'PAYMENT'
    return (cls, ev, st, conf, rid, evn, basis), act


cols = ['sid', 'doc_key', 'org', 'fy', 'date', 'des', 'des_norm', 'kol', 'moeeen', 'taf1', 'taf2', 'bed', 'bes', 'sharh_norm', 'f1', 'markaz', 'vahed']
rows = cur.execute('SELECT sid,doc_key,org,fy,date,des,des_norm,kol,moeen,taf1,taf2,bed,bes,sharh_norm,f1,markaz,vahed FROM sanad ORDER BY org,fy,src_row').fetchall()
docs = collections.OrderedDict()
for r in rows:
    docs.setdefault(r[1], []).append(dict(zip(cols, r)))

def own_amount(cls, l):
    if cls in ('EXP', 'ASSET', 'PREPAY', 'INV'): return l['bed'] + l['bes']  # reversals count with the same sign-free magnitude
    return max(l['bed'], l['bes'])

doc_out, line_out = [], []
own_map = {}
act_map = {}
for dk, lines in docs.items():
    org, fy = lines[0]['org'], lines[0]['fy']
    kind = doc_kind([l['des_norm'] or '' for l in lines])
    bed_total = sum(l['bed'] for l in lines)
    dates = sorted(l['date'] for l in lines)
    if kind != 'REGULAR':
        sub = {'OPENING': 'سند افتتاحیه', 'CLOSING_PERMANENT': 'سند اختتامیه', 'CLOSING_TEMPORARY': 'بستن حساب‌های موقت (انتقال به سود و زیان)',
               'INTERNAL_SETTLEMENT': 'بستن/تهاتر حساب‌های فی‌مابین'}[kind]
        ev, st = ('TT-NE-19', 'NEW_EVENT_CANDIDATE') if kind == 'INTERNAL_SETTLEMENT' else (None, 'NOT_AN_OPERATIONAL_EVENT')
        doc_out.append((dk, org, fy, kind, len(lines), bed_total, dates[0], dates[-1], ev, st, 0, '[]', 'HIGH', 'KIND-' + kind, sub, 0 if ev is None else 1))
        for l in lines:
            a = acat(org, l['kol'], l['moeeen'], l['taf1'])
            line_out.append((l['sid'], dk, org, fy, 'CLOSING' if kind != 'INTERNAL_SETTLEMENT' else 'SETTLEMENT', a, ev, st, 'HIGH', 'KIND-' + kind, 1, sub, ev, st, l['bed'], l['bes'], 0 if ev is None else 1))
        continue

    for l in lines:
        l['acat'] = acat(org, l['kol'], l['moeeen'], l['taf1'])
        l['t'] = T(l['des_norm'], l['sharh_norm'])
        l['ts'] = l['sharh_norm'] or l['des_norm'] or ''   # line-level narration first (Des is often a document-wide payee list)
    # ---- memo-only documents (off-balance guarantees etc.) ----
    if all(l['acat'] == 'MEMO' for l in lines):
        jt = ' '.join(l['t'] for l in lines)
        if R_GUAR.search(jt):
            ev = 'FE-16' if R_GUAR_END.search(jt) else 'FE-15'
            reason = 'ضمانت‌نامه/چک ضمانت شرکت‌های حمل‌ونقل یا بهره‌برداران در حساب انتظامی (خارج از ترازنامه) — ' + ('ابطال/عودت' if ev == 'FE-16' else 'اخذ/تمدید')
            out = ('EXISTING_EVENT_PROVISIONAL', 'LOW', 'MEMO-GUARANTEE')
        else:
            ev, reason, out = None, 'سند انتظامی بدون رویداد عملیاتی', ('NOT_AN_OPERATIONAL_EVENT', 'HIGH', 'MEMO-ONLY')
        doc_out.append((dk, org, fy, 'REGULAR', len(lines), bed_total, dates[0], dates[-1], ev, out[0], 0, json.dumps([ev] if ev else []), out[1], out[2], reason, 1 if ev else 0))
        for l in lines:
            line_out.append((l['sid'], dk, org, fy, 'MEMO', l['acat'], ev, out[0], out[1], out[2], 1, reason, ev, out[0], l['bed'], l['bes'], 1 if ev else 0))
        continue

    res = {}
    for i, l in enumerate(lines):
        a, t = l['acat'], l['t']
        if a == 'MEMO':
            res[i] = ('MEMO', None, 'NOT_AN_OPERATIONAL_EVENT', 'HIGH', 'MEMO', 1, 'حساب انتظامی (۹۱۸/۹۱۹)'); continue
        if a in ('BANK', 'TANKHAH'):
            res[i] = ('COMP', None, 'COMPONENT', 'HIGH', 'SETTLE-CASH', 1, 'سطر نقد/بانک/تنخواه'); continue
        if a == 'EXP': res[i] = ('EXP',) + exp_line(org, l, l['ts']); continue
        if a in ('REV_OP', 'REV_NONOP'): res[i] = ('REV',) + rev_line(org, l, t); continue
        if a == 'FIXED_ASSET': res[i] = ('ASSET',) + asset_line(org, l, t); continue
        if a == 'PREPAY': res[i] = ('PREPAY',) + prepay_line(org, l, t); continue
        if a == 'INVENTORY': res[i] = ('INV',) + inv_line(org, l, t); continue
        cls, ev, st, conf, rid, evn, basis = spec_line(org, l, t, lines)
        if ev is None and cls == 'SPEC': cls = 'WEAK'   # counter-leg with no event evidence of its own
        elif ev in SETTLE_EVENTS and cls in ('SPEC', 'SETTLE'): cls = 'SETTLE'
        res[i] = (cls, ev, st, conf, rid, evn, basis)
    if V2:
        for i in list(res):
            if res[i][0] in ('COMP', 'MEMO'): continue
            res[i], act_ = v2_adjust(org, i, lines, res[i])
            if act_: act_map[lines[i]['sid']] = act_

    # ---- driver-class selection (priority among materially large classes) ----
    cls_amt = collections.Counter()
    for i, l in enumerate(lines):
        c = res[i][0]
        if c in PRI: cls_amt[c] += own_amount(c, l)
    total = max(bed_total, 1)
    strong = [c for c in PRI if cls_amt.get(c, 0) >= STRONG_SHARE * total and cls_amt.get(c, 0) > 0]
    if any(c not in ('SETTLE', 'TRANSFER') for c in cls_amt):      # settlement legs only drive a document when nothing else is present
        strong = [c for c in strong if c not in ('SETTLE', 'TRANSFER')] or [c for c in PRI if c in cls_amt and c not in ('SETTLE', 'TRANSFER')][:1]
    if not strong and cls_amt:
        strong = [max(cls_amt, key=lambda c: (cls_amt[c], -PRI.index(c)))]
    if not cls_amt:
        weak = [i for i, r in res.items() if r[0] == 'WEAK']
        if weak:
            drivers = set(weak)
        else:  # pure cash/bank/tankhah document → transfer
            ev = 'FE-37' if any(l['acat'] == 'TANKHAH' for l in lines) else 'FE-68'
            for i in res:
                if res[i][0] == 'COMP':
                    res[i] = ('TRANSFER', ev, 'EXISTING_EVENT_PROVISIONAL', 'MEDIUM', 'XFER-CASH', 1, 'جابه‌جایی بین حساب‌های نقد/بانک/تنخواه')
            drivers = {i for i in res if res[i][0] == 'TRANSFER'}
    else:
        drivers = {i for i, r in res.items() if r[0] in strong}
    # ---- document-level outcome ----
    amt = collections.Counter()
    for i in drivers:
        amt[res[i][1] or 'NONE'] += own_amount(res[i][0], lines[i])
    business = {e for e in amt if e != 'NONE' and e not in SAT}
    sats = {e for e in amt if e != 'NONE' and e in SAT}
    minor = sorted({res[i][1] for i in res if i not in drivers and res[i][0] in PRI and res[i][1] and res[i][1] != (max(business or sats, key=lambda x: amt[x]) if (business or sats) else None)})
    pool = business or sats
    primary = max(pool, key=lambda e: (amt[e], 0)) if pool else None
    fams = {FAMILY.get(e, e) for e in business}
    multi = len(fams) > 1                         # >1 distinct business-event family → genuine COMPOSITE_TRANSACTION
    multi_event = len(business) > 1               # >1 event inside the document (same-family components allowed)
    prim_res = None
    if primary:
        prim_res = max((res[i] for i in drivers if res[i][1] == primary), key=lambda r: RANK[r[3]])
    if primary is None:
        outcome, conf, rid, reason = 'AMBIGUOUS_EVENT', 'LOW', 'DOC-NOPRIM', 'هیچ سطر محرک رویداد قابل تعیین نیست'
    elif multi:
        outcome, conf, rid, reason = 'COMPOSITE_TRANSACTION', 'MEDIUM', 'DOC-MULTI', 'چند رویداد کسب‌وکاری متمایز در یک سند: ' + ' + '.join(sorted(business))
    else:
        outcome, conf, rid, reason = prim_res[2], prim_res[3], 'DOC-' + prim_res[4], prim_res[6]
        if multi_event: reason += ' (اجزای هم‌خانواده در یک سند: ' + ' + '.join(sorted(business)) + ')'
    if minor: reason += ' | رویدادهای فرعی کمتر از ۱۰٪ مبلغ سند: ' + ' + '.join(minor)
    doc_out.append((dk, org, fy, 'REGULAR', len(lines), bed_total, dates[0], dates[-1], primary, outcome, 1 if outcome == 'COMPOSITE_TRANSACTION' else 0,
                    json.dumps(sorted(business | sats)), conf, rid, reason, 0 if outcome == 'EXISTING_EVENT_CONFIRMED' else 1))
    for i, l in enumerate(lines):
        cls, ev, st, conf, rid, evn, basis = res[i]
        own_map[l['sid']] = ev
        if cls == 'MEMO':
            line_out.append((l['sid'], dk, org, fy, 'MEMO', l['acat'], None, 'NOT_AN_OPERATIONAL_EVENT', 'HIGH', rid, 1, basis, primary, outcome, l['bed'], l['bes'], 0))
        elif i in drivers:
            line_out.append((l['sid'], dk, org, fy, 'DRIVER', l['acat'], ev, st, conf, rid, evn, basis, primary, outcome, l['bed'], l['bes'], 0 if st == 'EXISTING_EVENT_CONFIRMED' else 1))
        else:
            own = (' | شاهد خود سطر: %s' % ev) if ev and ev != primary else ''
            line_out.append((l['sid'], dk, org, fy, 'COMPONENT', l['acat'], primary, 'COMPONENT_OF_' + outcome, 'MEDIUM', rid, evn, (basis or '') + own, primary, outcome, l['bed'], l['bes'], 0 if outcome == 'EXISTING_EVENT_CONFIRMED' else 1))

cur.executemany('INSERT INTO doc_class VALUES(' + ','.join('?' * 16) + ')', doc_out)
cur.executemany('INSERT INTO line_event VALUES(' + ','.join('?' * 17) + ')', line_out)
cur.execute('ALTER TABLE line_event ADD COLUMN lifecycle_action')
cur.executemany('UPDATE line_event SET lifecycle_action=? WHERE sid=?', [(v, k) for k, v in act_map.items()])
cur.execute('ALTER TABLE line_event ADD COLUMN own_event')
cur.executemany('UPDATE line_event SET own_event=? WHERE sid=?', [(v, k) for k, v in own_map.items()])
cur.execute('UPDATE line_event SET own_event=event_id WHERE own_event IS NULL AND role IN ("CLOSING","SETTLEMENT")')
cur.execute('CREATE INDEX i_le_doc ON line_event(doc_key)')
cur.execute('CREATE INDEX i_le_ev ON line_event(event_id)')
con.commit()
print('docs', len(doc_out), 'lines', len(line_out))
for r in cur.execute('SELECT org,fy,outcome,count(*) FROM doc_class GROUP BY 1,2,3 ORDER BY 1,2,4 DESC'): print(r)
