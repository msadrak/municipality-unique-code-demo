"""Curated, evidence-based reassessment of the 157 old (Taxi/Terminals) accounts of the colleague's workbooks.

This is analytical judgement, NOT an approved crosswalk.  Every row is PROPOSED and needs expert review; nothing here
is binding.  The judgement uses: account nature (class/kol), the actual sub-accounts and their 1404–1405 ledger usage
(tt_v21.sqlite, prior project), the title in BOTH organisations, and the meaning of the candidate in the new chart.

Relation codes per target
  EQ  EQUIVALENT              same accounting meaning and function
  RN  RENAMED                 same meaning, materially different label
  SP  SPLIT_COMPONENT         one of several destinations; basis given in SUB_SPLIT (sub-account level)
  RC  RECLASSIFIED            same economic content, but located under another kol/class in the new chart
  CR  CANDIDATE_REVIEW        plausible equivalent; evidence incomplete
  RL  RELATED_NOT_EQUIVALENT  related concept, must not be used as a migration target without a decision

Account status
  EXACT_EQUIVALENCE_PROPOSED, RENAMED_EQUIVALENT, POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE, SPLIT_1_TO_N, RECLASSIFIED,
  RELATED_ONLY, NO_SUITABLE_CANDIDATE, EXPERT_REVIEW_REQUIRED, MODEL_AS_DIMENSION

Verdict on the colleague's best match
  VALID, PARTIALLY_VALID (correct for one component of a split), PLAUSIBLE_REVIEW (defensible alternative),
  RELATED_NOT_EQUIVALENT, INVALID_STRUCTURAL (incompatible element/nature), INVALID_SEMANTIC (compatible class,
  different function), INVALID_ENTITY (different numbered entity, e.g. region 1 vs 6), INVALID_PERSPECTIVE (the
  counterparty's mirror account, e.g. own capital ↔ investment in shares)
"""

REL_FA = {'EQ': 'هم‌ارز', 'RN': 'تغییر نام (هم‌ارز)', 'SP': 'جزء تفکیک ۱←N', 'RC': 'طبقه‌بندی مجدد', 'CR': 'کاندید نیازمند بازبینی',
          'RL': 'مرتبط ولی غیرهم‌ارز'}
REL_EN = {'EQ': 'EQUIVALENT', 'RN': 'RENAMED', 'SP': 'SPLIT_COMPONENT', 'RC': 'RECLASSIFIED', 'CR': 'CANDIDATE_REVIEW',
          'RL': 'RELATED_NOT_EQUIVALENT'}

# codes whose meaning differs between Taxi and Terminals (not mere spelling) — reviewed manually
MEANING_COLLISIONS = {'114-2-0-0', '114-9-0-0', '114-10-0-0', '116-6-0-0', '116-5-0-0', '114-3-0-0'}

NO_ACC_DEP = 'نمودار جدید (۲۳۴ ردیف) هیچ حساب استهلاک انباشته/کاهندهٔ دارایی ندارد؛ مهاجرت این مانده نیازمند تصمیم سیاستی (PEO-01) است.'
NO_PROV = 'نمودار جدید حساب ذخیره/کاهش ارزش ندارد (مبنای نقدی-بودجه‌ای)؛ تصمیم سیاستی لازم است (PEO-02).'
NO_EQUITY = 'ارزش خالص در نمودار جدید فقط ۳۱۰۰۱–۳۱۰۰۵ (مازاد انباشته/ارزیابی) است؛ سرمایه و اندوخته معادل ندارند.'

E = []


def e(code, org, status, targets, verdict, reason, domain='GENERAL', decision=None):
    E.append(dict(code=code, org=org, status=status, targets=targets, verdict=verdict, reason=reason, domain=domain,
                  decision=decision))


# ---------------------------------------------------------------- 111 cash
e('111-2-0-0', 'BOTH', 'SPLIT_1_TO_N', [(11002, 'SP', '۱۱۱-۲-۱ درآمد'), (11001, 'SP', '۱۱۱-۲-۲ هزینه'), (11005, 'SP', '۱۱۱-۲-۳ سپرده'),
  (11002, 'CR', 'پایانه‌ها ۱۱۱-۲-۴ «تمرکز وجوه درآمد سازمان»')], 'INVALID_SEMANTIC',
  'بهترین گزینهٔ همکار «بانک ارزی» است؛ هیچ شاهد گردش ارزی نیست. تفکیک واقعی با تفصیلی ۱/۲/۳ (درآمد/هزینه/سپرده) است.', decision='TG-D-05')
e('111-3-0-0', 'BOTH', 'EXACT_EQUIVALENCE_PROPOSED', [(11009, 'EQ', '')], 'VALID', 'تنخواه‌گردان ↔ تنخواه گردانها.')
e('111-4-0-0', 'BOTH', 'EXACT_EQUIVALENCE_PROPOSED', [(11008, 'EQ', '')], 'VALID', 'وجوه بین راه ↔ وجوه بین راهی.')
# ---------------------------------------------------------------- 112 short-term investments
e('112-1-0-0', 'BOTH', 'NO_SUITABLE_CANDIDATE', [(17001, 'RL', 'فقط اگر بلندمدت طبقه‌بندی شود')], 'RELATED_NOT_EQUIVALENT',
  'کل ۱۲۵ جدید فقط معین‌های نام‌دار (شرکت‌های طرف سرمایه‌گذاری شهرداری) دارد؛ معین عام «سهام کوتاه‌مدت» نیست. ۱۷۰۰۱ بلندمدت است.', decision='TG-D-07')
e('112-2-0-0', 'BOTH', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(12008, 'CR', 'حساب‌های سپرده بانکی')], 'INVALID_SEMANTIC',
  'سپرده سرمایه‌گذاری کوتاه‌مدت بانکی ≠ «حساب‌های درآمد بانکی» (گزینهٔ همکار). نزدیک‌ترین: ۱۲۰۰۸.', decision='TG-D-07')
e('112-3-0-0', 'BOTH', 'NO_SUITABLE_CANDIDATE', [], 'INVALID_SEMANTIC', 'اوراق قرضه کوتاه‌مدت؛ گزینهٔ همکار سهام بلندمدت است.', decision='TG-D-07')
e('112-8-0-0', 'BOTH', 'NO_SUITABLE_CANDIDATE', [], 'INVALID_SEMANTIC', 'سرمایه‌گذاری کوتاه‌مدت ≠ «سایر دارایی‌های ثابت مشهود».', decision='TG-D-07')
e('112-9-0-0', 'BOTH', 'NO_SUITABLE_CANDIDATE', [], 'INVALID_STRUCTURAL', 'کاهندهٔ دارایی ↔ درآمد (گزینهٔ همکار). ' + NO_PROV, decision='TG-D-03')
# ---------------------------------------------------------------- 113 receivables
e('113-1-0-0', 'BOTH', 'SPLIT_1_TO_N', [(11501, 'SP', 'مناطق و مجموعه شهرداری'), (11503, 'SP', 'سازمان‌ها و شرکت‌های وابسته'),
  (11505, 'SP', 'ادارات دولتی'), (11511, 'SP', 'شرکت‌های خصوصی، افراد، بهره‌برداران')], 'RELATED_NOT_EQUIVALENT',
  'حساب دریافتنی جاری و مختلط؛ گزینهٔ همکار «حساب‌های دریافتنی بلندمدت» (۱۸۰۰۳) است. تفکیک با تفصیلی‌ها (۲۸ زیرحساب، دو سازمان با معانی متفاوت) — جدول Account_Split_Evidence. '
  'برای پایانه‌ها ۱۱۳-۱-۱ (۳٫۲۶e12) جریان عاملیتی CD-01 است.', decision='TG-D-06')
e('113-1-20-0', 'Taxi', 'MODEL_AS_DIMENSION', [(11501, 'EQ', 'منطقه ۱ به‌عنوان طرف حساب/تفصیلی')], 'INVALID_ENTITY',
  '«شهرداری منطقه ۱» به «شهرداری منطقه ۶» (حساب رابط ۷۵۰۰۶ — در دفتر ۱۴۰۴ زیر ۷۱۰) تطبیق شده؛ تفاوت در عدد = نهاد دیگر. '
  'این یک طرف حساب است نه معین؛ معین مقصد ۱۱۵۰۱ با بُعد «منطقه».', decision='TG-D-06')
e('113-5-0-0', 'BOTH', 'SPLIT_1_TO_N', [(11513, 'SP', '۱۱۳-۵-۱ جاری'), (11514, 'SP', '۱۱۳-۵-۲ سنوات آتی'),
  (115014, 'SP', '۱۱۳-۵-۳ واخواستی (کد ۶ رقمی)'), (11513, 'CR', '۱۱۳-۵-۴ سنوات قبل')], 'PARTIALLY_VALID',
  'گزینهٔ همکار (۱۱۵۱۴ سال آتی) فقط برای زیرحساب ۱۱۳-۵-۲ صحیح است؛ بخش جاری (۱۱۳-۵-۱) بزرگ‌تر است.', decision='TG-D-06')
e('113-6-0-0', 'BOTH', 'RENAMED_EQUIVALENT', [(11512, 'RN', 'اسناد در جریان وصول عملیاتی')], 'INVALID_STRUCTURAL',
  'تطبیق «دقیق نام» همکار (۱۰۰٪) به ۲۳۰۰۴ است که در نمودار جدید زیر «پیش دریافت‌ها» (بدهی) ثبت شده؛ معادل دارایی ۱۱۵۱۲ است. '
  'شباهت ۱۰۰٪ متنی ≠ هم‌ارزی حسابداری.', decision='TG-D-02')
e('113-7-0-0', 'Terminals', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(115014, 'CR', 'اسناد واخواستی')], 'INVALID_SEMANTIC',
  'چک برگشتی ≈ اسناد واخواستی؛ گزینهٔ همکار «اسناد دریافتنی سال آتی» است. کد ۱۱۵۰۱۴ خود طول نامعتبر دارد.', decision='TG-D-02')
e('113-9-0-0', 'Terminals', 'NO_SUITABLE_CANDIDATE', [], 'INVALID_STRUCTURAL', 'ذخیره مطالبات مشکوک (کاهنده) ↔ «مطالبات از نهادهای دولتی». ' + NO_PROV, decision='TG-D-03')
# ---------------------------------------------------------------- 114 other receivables
e('114-1-0-0', 'BOTH', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(12002, 'CR', 'وام/مساعده کارکنان'), (12001, 'RL', 'غیرپرسنلی')],
  'INVALID_SEMANTIC', 'بدهکاران کارکنان ↔ «بدهکاران تراکم سیار» (گزینهٔ همکار) بی‌ربط است. مرز «پرسنلی/غیرپرسنلی» در نمودار جدید تعریف نشده.', decision='TG-D-08')
e('114-2-0-0', 'Taxi', 'EXPERT_REVIEW_REQUIRED', [(11501, 'CR', '۱۱۴-۲-۲ خزانه شهر - معین تاکسیرانی'), (11510, 'CR', '۱۱۴-۲-۱ خزانه ملی - معین تاکسیرانی')],
  'INVALID_STRUCTURAL', 'در تاکسیرانی این کد «خزانه معین شهرداری» است (۱۸۱ ردیف، ۱٫۰e12 بدهکار) ولی فهرست همکار عنوان پایانه‌ها '
  '(«اسناد دریافتنی غیرعملیاتی») را دارد و به ۲۳۰۰۵ (زیر پیش‌دریافت‌ها، بدهی) تطبیق داده است.', decision='TG-D-04')
e('114-2-0-0', 'Terminals', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(11511, 'CR', 'اسناد دریافتنی غیرعملیاتی')], 'INVALID_STRUCTURAL',
  'بدون گردش در پایانه‌ها؛ نمودار جدید اسناد دریافتنی غیرعملیاتی ندارد.', decision='TG-D-04')
e('114-3-0-0', 'Terminals', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(11511, 'CR', 'سود سهام دریافتنی')], 'INVALID_SEMANTIC',
  'سود سهام دریافتنی ↔ «سپرده‌ها و ودایع دریافتنی» (همکار) غیرهم‌ارز.', decision='TG-D-04')
e('114-3-0-0', 'Taxi', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(11511, 'CR', 'اسناد دریافتنی غیرعملیاتی')], 'INVALID_SEMANTIC',
  'در تاکسیرانی همین کد «اسناد دریافتنی غیرعملیاتی» است (برخورد معنایی).', decision='TG-D-04')
e('114-4-0-0', 'BOTH', 'EXACT_EQUIVALENCE_PROPOSED', [(12003, 'EQ', '')], 'VALID', 'سپرده ما نزد دیگران ↔ سپرده‌ها و ودایع دریافتنی.')
e('114-5-0-0', 'Taxi', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(11511, 'CR', '')], 'INVALID_SEMANTIC', 'سود سهام دریافتنی ↔ سپرده‌ها و ودایع (همکار).')
e('114-7-0-0', 'Taxi', 'EXPERT_REVIEW_REQUIRED', [(12005, 'CR', 'اگر وام اعطایی باشد')], 'INVALID_SEMANTIC',
  '«بازپرداخت وام به خزانه» در گروه دریافتنی‌ها؛ ماهیت (طلب یا پیش‌پرداخت بدهی) نامعلوم؛ گزینهٔ همکار «بانک پرداخت هزینه» است.', decision='TG-D-04')
e('114-8-0-0', 'Taxi', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(11511, 'CR', 'سایر دریافتنی‌ها')], 'INVALID_STRUCTURAL',
  'سایر بدهکاران (دارایی) ↔ «بدهی به کارکنان» (همکار).')
e('114-9-0-0', 'Taxi', 'RECLASSIFIED', [(12009, 'RC', 'مالیات ارزش افزوده خرید')], 'INVALID_ENTITY',
  'در تاکسیرانی «مالیات بر ارزش افزوده پرداختی» است (۳۴۰ ردیف)؛ فهرست همکار عنوان پایانه‌ها («خزانه معین بانک شهر») را دارد و به «خزانه معین منطقه ۶» تطبیق داده.', decision='TG-D-04')
e('114-9-0-0', 'Terminals', 'EXPERT_REVIEW_REQUIRED', [(11510, 'CR', 'وجوه نزد خزانه'), (710, 'RL', 'کل رابط تمرکز وجوه (فقط سطح کل)')],
  'INVALID_ENTITY', 'حساب خزانه معین سازمان؛ «منطقه ۶» نهاد دیگری است.', decision='TG-D-04')
e('114-10-0-0', 'Taxi', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(11511, 'CR', 'سایر حساب‌های دریافتنی')], 'INVALID_STRUCTURAL',
  'در تاکسیرانی «سایر حسابهای دریافتنی» است (۲۱ ردیف) و نه «صندوق ذخیره»؛ همکار به بدهی ۲۱۰۰۹ تطبیق داده است.', decision='TG-D-04')
e('114-10-0-0', 'Terminals', 'EXPERT_REVIEW_REQUIRED', [(750, 'RL', 'کل «صندوق ذخیره - سهم مناطق و سازمان‌ها»؛ معین سازمانی ندارد')],
  'INVALID_PERSPECTIVE', 'سهم سازمان در صندوق ذخیرهٔ خزانه (دارایی) ↔ «صندوق ذخیره خزانه‌داری» ۲۱۰۰۹ که در نمودار شهرداری بدهی است؛ آینهٔ طرف مقابل.', decision='TG-D-04')
# ---------------------------------------------------------------- 115 inventories
e('115-5-0-0', 'BOTH', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(13001, 'CR', 'ملزومات'), (13003, 'RL', 'کالا')], 'PLAUSIBLE_REVIEW',
  'کالای مصرفی پایانه‌ها (۴۱۹ ردیف)؛ ملزومات یا کالا — تعریف معین‌های ۱۳۰ جدید لازم است.', decision='TG-D-08')
e('115-6-0-0', 'BOTH', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(13005, 'CR', 'سایر موجودی‌ها')], 'INVALID_SEMANTIC',
  'کالای امانی ما نزد دیگران (موجودی) ↔ «سایر حساب‌ها و اسناد دریافتنی» (همکار).')
e('115-8-0-0', 'BOTH', 'EXACT_EQUIVALENCE_PROPOSED', [(13005, 'EQ', '')], 'VALID', 'سایر موجودی‌ها.')
e('115-9-0-0', 'BOTH', 'NO_SUITABLE_CANDIDATE', [], 'INVALID_STRUCTURAL', 'ذخیره کاهش ارزش موجودی ↔ «صندوق ذخیره خزانه‌داری» (فقط واژهٔ «ذخیره» مشترک). ' + NO_PROV, decision='TG-D-03')
# ---------------------------------------------------------------- 116 prepayments
e('116-1-0-0', 'BOTH', 'EXACT_EQUIVALENCE_PROPOSED', [(14003, 'EQ', '')], 'VALID', 'پیش‌پرداخت سرمایه‌ای.')
e('116-2-0-0', 'BOTH', 'EXACT_EQUIVALENCE_PROPOSED', [(14002, 'EQ', '')], 'INVALID_SEMANTIC', 'پیش‌پرداخت هزینه‌ای ↔ همکار: پیش‌پرداخت خرید سرمایه‌ای (ماهیت مخالف).')
e('116-3-0-0', 'BOTH', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(14003, 'CR', 'علی‌الحساب سرمایه‌ای')], 'VALID', 'علی‌الحساب اقلام سرمایه‌ای ↔ پیش‌پرداخت خریدهای سرمایه‌ای.')
e('116-4-0-0', 'BOTH', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(14002, 'CR', 'علی‌الحساب هزینه‌ای'), (22006, 'RL', 'اگر تنخواه کارکنان باشد')],
  'INVALID_SEMANTIC', 'علی‌الحساب اقلام هزینه‌ای ↔ «حساب‌های هزینه بانکی» (همکار) بی‌ربط.')
e('116-5-0-0', 'Terminals', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(14005, 'CR', 'پیش‌پرداخت مالیات')], 'INVALID_SEMANTIC',
  'پیش‌پرداخت مالیات ↔ «پیش پرداخت غرامت تملکات» (همکار).', decision='TG-D-04')
e('116-5-0-0', 'Taxi', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(14005, 'CR', 'پیش‌پرداخت بیمه')], 'INVALID_SEMANTIC',
  'در تاکسیرانی همین کد «پیش پرداخت بیمه» است.', decision='TG-D-04')
e('116-6-0-0', 'Terminals', 'RECLASSIFIED', [(12009, 'RC', 'ارزش افزوده خرید (از پیش‌پرداخت به دریافتنی)')], 'INVALID_SEMANTIC',
  'پیش‌پرداخت ارزش افزوده ↔ «پیش پرداخت پروژه‌ها» (همکار).', decision='TG-D-04')
e('116-6-0-0', 'Taxi', 'MODEL_AS_DIMENSION', [(14002, 'CR', 'نام شرکت → بُعد طرف حساب')], 'INVALID_SEMANTIC',
  'در تاکسیرانی این معین نام یک شرکت است («شرکت رهپویان اندیشه دنا»)؛ طرف حساب در سطح معین.', decision='TG-D-04')
e('116-7-0-0', 'Taxi', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(14003, 'CR', 'پیش‌پرداخت دارایی')], 'VALID', 'پیش‌پرداخت دارایی ↔ خرید سرمایه‌ای.')
# ---------------------------------------------------------------- 120 / 121 / 122 / 123 / 124 / 125
e('120-1-0-0', 'Terminals', 'MODEL_AS_DIMENSION', [(15006, 'CR', 'زمین؛ نام ملک → شناسهٔ دارایی')], 'INVALID_STRUCTURAL',
  'زمین مشخص (نام ملک) ↔ «دیون با محل» (هزینه). ملک باید در دفتر اموال/بُعد دارایی باشد.', domain='RELATED_INSUFFICIENT', decision='TG-D-09')
e('120-2-0-0', 'Terminals', 'MODEL_AS_DIMENSION', [(15006, 'CR', 'زمین؛ نام ملک → شناسهٔ دارایی')], 'INVALID_STRUCTURAL',
  'زمین مشخص ↔ «هزینه‌های بانکی» (همکار).', domain='RELATED_INSUFFICIENT', decision='TG-D-09')
e('121-1-0-0', 'BOTH', 'EXACT_EQUIVALENCE_PROPOSED', [(15006, 'EQ', '')], 'VALID', 'زمین.')
e('121-2-0-0', 'BOTH', 'RENAMED_EQUIVALENT', [(15005, 'RN', 'ساختمان و مستحدثات')], 'INVALID_STRUCTURAL',
  'ساختمان (دارایی) ↔ «ساختمان مسکونی» ۲۳۰۰۲ زیر پیش‌دریافت‌ها (بدهی پیش‌فروش). گزینهٔ دوم همکار (۱۵۰۰۵) صحیح است.')
e('121-3-0-0', 'BOTH', 'EXACT_EQUIVALENCE_PROPOSED', [(15004, 'EQ', '')], 'VALID', 'ماشین‌آلات (و تجهیزات).')
e('121-4-0-0', 'BOTH', 'EXACT_EQUIVALENCE_PROPOSED', [(15012, 'EQ', '')], 'VALID', 'تأسیسات.')
e('121-5-0-0', 'BOTH', 'RENAMED_EQUIVALENT', [(15003, 'RN', 'وسایل نقلیه زمینی و زیرزمینی')], 'VALID',
  'هم‌ارز با شباهت متنی پایین (۵۱٫۳٪) — نمونهٔ «شباهت پایین، هم‌ارزی بالا».')
e('121-6-0-0', 'BOTH', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(15016, 'CR', 'سایر دارایی‌های ثابت'), (15004, 'RL', 'تجهیزات')],
  'INVALID_STRUCTURAL', 'ابزارآلات (دارایی ثابت) ↔ «عوارض آلایندگی» (درآمد) با شباهت ۴۳٫۵٪؛ معین ابزارآلات در نمودار جدید نیست.', decision='TG-D-08')
e('121-7-0-0', 'BOTH', 'RENAMED_EQUIVALENT', [(15002, 'RN', 'اثاثه و منصوبات')], 'INVALID_SEMANTIC',
  'اثاثیه اداری ↔ «دارایی اجاره‌ای» (همکار)؛ گزینهٔ سوم همکار (۱۵۰۰۲) صحیح است.')
e('121-8-0-0', 'BOTH', 'EXACT_EQUIVALENCE_PROPOSED', [(15016, 'EQ', '')], 'VALID', 'سایر دارایی‌های ثابت مشهود.')
e('121-9-0-0', 'BOTH', 'RENAMED_EQUIVALENT', [(15001, 'RN', 'دارایی در جریان تکمیل')], 'VALID', 'دارایی در جریان ساخت ↔ در جریان تکمیل.')
e('121-10-0-0', 'Taxi', 'RECLASSIFIED', [(16005, 'RC', 'نرم‌افزار → نامشهود (معین نرم‌افزار ندارد)')], 'INVALID_STRUCTURAL',
  'نرم‌افزار در کل «دارایی ثابت مشهود» ثبت شده؛ همکار به ۶۱۶۰۲ (هزینهٔ تملک تجهیزات رایانه‌ای، مبنای بودجه) تطبیق داده. جای صحیح نامشهود است.', decision='TG-D-08')
e('121-11-0-0', 'Taxi', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(15004, 'CR', 'تجهیزات GPS ناوگان')], 'INVALID_STRUCTURAL',
  'تجهیز و نصب GPS (دارایی) ↔ ۶۱۶۰۲ هزینهٔ تملک تجهیزات اداری (جریان بودجه).', domain='DIRECT_TAXI', decision='TG-D-08')
for c, t in (('122-1-0-0', 'ساختمان'), ('122-2-0-0', 'ماشین‌آلات و تجهیزات'), ('122-3-0-0', 'تأسیسات'), ('122-4-0-0', 'وسایط نقلیه'),
             ('122-5-0-0', 'ابزارآلات'), ('122-6-0-0', 'اثاثیه اداری'), ('122-7-0-0', 'لوازم فنی'), ('122-8-0-0', 'سایر دارایی‌های ثابت'),
             ('122-10-0-0', 'نرم‌افزار'), ('122-11-0-0', 'دارایی در جریان ساخت')):
    v = 'INVALID_STRUCTURAL'
    extra = ''
    if c == '122-2-0-0':
        extra = ' همکار آن را به خودِ دارایی ۱۵۰۰۴ (علامت مخالف) تطبیق داده است.'
    if c == '122-11-0-0':
        extra = ' استهلاک «دارایی در جریان ساخت» خود از نظر حسابداری غیرعادی است و باید بررسی شود.'
    e(c, 'BOTH', 'NO_SUITABLE_CANDIDATE', [], v, f'استهلاک انباشته {t} (کاهندهٔ دارایی). ' + NO_ACC_DEP + extra, decision='TG-D-03')
e('123-1-0-0', 'BOTH', 'EXACT_EQUIVALENCE_PROPOSED', [(16002, 'EQ', '')], 'VALID', 'سرقفلی.')
e('123-2-0-0', 'BOTH', 'EXACT_EQUIVALENCE_PROPOSED', [(16005, 'EQ', '')], 'INVALID_STRUCTURAL',
  'حق‌الامتیاز (دارایی نامشهود) ↔ ۶۱۹۰۱ «حقوق و امتیازات» (هزینهٔ تملک مبنای بودجه)؛ گزینهٔ دوم همکار (۱۶۰۰۵) صحیح است.')
e('123-3-0-0', 'BOTH', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(16005, 'CR', 'حق انشعاب = حق امتیاز')], 'INVALID_STRUCTURAL',
  'حق‌الانشعاب ↔ «حقوق ثابت» (هزینهٔ کارکنان) — همنامی «حق/حقوق».')
e('123-8-0-0', 'BOTH', 'NO_SUITABLE_CANDIDATE', [(16005, 'RL', 'تنها معین نامشهود عام')], 'INVALID_SEMANTIC',
  'سایر دارایی‌های نامشهود ↔ «سایر دارایی‌های ثابت مشهود» (شباهت ۸۹٫۸٪) — مشهود/نامشهود متضاد.', decision='TG-D-08')
e('124-1-0-0', 'BOTH', 'EXACT_EQUIVALENCE_PROPOSED', [(17001, 'EQ', '')], 'VALID', 'سرمایه‌گذاری بلندمدت در سهام.')
e('124-3-0-0', 'BOTH', 'NO_SUITABLE_CANDIDATE', [], 'INVALID_SEMANTIC', 'اوراق قرضه بلندمدت (سرمایه‌گذاری) ↔ «حساب‌های دریافتنی بلندمدت».', decision='TG-D-07')
e('124-4-0-0', 'BOTH', 'NO_SUITABLE_CANDIDATE', [], 'INVALID_STRUCTURAL', 'ذخیره کاهش ارزش (کاهنده) ↔ درآمد سرمایه‌گذاری. ' + NO_PROV, decision='TG-D-03')
e('124-5-0-0', 'Taxi', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(17001, 'CR', 'اگر سهم مالکانه'), (17002, 'CR', 'اگر مشارکت')],
  'PLAUSIBLE_REVIEW', 'سرمایه‌گذاری در مرکز معاینه فنی؛ نوع سرمایه‌گذاری (سهم/مشارکت) در منبع مشخص نیست.', domain='RELATED_INSUFFICIENT', decision='TG-D-07')
e('125-2-0-0', 'BOTH', 'NO_SUITABLE_CANDIDATE', [], 'INVALID_STRUCTURAL', 'هزینه‌های تأسیس (داراییِ انتقالی) ↔ هزینهٔ مطالعاتی.', decision='TG-D-08')
e('125-3-0-0', 'BOTH', 'NO_SUITABLE_CANDIDATE', [(15017, 'RL', 'دارایی اجاره‌ای')], 'INVALID_SEMANTIC', 'بهسازی اموال استیجاری ↔ «حساب‌های دریافتنی بلندمدت».', decision='TG-D-08')
e('125-4-0-0', 'BOTH', 'NO_SUITABLE_CANDIDATE', [(14005, 'RL', 'فقط اگر جاری شود')], 'RELATED_NOT_EQUIVALENT', 'پیش‌پرداخت بلندمدت ↔ پیش‌پرداخت جاری خرید کالا.', decision='TG-D-08')
e('125-5-0-0', 'Taxi', 'NO_SUITABLE_CANDIDATE', [], 'INVALID_STRUCTURAL',
  'حق عضویت در اتحادیه سازمان‌های تاکسیرانی (دارایی) ↔ «مال‌الاجاره ساختمان‌ها و تأسیسات شهرداری» (درآمد). سرمایه‌ای بودن عضویت باید تأیید شود.',
  domain='DIRECT_TAXI', decision='TG-D-08')
# ---------------------------------------------------------------- 211–224 liabilities
e('211-1-0-0', 'BOTH', 'SPLIT_1_TO_N', [(21001, 'SP', 'مجموعه شهرداری/مناطق'), (21005, 'SP', 'ادارات دولتی'), (21012, 'SP', 'شرکت‌ها، افراد، سایر'),
  (21003, 'SP', 'سازمان‌ها (پایانه‌ها ۱۱۱-۱-۶)')], 'INVALID_STRUCTURAL',
  'حساب‌های پرداختنی مختلط (بدهی) ↔ ۱۲۰۰۸ «حساب‌های سپرده بانکی» (دارایی) با شباهت ۸۰٪. پایانه‌ها ۲۱۱-۱-۱ = مطالبهٔ درآمد برای شهرداری (CD-01).', decision='TG-D-06')
e('211-1-10-0', 'Taxi', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(21001, 'CR', 'بدهی به شهرداری')], 'RELATED_NOT_EQUIVALENT',
  'بستانکاران خزانه‌داری شهرداری ↔ «بستانکاران نقل و انتقال» (همکار).', decision='TG-D-06')
e('211-2-0-0', 'Taxi', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(21001, 'CR', 'بدهی به مناطق و مدیریت‌های شهرداری')], 'RELATED_NOT_EQUIVALENT',
  'پرداختنی به شهرداری ↔ «سایر حساب‌های پرداختنی عملیاتی» (همکار).', decision='TG-D-06')
e('211-5-0-0', 'BOTH', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(21019, 'CR', 'اسناد پرداختنی تجاری'), (21017, 'CR', 'اگر ذی‌نفع شهرداری/سازمان')],
  'RELATED_NOT_EQUIVALENT', 'اسناد پرداختنی ↔ «اسناد پرداختنی معوق» (همکار) که زیرمجموعهٔ سررسیدگذشته است.')
e('212-1-0-0', 'BOTH', 'EXACT_EQUIVALENCE_PROPOSED', [(22001, 'EQ', '')], 'INVALID_SEMANTIC',
  'بستانکاران کارکنان ↔ «بستانکاران - نقل و انتقال» (همکار)؛ گزینهٔ سوم همکار (۲۲۰۰۱) صحیح است.')
e('212-1-20-0', 'Terminals', 'MODEL_AS_DIMENSION', [(22001, 'EQ', 'شخص → بُعد طرف حساب')], 'INVALID_STRUCTURAL',
  'بدهی به یک بازنشستهٔ مشخص (بدهی) ↔ «هزینه‌های رفاهی بازنشستگان» (هزینه). نام شخص نباید معین باشد.', decision='TG-D-10')
e('212-2-0-0', 'BOTH', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(21012, 'CR', 'هزینه‌های پرداختنی')], 'INVALID_SEMANTIC',
  'ذخیره هزینه‌های پرداختنی ↔ «سایر سپرده‌های پرداختنی» (همکار).', decision='TG-D-03')
e('212-3-0-0', 'BOTH', 'SPLIT_1_TO_N', [(22002, 'SP', 'مالیات تکلیفی/حقوق'), (22003, 'RL', 'فقط مالیات اجاره')], 'RELATED_NOT_EQUIVALENT',
  'مالیات‌های پرداختنی/تکلیفی ↔ «مالیات اجاره پرداختنی» (همکار) که فقط یک نوع است.')
e('212-4-0-0', 'BOTH', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(22002, 'CR', 'کسورات قانونی (بیمه)')], 'INVALID_SEMANTIC',
  'حق بیمه پرداختنی ↔ «غرامت ملکی پرداختنی» (همکار).')
e('212-5-0-0', 'Taxi', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(22002, 'CR', 'کسورات قانونی')], 'INVALID_SEMANTIC',
  'مالیات پیمانکاران (بدهی به سازمان مالیاتی) ↔ «بدهی به پیمانکاران» (همکار).')
e('212-6-0-0', 'BOTH', 'SPLIT_1_TO_N', [(22505, 'SP', 'مناقصه'), (22506, 'SP', 'مزایده'), (22501, 'SP', 'حسن انجام کار'), (22504, 'SP', 'بیمه'),
  (22507, 'SP', 'انجام تعهدات غرفات/شرکت‌ها و سایر')], 'PARTIALLY_VALID',
  'گزینهٔ همکار (سپرده مزایده) فقط برای ۲۱۲-۶-۲ صحیح است؛ بیشترین گردش (پایانه‌ها ۲۱۲-۶-۵ غرفات) به ۲۲۵۰۷ می‌رود.', decision='TG-D-06')
e('212-7-0-0', 'BOTH', 'SPLIT_1_TO_N', [(22002, 'SP', 'کسورات قانونی'), (22001, 'SP', 'کسورات اختیاری (تعاونی/اقساط) — TT-NE-30')], 'PARTIALLY_VALID',
  'کسورات قانونی صحیح است ولی کسورات اختیاری حقوق قانونی نیستند.')
e('212-8-0-0', 'BOTH', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(21012, 'CR', 'سایر پرداختنی‌ها')], 'RELATED_NOT_EQUIVALENT',
  'سایر بستانکاران (حساب) ↔ «سایر اسناد پرداختنی تجاری» (سند).')
e('212-9-0-0', 'Taxi', 'RENAMED_EQUIVALENT', [(22011, 'RN', 'ارزش افزوده فروش')], 'INVALID_STRUCTURAL',
  'مالیات ارزش افزودهٔ دریافتی از مشتری (بدهی) ↔ ۱۲۰۰۹ «ارزش افزوده دریافتنی بابت خرید» (دارایی) — طرف مخالف.')
e('212-10-0-0', 'Taxi', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(22011, 'CR', 'تعدیلات ارزش افزوده')], 'INVALID_SEMANTIC',
  'تعدیلات ارزش افزوده ↔ «تسهیلات مالی دریافتی از بانک‌ها» (همکار).')
e('212-11-0-0', 'Taxi', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(22009, 'CR', 'تعهدات مرتبط با کمک بلاعوض')], 'INVALID_SEMANTIC',
  'تعهدات کمک ایاب و ذهاب دانش‌آموزان استثنایی ↔ «بستانکاران نقل و انتقال». اعتبار مصرف‌معین (TT-NE-04).', domain='DIRECT_TAXI', decision='TG-D-11')
e('212-12-0-0', 'Taxi', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(22009, 'CR', '')], 'INVALID_SEMANTIC',
  'تعهدات ناشی از آلودگی هوا و تعطیلات ↔ «بستانکاران نقل و انتقال».', domain='RELATED_INSUFFICIENT', decision='TG-D-11')
e('212-13-0-0', 'Taxi', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(22009, 'CR', '')], 'INVALID_STRUCTURAL',
  'تعهدات استثنایی شهرداری (بدهی) ↔ «اعتبارات در اختیار شهردار» (هزینه).', decision='TG-D-11')
e('212-14-0-0', 'Taxi', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(22009, 'CR', '')], 'RELATED_NOT_EQUIVALENT',
  'تعهدات بیمه تکمیلی رانندگان ↔ «بستانکاران نقل و انتقال».', domain='DIRECT_TAXI', decision='TG-D-11')
e('213-1-0-0', 'BOTH', 'NO_SUITABLE_CANDIDATE', [(23001, 'RL', 'پیش‌دریافت پروژه‌ها')], 'RELATED_NOT_EQUIVALENT',
  'پیش‌دریافت فروش؛ کل ۲۳۰ جدید فقط پروژه/ساختمان/واحد تجاری دارد.', decision='TG-D-12')
e('213-2-0-0', 'BOTH', 'EXPERT_REVIEW_REQUIRED', [(23001, 'RL', 'فقط هم‌خانواده'), (22507, 'CR', 'تاکسیرانی ۲۱۳-۲-۵ وجوه امانی سفیر مهر')],
  'RELATED_NOT_EQUIVALENT', 'پیش‌دریافت خدمات: پایانه‌ها ۲۱۳-۲-۴ (چک اجاره اشخاص، ۳٫۱e12) و تاکسیرانی ۲۱۳-۲-۵ (وجوه عبوری سرویس مدارس، ۲٫۷e12). '
  'معین هم‌ارز در نمودار جدید نیست؛ وجوه سفیر مهر امانی است نه پیش‌دریافت درآمد.', decision='TG-D-12')
e('214-1-0-0', 'BOTH', 'EXPERT_REVIEW_REQUIRED', [(22002, 'RL', 'اگر بدهی قطعی')], 'INVALID_SEMANTIC', 'ذخیره مالیات ↔ «تسهیلات مالی دریافتی». ' + NO_PROV, decision='TG-D-03')
e('214-2-0-0', 'BOTH', 'NO_SUITABLE_CANDIDATE', [], 'RELATED_NOT_EQUIVALENT', 'سایر ذخایر مالیاتی. ' + NO_PROV, decision='TG-D-03')
e('215-1-0-0', 'BOTH', 'NO_SUITABLE_CANDIDATE', [], 'RELATED_NOT_EQUIVALENT', 'سود سهام پرداختنی به مالک (شهرداری) — درون‌گروهی؛ معادل ندارد.', decision='TG-D-13')
e('215-2-0-0', 'BOTH', 'NO_SUITABLE_CANDIDATE', [], 'RELATED_NOT_EQUIVALENT', 'همان.', decision='TG-D-13')
e('215-3-0-0', 'BOTH', 'NO_SUITABLE_CANDIDATE', [], 'RELATED_NOT_EQUIVALENT', 'همان.', decision='TG-D-13')
e('216-1-0-0', 'BOTH', 'EXACT_EQUIVALENCE_PROPOSED', [(23501, 'EQ', 'تفکیک کوتاه/بلندمدت از دست می‌رود')], 'VALID', 'تسهیلات از بانک‌ها.')
e('216-3-0-0', 'BOTH', 'EXPERT_REVIEW_REQUIRED', [(22008, 'CR', 'تسهیلات مالی دریافتی'), (23502, 'CR', 'سایر منابع')], 'INVALID_SEMANTIC',
  'تسهیلات از خزانه/مجموعه شهرداری (درون‌گروهی) ↔ «تسهیلات از بانک‌ها».', decision='TG-D-13')
e('216-8-0-0', 'BOTH', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(23502, 'CR', '')], 'INVALID_STRUCTURAL',
  'سایر تسهیلات دریافتی (بدهی) ↔ «تسهیلات مالی پرداختی» (دارایی، وام اعطایی).')
for c, t in (('221-1-0-0', 'مجموعه شهرداری'), ('221-2-0-0', 'ادارات دولتی'), ('221-3-0-0', 'شرکت‌ها'), ('221-4-0-0', 'اشخاص'), ('221-8-0-0', 'سایر')):
    e(c, 'BOTH', 'NO_SUITABLE_CANDIDATE', [], 'INVALID_STRUCTURAL',
      f'حساب پرداختنی بلندمدت - {t} (بدهی) ↔ ۱۸۰۰۳ «حساب‌های دریافتنی بلندمدت» (دارایی). کل ۲۵۰ فقط اوراق مشارکت دارد.', decision='TG-D-12')
e('221-5-0-0', 'BOTH', 'NO_SUITABLE_CANDIDATE', [], 'RELATED_NOT_EQUIVALENT', 'اسناد پرداختنی بلندمدت ↔ اسناد پرداختنی معوق (جاری).', decision='TG-D-12')
e('222-1-0-0', 'BOTH', 'EXACT_EQUIVALENCE_PROPOSED', [(23501, 'EQ', '')], 'VALID', 'تسهیلات بلندمدت بانکی.')
e('222-2-0-0', 'BOTH', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(23502, 'CR', 'سایر منابع (دولت)')], 'INVALID_SEMANTIC', 'تسهیلات از دولت ↔ تسهیلات از بانک‌ها.')
e('222-3-0-0', 'BOTH', 'EXPERT_REVIEW_REQUIRED', [(23502, 'CR', ''), (22008, 'CR', '')], 'INVALID_SEMANTIC', 'تسهیلات بلندمدت از شهرداری ↔ تسهیلات از بانک‌ها.', decision='TG-D-13')
e('222-8-0-0', 'BOTH', 'EXACT_EQUIVALENCE_PROPOSED', [(23502, 'EQ', '')], 'VALID', 'سایر تسهیلات بلندمدت.')
e('223-1-0-0', 'BOTH', 'NO_SUITABLE_CANDIDATE', [(65101, 'RL', 'هزینهٔ پاداش پایان خدمت (جریان)')], 'INVALID_STRUCTURAL',
  'ذخیره مزایای پایان خدمت (بدهی) ↔ «هزینه‌های رفاهی کارکنان» (هزینه). ' + NO_PROV, decision='TG-D-03')
e('223-8-0-0', 'BOTH', 'NO_SUITABLE_CANDIDATE', [(65101, 'RL', '')], 'INVALID_STRUCTURAL', 'ذخیره (بدهی) ↔ پاداش پایان خدمت (هزینه). ' + NO_PROV, decision='TG-D-03')
e('224-1-0-0', 'Taxi', 'NO_SUITABLE_CANDIDATE', [], 'INVALID_STRUCTURAL', 'ذخیره مطالبات مشکوک ↔ «مطالبات از نهادهای دولتی». ' + NO_PROV, decision='TG-D-03')
# ---------------------------------------------------------------- 3xx equity
e('311-1-0-0', 'BOTH', 'NO_SUITABLE_CANDIDATE', [], 'INVALID_STRUCTURAL', 'سرمایه ↔ «ضبط سپرده‌های معاملات» (درآمد). ' + NO_EQUITY, decision='TG-D-13')
e('311-4-0-0', 'BOTH', 'NO_SUITABLE_CANDIDATE', [], 'INVALID_PERSPECTIVE',
  'سرمایهٔ ثبت‌شدهٔ سازمان (حقوق مالکانه) ↔ ۱۷۰۰۱ «سرمایه‌گذاری در سهام سازمان‌ها» (دارایی شهرداری) — آینهٔ سرمایه‌گذار؛ در تلفیق حذف می‌شوند. ' + NO_EQUITY, decision='TG-D-13')
e('311-5-0-0', 'BOTH', 'NO_SUITABLE_CANDIDATE', [], 'INVALID_ENTITY', 'سرمایه تعهدشده ↔ «شرکت تأمین سرمایه تمدن» (یک شرکت مشخص).', decision='TG-D-13')
e('313-1-0-0', 'BOTH', 'NO_SUITABLE_CANDIDATE', [], 'INVALID_STRUCTURAL', 'اندوخته قانونی ↔ «ساختمان مسکونی» (پیش‌دریافت). ' + NO_EQUITY, decision='TG-D-13')
e('314-1-0-0', 'BOTH', 'NO_SUITABLE_CANDIDATE', [], 'INVALID_STRUCTURAL', 'اندوخته احتیاطی ↔ «بانک وجوه اختصاصی».', decision='TG-D-13')
e('314-2-0-0', 'BOTH', 'NO_SUITABLE_CANDIDATE', [], 'INVALID_STRUCTURAL', 'اندوخته توسعه ↔ «اسناد واخواستی».', decision='TG-D-13')
e('314-4-0-0', 'BOTH', 'NO_SUITABLE_CANDIDATE', [], 'INVALID_STRUCTURAL', 'سایر اندوخته‌ها ↔ «سایر پیش‌پرداخت‌ها» (فقط واژهٔ «سایر»).', decision='TG-D-13')
e('315-1-0-0', 'BOTH', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(31004, 'CR', 'ارزیابی دارایی‌ها'), (31005, 'RL', 'ارزیابی اموال')],
  'INVALID_STRUCTURAL', 'مازاد تجدید ارزیابی (ارزش خالص) ↔ «سایر دارایی‌های ثابت مشهود» (دارایی)؛ گزینهٔ دوم همکار ۳۱۰۰۴ است.')
e('316-1-0-0', 'BOTH', 'EXPERT_REVIEW_REQUIRED', [(31003, 'CR', 'مازاد انباشته تعهدی'), (31001, 'RL', ''), (31002, 'RL', '')], 'INVALID_STRUCTURAL',
  'سود و زیان انباشته ↔ ۲۳۰۰۶ (زیر پیش‌دریافت‌ها). انتخاب ۳۱۰۰۱/۲/۳ به علامت مانده و مبنای حسابداری بستگی دارد.', decision='TG-D-13')
e('316-2-0-0', 'BOTH', 'EXPERT_REVIEW_REQUIRED', [(31003, 'CR', 'اصلاح از طریق مازاد انباشته')], 'INVALID_STRUCTURAL',
  'اصلاح اشتباهات دوره‌های قبل (ارزش خالص) ↔ «حساب‌های دریافتنی بلندمدت».', decision='TG-D-13')
e('316-3-0-0', 'BOTH', 'EXPERT_REVIEW_REQUIRED', [(31003, 'CR', 'بستن به مازاد')], 'INVALID_STRUCTURAL', 'سود و زیان جاری ↔ «وجوه بین راهی».', decision='TG-D-13')
# ---------------------------------------------------------------- 4xx revenue / cost of sales
e('411-1-0-0', 'BOTH', 'EXPERT_REVIEW_REQUIRED', [(41303, 'CR', 'درآمد واحدهای خدماتی (فروش سوخت/کالا)')], 'INVALID_SEMANTIC',
  'فروش کالا/محصولات ↔ «فروش اموال غیرمنقول» (فروش دارایی).', decision='TG-D-14')
e('413-1-0-0', 'Taxi', 'SPLIT_1_TO_N', [(41204, 'SP', 'درآمد خدمات سازمان‌ها (پروانه، عضویت، نقل‌وانتقال، سهم سرویس مدارس)'),
  (41303, 'RL', 'درآمد واحدهای خدماتی')], 'PLAUSIBLE_REVIEW',
  'درآمد عملیاتی تاکسیرانی (۴٬۰۷۷ ردیف، ۲۳ زیرحساب)؛ نمودار جدید معین «درآمد خدمات تاکسیرانی» ندارد؛ ۴۱۲۰۴ صریحاً سازمان‌ها را می‌گوید. '
  'کد ۴۱۳ در شهرداری «درآمد وجوه و اموال» است (برخورد عددی).', domain='DIRECT_TAXI', decision='TG-D-14')
e('413-1-0-0', 'Terminals', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(41204, 'CR', 'درآمد نمایندگی')], 'PLAUSIBLE_REVIEW',
  'پایانه‌ها فقط ۴ ردیف (درآمد نمایندگی).', decision='TG-D-14')
e('413-1-10-0', 'Taxi', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(41303, 'CR', 'درآمد واحد خدماتی (جایگاه گاز)'), (41204, 'CR', '')],
  'INVALID_STRUCTURAL', 'درآمد جایگاه گاز ↔ «دارایی اجاره‌ای».', domain='DIRECT_TAXI', decision='TG-D-14')
e('413-1-20-0', 'Taxi', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(41204, 'CR', 'حق بهره‌برداری خطوط')], 'INVALID_STRUCTURAL',
  'حق بهره‌برداری امتیاز خطوط و مسیر (درآمد) ↔ «حق بیمه سهم شهرداری» (هزینه) — اشتراک واژهٔ «حق».', domain='DIRECT_TAXI', decision='TG-D-14')
e('413-8-0-0', 'Taxi', 'SPLIT_1_TO_N', [(41204, 'SP', 'معاینه فنی، خدمات پیمانکاری، تبلیغات'), (41502, 'RL', 'جرائم'),
  (None, 'SP', '۴۱۳-۸-۱/۲ کمک بودجه شهرداری: درون‌گروهی، معادل ندارد')], 'RELATED_NOT_EQUIVALENT',
  'سایر درآمدهای تاکسیرانی: ۱٫۰۸e12 «کمک از محل اعتبارات شهرداری» (TT-NE-02، درون‌گروهی) + جرائم ۱٫۷e11 + متفرقه ۱٫۸e11.', domain='DIRECT_TAXI', decision='TG-D-14')
e('413-8-0-0', 'Terminals', 'SPLIT_1_TO_N', [(41301, 'SP', 'اجاره غرفات/شرکت‌ها'), (41204, 'SP', 'حق شارژ، ۵٪ فروش بلیط')], 'RELATED_NOT_EQUIVALENT',
  'زیرحساب‌های پایانه‌ها (اجاره غرفات، حق شارژ، ۵٪ بلیط) مستقیماً پایانه‌ای‌اند ولی گردش ۱۴۰۴–۱۴۰۵ تقریباً صفر است (درآمد در ۲۱۱-۱-۱ ثبت می‌شود — CD-01).',
  domain='DIRECT_TERMINAL', decision='TG-D-01')
e('413-8-10-0', 'Taxi', 'NO_SUITABLE_CANDIDATE', [], 'INVALID_STRUCTURAL', 'کسر و اضافهٔ موجودی جایگاه گاز (تعدیل سود/زیان) ↔ «سایر موجودی‌ها» (دارایی).', domain='DIRECT_TAXI', decision='TG-D-14')
e('414-1-0-0', 'BOTH', 'NO_SUITABLE_CANDIDATE', [], 'INVALID_STRUCTURAL', 'بهای تمام‌شده فعالیت ↔ «سایر حساب‌های پرداختنی». نمودار جدید بهای تمام‌شده ندارد (هزینه بر اساس ماهیت).', decision='TG-D-14')
e('414-8-0-0', 'BOTH', 'NO_SUITABLE_CANDIDATE', [], 'INVALID_STRUCTURAL', 'بهای تمام‌شده سایر خدمات ↔ «حساب انتظامی - سایر تخفیفات».', decision='TG-D-14')
# ---------------------------------------------------------------- 6xx expense
e('611-1-0-0', 'BOTH', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(61001, 'CR', 'حقوق ثابت (بخش متغیر دستمزد؟)')], 'INVALID_STRUCTURAL',
  'حقوق و دستمزد ↔ ۶۱۹۰۱ «حقوق و امتیازات» (دارایی نامشهود/تملک) — همنامی «حقوق»؛ گزینهٔ دوم همکار ۶۱۰۰۱ صحیح است.')
e('611-2-0-0', 'BOTH', 'EXACT_EQUIVALENCE_PROPOSED', [(61002, 'EQ', '')], 'VALID', 'مزایا و فوق‌العاده‌ها.')
e('611-2-10-0', 'Taxi', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(61002, 'CR', ''), (61404, 'RL', 'رفاهی')], 'INVALID_STRUCTURAL',
  'سایر مزایای غیرنقدی (هزینه) ↔ «سایر حساب‌های پرداختنی غیرنقدی» (بدهی) — اشتراک واژهٔ «غیرنقدی».')
e('612-3-0-0', 'BOTH', 'SPLIT_1_TO_N', [(61101, 'SP', 'مأموریت و سفر'), (61103, 'SP', 'پست، تلفن، اینترنت')], 'PARTIALLY_VALID',
  'گزینهٔ همکار (۶۱۱۰۳) فقط برای ۶۱۲-۳-۳ صحیح است.')
e('612-4-0-0', 'BOTH', 'EXACT_EQUIVALENCE_PROPOSED', [(61111, 'EQ', '')], 'VALID', 'اجاره‌بها و کرایه ↔ اجاره و کرایه.')
e('612-5-0-0', 'BOTH', 'SPLIT_1_TO_N', [(61102, 'SP', 'خدمات پیمانکاری، حق‌الزحمه، حسابرسی'), (61104, 'SP', 'نگهداری و تعمیرات'),
  (61105, 'SP', 'چاپ و انتشارات'), (61106, 'SP', 'جشن و پذیرایی'), (61107, 'SP', 'بانکی و حقوقی'), (61110, 'SP', 'مطالعاتی'),
  (61404, 'SP', 'رفاهی، ورزشی، ناهار کارکنان')], 'PARTIALLY_VALID',
  'خدمات قراردادی سازمان ۲۰ زیرحساب با ماهیت‌های مختلف دارد؛ ۶۱۱۰۲ فقط بخش پیمانکاری/حق‌الزحمه را پوشش می‌دهد.', decision='TG-D-06')
e('612-5-10-0', 'BOTH', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(61102, 'CR', 'آموزش شهروندی (خدمات)')], 'INVALID_SEMANTIC',
  'آموزش شهروندی ↔ «هزینه‌های بانکی».')
e('612-5-20-0', 'Taxi', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(61107, 'CR', 'هزینه‌های مالی/بانکی'), (62001, 'RL', 'اگر سود تسهیلات')],
  'PLAUSIBLE_REVIEW', 'هزینه‌های مالی ↔ هزینه‌های بانکی؛ سود تسهیلات در نمودار جدید ۶۲۰۰۱ است.')
e('612-6-0-0', 'BOTH', 'EXACT_EQUIVALENCE_PROPOSED', [(61108, 'EQ', 'زیرحساب‌ها: سوخت، آب، برق (تلفن در ۶۱۲-۳-۳ است)')], 'VALID', 'سوخت، آب، برق.')
e('612-7-0-0', 'BOTH', 'EXACT_EQUIVALENCE_PROPOSED', [(61109, 'EQ', '')], 'VALID', 'مواد و لوازم مصرف‌شدنی.')
e('612-7-10-0', 'BOTH', 'EXACT_EQUIVALENCE_PROPOSED', [(61109, 'EQ', '')], 'VALID', 'سایر مواد و لوازم مصرف‌شدنی (تجمیع N←۱ با ۶۱۲-۷).')
e('613-16-0-0', 'BOTH', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(61304, 'CR', 'کمک به بخش عمومی')], 'VALID', 'کمک به بخش عمومی.')
e('613-17-0-0', 'BOTH', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(61303, 'CR', 'کمک به مؤسسات خصوصی'), (63001, 'RL', 'یارانه')],
  'RELATED_NOT_EQUIVALENT', 'کمک به بخش خصوصی (۱۴۰ ردیف؛ کمک به رانندگان TT-NE-09) ↔ «هدایا و پرداخت‌های تشویقی».', domain='RELATED_INSUFFICIENT', decision='TG-D-11')
e('613-18-0-0', 'BOTH', 'SPLIT_1_TO_N', [(62001, 'SP', 'اصل و سود تسهیلات'), (61107, 'SP', 'کارمزد')], 'RELATED_NOT_EQUIVALENT',
  'بازپرداخت وام و کارمزد ↔ «بازپرداخت اوراق مشارکت» (همکار)؛ گزینهٔ دوم همکار ۶۲۰۰۱ نزدیک‌تر است. اصل وام در مبنای تعهدی هزینه نیست.')
e('613-19-0-0', 'BOTH', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(61404, 'CR', 'رفاهی کارکنان'), (63002, 'RL', 'پرداخت انتقالی')],
  'INVALID_STRUCTURAL', 'پرداخت انتقالی به کارکنان (هزینه) ↔ ۱۲۰۰۴ «پرداخت‌های انتقالی» زیر سایر دریافتنی‌ها (دارایی) با شباهت ۷۳٫۹٪.')
e('613-20-0-0', 'BOTH', 'NO_SUITABLE_CANDIDATE', [], 'INVALID_SEMANTIC',
  'هزینهٔ استهلاک (و مطالبات مشکوک) ↔ «هزینه‌های بانکی» (شباهت ۷۵٪). نمودار جدید هزینهٔ استهلاک ندارد (PEO-01).', decision='TG-D-03')
e('613-20-10-0', 'BOTH', 'NO_SUITABLE_CANDIDATE', [], 'INVALID_SEMANTIC', 'هزینهٔ استهلاک نرم‌افزار ↔ «هزینه‌های رفاهی کارکنان».', decision='TG-D-03')
e('613-21-0-0', 'Taxi', 'EXPERT_REVIEW_REQUIRED', [(65001, 'CR', 'دیون با محل'), (652, 'RL', 'کل تعهدات انتقالی سنواتی')], 'INVALID_SEMANTIC',
  'هزینه‌های سنوات قبل ↔ «هزینه‌های بانکی».', decision='TG-D-13')
# ---------------------------------------------------------------- 812 non-operating
e('812-1-0-0', 'BOTH', 'NO_SUITABLE_CANDIDATE', [(41701, 'RL', 'فروش اموال منقول (ناخالص)'), (41601, 'RL', 'فروش اموال غیرمنقول (ناخالص)')],
  'INVALID_SEMANTIC', 'سود/زیان فروش دارایی (خالص) ↔ «نگهداری و تعمیر دارایی‌های ثابت».', decision='TG-D-14')
e('812-2-0-0', 'BOTH', 'RENAMED_EQUIVALENT', [(41304, 'RN', 'درآمد وجوه سپرده')], 'VALID', 'درآمد سپرده‌های بانکی.')
e('812-3-0-0', 'BOTH', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE', [(41302, 'CR', 'سود سهام'), (41602, 'CR', 'درآمد سرمایه‌گذاری')], 'PLAUSIBLE_REVIEW',
  'سود/زیان سرمایه‌گذاری؛ سمت زیان معادل ندارد.', decision='TG-D-14')
e('812-4-0-0', 'BOTH', 'RENAMED_EQUIVALENT', [(41501, 'RN', 'ضبط سپرده معاملات')], 'VALID', 'درآمد ضبط سپرده.')
e('812-5-0-0', 'Terminals', 'EXPERT_REVIEW_REQUIRED', [(31003, 'CR', 'اصلاح سنواتی از مازاد'), (65103, 'RL', 'سایر هزینه‌ها')], 'INVALID_STRUCTURAL',
  'اصلاح حساب‌های سنواتی ↔ «سایر حساب‌ها و اسناد دریافتنی» (دارایی).', decision='TG-D-13')
e('812-8-0-0', 'BOTH', 'EXPERT_REVIEW_REQUIRED', [(65103, 'CR', 'سمت هزینه'), (None, 'CR', 'سمت درآمد: معین عام درآمد متفرقه نیست')], 'RELATED_NOT_EQUIVALENT',
  'درآمد/هزینهٔ متفرقهٔ غیرعملیاتی (مختلط) ↔ «درآمد واحدهای خدماتی».', decision='TG-D-14')
# ---------------------------------------------------------------- 9xx memo
e('918-1-0-0', 'BOTH', 'SPLIT_1_TO_N', [(81001, 'SP', 'اسناد ضمانتی دیگران نزد ما'), (81002, 'SP', 'اسناد ضمانتی ما نزد دیگران')], 'INVALID_SEMANTIC',
  'حساب انتظامی (ضمانت‌نامه/چک ضمانت) ↔ «حساب انتظامی - یورو». کالای امانی و حساب‌های کنترل معادل ندارند.', decision='TG-D-15')
e('918-2-0-0', 'Taxi', 'SPLIT_1_TO_N', [(82001, 'SP', 'طرف اسناد ضمانتی دیگران نزد ما'), (82002, 'SP', 'طرف اسناد ضمانتی ما نزد دیگران')], 'INVALID_SEMANTIC',
  'طرف حساب انتظامی (بستانکار) ↔ «حساب انتظامی - یورو» (بدهکار، ارزی). گزینهٔ دوم همکار ۸۲۰۰۱ صحیح است.', decision='TG-D-15')
e('919-1-0-0', 'Terminals', 'SPLIT_1_TO_N', [(82001, 'SP', 'طرف اسناد ضمانتی دیگران نزد ما')], 'INVALID_SEMANTIC',
  'طرف حساب انتظامی پایانه‌ها ↔ «حساب انتظامی - یورو».', decision='TG-D-15')

ENTRIES = E

# ---------------------------------------------------------------- sub-account split basis (org, 'kol-moeen-taf1') → (new code|None, relation, note)
SUB_SPLIT = {}


def s(org, key, code, rel='SP', note=''):
    SUB_SPLIT[(org, key)] = (code, rel, note)


for o in ('Taxi', 'Terminals'):
    s(o, '111-2-1', 11002, note='بانک درآمد')
    s(o, '111-2-2', 11001, note='بانک هزینه')
    s(o, '111-2-3', 11005, note='بانک سپرده')
s('Terminals', '111-2-4', 11002, 'CR', 'تمرکز وجوه درآمد سازمان')
# 113-1 (different meanings per org for the same tafsili code)
s('Taxi', '113-1-1', 11505, 'CR', 'شرکت نفت (جایگاه گاز) — دولتی؟')
s('Terminals', '113-1-1', 11501, 'SP', 'مجموعه شهرداری مرکزی — جریان عاملیتی CD-01')
for o in ('Taxi', 'Terminals'):
    s(o, '113-1-2', 11505, note='ادارات دولتی')
    s(o, '113-1-3', 11511, note='شرکت‌های خصوصی')
    s(o, '113-1-5', 11501, note='شهرداری مرکزی/مجموعه شهرداری')
s('Taxi', '113-1-4', 11511, note='افراد')
s('Terminals', '113-1-4', 11511, note='بهره‌برداران پایانه')
s('Taxi', '113-1-6', 11501, note='شهرداری منطقه ۱۲')
s('Terminals', '113-1-6', 11511, note='افراد')
s('Terminals', '113-1-7', 12005, 'CR', 'بازپرداخت وام')
s('Taxi', '113-1-7', 11503, note='سازمان آرامستان‌ها')
s('Taxi', '113-1-8', 11503, note='سازمان میادین')
s('Terminals', '113-1-8', 11511, 'CR', '۵٪ فروش بلیط شرکت‌های مسافربری')
s('Taxi', '113-1-9', 11511, note='تعاونی تاکسیرانی (معاینه فنی)')
s('Terminals', '113-1-9', 11511, note='شرکت بیمه')
for t in (10, 11, 12, 13, 14, 23, 24, 25):
    s('Taxi', f'113-1-{t}', 11503, note='سازمان وابستهٔ شهرداری' + (' — سازمان پایانه‌ها (درون دامنه؛ حذف در تلفیق)' if t == 12 else ''))
for t in (15, 16, 17, 18, 19, 20, 21, 22, 26, 27):
    s('Taxi', f'113-1-{t}', 11501, note='شهرداری منطقه (طرف حساب → بُعد)')
for o in ('Taxi', 'Terminals'):
    s(o, '113-5-1', 11513, note='جاری')
    s(o, '113-5-2', 11514, note='سنوات آتی')
    s(o, '113-5-3', 115014, note='واخواستی')
    s(o, '113-5-4', 11513, 'CR', 'سنوات قبل')
s('Taxi', '114-2-1', 11510, 'CR', 'خزانه ملی')
s('Taxi', '114-2-2', 11501, 'CR', 'خزانه شهر')
# 211-1
for o in ('Taxi', 'Terminals'):
    s(o, '211-1-1', 21001, note='مجموعه شهرداری' + (' — مطالبهٔ درآمد برای شهرداری (CD-01)' if o == 'Terminals' else ''))
    s(o, '211-1-2', 21005, note='ادارات دولتی')
    s(o, '211-1-3', 21012, note='شرکت‌های خصوصی')
    s(o, '211-1-4', 21012, note='افراد')
s('Taxi', '211-1-5', 21012, 'CR', 'بستانکاران نامشخص (EXC-01)')
s('Terminals', '211-1-5', 21012, note='سایر')
s('Taxi', '211-1-6', None, 'CR', 'حساب واسط — معادل ندارد')
s('Terminals', '211-1-6', 21001, 'CR', 'مناطق و سازمان‌ها (۲۱۰۰۱/۲۱۰۰۳)')
s('Taxi', '211-1-7', 21012, note='تعاونی تاکسیرانی')
s('Terminals', '211-1-7', 21005, note='ادارات و شرکت‌های دولتی')
s('Taxi', '211-1-8', 21012, note='شرکت')
s('Terminals', '211-1-8', 21012, 'CR', 'ذخیره هزینه‌های پرداختنی')
s('Taxi', '211-1-9', 21012, note='تعاونی کارگران')
s('Taxi', '211-1-11', 21012, note='شرکت‌های کارگزار')
# 212-1 (retirees → person dimension)
for o in ('Taxi', 'Terminals'):
    s(o, '212-1-1', 22001, note='جاری کارکنان')
    s(o, '212-1-2', 22001, note='پس‌انداز')
s('Taxi', '212-1-3', 22001, note='حقوق پرداختنی')
for t in range(3, 30):
    s('Terminals', f'212-1-{t}', 22001, note='بازنشستهٔ مشخص → بُعد شخص')
for o in ('Taxi', 'Terminals'):
    s(o, '212-3-1', 22002, note='مالیات پیمانکاران')
    s(o, '212-3-2', 22002, note='مالیات تکلیفی/حقوق')
    s(o, '212-6-1', 22505, note='مناقصه')
    s(o, '212-6-2', 22506, note='مزایده')
    s(o, '212-6-3', 22501, note='حسن انجام کار')
    s(o, '212-6-8', 22507, note='سایر')
s('Taxi', '212-6-4', 22504, note='سپرده بیمه')
s('Terminals', '212-6-4', 22503, 'CR', 'انجام تعهدات پیمانکاران')
s('Taxi', '212-6-5', 22507, note='انجام تعهدات')
s('Terminals', '212-6-5', 22507, note='انجام تعهدات غرفات')
s('Terminals', '212-6-6', 22504, note='بیمه')
s('Terminals', '212-6-7', 22507, note='انجام تعهدات شرکت‌ها')
s('Taxi', '213-2-3', None, 'CR', 'پیش‌دریافت خدمات شرکت‌ها — معین هم‌ارز نیست')
s('Terminals', '213-2-4', None, 'CR', 'پیش‌دریافت اجاره اشخاص (چک) — معین هم‌ارز نیست')
s('Taxi', '213-2-5', 22507, 'CR', 'وجوه امانی سفیر مهر (عبوری)')
for t in range(1, 24):
    s('Taxi', f'413-1-{t}', 41204, 'SP', 'درآمد خدمات تاکسیرانی')
s('Taxi', '413-1-10', 41303, 'CR', 'جایگاه گاز')
s('Terminals', '413-1-3', 41204, 'CR', 'درآمد نمایندگی')
s('Taxi', '413-8-1', None, 'SP', 'کمک بودجه از شهرداری — درون‌گروهی')
s('Taxi', '413-8-2', None, 'SP', 'کمک بودجه غیرنقدی — درون‌گروهی')
s('Taxi', '413-8-5', 41502, 'RL', 'جرائم و خسارات (۴۱۵۰۲ فقط ماده ۱۰۰)')
s('Taxi', '413-8-8', None, 'CR', 'درآمد متفرقه — معین عام ندارد')
s('Taxi', '413-8-11', 41204, 'CR', 'تبلیغات')
s('Taxi', '413-8-12', 41204, 'CR', 'خدمات پیمانکاری')
s('Taxi', '413-8-13', 41204, 'CR', 'معاینه فنی')
s('Terminals', '413-8-4', None, 'CR', 'متفرقه — معین عام ندارد')
s('Terminals', '413-8-5', None, 'CR', 'سایر حساب‌ها')
s('Terminals', '413-8-6', 41204, 'CR', 'درآمد معاینه فنی')
s('Terminals', '413-8-7', None, 'SP', 'کمک از محل اعتبارات شهرداری — درون‌گروهی')
s('Terminals', '413-8-1', 41301, note='اجاره غرفات')
s('Terminals', '413-8-2', 41301, note='اجاره شرکت‌ها')
s('Terminals', '413-8-3', 41204, 'CR', 'حق شارژ')
s('Terminals', '413-8-8', 41204, 'CR', '۵٪ فروش بلیط')
for o in ('Taxi', 'Terminals'):
    for t, c in ((1, 61104), (2, 61104), (3, 61104), (4, 61104), (5, 61105), (6, 61106), (7, 61404), (8, 61404), (9, 61102), (10, 61102),
                 (11, 61110), (12, 61107), (13, 61102), (14, 61102), (15, 61102), (16, 61102), (17, 61102), (18, 61404), (19, 61105), (20, 61107)):
        s(o, f'612-5-{t}', c, 'SP' if t not in (9, 10, 17) else 'CR', '')
    s(o, '612-3-1', 61101, note='مأموریت داخل')
    s(o, '612-3-2', 61101, note='مأموریت خارج')
    s(o, '612-3-3', 61103, note='پست، تلفن، اینترنت')
    s(o, '918-1-2', 81001, note='اسناد ضمانتی دیگران نزد ما')
    s(o, '918-1-5', 81002, note='اسناد ضمانتی ما نزد دیگران')
    for t in (1, 3, 4, 6):
        s(o, f'918-1-{t}', None, 'CR', 'حساب کنترل/کالای امانی — معین هم‌ارز نیست')
s('Taxi', '918-2-2', 82001, note='طرف اسناد ضمانتی دیگران نزد ما')
s('Taxi', '918-2-5', 82002, note='طرف اسناد ضمانتی ما نزد دیگران')
for t in (1, 3, 4, 6):
    s('Taxi', f'918-2-{t}', None, 'CR', 'طرف حساب کنترل/کالای امانی')
s('Terminals', '919-1-2', 82001, note='طرف اسناد ضمانتی دیگران نزد ما')
for t in (1, 3, 4, 5, 6):
    s('Terminals', f'919-1-{t}', None if t != 5 else 82002, 'CR', '')
# accounts whose split is evaluated at sub-account level
SPLIT_ACCOUNTS = {'111-2-0-0', '113-1-0-0', '113-5-0-0', '114-2-0-0', '211-1-0-0', '212-3-0-0', '212-6-0-0', '213-2-0-0',
                  '413-1-0-0', '413-8-0-0', '612-3-0-0', '612-5-0-0', '918-1-0-0', '918-2-0-0', '919-1-0-0'}

# ---------------------------------------------------------------- domain keyword scan (Part 5)
DOMAIN_TERMS = [
    ('DIRECT_TAXI', ['تاکسی', 'راننده', 'خطوط و مسیر', 'جایگاه گاز', 'g p s', 'gps', 'سرویس مدارس', 'دانش آموزان', 'سفیر مهر', 'پروانه تاکسیرانی',
                     'پروانه بهره برداری', 'تاکسی های اینترنتی', 'ناوگان']),
    ('DIRECT_TERMINAL', ['پایانه', 'غرفات', 'غرفه', 'فروش بلیط', 'بلیط', 'حق شارژ', 'مسافربری', 'تابلو تبلیغاتی']),
    ('RELATED_INSUFFICIENT', ['معاینه فنی', 'آلودگی هوا', 'حمل ونقل', 'حمل و نقل', 'وسائط نقلیه', 'وسایط نقلیه', 'وسایل نقلیه', 'اتوبوس', 'مترو',
                              'شماره گذاری', 'پارکینگ']),
]
