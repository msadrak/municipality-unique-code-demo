# سامانه مالی شهرداری اصفهان - مستندات UI

## نمای کلی سیستم

این سامانه یک رابط کاربری حرفه‌ای برای سیستم مالی دولتی شهرداری اصفهان است که بر اساس اصول طراحی زیر ساخته شده:

### اصول طراحی

1. **یک تصمیم در هر صفحه** - هر صفحه فقط یک تصمیم اصلی از کاربر می‌خواهد
2. **افشای تدریجی** - اطلاعات پیچیده در accordion، modal یا step پنهان می‌شوند
3. **سلسله‌مراتب بصری** - عمل اصلی به صورت بصری برجسته است
4. **پالت رنگی دولتی** - رنگ‌های خنثی و حرفه‌ای
5. **RTL و فارسی** - کاملاً راست‌به‌چپ با فونت Vazirmatn

---

## ساختار کامپوننت‌ها

### صفحات اصلی

#### 1. Login (`/components/Login.tsx`)
**هدف:** ورود کاربران به سامانه

**ویژگی‌ها:**
- فرم ساده ورود با نام کاربری و رمز عبور
- هدایت خودکار بر اساس نقش (admin/user)
- لینک به داشبورد عمومی
- هویت بصری دولتی (لوگو، عنوان، رنگ‌بندی)

**تصمیم اصلی:** آیا می‌خواهید وارد شوید؟

---

#### 2. User Portal (`/components/UserPortal.tsx`)
**هدف:** محیط کاربر برای ایجاد تراکنش

**ویژگی‌ها:**
- دو تب: "ایجاد تراکنش جدید" و "تراکنش‌های من"
- هدر با اطلاعات کاربر و دکمه خروج
- استفاده از TransactionWizard برای ایجاد تراکنش

**تصمیم اصلی:** آیا می‌خواهید تراکنش جدید ایجاد کنید یا تراکنش‌های قبلی را ببینید؟

---

#### 3. Admin Dashboard (`/components/AdminDashboard.tsx`)
**هدف:** بررسی و تایید/رد تراکنش‌ها توسط مدیر

**ویژگی‌ها:**
- کارت‌های آمار (کل، در انتظار، تایید شده، رد شده)
- فیلتر و جستجو
- جدول تراکنش‌ها بدون ویرایش inline
- کلیک روی ردیف → باز شدن side panel
- صفحه‌بندی

**تصمیم اصلی:** کدام تراکنش را می‌خواهید بررسی کنید؟

**کامپوننت وابسته:** `TransactionReviewPanel` - پنل کناری برای بررسی جزئیات و تایید/رد

---

#### 4. Public Dashboard (`/components/PublicDashboard.tsx`)
**هدف:** نمایش عمومی آمار بودجه و تراکنش‌ها (فقط خواندنی)

**ویژگی‌ها:**
- 3 تب: آمار کلی، وضعیت بودجه، کدهای یکتا
- خلاصه بودجه با نمودارهای پیشرفت
- لیست کدهای یکتای اخیر
- توضیحات ساختار کد ۱۱ بخشی در accordion

**تصمیم اصلی:** کدام دسته اطلاعات را می‌خواهید ببینید؟

---

### Transaction Wizard (7 مرحله)

**مسیر:** `/components/TransactionWizard.tsx`

**فلسفه طراحی:** هر مرحله فقط یک دسته تصمیم می‌خواهد. اطلاعات پیچیده پنهان شده و به تدریج نمایش داده می‌شود.

#### Step 1: Transaction Type (`/components/wizard-steps/WizardStep1_TransactionType.tsx`)
- **تصمیم:** نوع تراکنش (هزینه‌ای / سرمایه‌ای) و سال مالی
- **UI:** Radio button با کارت‌های بزرگ برای هر گزینه
- **Progressive Disclosure:** هیچ

#### Step 2: Organization (`/components/wizard-steps/WizardStep2_Organization.tsx`)
- **تصمیم:** مسیر سازمانی (منطقه → اداره → قسمت)
- **UI:** سه Select که به صورت تدریجی باز می‌شوند
- **Progressive Disclosure:** اداره تا زمانی که منطقه انتخاب نشود نمایش داده نمی‌شود

#### Step 3: Budget (`/components/wizard-steps/WizardStep3_Budget.tsx`)
- **تصمیم:** انتخاب ردیف بودجه
- **UI:** جستجو + Accordion برای هر ردیف
- **Progressive Disclosure:** جزئیات بودجه (مصوب، تخصیص، هزینه شده) در accordion پنهان است
- **ویژگی:** هشدار اگر بودجه کم باشد

#### Step 4: Financial Event (`/components/wizard-steps/WizardStep4_FinancialEvent.tsx`)
- **تصمیم:** رویداد مالی، مرکز هزینه، اقدام مستمر
- **UI:** سه Select
- **Progressive Disclosure:** اقدام مستمر اختیاری است

#### Step 5: Beneficiary (`/components/wizard-steps/WizardStep5_Beneficiary.tsx`)
- **تصمیم:** اطلاعات ذینفع و مبلغ
- **UI:** Input ساده با validation
- **Progressive Disclosure:** هشدار اگر مبلغ بیشتر از بودجه باشد
- **ویژگی:** فرمت خودکار اعداد فارسی با جداکننده هزار

#### Step 6: Preview (`/components/wizard-steps/WizardStep6_Preview.tsx`)
- **تصمیم:** بررسی نهایی
- **UI:** نمایش کد یکتا + خلاصه همه اطلاعات در کارت‌های گروه‌بندی شده
- **Progressive Disclosure:** اجزای کد یکتا در کارت جداگانه نمایش داده می‌شود

#### Step 7: Submit (`/components/wizard-steps/WizardStep7_Submit.tsx`)
- **تصمیم:** آیا آماده ثبت هستید؟
- **UI:** چک‌لیست نهایی + توضیحات گردش کار
- **Progressive Disclosure:** هشدارها و validation errors
- **Primary Action:** دکمه سبز بزرگ "ثبت نهایی"

---

### کامپوننت‌های پشتیبان

#### My Transactions List (`/components/MyTransactionsList.tsx`)
- لیست تراکنش‌های کاربر با فیلتر و جستجو
- Badge برای وضعیت‌ها (pending, approved, rejected, paid)
- نمایش دلیل رد در صورت reject شدن

#### Transaction Review Panel (`/components/TransactionReviewPanel.tsx`)
- Side panel برای admin
- نمایش جزئیات کامل بدون قابلیت ویرایش inline
- **تصمیم اصلی:** تایید یا رد؟
- **Progressive Disclosure:** فرم رد تنها زمانی نمایش داده می‌شود که admin دکمه "رد" را بزند

---

## رنگ‌بندی وضعیت‌ها

| وضعیت | رنگ | توضیح |
|-------|-----|-------|
| `draft` | خاکستری (#9ca3af) | پیش‌نویس |
| `pending` | زرد/نارنجی (#d97706) | در انتظار تایید |
| `approved` | سبز (#16a34a) | تایید شده |
| `rejected` | قرمز (#dc2626) | رد شده |
| `paid` | آبی (#2563eb) | پرداخت شده |

---

## Data Flow

```
User Creates Transaction (7 steps)
         ↓
Status: PENDING (زرد)
         ↓
Admin Reviews in Side Panel
         ↓
    ┌────┴────┐
    ↓         ↓
APPROVED   REJECTED
  (سبز)    (قرمز + دلیل)
    ↓
   PAID
  (آبی)
```

---

## اصول کلیدی UX

### 1. No Cognitive Overload
- هر صفحه حداکثر یک تصمیم اصلی
- اطلاعات پیچیده در accordion/modal پنهان

### 2. Visual Hierarchy
- Primary action همیشه بزرگ‌تر و رنگی‌تر
- Secondary actions outline یا ghost
- Destructive actions (رد کردن) با رنگ قرمز

### 3. Progressive Disclosure
- فیلدهای بعدی تا زمان تکمیل قبلی‌ها نمایش داده نمی‌شوند
- جزئیات پیچیده در accordion
- فرم‌های تو در تو (مثل reject reason) فقط در صورت نیاز باز می‌شوند

### 4. Clear Feedback
- وضعیت‌های رنگی
- پیام‌های validation واضح
- Progress bar در wizard
- خلاصه انتخاب‌ها در هر مرحله

### 5. Government Appropriate
- رنگ‌های محافظه‌کارانه
- فونت خوانا
- کنتراست بالا
- بدون تزئینات اضافی

---

## Component Naming Convention

| نوع | نامگذاری | مثال |
|-----|----------|------|
| صفحه اصلی | PascalCase | `AdminDashboard` |
| ویزارد استپ | `WizardStepN_Description` | `WizardStep1_TransactionType` |
| پنل/مودال | `Description + Panel/Modal` | `TransactionReviewPanel` |
| لیست | `Entity + List` | `MyTransactionsList` |

---

## نکات فنی

### RTL Support
```css
[dir="rtl"] {
  direction: rtl;
  text-align: right;
}
```

### Persian Number Formatting
```typescript
const formatCurrency = (amount: number) => {
  return new Intl.NumberFormat('fa-IR').format(amount) + ' ریال';
};
```

### Status Color Classes
```css
.status-pending { background-color: var(--status-pending); }
.status-approved { background-color: var(--status-approved); }
.status-rejected { background-color: var(--status-rejected); }
.status-paid { background-color: var(--status-paid); }
```

---

## Mock Data

همه کامپوننت‌ها با داده‌های mock کار می‌کنند. در production باید با API backend متصل شوند:

- `ZONES`, `DEPARTMENTS`, `SECTIONS` - ساختار سازمانی
- `BUDGET_ITEMS` - ردیف‌های بودجه
- `FINANCIAL_EVENTS` - رویدادهای مالی
- `COST_CENTERS` - مراکز هزینه
- `MOCK_TRANSACTIONS` - تراکنش‌های نمونه

---

## مسیر یادگیری کاربر

### کاربر عادی:
1. ورود → هدایت به User Portal
2. کلیک "ایجاد تراکنش جدید"
3. طی کردن 7 مرحله wizard (یک تصمیم در هر مرحله)
4. مشاهده پیش‌نمایش کد یکتا
5. ثبت نهایی
6. پیگیری در تب "تراکنش‌های من"

### ادمین:
1. ورود → هدایت به Admin Dashboard
2. مشاهده آمار
3. کلیک روی تراکنش pending
4. باز شدن side panel
5. تصمیم: تایید یا رد؟
6. در صورت رد: وارد کردن دلیل
7. ثبت تصمیم

### بازدیدکننده عمومی:
1. کلیک "داشبورد عمومی" در صفحه login
2. مشاهده آمار کلی در 3 تب
3. جستجوی کد یکتا
4. مشاهده ساختار کد در accordion

---

## نتیجه‌گیری

این سیستم یک UI تمیز، حرفه‌ای و کاربرپسند برای سیستم مالی دولتی ارائه می‌دهد که:

✅ بار شناختی را کاهش می‌دهد (یک تصمیم در هر صفحه)
✅ سلسله‌مراتب واضح دارد (primary action برجسته)
✅ اطلاعات پیچیده را پنهان می‌کند (progressive disclosure)
✅ برای محیط دولتی مناسب است (رنگ‌بندی محافظه‌کارانه، فرمال)
✅ RTL و فارسی را پشتیبانی می‌کند
✅ از اصول accessibility پیروی می‌کند

---

**تاریخ:** 1403/09/23
**نسخه:** 1.0.0
**سازمان:** شهرداری اصفهان - معاونت مالی و اقتصادی
