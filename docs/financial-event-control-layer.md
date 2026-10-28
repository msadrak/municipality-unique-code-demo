# لایهٔ کنترل طبقه‌بندی مالی پیش‌حسابداری

## وضعیت و هدف

این سند، مدل کنترل پیش‌حسابداری شهرداری را بر پایهٔ audit مخزن و تصمیم‌های ثبت‌شده در `docs/adr/0001-*.md` تا `docs/adr/0027-*.md` تثبیت می‌کند. هدف، تبدیل اطلاعات عملیاتی به یک بستهٔ ساخت‌یافته، قابل‌ممیزی و آمادهٔ ارجاع به حسابداری است؛ نه بازطراحی دفترکل یا تبدیل استنباط AI به master data.

## واژگان و تفکیک‌های قطعی

- **رویداد مالی** می‌گوید چه رخداد کسب‌وکاری/حسابداری واقع شده است.
- **مرکز هزینه** حوزهٔ خدمت/مسئولیت مصرف یا ایجاد هزینه را بیان می‌کند.
- یک رابطهٔ تاریخی رویداد–مرکز هزینه فقط **رابطهٔ مشاهده‌شده** است؛ رابطهٔ مجاز فقط از قواعد authoritative می‌آید.
- **زیرسامانهٔ مبدأ** یکی از ۱۴ زیرسامانهٔ حسابداری و دقیقاً یک ورودی برای هر Package است. این مفهوم با ۱۶ **حوزهٔ خدمت** taxonomy مرکز هزینه هیچ شناسه یا معنای مشترکی ندارد.
- **Pre-Accounting Package** ظرف workflow با یک یا چند **Classification Line** است. فراداده و پیوست‌های مشترک در Package و طبقه‌بندی مالی در Line نگهداری می‌شود.
- کد یکتا و سایر شناسه‌های بالادستی فقط **Source Reference** هستند؛ Package و Line هویت داخلی پایدار و غیرمعنایی خود را دارند.

تعاریف زنده در `CONTEXT.md` نگهداری می‌شوند.

## منابع فعلی و وضعیت audit

| منبع | نقش | وضعیت |
|---|---|---|
| `C:/Users/sadra/Downloads/بسته_نهایی_مراکز_هزینه_با_شماره_سند_حسابداری_v3.xlsx` | baseline بررسی‌شدهٔ مراکز هزینه و mappingهای دفتر روزنامه | تغییرناپذیر؛ master پیشنهادی، نه master فعال ERP |
| `data/reports/اطلاعات حسابداری1404.xlsx` | corpus ساخت‌یافتهٔ journal ۱۴۰۴ | دو شیت `مرکزی` (۵۱٬۷۴۱ ردیف شامل header) و `سایر مناطق` (۲۸۵٬۵۲۹ ردیف شامل header) |
| `C:/Users/sadra/Downloads/تحلیل_جامع_مراکز_هزینه_و_فعالیت_های_شهرداری_اصفهان.xlsx` | نگاشت بودجه/شرح مالی به taxonomy پیشنهادی | شامل `نگاشت_ردیف_های_مالی` با ۲٬۸۳۱ ردیف شامل header |
| `C:/Users/sadra/Downloads/مراکز هزینه طبق بودجه.xlsx` | منبع بودجه و ردیف‌های هزینه | ۲٬۴۴۹ ردیف شامل header؛ transaction-document نیست |
| `docs/civil/آمار و عمران/` | ۱۳ PDF پشتیبان عمرانی، شامل پیش‌پرداخت/تحویل/قرارداد | evidence تکمیلی محدود به همان حوزه |
| `data/reports/Clean_Unique_Counterparties_v4.xlsx` | Candidate Counterparty Reference Registry | staged/non-authoritative؛ ۳۷۰ ردیف Master شامل header و ۱۹ مورد Needs_Review |
| `data/reports/Clean_Counterparties_1404.xlsx` | شواهد گسترده‌تر alias/crosswalk طرف حساب | ۱٬۳۶۶ ردیف Master شامل header و ۲۷۹ مورد Needs_Review |

منبع ساخت‌یافتهٔ عمومیِ جداگانه‌ای برای اسناد هزینه پیدا نشد. `اعتبارات هزینه ای.xlsx` دادهٔ تجمیعی بودجه/هزینه است و نباید شاهد سند تراکنشی تلقی شود. هر مخزن اسناد هزینهٔ آینده باید منبع evidence مستقل و versioned با lineage خودش باشد.

### workbook فعلی و ستون‌های B/C

اسکریپت `scripts/cost_center_package/build_full_v3.py` workbook v3 را از v2، تحلیل جامع و journal ۱۴۰۴ تولید می‌کند. در شیت `فهرست_نهایی_پیشنهادی`:

- ستون B: `عنوان مرکز هزینه`
- ستون C: `حوزه خدمت`

این‌ها دادهٔ core master هستند. طبق ADR-06، v3 baseline تغییرناپذیر می‌ماند و حذف B/C فقط در **نمای تحلیلی مشتق‌شدهٔ رویداد مالی** انجام می‌شود.

### وضعیت CC-502 تا CC-506

همه در حوزهٔ `عمران، معابر و ابنیه فنی شهری` هستند:

| کد | عنوان | سطرهای فعلی `Doc_No_Mapping` |
|---|---|---:|
| CC-502 | روکش، لکه‌گیری و بهسازی آسفالت معابر شهری | ۲۳۲ |
| CC-503 | احداث، بهسازی و سنگ‌فرش پیاده‌روها | ۲۷ |
| CC-504 | مناسب‌سازی معابر و فضاهای شهری برای معلولین و توان‌خواهان | ۰ |
| CC-505 | احداث، مقاوم‌سازی و نگهداری پل‌های سواره‌رو و تقاطع‌های غیرهمسطح | ۸ |
| CC-506 | مدیریت، هماهنگی و نظارت بر حفاری‌های شهری | ۰ |

این فراوانی‌ها فقط mapping تاریخیِ مبتنی بر کد بودجه‌اند و مجوز رویداد–مرکز هزینه نیستند.

## مدل و configuration

### Catalog و crosswalk

کاتالوگ canonical رویدادهای مالی globally versioned است. رویدادهای `FinancialEventRef`، seedهای قدیمی، ماتریس پیمان، UI فعلی و منابع آینده حفظ می‌شوند و از طریق crosswalk صریح به شناسهٔ canonical غیرمعنایی مانند `FE-000001` متصل می‌گردند. rename شناسه را تغییر نمی‌دهد؛ split/merge شناسه‌های جدید و lineage صریح ایجاد می‌کند.

### Rule Profile

قواعد عملیاتی به‌صورت profile نسخه‌دار برای جفت `Source Subsystem + Canonical Financial Event` منتشر می‌شوند. profile به‌صورت اتمیک فعال می‌شود؛ ruleهای درون آن status مستقل دارند. ruleها می‌توانند cardinality، required/optional/prohibited، Cost Center/Account Head/Contract/Project/Person/Org Unit، پیوست‌ها و validation را بیان کنند. تا رسیدن جدول authoritative آقای خداپرست، هیچ Rule Profile production فعال نمی‌شود.

### Package و provenance

هر Package یک Source Subsystem دارد، چند Source Reference و یک یا چند Line دارد. هر Line identity منطقی پایدار و snapshot revision-specific دارد. مقدارهای imported خام تغییرناپذیرند؛ Source Correction و Effective Override دو مفهوم جدا هستند. هر override مقدار خام/پیشنهادی/مؤثر، دلیل، درخواست‌کننده، تأییدکننده، زمان، status و دورهٔ اعتبار را حفظ می‌کند.

### validation

ترتیب قطعی اعتبارسنجی:

```text
واقعیت خام منبع
→ تصحیح منبع / override مؤثرِ تأییدشده
→ اعتبار master data
→ Rule Profile authoritative
→ exception صریح، مقید و مصوب
→ نتیجهٔ نهایی
```

AI/history/confidence/Candidate Event هرگز روی validation authoritative اثر مستقیم ندارند. exception فقط requirement دقیقِ ثبت‌شده را bypass می‌کند؛ integrity، provenance، authorization، identity و revision immutable استثناپذیر نیستند.

### مبلغ و reconciliation

وقتی rule انتساب مبلغ را کاربردی بداند، Line مبلغ، basis، دلیل، actor و evidence را دارد. split باید صریح، source-backed و reconcile‌شده باشد. برای corpus ریالی فعلی tolerance پیش‌فرض دقیقاً صفر ریال است؛ tolerance غیرصفر فقط با Rule Profile authoritative و scope/version مشخص مجاز است. جهت مالی عملیاتی تا تعیین قواعد posting از Debit/Credit حسابداری جداست.

## حالت کد یکتا و ورود کنترل‌شده

- **کد یکتا موجود:** payload خام و provenance نمایش داده می‌شود؛ کاربر آن را بازنویسی نمی‌کند و صرفاً درخواست override ساخت‌یافته ثبت می‌کند.
- **کد یکتا موجود نیست:** همان ابعاد با selector کنترل‌شده، autocomplete و dependent filtering تکمیل می‌شوند. ورود آزاد جایگزین master data نیست.

## workflow و handoff

Package state از Line validation state جداست:

```text
DRAFT → READY_FOR_REVIEW → IN_REVIEW
  → NEEDS_COMPLETION | AWAITING_AUTHORITY | VALIDATED_FOR_ACCOUNTING
  → HANDED_OFF_TO_ACCOUNTING → ACKNOWLEDGED
```

`VALIDATED_FOR_ACCOUNTING` فقط زمانی ممکن است که تمام Lineها ruleهای authoritative، مرکز هزینه یا crosswalk/exception مجاز، ابعاد، پیوست‌های مصوب، provenance و override controls را رعایت کنند. طبقه‌بندی provisional فقط به `AWAITING_AUTHORITY` می‌رود. snapshot handoff شده immutable است و بازگشت با revision جدید انجام می‌شود.

Handoff فاز فعلی یک انتقال ساخت‌یافته و قابل‌ممیزی به Accounting Inbox/Queue است؛ `POST /accounting/.../post` فعلی که جزئیات event/center/line را حفظ نمی‌کند، استفاده نمی‌شود. بازطراحی journal/posting workstream مستقل بعدی است.

## حاکمیت

نقش‌ها مستقل از اشخاص‌اند:

- عملیاتی: `Initiator`، `Classification Reviewer`، `Accounting Receiver`
- taxonomy: `Taxonomy Preparer`، `Taxonomy Approver`، `Taxonomy Publisher`
- دادهٔ منبع: `Source Data Steward`

آقای خداپرست در نبود مجوز سازمانی صریح، `Taxonomy Preparer` است. تهیهٔ تغییر به‌تنهایی publication authoritative نیست. استثنای رابطهٔ Event–Cost Center زیر حاکمیت taxonomy است و استثنای مرکز هزینهٔ inactive/proposed زیر حاکمیت master-data؛ در صورت هم‌زمانی، هر دو مرجع لازم‌اند.

## مرز پیاده‌سازی فعلی

### قابل پیاده‌سازی اکنون

1. pipeline غیرمخرب discovery، فرهنگ Candidate Event، matrix شاهد، lineage، QA و derived Excel؛
2. schema/config/import staging نسخه‌دار برای جدول آینده؛
3. validation server-side برای ruleهای فعال و جلوگیری از handoff provisional؛
4. Package/Line/revision/provenance/override/exception model؛
5. UI configuration-driven RTL برای دو مسیر کد یکتا/ورود کنترل‌شده؛
6. Candidate Counterparty Reference Registry staged؛
7. Accounting Inbox handoff contract بدون journal posting.

### وابسته به جدول آقای خداپرست

- رابطهٔ مجاز/ممنوع Event↔Cost Center و سایر ابعاد؛
- cardinality دقیق و required/optional/prohibited؛
- مدارک اختصاصی رویداد؛
- profileهای production و فعال‌سازی handoff نهایی؛
- promotion مراکز هزینهٔ Proposed و crosswalkهای عملیاتی.

## ریسک‌های audit

- v3 حاوی ۷۴ مرکز پیشنهادی است؛ baseline catalog اولیه ۷۵ مرکز از جمله CC-1304 داشته که v2 آن را حذف کرده است. بازگرداندن/تغییر آن خارج از این کار است.
- چهارده زیرسامانه با شانزده حوزهٔ خدمت یکسان نیستند.
- `TransactionWizard` فعلی رویدادها و برخی مراکز هزینه را hardcode می‌کند و attachment آن شبیه‌سازی‌شده است؛ نباید الگوی فرم جدید باشد.
- `CostCenterRef` عملیاتی فقط master ساده‌ای است و seed موجود destructive است؛ v3 نباید با آن seed شود.
- `FinancialEventRef`، matrix پیمان و فهرست‌های UI/seed چند vocabulary ناسازگار دارند؛ فقط crosswalk versioned، نه rewrite مخرب، مجاز است.
- جدول آقای خداپرست در مخزن، داده‌های گزارش و فایل‌های معرفی‌شده پیدا نشد.
