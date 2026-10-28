# Municipal Financial Identity & Cost Accounting

The domain of issuing an immutable financial identity for every rial the municipality commits or pays, and of attributing that spend to the activity that consumed it.

This glossary records only terms whose meaning is settled. رویداد مالی and مرکز هزینه are settled; فعالیت and متولی remain deliberately absent until resolved.

## Language

### Financial Classification

**رویداد مالی (Financial Event)**:
طبقه‌بندیِ رخداد کسب‌وکاری/حسابداریِ واقع‌شده است؛ مانند پیش‌پرداخت، صورت‌وضعیت موقت یا ضمانت‌نامه. رویداد مالی مستقل از محل مسئولیت هزینه است و می‌تواند با صفر، یک یا چند مرکز هزینه رابطه داشته باشد.
_Avoid_: مرکز هزینه، فعالیت، ردیف بودجه، شماره سند

**مرکز هزینه (Cost Center)**:
حوزهٔ فعالیت، خدمت یا مسئولیت هزینه‌ای شهرداری است که عملیات یا هزینه برای آن ایجاد می‌شود. مرکز هزینه مقصدِ مسئولیت/مصرف را بیان می‌کند، نه نوع رخداد مالی را.
_Avoid_: رویداد مالی، ردیف بودجه، شماره سند

**رابطهٔ مشاهده‌شده (Observed Relationship)**:
هم‌رخدادیِ مستند یک رویداد مالی و یک بُعد در دادهٔ تاریخی است. این رابطه شاهد است، نه مجوز کسب‌وکاری.
_Avoid_: رابطهٔ مجاز، قانون قطعی

**رابطهٔ تأییدشده (Authoritative Relationship)**:
رابطه‌ای است که منبع مرجع کسب‌وکاری آن را به‌عنوان ترکیب مجاز اعلام کرده است. تا پیش از تأیید، دادهٔ استنباط‌شده فقط پیشنهادی یا نیازمند بررسی است.
_Avoid_: هم‌رخدادی تاریخی، حدس مدل

**بستهٔ پیش‌حسابداری (Pre-Accounting Package)**:
تجمیعِ گردش‌کارِ یک یا چند سطر طبقه‌بندی با فراداده و پیوست‌های مشترک است و شناسهٔ داخلی پایدار خود را دارد. بسته ظرفِ ارسال و بازبینی است، نه جایگزین سطرهای مالیِ قابل‌ردیابی.
_Avoid_: سند حسابداری، سطر طبقه‌بندی، رویداد مالی

**سطر طبقه‌بندی (Classification Line)**:
سطر صریحی با شناسهٔ منطقی پایدار در یک بستهٔ پیش‌حسابداری است که طبقه‌بندی مالی و ابعادیِ یک مورد را نگه می‌دارد. هر revision یک snapshot تغییرناپذیر از سطر دارد و split/merge، شناسهٔ منطقی جدید با lineage صریح می‌سازد.
_Avoid_: بستهٔ پیش‌حسابداری، پیوست، تخصیص مبهم

**مقدار مؤثر (Effective Value)**:
مقداری است که پس از اعمال override محلیِ مجاز در فرایند استفاده می‌شود و منبع، دلیل، هویت و زمان آن حفظ می‌گردد. مقدار مؤثر هرگز payload خام و تغییرناپذیرِ منبع را جایگزین نمی‌کند و از تصحیح منبع متمایز است.
_Avoid_: payload خام، بازنویسی منبع، تصحیح منبع

**زیرسامانهٔ مبدأ (Source Subsystem)**:
یکی از چهارده زیرسامانهٔ حسابداری و کانال ورود یک بستهٔ پیش‌حسابداری است. هر بسته دقیقاً یک زیرسامانهٔ مبدأ دارد و این مفهوم هیچ نقش یا شناسهٔ مشترکی با حوزهٔ خدمت ندارد.
_Avoid_: حوزهٔ خدمت، مرکز هزینه

**حوزهٔ خدمت (Cost Center Service Domain)**:
طبقه‌ای در taxonomy مراکز هزینه است که از مرکز هزینهٔ انتخاب‌شده در سطر طبقه‌بندی تعیین می‌شود. حوزهٔ خدمت منبع ورود بسته نیست.
_Avoid_: زیرسامانهٔ مبدأ، حوزهٔ ورود

**کاتالوگ مرجع رویداد مالی (Canonical Financial Event Catalog)**:
کاتالوگ نسخه‌دار و مرجعِ شناسه‌ها و عنوان‌های رویداد مالی است. فهرست‌های قدیمی با crosswalk صریح به آن متصل می‌شوند و ابهام نگاشت به اجبار رفع نمی‌شود.
_Avoid_: seed رویداد، فهرست ایستای UI، نگاشت قطعیِ ساختگی

**ارجاع به حسابداری (Accounting Handoff)**:
انتقال یک بستهٔ پیش‌حسابداریِ معتبر و قابل‌ممیزی به Inbox یا Queue حسابداری است. ارجاع به حسابداری به‌خودی‌خود posting خودکار journal نیست.
_Avoid_: ثبت سند خودکار، posting

**رویداد مالی پیشنهادی (Candidate Financial Event)**:
رویداد مالیِ استخراج‌شده از شواهد است که هنوز به کاتالوگ canonical یا قواعد مجاز authoritative ارتقا نیافته است. ابهام آن با alias یا ادغام اجباری پنهان نمی‌شود.
_Avoid_: رویداد تأییدشده، نگاشت قطعیِ بدون شواهد

**مرجع منشأ (Source Reference)**:
سند یا شناسهٔ قابل‌ردیابیِ منشأ یک بسته یا سطر طبقه‌بندی است. یک مرجع می‌تواند با split صریح از چند سطر پشتیبانی کند و نبود آن فقط با توجیه ساخت‌یافته ثبت می‌شود.
_Avoid_: پیوستِ اختیاریِ بی‌ردیابی، شرح آزاد

**طبقه‌بندی موقت (Provisional Classification)**:
تخصیص یک رویداد مالی canonical یا پیشنهادی در Review پیش از اعتبارسنجی با Rule Profile authoritative است. طبقه‌بندی موقت نه قانون مجاز است و نه طبقه‌بندی authoritative.
_Avoid_: اعتبارسنجی authoritative، رویداد مالی تأییدشده

**مرکز هزینهٔ پیشنهادی (Proposed Cost Center)**:
مرکز هزینهٔ نسخه‌دارِ baseline بازبینی است که فقط در Draft و Review انتخاب‌پذیر است. وضعیت آن از entity/version خود می‌آید و با تاریخچه یا seed عملیاتی فعال نمی‌شود.
_Avoid_: مرکز هزینهٔ فعال، CostCenterRef عملیاتی


**آمادهٔ بازبینی (Ready for Review)**:
وضعیتی برای بستهٔ پیش‌حسابداری است که مرجع منشأ یا توجیه ساخت‌یافتهٔ فقدان آن را دارد. این وضعیت نه انتشار قواعد است و نه handoff حسابداری.
_Avoid_: Draft، handoff حسابداری

**پروفایل قواعد (Rule Profile)**:
گروه نسخه‌دار قواعد عملیاتی برای یک جفتِ زیرسامانهٔ مبدأ و رویداد مالی canonical است. انتشار profile به‌شکل اتمیک فعال می‌شود، اما هر قاعده lifecycle و status مستقل دارد.
_Avoid_: نسخهٔ کاتالوگ، قاعدهٔ منفردِ منتشرشده

**اعتبارسنجی سطر طبقه‌بندی (Classification Line Validation)**:
نتیجهٔ سنجش یک سطر طبقه‌بندی در برابر Rule Profile و نسخه‌های دقیقِ آن است. وضعیت اعتبارسنجی سطر از وضعیت workflow بسته جداست.
_Avoid_: وضعیت Package، طبقه‌بندی موقت

**تصحیح منبع (Source Correction)**:
اصلاحی است که در منبع بالادستی یا تحت اختیار Source Data Steward انجام می‌شود. تصحیح منبع payload خامِ قبلی را بازنویسی نمی‌کند، بلکه به‌عنوان منبع/مرجع جدیدِ قابل‌ردیابی ثبت می‌شود.
_Avoid_: override محلی، بازنویسی payload خام

**استثنای تراکنش (Transaction Exception)**:
اجازهٔ نسخه‌دار، مقید و دلیل‌دار برای عبور یک مورد از شرط master-data یا Rule Profile در handoff است. استثنا زمان‌مند و قابل‌ممیزی است و taxonomy یا master data را تغییر نمی‌دهد.
_Avoid_: تغییر master، مجوز دائمی، تصمیم بازبین طبقه‌بندی

**revision بستهٔ پیش‌حسابداری (Pre-Accounting Package Revision)**:
نسخهٔ اصلاح‌شده با Revision ID یکتا و immutable برای یک Package ID ثابت است؛ snapshot handoff قبلی را تغییر نمی‌دهد. هر revision برای handoff مستقل است.
_Avoid_: ویرایش snapshot handoffشده، بازنویسی تاریخچه

**پیشنهاد AI رویداد مالی (AI Financial Event Suggestion)**:
پیشنهاد رتبه‌بندی‌شده و غیرauthoritative برای رویداد مالی است که از AI، تاریخچه یا clustering به‌دست می‌آید. فقط اقدام صریح Classification Reviewer می‌تواند آن را به طبقه‌بندی موقت تبدیل کند.
_Avoid_: طبقه‌بندی موقت خودکار، authority کسب‌وکاری

**انتساب مبلغ (Monetary Attribution)**:
مبلغ صریح و قابل‌ردیابیِ یک سطر طبقه‌بندی، هنگامی که Rule کاربرد آن را تعیین کرده است. split مبلغ باید source-backed، reconciliation‌شده و دارای basis و دلیل باشد.
_Avoid_: تقسیم ضمنی، تخصیص AI، درصد بدون rule

**رجیستری نامزد طرف حساب (Candidate Counterparty Reference Registry)**:
مرجع نسخه‌دارِ غیرauthoritative از نام‌ها و شناسه‌های طرف حساب است که selector کنترل‌شده را پشتیبانی می‌کند. رکوردهای Needs_Review در آن گزینهٔ معتبر عادی نیستند و متن خام تاریخی را جایگزین نمی‌کند.
_Avoid_: Counterparty Master authoritative، جایگزینی مخرب متن خام


**ترتیب اعتبارسنجی (Validation Precedence)**:
ارزیابی قطعیِ یک سطر از واقعیت خام به مقدار مؤثر تأییدشده، اعتبار master data، Rule Profile و در پایان استثنای صریح و مقید می‌رسد. پیشنهاد AI یا تاریخچه هیچ اثر مستقیمی بر آن ندارد و invariantهای یکپارچگی استثناپذیر نیستند.
_Avoid_: bypass ضمنی، authority هوش مصنوعی

**reconciliation مبلغ (Monetary Reconciliation)**:
تطبیق انتساب‌های مبلغ با مقدار قابل‌تخصیص منبع در کوچک‌ترین واحد پولی authoritative آن است. برای corpus ریالی فعلی tolerance پیش‌فرض دقیقاً صفر ریال است.
_Avoid_: epsilon پنهان، tolerance سراسری، normalization به‌عنوان tolerance

**شناسهٔ پایدار غیرمعنایی (Stable Non-Semantic Identity)**:
شناسهٔ opaque و پایدار است که ویژگی‌های قابل‌تغییر کسب‌وکاری را encode نمی‌کند. rename identity را تغییر نمی‌دهد و split/merge معنایی identityهای جدید با lineage صریح می‌سازد.
_Avoid_: کد معنایی، reuse شناسهٔ superseded، کلید عنوان

### Identity

**کد یکتا (Yekta Code)**:
An eleven-segment identifier minted once for a single financial event row and never changed. It remains that row’s identity; when carried into a Pre-Accounting Package, it is a Source Reference rather than the Package or Classification Line identity.
_Avoid_: unique code, tracking number, شناسه یکتا, code_yekta

**سریال (Sequence)**:
The counter that distinguishes otherwise identical Yekta Codes sharing the same prefix. It is the only segment that may differ between two rows with the same economic meaning.
_Avoid_: occurrence, serial number, incrementer

### Contractor settlement

**صورت‌وضعیت (Progress Statement)**:
A contractor's claim for work performed in a period, submitted for verification and approved as a gross amount before any statutory treatment.
_Avoid_: invoice, bill, claim, صورت حساب

**ماتریس مالی (Financial Matrix)**:
The complete set of financial event rows derived from one approved Progress Statement. It is exhaustive by construction: the gross claim, every statutory addition and withholding, and the net payable.
_Avoid_: breakdown, split, allocation table, ۹گانه

**ذینفع (Beneficiary)**:
The party that receives settlement of one financial event row. Different rows of the same Financial Matrix have different beneficiaries — the tax authority, the social security organisation, a municipal deposit account, or the contractor.
_Avoid_: payee, counterparty, vendor, recipient

**کسور قانونی (Statutory Withholding)**:
An amount deducted from a contractor's gross claim because law obliges the municipality to remit it elsewhere. It reduces the net payable without reducing the cost of the work.
_Avoid_: deduction, کسورات, withholding tax

**سپرده (Refundable Withholding)**:
An amount withheld from a contractor and held by the municipality against future obligations, returnable once those obligations lapse. Distinct from a Statutory Withholding because the municipality is the holder, not a conduit.
_Avoid_: guarantee, retention, ضمانت‌نامه, escrow

**ضمانت‌نامه (Bank Guarantee)**:
An instrument issued by a bank on the contractor's behalf that the municipality may call. It is not money the municipality holds, so it is never a Refundable Withholding.
_Avoid_: bond, deposit, سپرده

### Budget

**ردیف بودجه (Budget Line)**:
The level-five line of the budget approved by the city council, which authorises spend. It states what the municipality is permitted to spend money on, never what the money was consumed by.
_Avoid_: budget code, budget row, ردیف, کد بودجه, budget item

**تامین اعتبار (Credit Provision)**:
The reservation of an amount of a Budget Line against a future obligation. It commits budget without consuming any resource.
_Avoid_: funding, allocation, blocking, credit request
