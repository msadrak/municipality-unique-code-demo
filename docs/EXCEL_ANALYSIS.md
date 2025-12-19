# Excel Analysis Report: Hesabdary Information.xlsx

## Overview

| Property | Value |
|----------|-------|
| File Name | Hesabdary Information.xlsx |
| File Size | 67 MB |
| Total Sheets | 2 |
| Total Rows | 579,085 |
| Analysis Date | 2024-12-14 |

## Sheet Inventory

| Sheet Name | Row Count | Column Count | Description |
|------------|-----------|--------------|-------------|
| مرکزی (Central) | 99,067 | 24 | Central Municipality (zone_code=20) |
| سایر مناطق (Other Regions) | 480,018 | 24 | All other zones (1-19) |

## Column Structure (Both Sheets Identical)

| # | Column Name | Persian/English | Data Type | Null Rate | Unique Count | Purpose |
|---|-------------|-----------------|-----------|-----------|--------------|---------|
| 1 | کد منطقه | Zone Code | integer | 0% | 1-19 | Zone identifier |
| 2 | منطقه | Zone Name | text | 0% | 19 | Zone title |
| 3 | تاریخ | Date | date_string | 0% | ~300 | Transaction date (1403/MM/DD) |
| 4 | شماره سند | Doc Number | integer | 0% | ~12k | Document number |
| 5 | TitkNo | Account Kol Code | integer | 0% | ~40 | کل account code |
| 6 | TitkNam | Account Kol Name | text | 0% | ~40 | کل account name |
| 7 | TitMNo | Account Moein Code | integer | 0% | ~32 | معین account code |
| 8 | شرح سرفصل حساب معین | Account Moein Desc | text | 0% | ~150 | معین description |
| 9 | TitTNo | Account Tafsili Code | integer | 0% | ~800-1400 | تفصیلی code |
| 10 | شرح سرفصل حساب تفضیلی | Account Tafsili Desc | text | 0% | ~1600-6200 | تفصیلی description |
| 11 | titjno | Account Joz Code | integer | 0% | ~1000-2200 | جزء code |
| 12 | شرح سرفصل حساب جزء | Account Joz Desc | text | 5-6% | ~7000-24000 | جزء description |
| 13 | RadKNo | Cost Center Kol | float | 33-49% | ~13 | Cost center کل |
| 14 | RadMNo | Cost Center Moein | float | 33-49% | ~16 | Cost center معین |
| 15 | RadTNo | Cost Center Tafsili | float | 33-49% | ~75 | Cost center تفصیلی |
| 16 | RadJNo | Cost Center Joz | float | 33-49% | ~238 | Cost center جزء |
| 17 | شرح مرکزهزینه | Cost Center Desc | text | 33-49% | ~420 | Cost center name |
| 18 | مبلغ بدهکار | Debit Amount | integer | 0% | ~30k-100k | Debit amount |
| 19 | مبلغ بستانکار | Credit Amount | integer | 0% | ~30k-113k | Credit amount |
| 20 | کاربر | User | text | 0% | ~60-130 | Operator username |
| 21 | شماره درخواست | Request ID | text | 0% | ~6k-12k | Request/transaction ID |
| 22 | نوع درخواست | Request Type | text | 0% | ~88-137 | Transaction type (TypDesc) |
| 23 | کد بودجه | Budget Code | float | 78-83% | ~620-880 | Budget code (nullable) |
| 24 | ماهیت سند | Doc Nature | text | 0% | 5 | Document type (افتتاحیه, عملیاتی, etc.) |

## Data Quality Issues

### 1. Leading Zero Loss in Float Columns ⚠️
- **Affected columns**: `RadMNo`, `RadTNo`, `RadJNo`
- **Count**: ~1,700 rows total
- **Issue**: Values like `01`, `02` stored as `1.0`, `2.0`
- **Risk**: Low - cost center codes are numeric, leading zeros are not significant

### 2. High Null Rate in Budget Code ⚠️
- **Column**: `کد بودجه` (Budget Code)
- **Null rate**: 78-83%
- **Expected**: Many transactions (bank entries, opening balances) don't have budget codes
- **Risk**: None - this is expected behavior

### 3. High Null Rate in Cost Center Fields
- **Columns**: `RadKNo`, `RadMNo`, `RadTNo`, `RadJNo`, `شرح مرکزهزینه`
- **Null rate**: 33-49%
- **Expected**: Not all transactions are associated with cost centers
- **Risk**: None - nullable by design

### 4. Duplicate Values in Code Columns
- **Columns**: `کد منطقه`, `شماره سند`, `شماره درخواست`, `کد بودجه`
- **Expected**: Multiple rows per document/request (journal entries have multiple lines)
- **Risk**: None - these are NOT unique keys

## Key Candidates

**There are no single-column unique keys** in this transactional data.

Potential composite keys:
- `(کد منطقه, شماره سند, شماره درخواست, TitkNo, TitMNo, TitTNo, titjno)` - may be unique per journal line

## Sample Data (مرکزی Sheet)

```
Row 1:
  کد منطقه: 20
  منطقه: شهرداري مركزي
  تاریخ: 1403/01/07
  شماره سند: 1
  TitkNo: 611
  TitkNam: موجودي نقد و بانک ها
  TitMNo: 1
  شرح سرفصل حساب معین: بانک پرداخت هزينه
  TitTNo: 1
  شرح سرفصل حساب تفضیلی: بانک ملي
  titjno: 8
  شرح سرفصل حساب جزء: سپرده 0216060960007 ملي اصفهان
  RadKNo: null
  RadMNo: null
  RadTNo: null
  RadJNo: null
  شرح مرکزهزینه: null
  مبلغ بدهکار: 388821984777
  مبلغ بستانکار: 0
  کاربر: صمديه
  شماره درخواست: 4296
  نوع درخواست: صدور اسناد اصلاحي (حسابداري)
  کد بودجه: null
  ماهیت سند: افتتاحيه
```

## Compatibility Assessment

**Verdict: Compatible with Small Adapters (Level 2)**

### Rationale:
1. ✅ Same data model (transactional journal entries)
2. ✅ Column names are different but map 1:1 to existing fields
3. ✅ Data types are compatible (integer→integer, text→text)
4. ⚠️ Persian column names require adapter update
5. ⚠️ Some columns renamed (e.g., `AreaNo`→`کد منطقه`, `Requests`→`شماره درخواست`)
6. ✅ No new entities required
7. ✅ No schema changes needed

### Required Changes:
- Update column name mappings in import script
- Handle Persian column names in pandas read
- Preserve existing API contracts (no changes needed)
