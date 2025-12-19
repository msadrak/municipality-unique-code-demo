# Column Mapping: Hesabdary Information.xlsx → Database

## Mapping Overview

This document maps columns from `Hesabdary Information.xlsx` to the existing database models and API outputs.

## Old File vs New File Column Comparison

| Old File Column | New File Column | Notes |
|-----------------|-----------------|-------|
| AreaNo | کد منطقه | Zone code (integer) |
| - | منطقه | Zone name (new column) |
| - | تاریخ | Date string (new - use for date_str) |
| DocNo | شماره سند | Document number |
| TitkNo | TitkNo | Same - Account kol code |
| TitkNam | TitkNam | Same - Account kol name |
| TitMNo | TitMNo | Same - Account moein code |
| - | شرح سرفصل حساب معین | Moein description (new) |
| TitTNo | TitTNo | Same - Account tafsili code |
| TitTNam | شرح سرفصل حساب تفضیلی | Tafsili description (renamed) |
| TitJNo | titjno | Same but lowercase in new file |
| TitJNam | شرح سرفصل حساب جزء | Joz description (renamed) |
| RadKNo | RadKNo | Same (nullable) |
| RadMNo | RadMNo | Same (nullable) |
| RadTNo | RadTNo | Same (nullable) |
| RadJNo | RadJNo | Same (nullable) |
| RadJNam | شرح مرکزهزینه | Cost center description (renamed) |
| DebitAmnt | مبلغ بدهکار | Debit amount |
| CreditAmnt | مبلغ بستانکار | Credit amount |
| OprCod | کاربر | User/operator (different format) |
| Requests | شماره درخواست | Request ID |
| TypDesc | نوع درخواست | Request/transaction type |
| BodgetNo | کد بودجه | Budget code |
| - | ماهیت سند | Document nature (new) |
| FinYear | - | Removed - extract from تاریخ |

## Excel → Database Field Mapping

### FinancialDocument Model

| Excel Column (New) | DB Field | Type | Transformation |
|--------------------|----------|------|----------------|
| کد منطقه | zone_code | String | `str(val)` |
| شماره سند | doc_number | Integer | `int(val)` |
| شرح سرفصل حساب جزء | description | String | Combine with نوع درخواست |
| شرح مرکزهزینه | beneficiary | String | Use as beneficiary/cost center |
| - | amount | String | Use debit or credit (whichever > 0) |
| مبلغ بدهکار | debit | String | `str(val)` |
| مبلغ بستانکار | credit | String | `str(val)` |
| کد بودجه | budget_code | String | `str(int(val))` if not null |
| RadJNo | rad_code | String | `str(int(val))` if not null |
| TitTNo | tit_code | String | `str(val)` |
| شرح سرفصل حساب تفضیلی | tit_title | String | Direct copy |
| کاربر | opr_code | String | Direct copy |
| شماره درخواست | requests | String | Direct copy |
| تاریخ | date_str | String | Extract year or use as-is |

### Reference Data Extraction

#### BudgetRef (from distinct کد بودجه)
| Excel Column | DB Field | Transformation |
|--------------|----------|----------------|
| کد بودجه | budget_code | `str(int(val))` |
| کد منطقه | zone_raw | `str(val)` |
| - | title | Default `"Budget {code}"` |
| - | row_type | Default `"Current"` |

#### CostCenterRef (from distinct شرح مرکزهزینه)
| Excel Column | DB Field | Transformation |
|--------------|----------|----------------|
| - | code | Auto-generate `CC-{n:04d}` |
| شرح مرکزهزینه | title | Direct copy |

#### FinancialEventRef (from distinct نوع درخواست)
| Excel Column | DB Field | Transformation |
|--------------|----------|----------------|
| - | code | Auto-generate `EVT-{n:03d}` |
| نوع درخواست | title | Direct copy (strip whitespace) |

## Database → API Output Mapping

### /financial-docs/{zone_code} Endpoint

```python
# API Response Field → DB Field
{
    "id": doc.id,
    "zone_code": doc.zone_code,
    "doc_number": doc.doc_number,
    "description": doc.description,
    "beneficiary": doc.beneficiary,
    "amount": doc.amount,
    "debit": doc.debit,
    "credit": doc.credit,
    "budget_code": doc.budget_code,
    "rad_code": doc.rad_code,
    "tit_code": doc.tit_code,
    "tit_title": doc.tit_title,
    "opr_code": doc.opr_code,
    "requests": doc.requests,
    "date_str": doc.date_str
}
```

## Transformation Rules

### 1. Zone Code Normalization
```python
def normalize_zone_code(val):
    """Convert zone code to string, handling floats."""
    if pd.isna(val):
        return None
    return str(int(float(val)))
```

### 2. Budget Code Handling
```python
def clean_budget_code(val):
    """Convert budget code to string, preserving full precision."""
    if pd.isna(val):
        return None
    # Budget codes like 14010101.0 → "14010101"
    return str(int(float(val)))
```

### 3. Amount Debit/Credit Logic
```python
def calculate_amount(debit, credit):
    """Determine primary amount from debit/credit."""
    d = float(debit) if pd.notna(debit) else 0
    c = float(credit) if pd.notna(credit) else 0
    return str(int(d)) if d > 0 else str(int(c))
```

### 4. Date String Extraction
```python
def extract_year(date_str):
    """Extract fiscal year from date."""
    # تاریخ format: 1403/01/07
    if pd.isna(date_str):
        return "1403"
    parts = str(date_str).split('/')
    return parts[0] if len(parts) >= 1 else "1403"
```

### 5. Description Construction
```python
def build_description(row):
    """Combine multiple fields into description."""
    parts = []
    if pd.notna(row.get('شرح سرفصل حساب جزء')):
        parts.append(str(row['شرح سرفصل حساب جزء']).strip())
    if pd.notna(row.get('نوع درخواست')):
        parts.append(str(row['نوع درخواست']).strip())
    return " - ".join(parts)[:500]
```

## Column Name Mapping Constant

```python
COLUMN_MAP = {
    # New → Old (internal)
    'کد منطقه': 'zone_code',
    'منطقه': 'zone_name',
    'تاریخ': 'date_str',
    'شماره سند': 'doc_number',
    'TitkNo': 'titk_no',
    'TitkNam': 'titk_name',
    'TitMNo': 'titm_no',
    'شرح سرفصل حساب معین': 'titm_desc',
    'TitTNo': 'titt_no',
    'شرح سرفصل حساب تفضیلی': 'titt_desc',
    'titjno': 'titj_no',
    'شرح سرفصل حساب جزء': 'titj_desc',
    'RadKNo': 'radk_no',
    'RadMNo': 'radm_no',
    'RadTNo': 'radt_no',
    'RadJNo': 'radj_no',
    'شرح مرکزهزینه': 'cost_center_desc',
    'مبلغ بدهکار': 'debit',
    'مبلغ بستانکار': 'credit',
    'کاربر': 'operator',
    'شماره درخواست': 'request_id',
    'نوع درخواست': 'request_type',
    'کد بودجه': 'budget_code',
    'ماهیت سند': 'doc_nature'
}
```

## API Contract Impact

| API Endpoint | Impact | Notes |
|--------------|--------|-------|
| `/org/root` | None | Uses OrgUnit, not affected |
| `/org/{id}/children` | None | Uses OrgUnit, not affected |
| `/budgets/by-zone/{zone_code}` | None | Uses BudgetItem, not affected |
| `/financial-events` | Minor | May get additional event types |
| `/cost-centers` | Minor | May get additional cost centers |
| `/continuous-actions` | None | Not affected |
| `/financial-docs/{zone_code}` | None | Schema unchanged |

**Conclusion: No API contract changes required.**
