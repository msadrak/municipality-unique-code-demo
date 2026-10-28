"""Build the client-only Persian PDF handover, with embedded fonts and local rendering.

Reads audited metrics only; never mutates source/audit/v1 workbooks. Windows' native
PDF renderer provides page images without uploading financial data.
"""
from pathlib import Path
import json
import subprocess
import hashlib
import re

import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageStat
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4

BASE = Path(__file__).resolve().parents[1]
DELIVERY = BASE / 'data/deliverables'
AUDIT = DELIVERY / 'journal_1404_enrichment_v1_independent_audit'
FINAL = DELIVERY / 'FINAL_CLIENT_HANDOVER_1404'
BUILD = DELIVERY / 'handover_1404_build'
FONT = Path('C:/Windows/Fonts/tahoma.ttf')
BOLD = Path('C:/Windows/Fonts/tahomabd.ttf')
INK = HexColor('#17334b')
TEAL = HexColor('#087b86')
GRAY = HexColor('#526473')
PALE = HexColor('#edf4f7')
W, H = A4
LEFT, RIGHT = 46, W - 46
NUM = str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹')

def number(value):
    return f'{value:,}'.translate(NUM)

def fa(text):
    return get_display(arabic_reshaper.reshape(str(text)), base_dir='R')

class Document:
    def __init__(self, filename, title, pages):
        self.path = FINAL / filename
        self.c = canvas.Canvas(str(self.path), pagesize=A4, pageCompression=1)
        self.c.setTitle(title)
        self.c.setAuthor('Municipality financial-data handover')
        self.title, self.pages, self.page, self.y = title, pages, 0, 0
        self.bounds = []

    def new(self, subtitle):
        if self.page:
            self.c.showPage()
        self.page += 1
        c = self.c
        c.setFillColor(INK)
        c.rect(0, H - 94, W, 94, fill=1, stroke=0)
        c.setFillColor(HexColor('#ffffff'))
        c.setFont('PersianBold', 16)
        c.drawRightString(RIGHT, H - 39, fa(self.title))
        c.setFont('Persian', 10)
        c.drawRightString(RIGHT, H - 66, fa(subtitle))
        c.setStrokeColor(TEAL)
        c.setLineWidth(2)
        c.line(LEFT, 47, RIGHT, 47)
        c.setFillColor(GRAY)
        c.setFont('Persian', 8)
        c.drawRightString(RIGHT, 30, fa('محرمانه | تحویل تحلیلی سال ۱۴۰۴ | نیازمند تصمیم مرجع مجاز'))
        c.drawString(LEFT, 30, fa(f'صفحه {number(self.page)} از {number(self.pages)}'))
        self.y = H - 118

    def lines(self, text, size=10.5, width=None, bold=False):
        font = 'PersianBold' if bold else 'Persian'
        width = width or RIGHT - LEFT
        result = []
        for paragraph in str(text).split('\n'):
            line = ''
            for word in paragraph.split():
                test = (line + ' ' + word).strip()
                if pdfmetrics.stringWidth(fa(test), font, size) <= width:
                    line = test
                else:
                    if not line:
                        raise ValueError('Unwrappable word: ' + word)
                    result.append(line)
                    line = word
            result.append(line)
        return result

    def text(self, text, size=10.5, bold=False, color=INK, gap=8):
        c = self.c
        lines = self.lines(text, size, bold=bold)
        leading = size * 1.75
        if self.y - len(lines) * leading < 64:
            raise ValueError(f'Page {self.page} overflow in {self.path.name}: {text[:50]}')
        c.setFillColor(color)
        c.setFont('PersianBold' if bold else 'Persian', size)
        for line in lines:
            c.drawRightString(RIGHT, self.y, fa(line))
            self.bounds.append({'page': self.page, 'baseline': round(self.y, 2), 'width': round(pdfmetrics.stringWidth(fa(line), 'PersianBold' if bold else 'Persian', size), 2)})
            self.y -= leading
        self.y -= gap

    def heading(self, text):
        self.text(text, 12, True, TEAL, 9)

    def table(self, rows, widths=(0.66, 0.34)):
        total = RIGHT - LEFT
        for i, row in enumerate(rows):
            # Rows supplied in logical right-to-left order.
            wrapped = [self.lines(v, 10, total * fraction - 20, bold=i == 0) for v, fraction in zip(row, widths)]
            height = max(map(len, wrapped)) * 17 + 15
            if self.y - height < 64:
                raise ValueError('Table overflow: ' + self.path.name)
            c = self.c
            c.setFillColor(INK if i == 0 else (PALE if i % 2 else HexColor('#ffffff')))
            c.rect(LEFT, self.y - height, total, height, fill=1, stroke=0)
            x = RIGHT
            for lines, fraction in zip(wrapped, widths):
                c.setFont('PersianBold' if i == 0 else 'Persian', 10)
                c.setFillColor(HexColor('#ffffff') if i == 0 else INK)
                for j, line in enumerate(lines):
                    c.drawRightString(x - 10, self.y - 17 - j * 17, fa(line))
                x -= total * fraction
            self.y -= height
        self.y -= 16

    def ltr(self, text, size=8.2):
        self.c.setFillColor(GRAY)
        self.c.setFont('Persian', size)
        if pdfmetrics.stringWidth(text, 'Persian', size) > RIGHT - LEFT:
            raise ValueError('Filename line too wide: ' + text)
        self.c.drawString(LEFT, self.y, text)
        self.y -= 22

    def save(self):
        if self.page != self.pages:
            raise ValueError('Unexpected page count')
        self.c.save()
        return {'filename': self.path.name, 'expected_pages': self.pages, 'bytes': self.path.stat().st_size, 'sha256': hashlib.sha256(self.path.read_bytes()).hexdigest(), 'minimum_body_baseline': min(x['baseline'] for x in self.bounds), 'font_embedding': '/FontFile2' in self.path.read_bytes().decode('latin1')}


def management(m, e, s):
    d = Document('02_Management_Report_FA.pdf', 'گزارش مدیریتی تکمیل دفتر روزنامه ۱۴۰۴', 6)
    d.new('A — جمع‌بندی مدیریتی و وضعیت مجاز استفاده')
    d.heading('A | تصمیم مدیریتی در یک نگاه')
    d.text('بسته حاضر، نسخه موجود تکمیل‌شده دفتر روزنامه و شواهد ممیزی مستقل آن را برای بررسی مدیریتی و کارشناسی تحویل می‌دهد. نتیجه ممیزی: قابل استفاده برای تحلیل محدود و بازبینی، مشروط به رسیدگی؛ هنوز قابل قبول برای تحویل رسمی و حاکمیتی به سامانه برنامه‌ریزی منابع سازمانی نیست.', 12, True)
    d.text('کدگذاری و داده‌های تکمیلی، پیشنهادی و مبتنی بر شواهد محلی‌اند؛ نه تأیید حسابداری، نه مصوبه کمیته و نه داده اصلی مصوب سامانه. هیچ تأیید مرجع مجاز از پیش درج نشده است. هیچ نسخه دوم غنی‌سازی یا اصلاح خودکار در این تحویل ایجاد نشده است.')
    d.text('هدف، تکمیل ستون‌های سبزرنگ وضعیت مطلوب بر پایه دفتر روزنامه منبع و مراجع بومی موجود است؛ روش، انتشار ساخت‌یافته همان ردیف و بازیابی مرجع با کنترل زمینه حسابداری، سپس ممیزی مستقل بوده است. نسخه تکمیل‌شده پیشنهادی — نیازمند بازبینی و تأیید کارشناسی.', 10.5, True)
    d.table([('شاخص کلیدی', 'مقدار ممیزی مستقل'), ('ردیف‌های دفتر روزنامه', number(m['measured']['rows'])), ('زوج یکتای منطقه و سند', number(m['unique_region_document_pairs'])), ('سلول‌های افزوده‌شده', number(sum(m['added'].values()))), ('ردیف‌های هزینه‌ای', number(m['measured']['expense'])), ('نمونه معنایی مبتنی بر ریسک', number(s['distinct_sample_rows']))])
    d.text('پیام تصمیم: حفظ نسخه فعلی، بررسی موارد ارجاعی، دریافت داده‌های مرجع مصوب و سپس تصمیم مستند درباره پذیرش یا اصلاح. پر بودن سلول، معادل صحت هویت یا مجاز بودن رابطه مالی نیست.', 11, True)
    d.new('B — دامنه کار و حفظ داده‌های اصلی')
    d.heading('B | دامنه و جمعیت داده')
    d.text('منبع: «دفتر روزنامه 1404 - با اشخاص جدید.xlsx». کار شامل تکمیل محدود ابعاد دارای شاهد، تطبیق مستقل جمعیت و بررسی معنایی ریسک‌محور است. فایل اصلی، نسخه اول و فایل‌های ممیزی محفوظ‌اند؛ فایل تحویلی دفتر روزنامه، کپی همسان نسخه اول است.')
    d.text('جمعیت کار: ۵۵۳٬۶۶۷ ردیف، ۷۵٬۲۷۹ زوج منطقه و سند، ۴۶٬۰۱۵ ردیف هزینه‌ای و ۲۰ فیلد هدف سبزرنگ. تکمیل صرفاً در محل دارای شاهد انجام شده؛ شمارش پرشدگی را نباید با پذیرش رسمی یکی دانست.')
    d.table([('کنترل', 'نتیجه'), ('ردیف‌های مقایسه‌شده مستقل', number(m['measured']['rows'])), ('سلول‌های افزوده‌شده با شاهد تطبیق', '۱۹۸٬۳۳۶'), ('نقض حفظ داده‌های اصلی', 'صفر'), ('مجموع بدهکار؛ منبع و نسخه تکمیل‌شده', number(int(e['financial_totals']['source_Q'])) + ' ریال'), ('مجموع بستانکار؛ منبع و نسخه تکمیل‌شده', number(int(e['financial_totals']['source_R'])) + ' ریال'), ('تغییر داده‌های اشخاص موجود', 'صفر ردیف')])
    d.text('برابری مبالغ، کنترل حفاظتی است و به‌تنهایی تأیید ماهیت اقتصادی طبقه‌بندی‌ها نیست. مقادیر و فرمول‌های اصلی دستکاری نشده‌اند. داده‌های بانک از فیلد ساخت‌یافته همان ردیف منتشر شده‌اند؛ مرکز هزینه از مرجع بومی با محدودسازی زمینه‌ای به دست آمده است.')
    d.text('دامنه مجاز: مرور کارشناسی، تحلیل محدود و آماده‌سازی تصمیم. خارج از دامنه: ثبت خودکار سند، ادغام هویت اشخاص، تصویب نگاشت سامانه یا اعمال جایگزین پیشنهادی بدون اختیار رسمی.', 11, True)
    d.new('C — نتایج تکمیل و مسیر تعیین مرکز هزینه')
    d.heading('C | خروجی واقعی تکمیل')
    d.table([('نوع تکمیل', 'تعداد'), ('ردیف دریافت‌کننده کد مرکز هزینه', '۲۳٬۲۴۳'), ('سلول افزوده‌شده مرکز هزینه؛ کد و عنوان', '۴۷٬۶۸۸'), ('نام بانک منتشرشده از همان ردیف', '۱۵۰٬۶۴۸'), ('کل سلول‌های افزوده‌شده', '۱۹۸٬۳۳۶')])
    d.text('از ردیف‌های تکمیل‌شده مرکز هزینه، ۱۹٬۸۸۶ ردیف از ارتباط اولیه یکتا و ۳٬۳۵۷ ردیف از ارتباط اولیه چندگانه با استفاده از زمینه حسابداری محدود شده‌اند. این کاهش ابهام، تأیید کارشناسی یا اجازه ثبت سامانه نیست.')
    d.text('پوشش فیزیکی ۲۰ فیلد هدف از ۳۶٫۷۶۷۷٪ به ۳۸٫۵۵۸۸٪ رسیده است. نام بانک، انتشار ساخت‌یافته همان ردیف است؛ نه بازیابی شناسه مرجع بانک. مرکز هزینه، بازیابی زمینه‌مند مرجع بومی است؛ نه نگاشت مصوب سامانه.')
    d.heading('D | پوشش و آشتی‌سازی مرکز هزینه')
    d.table([('وضعیت نهایی ردیف‌های هزینه‌ای', 'ردیف'), ('کد مرکز هزینه افزوده‌شده', '۲۳٬۲۴۳'), ('تعارض با داده یا زمینه موجود', '۸٬۰۴۲'), ('پیشنهادی؛ بدون اعمال', '۶٬۹۷۷'), ('چندگزینه‌ای حل‌نشده', '۳۱'), ('فاقد شاهد قابل استفاده', '۷٬۷۲۲'), ('جمع ردیف‌های هزینه‌ای', '۴۶٬۰۱۵')])
    d.text('اعمال‌شده: کد بومی بازیابی شده، نه تأیید رسمی. تعارض: ناسازگاری نام یا زمینه حسابداری نیازمند رسیدگی. پیشنهادی: گزینه دارای مرجع، بدون اعمال و نیازمند تصویب. چندگزینه‌ای: انتخاب میان بدیل‌ها ممکن نشده است. فاقد شاهد: مرجع قابل استفاده وجود ندارد؛ خالی‌ماندن عمدی از پرکردن حدسی ایمن‌تر است.', 9.5)
    d.new('تکمیل بخش D — پوشش ابعاد و تفسیر درست شاخص‌ها')
    d.heading('پوشش فیزیکی با پذیرش رسمی متفاوت است')
    d.text('پوشش فیزیکی مجموعه فیلدهای هدف از ۳۶٫۷۶۷۷٪ به ۳۸٫۵۵۸۸٪ رسیده است. این شاخص شمارش پرشدگی است، نه درصد آمادگی سامانه. مخرج‌های زیر بر شواهد مثبت مشاهده‌شده متکی‌اند؛ قاعده عمومی الزام یا عدم کاربرد همه ابعاد هنوز مصوب نشده است.')
    d.table([('بعد و وضعیت', 'جمعیت مشاهده‌شده'), ('مرکز هزینه؛ هزینه‌ای واجد شاهد', '۴۶٬۰۱۵'), ('مرکز هزینه؛ دارای کد تکمیلی', '۲۳٬۲۴۳'), ('مرکز هزینه؛ بدون تناقض کشف‌شده', '۲۲٬۳۵۹'), ('بانک؛ واجد شاهد در بعد مربوط', '۱۵۰٬۶۱۴'), ('بانک؛ نام دارای پشتیبانی مرجع حساب', '۱۵۰٬۴۰۳'), ('واحد سازمانی؛ فرمول معتبر و منطبق', '۱۶۸٬۹۱۵'), ('شخص؛ زوج کد و نام موجود و محفوظ', '۱۴۱٬۷۳۸')])
    d.text('در ۱۶۸٬۹۱۵ ردیف، فرمول‌های واحد سازمانی بازمحاسبه و با مقدار ذخیره‌شده و زوج کد/نام بومی منطبق‌اند؛ ۳۸۴٬۷۵۲ ردیف فاقد فرمول/کد هستند. صحت محاسباتی، مسئولیت مصوب در سطح ردیف را اثبات نمی‌کند.')
    d.text('شناسه رسمی بانک اعتبارسنجی نشده است. هویت و نقش مرجع اشخاص تأیید نشده‌اند. مخرج معتبر قرارداد و پروژه تعیین نشده؛ بنابراین درصد صفر یا صد برای آنها گزارش نمی‌شود. جمعیت صریح «عدم کاربرد» صفر است؛ نبود داده، عدم کاربرد نیست.', 10.5, True)
    d.new('E — یافته‌های ممیزی مستقل و مثال‌های تصمیم‌ساز')
    d.heading('E | ممیزی مستقل و ریسک‌های باقی‌مانده')
    d.text('حفظ داده‌های اصلی بدون نقض و تطبیق ۱۹۸٬۳۳۶ سلول افزوده‌شده تأیید شده؛ مجموع بدهکار و بستانکار در منبع و خروجی هرکدام ' + number(int(e['financial_totals']['source_Q'])) + ' ریال است. ۱۶۸٬۹۱۵ فرمول واحد سازمانی از نظر محاسباتی منطبق‌اند؛ نه تأیید مسئولیت رسمی.', 9.5)
    d.table([('موضوع بازبینی', 'تعداد'), ('مرکز هزینه اعمال‌شده نیازمند رسیدگی', '۸۸۴ ردیف'), ('مرکز هزینه اعمال‌شده؛ رد قطعی در ممیزی', 'صفر'), ('استثنای نام بانک/عنوان حساب', '۲۴۵ ردیف'), ('گزینه اصلاح مرکز هزینه؛ صرفاً پیشنهادی', '۵۱ مورد'), ('گروه یک شناسه شخص با صورت‌های نام', '۳۷ گروه'), ('گروه نام نرمال‌شده با چند شناسه', '۵۸۸ گروه')])
    d.text('نمونه مستقل ۳۷۳ ردیف یکتا با پوشش ریسک و اسکن جمعیت متاثر استفاده شده است؛ این نمونه تصادفی برای برآورد نرخ خطای کل نیست.')
    d.text('نمونه ۴٬۵۳۳: هزینه تعمیر ماشین‌آلات با مرکز نگهداری ساختمان؛ ذی‌نفع و محل تجهیز باید روشن شود. نمونه ۸٬۸۷۲: تجهیز فنی در مرکز ساخت ساختمان؛ شاهد پروژه و سرمایه‌ای بودن لازم است. نمونه ۱۵۱٬۹۱۱: تجهیز فرهنگسرا در مرجع ورزشی؛ حوزه استفاده نیازمند تأیید است.')
    d.text('نمونه ۸۷٬۵۸۷: نام بانک ملی از همان ردیف منتشر شده، اما عنوان حساب تنخواه نام بانک را ندارد. نمونه ۳۹۰٬۵۹۹: طرف با عنوان صندوق کارآفرینی امید، بدون مجوز مرجع نباید به هویت بانک تبدیل شود.')
    d.text('۲۶٬۴۹۴ ردیف درآمدی دارای نام مرکز هزینه اصلی محفوظ‌اند؛ نه مشروع بودن استفاده تاریخی و نه اشتباه قطعی منبع اثبات شده است. شباهت نام اشخاص، مجوز ادغام شناسه‌ها نیست.', 10.5, True)
    d.new('F–H — تصمیم کارشناسی، مرجع لازم و شروط پذیرش')
    d.heading('F | محدودیت‌های باقی‌مانده')
    d.text('ریسک معنایی باقی است؛ نگاشت مصوب مرکز هزینه، مراجع قرارداد/پروژه، شناسه رسمی سراسری بانک و قواعد حاکمیتی رویداد/ابعاد ارائه نشده‌اند. سیاست استفاده از فیلد مرکز هزینه در ردیف‌های درآمدی روشن نیست. این خلأها با یکتایی بودجه یا شباهت نام برطرف نمی‌شوند.')
    d.heading('G | تصمیم‌های درخواستی از کارشناسان')
    d.text('از آقای خداپرست، تیم مالی و مالکان تعیین‌شده توسط کارفرما درخواست می‌شود: موارد ارجاعی و ۵۱ گزینه اصلاح را با شاهد بررسی کنند؛ مالک و اختیار هر مرجع را تأیید کنند؛ و تصمیم، دلیل، شاهد، تاریخ و نسخه را در فایل کارشناسی ثبت کنند. این درخواست، انتصاب رسمی یا تأیید از پیش ثبت‌شده نیست. مراجع لازم در فایل چهارم آمده‌اند.')
    d.heading('H | جمع‌بندی پذیرش و گام بعد')
    d.table([('حوزه', 'نتیجه ممیزی'), ('حفظ داده و بازتولیدپذیری ممیزی', 'قابل قبول'), ('مرکز هزینه، بانک، واحد و شخص', 'قابل قبول با رسیدگی'), ('پوشش ابعاد و آمادگی حاکمیتی', 'هنوز قابل قبول نیست'), ('تحویل رسمی و حاکمیتی به سامانه', 'مجاز نشده است')])
    d.text('گام بعد: تخصیص مالک هر مسئله؛ دریافت مراجع رسمی؛ بررسی موارد ارجاعی؛ تصویب تصمیم‌های قابل ردیابی؛ و تنها پس از پذیرش همه کنترل‌ها، تصمیم درباره نسخه اصلاحی یا تحویل سامانه. در این بسته هیچ نسخه دوم یا تأیید از پیش ثبت‌شده وجود ندارد.', 11, True)
    d.text('مبنای گزارش: ممیزی مستقل نسخه اول، شاخص‌های جمعیت، پوشش ابعاد و ممیزی معنایی موجود در پوشه شواهد فنی. اسناد ردیفی حاوی اطلاعات مالی و شخصی‌اند؛ دسترسی و توزیع باید محدود و دارای مجوز باشد.', 9.5)
    return d.save()


def references():
    d = Document('04_Required_Reference_Data_FA.pdf', 'داده‌های مرجع لازم برای پذیرش رسمی', 4)
    cards = [
        ('مرکز هزینه', 'مرجع مصوب و نگاشت بومی به سامانه', 'اثبات مجاز بودن تخصیص هزینه و حفظ تبار تغییرات', 'شناسه پایدار؛ کد/نام بومی و سامانه؛ حوزه؛ روابط اصلاح‌شده بودجه؛ قواعد کاربرد و هم‌پوشانی؛ تاریخ اثر؛ نسخه؛ تصویب؛ تبار تفکیک/ادغام', 'بودجه و حسابداری با مالکان حوزه هزینه', '۸۸۴ ردیف اعمال‌شده نیازمند رسیدگی؛ ۵۱ گزینه پیشنهادی؛ نگاشت مصوب ارائه نشده', 'فوری، پیش از پذیرش', 'تطبیق بومی، مجوز تخصیص یا کد اصلی سامانه نخواهد شد'),
        ('واحد سازمانی', 'ساختار نسخه‌دار و رابطه مسئولیت واحد با ردیف', 'تمایز نتیجه فرمول سند از مسئولیت واقعی عملیات', 'شناسه واحد؛ عنوان؛ والد؛ تاریخ اثر؛ نسخه؛ منطقه/سند/ردیف؛ نقش؛ شاهد و مرجع تصویب', 'توسعه سازمانی و حسابداری', '۱۶۸٬۹۱۵ فرمول صحیح‌اند، اما مسئولیت مصوب سطح ردیف اثبات نشده', 'فوری، پیش از پذیرش', 'واحد محاسبه‌شده مبنای قطعی مسئولیت ردیف نخواهد بود'),
        ('شخص', 'مرجع هویت و نقش طرف معامله، با سابقه معتبر', 'تشخیص هویت حقوقی و نقش بدون ادغام مبتنی بر نام', 'شناسه پایدار؛ نوع شخص؛ شناسه معتبر هویتی؛ نام رسمی؛ نقش؛ تاریخ اثر؛ وضعیت؛ شاهد تغییر', 'مالک مرجع اشخاص با حقوقی و مالی', '۳۷ گروه تفاوت نام یک شناسه؛ ۵۸۸ گروه نام مشابه چندشناسه', 'بالا، پیش از هر اصلاح هویتی', 'نرمال‌سازی نمایش یا شباهت نام، مجوز اصلاح/ادغام هویت نیست'),
        ('بانک', 'مرجع بانک/مؤسسه و ثبت حساب و مالکیت', 'اعتبارسنجی شناسه بانک و نسبت حساب با بانک و مالک', 'شناسه بانک؛ نوع مؤسسه؛ نام رسمی؛ حساب/شبا؛ مالک؛ عنوان حساب؛ مرجع تسویه خزانه‌داری؛ تاریخ اعتبار؛ نسخه و تأیید', 'خزانه‌داری با مالک مرجع حساب‌ها', '۱۵۰٬۶۴۸ انتشار نام همان ردیف؛ ۲۴۵ استثنا؛ شناسه بانک معتبرسازی نشده', 'فوری، پیش از پذیرش بعد بانک', 'نام منتشرشده نمی‌تواند جانشین شناسه رسمی یا اثبات مالکیت شود'),
        ('قرارداد', 'فهرست مصوب قرارداد و ارتباط صریح با ردیف', 'تعیین کاربرد قرارداد و انتساب هزینه قابل پیگیری', 'شناسه پایدار؛ شماره قرارداد؛ طرف؛ موضوع؛ وضعیت؛ تاریخ؛ مبلغ؛ پیوند پروژه؛ منطقه/سند/ردیف؛ سند پشتیبان؛ قواعد کاربرد', 'امور قراردادها و حسابداری', 'شاهد ردیفی و مخرج معتبر کاربرد قرارداد ارائه نشده', 'بالا، پیش از ادعای پوشش کامل', 'نه تکمیل حدسی مجاز است و نه اعلام صفر/صد درصد پوشش'),
        ('پروژه', 'مرجع پروژه و پیوند عملیات به ردیف مالی', 'تفکیک هزینه عملیاتی/سرمایه‌ای و مشخص کردن ذی‌نفع', 'شناسه پروژه؛ عنوان؛ نوع؛ مالک؛ وضعیت؛ تاریخ؛ رابطه قرارداد و بودجه؛ پیوند ردیف؛ شاهد سرمایه‌ای بودن', 'فنی/عمرانی و برنامه‌ریزی با حسابداری', 'رابطه پروژه و مخرج معتبر مشخص نشده؛ مثال تجهیز/ساخت نیازمند شاهد', 'بالا، پیش از انتساب قطعی پروژه', 'حساب یا بودجه یکتا به‌تنهایی مشروعیت تخصیص پروژه را اثبات نمی‌کند'),
        ('رویداد مالی', 'کاتالوگ نسخه‌دار و قواعد روابط/کاربرد مصوب', 'تعریف مجاز، ممنوع، الزامی و نامربوط بودن ابعاد', 'شناسه پایدار؛ نسخه؛ زیرسیستم؛ روابط حساب، مرکز هزینه، شخص، قرارداد، پروژه و واحد؛ الزام/اختیار و کاردینالیتی؛ تاریخ اثر؛ استثنای دقیق با تصویب کمیته', 'حاکمیت مالی و مالکان زیرسیستم', 'روابط تاریخی مشاهده‌شده‌اند، نه قواعد مصوب؛ عدم کاربرد صریح اثبات نشده', 'فوری، پیش از تحویل رسمی', 'پیشنهاد یا سابقه نمی‌تواند به‌تنهایی نتیجه معتبر رسمی ایجاد کند'),
    ]
    for page, group in enumerate([cards[:2], cards[2:4], cards[4:6], cards[6:]], 1):
        d.new('درخواست عملیاتی مرجع؛ مالک پیشنهادی نیازمند تأیید رسمی')
        if page == 1:
            d.text('مالکان زیر صرفاً پیشنهاد هستند و انتصاب رسمی در مستندات تحویل اثبات نشده است. هیچ نام یا تأیید از پیش درج نشده؛ مسئول و اختیار باید توسط کارفرما تأیید شوند.', 10, True)
        for area, item, purpose, fields, owner, issue, priority, consequence in group:
            d.heading(area)
            for label, value in [('قلم درخواستی', item), ('هدف', purpose), ('حداقل فیلدها', fields), ('مالک پیشنهادی ـ نیازمند تأیید', owner), ('مسئله فعلی', issue), ('اولویت', priority), ('پیامد نبود داده', consequence)]:
                d.text(label + ': ' + value, 9.5, gap=3)
            d.y -= 8
        if page == 4:
            d.heading('کنترل مشترک تحویل مرجع')
            d.text('هر مرجع باید منبع، مالک، نسخه، تاریخ اثر، دامنه کاربرد، تصویب‌کننده و شاهد پذیرش داشته باشد. رابطه فاقد سند با ممنوعیت صریح متفاوت است؛ هیچ نقص مدرک به‌طور خودکار «عدم کاربرد» تلقی نشود.')
            d.text('اصلاح منبع و جایگزین محلی باید جدا، قابل ردیابی و دارای اختیار مناسب باشند. داده خام محفوظ بماند. تغییر معنایی هویت‌ها یا تقسیم/ادغام مراکز باید با تبار روشن ثبت شود؛ بازنویسی بی‌ردپا مجاز نیست.')
            d.text('داده‌های هویتی، حساب بانکی و شواهد قرارداد تنها در محیط محلی و با دسترسی محدود تبادل شوند. تعیین مالک و دریافت مرجع به‌خودی‌خود به معنای تصویب محتوای آن نیست.', 10, True)
    return d.save()


def readme():
    d = Document('05_Readme_FA.pdf', 'راهنمای استفاده از بسته تحویل ۱۴۰۴', 2)
    d.new('محتویات و ترتیب مطالعه')
    d.text('این بسته برای بررسی مدیریتی و کارشناسی است؛ نه مجوز ثبت خودکار در سامانه. فایل تکمیل‌شده نسخه اول بدون بازسازی و بدون اعمال گزینه‌های اصلاحی تحویل شده است. فایل‌های منبع و ممیزی اصلی محفوظ‌اند.', 11, True)
    items = [
        ('01_Accounting_Journal_Enriched_1404.xlsx', 'دفتر روزنامه تکمیل‌شده؛ کپی همسان نسخه اول. فقط در نسخه کاری بررسی شود؛ داده اصلی و فرمول‌ها تغییر نکند.'),
        ('02_Management_Report_FA.pdf', 'جمع‌بندی مدیریتی، آمار فعلی، محدودیت‌ها، یافته‌های ممیزی و شروط پذیرش رسمی.'),
        ('03_Expert_Review_and_Decisions.xlsx', 'فهرست رسیدگی و ثبت تصمیم کارشناسی؛ موارد پیشنهادی، تأیید مرجع سامانه محسوب نمی‌شوند.'),
        ('04_Required_Reference_Data_FA.pdf', 'درخواست ساخت‌یافته مراجع مرکز هزینه، واحد، شخص، بانک، قرارداد، پروژه و رویداد مالی.'),
        ('05_Readme_FA.pdf', 'همین راهنما؛ ترتیب استفاده، مسیر شواهد و کنترل محرمانگی.'),
    ]
    for name, explanation in items:
        d.ltr(name)
        d.text(explanation, 10, gap=12)
    d.heading('ترتیب پیشنهادی استفاده')
    d.text('ابتدا گزارش مدیریتی را بخوانید؛ سپس مسئول رسیدگی را تعیین کنید و فایل بررسی کارشناسی را در کپی کاری باز کنید. داده‌های مرجع را مطابق فایل چهارم درخواست کنید. برای هر نتیجه، مرجع تصمیم، دلیل، شاهد، تاریخ و نسخه ثبت شود؛ سلول خالی تصمیم به معنای تأیید نیست.')
    d.new('شواهد فنی، محرمانگی و گام بعد')
    d.heading('محل نسبی شواهد فنی')
    d.ltr('./Technical_Audit/')
    d.text('این پوشه در کنار پنج فایل اصلی قرار دارد و شامل گزارش اجرا، گزارش ممیزی مستقل، تطبیق ردیفی، استثناهای بانک و اشخاص، کنترل فرمول واحد، پوشش ابعاد، ممیزی معنایی و گزینه‌های اصلاحی است. شواهد ردیفی برای کارشناسان مجاز است؛ نسخه مدیریتی عمومی تلقی نشود.')
    d.text('فهرست فایل‌ها و هش‌های بسته برای تشخیص تمامیت ارائه می‌شود. پیش از استفاده عملیاتی، تمامیت فایل دریافتی با فهرست کنترل بسته تطبیق داده شود. یکسان بودن هش، فقط یکسان بودن فایل است و تصویب رابطه مالی یا مجوز دسترسی را اثبات نمی‌کند.')
    d.heading('محرمانگی و نگهداری')
    d.text('بسته شامل اطلاعات مالی، هویتی و شواهد حساب است. فقط برای افراد دارای نیاز کاری و مجوز دسترسی نگهداری شود. ارسال عمومی، بارگذاری در سرویس بیرونی یا انتشار فایل‌های ردیفی بدون مجوز مناسب انجام نشود. مجوز انتشار و سیاست نگهداری باید توسط مسئول مربوط تأیید شود؛ اجرای محلی جایگزین تصویب امنیت نیست.')
    d.heading('مرز تصمیم و گام بعد')
    d.text('هیچ تأیید مرجع مجاز از پیش ثبت نشده است. تکمیل فیزیکی، صحت نام، یکتایی بودجه و تطابق فرمول، مجوز پذیرش قطعی نیستند. ۸۸۴ مورد مرکز هزینه اعمال‌شده و ۲۴۵ مورد بانک نیازمند رسیدگی‌اند؛ ۵۱ گزینه اصلاح مرکز هزینه فقط نامزد تصمیم‌اند.')
    d.text('گام بعد: تأیید مالک مسئله، دریافت داده مرجع رسمی، بررسی شواهد و ثبت تصمیم مستند. فقط پس از پذیرش همه کنترل‌ها، درباره اصلاح نسخه‌دار یا تحویل رسمی سامانه تصمیم گرفته شود. در این بسته نسخه دوم یا اصلاح خودکار تولید نشده است.', 11, True)
    return d.save()


RENDER_PS = r'''
param([string]$InputPdf, [string]$OutputDirectory)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
[Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime] | Out-Null
[Windows.Storage.StorageFolder,Windows.Storage,ContentType=WindowsRuntime] | Out-Null
[Windows.Data.Pdf.PdfDocument,Windows.Data.Pdf,ContentType=WindowsRuntime] | Out-Null
[Windows.Data.Pdf.PdfPageRenderOptions,Windows.Data.Pdf,ContentType=WindowsRuntime] | Out-Null
[Windows.Storage.Streams.IRandomAccessStream,Windows.Storage.Streams,ContentType=WindowsRuntime] | Out-Null
function Await-Result($Operation, [Type]$ResultType) {
  $method = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetGenericArguments().Count -eq 1 -and $_.GetParameters().Count -eq 1 } | Select-Object -First 1
  $task = $method.MakeGenericMethod($ResultType).Invoke($null, @($Operation))
  $task.GetAwaiter().GetResult()
}
function Await-Action($Operation) {
  $method = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and -not $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 } | Select-Object -First 1
  $task = $method.Invoke($null, @($Operation))
  $task.GetAwaiter().GetResult() | Out-Null
}
$InputPdf = [System.IO.Path]::GetFullPath($InputPdf.Replace('/', '\'))
$OutputDirectory = [System.IO.Path]::GetFullPath($OutputDirectory.Replace('/', '\'))
$file = Await-Result ([Windows.Storage.StorageFile]::GetFileFromPathAsync($InputPdf)) ([Windows.Storage.StorageFile])
$pdf = Await-Result ([Windows.Data.Pdf.PdfDocument]::LoadFromFileAsync($file)) ([Windows.Data.Pdf.PdfDocument])
$folder = Await-Result ([Windows.Storage.StorageFolder]::GetFolderFromPathAsync($OutputDirectory)) ([Windows.Storage.StorageFolder])
for ($i=0; $i -lt $pdf.PageCount; $i++) {
  $page = $pdf.GetPage($i)
  $out = Await-Result ($folder.CreateFileAsync(('page_{0:d2}.png' -f ($i+1)), [Windows.Storage.CreationCollisionOption]::ReplaceExisting)) ([Windows.Storage.StorageFile])
  $stream = Await-Result ($out.OpenAsync([Windows.Storage.FileAccessMode]::ReadWrite)) ([Windows.Storage.Streams.IRandomAccessStream])
  $options = New-Object Windows.Data.Pdf.PdfPageRenderOptions
  $options.DestinationWidth = 1190
  Await-Action ($page.RenderToStreamAsync($stream, $options))
  $stream.Dispose()
  $page.Dispose()
}
Write-Output ('PAGE_COUNT=' + $pdf.PageCount)
'''


def render(record):
    out = BUILD / 'pdf_renders' / Path(record['filename']).stem
    out.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(BUILD / 'render_pdfs.ps1'), '-InputPdf', str(FINAL / record['filename']), '-OutputDirectory', str(out)], text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError('Native renderer failed: ' + result.stderr + result.stdout)
    match = re.search(r'PAGE_COUNT=(\d+)', result.stdout)
    if not match or int(match.group(1)) != record['expected_pages']:
        raise RuntimeError('Renderer page count mismatch: ' + result.stdout)
    images = sorted(out.glob('page_*.png'))
    if len(images) != record['expected_pages']:
        raise RuntimeError('Missing rendered pages')
    evidence = []
    thumbs = []
    for path in images:
        with Image.open(path) as im:
            im = im.convert('RGB')
            gray = im.convert('L')
            # Body-only check, excluding colored header/footer: detects genuinely populated pages.
            body = gray.crop((80, 210, im.width - 80, im.height - 120))
            hist = body.histogram()
            nonwhite = sum(hist[:230]) / (body.width * body.height)
            if nonwhite < 0.004:
                raise RuntimeError('Blank page body: ' + str(path))
            evidence.append({'image': str(path.relative_to(BASE)), 'dimensions': [im.width, im.height], 'body_nonwhite_fraction': round(nonwhite, 6), 'nonblank': True})
            thumb = im.copy()
            thumb.thumbnail((397, 562))
            thumbs.append(thumb)
    contact = Image.new('RGB', (397 * 2, 562 * ((len(thumbs) + 1) // 2)), 'white')
    for idx, im in enumerate(thumbs):
        contact.paste(im, ((idx % 2) * 397, (idx // 2) * 562))
    contact.save(out / 'contact_sheet.png')
    record.update({'renderer': 'Windows.Data.Pdf / local WinRT renderer', 'rendered_page_count': len(images), 'pages': evidence, 'contact_sheet': str((out / 'contact_sheet.png').relative_to(BASE))})


def main():
    FINAL.mkdir(parents=True, exist_ok=True)
    BUILD.mkdir(parents=True, exist_ok=True)
    for font, path in [('Persian', FONT), ('PersianBold', BOLD)]:
        pdfmetrics.registerFont(TTFont(font, str(path)))
    m = json.loads((AUDIT / 'independent_metrics.json').read_text(encoding='utf-8'))
    e = json.loads((AUDIT / 'eligibility_metrics.json').read_text(encoding='utf-8'))
    s = json.loads((AUDIT / 'semantic_metrics.json').read_text(encoding='utf-8'))
    records = [management(m, e, s), references(), readme()]
    (BUILD / 'render_pdfs.ps1').write_text(RENDER_PS, encoding='utf-8-sig')
    for record in records:
        render(record)
    metadata = {'fonts': [str(FONT), str(BOLD)], 'rtl': 'logical-word wrapping, arabic_reshaper joining, python-bidi visual ordering per line', 'network_upload': False, 'sources': [str((AUDIT / name).relative_to(BASE)) for name in ['independent_metrics.json', 'eligibility_metrics.json', 'semantic_metrics.json', 'Independent_Audit_Report_EN.md']], 'documents': records}
    (BUILD / 'pdf_build_metrics.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'documents': [{k: r[k] for k in ['filename', 'bytes', 'rendered_page_count', 'font_embedding', 'contact_sheet']} for r in records]}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
