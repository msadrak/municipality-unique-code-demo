"""v2.1 decision matrix = v2 matrix (rows regenerated from the v2.1 database / EVENT_REVIEW) + the decisions raised by the v2.1 audit."""
from decisions_v2 import build_decisions, COLS, VER, PROV, AUTH


def build_decisions_v21(q, one):
    D = [list(r) for r in build_decisions(q, one)]
    n = lambda s, *a: f'{one(s, *a):,}'
    cov = {(r[0], r[1]): r for r in q("SELECT version,organization,eligible_lines,selected_high_lines,selected_medium_lines,selected_low_lines,multiple_lines,insufficient_lines FROM cc_confidence_coverage")}
    low = {o: cov[('v2.1', o)][5] for o in ('Taxi', 'Terminals')}
    unres = {o: cov[('v2.1', o)][6] + cov[('v2.1', o)][7] for o in ('Taxi', 'Terminals')}
    for r in D:
        if r[0] == 'CD-08':
            r[3] = r[3] + f" در v2.1: حقوق پایانه‌ها (MEDIUM) به CC-1301 با سابقه v4؛ ردیف‌های حقوقی با اطمینان LOW پس از ممیزی به نامزدهای چندگانه بازگشتند."
    D.append(['CD-PEO', 'هر دو', 'استهلاک و ذخایر: عملیات حسابداری پایان دوره (PEO-01/PEO-02) خارج از FE-70 و خارج از رویدادهای canonical؛ مصرف ذخیره = تسویه بدهی (TT-NE-11)',
              f"تعریف FE-70 در v7.1: «ثبت‌های اصلاحی، انتقال مانده، بستن حساب‌های موقت و اسناد اختتامیه». استهلاک دوره‌ای (بدهکار ۶۱۳-۲۰ / بستانکار ۱۲۲) و شناسایی ذخیره (بستانکار ۲۱۲-۲/۲۲۳/۲۱۴/۲۱۷) نه اصلاح‌اند نه بستن حساب. v2.1: {n('SELECT count(*) FROM fe70_review WHERE v21_event=?', 'PEO-01')} خط PEO-01، {n('SELECT count(*) FROM fe70_review WHERE v21_event=?', 'PEO-02')} خط PEO-02، {n('SELECT count(*) FROM fe70_review WHERE v21_event=?', 'TT-NE-11')} خط مصرف ذخیره → TT-NE-11.",
              'ثبت PEO-01/02 به‌عنوان «عملیات حسابداری پایان دوره» در کاتالوگ جداگانه (نه رویداد پیش‌حسابداری)؛ بدون شناسهٔ FE جدید؛ FE-70 فقط برای اصلاح/انتقال/بستن',
              'الف) رویداد canonical مستقل؛ ب) زیرنوع پُست حسابداری؛ ج) گسترش تعریف FE-70 (مخالف تعریف فعلی)', 'ماتریس رویداد-مرکز؛ بدون اثر بر مبالغ؛ مرکز هزینه استهلاک نیازمند ثبت دارایی',
              'TAXI-1404-2038 (استهلاک)، TAXI-1405-425 (استهلاک: توجه به بستانکار ۱۲۲-۴ در دو ردیف اثاثیه)، TAXI-1404-72 (مصرف ذخیره)', 'حسابدار ارشد شهرداری؛ کمیته رویداد مالی', 'کمیته رویداد مالی', 'خیر', AUTH, 'تصمیم دربارهٔ رده‌بندی عملیات پایان دوره و شمول مدل حسابداری'])
    D.append(['CD-LOWCC', 'هر دو', 'سیاست نهایی برای ردیف‌های مرکز هزینه با اطمینان LOW و ردیف‌های چندنامزد/ناکافی پس از ممیزی v2.1',
              f"ممیزی ۱٬۰۱۶ تخصیص LOW جدید: ردیف‌های LOW باقی‌مانده {low}؛ ردیف‌های حل‌نشده (چندنامزد+ناکافی) {unres}. شواهد: low_confidence_cc_audit_v2.1.xlsx.",
              'LOW به‌عنوان تحلیلی/پیشنهادی بماند؛ استفاده در گزارش‌های مدیریتی فقط با برچسب اطمینان؛ مراکز نامزد را کارشناسان مراکز هزینه نهایی کنند',
              'پذیرش نامزد پیش‌فرض؛ ایجاد قواعد جدید با شواهد بیشتر؛ ثبت منبع فعالیت در سامانه حسابداری', 'پوشش «پشتیبانی‌شده با شاهد» (MEDIUM+HIGH) جدا از پوشش تحلیلی گزارش می‌شود',
              'ممیزی v2.1: انبار، پذیرایی، قواعد واژه‌محور', 'دبیر کارگروه مراکز هزینه؛ مدیر مالی هر سازمان', 'کارگروه مراکز هزینه', 'خیر', AUTH, 'بازبینی کارشناسی نامزدها؛ ثبت کد فعالیت در منبع'])
    return [tuple(r) for r in D]
