# Region 14 Micro-Segmentation Guide

## Overview

The Region 14 deployment implements a **Section-Based Isolation** strategy, distributing budget rows across 5 specialized Civil Sections based on intelligent keyword analysis. This approach ensures proper segregation of duties and budget control at a granular level.

## Architecture Philosophy

### Micro-Segmentation Strategy
Instead of a single generic admin for Region 14, the system creates **5 isolated sections**, each with:
- Dedicated Organizational Unit (OrgUnit)
- Dedicated Admin User (ADMIN_L1)
- Exclusive Budget Rows
- Strict Activity Constraints

### Zero Trust Budget Control
- **1-to-1 Mapping**: Every budget row → Unique Activity → Unique BudgetRow
- **Section Isolation**: Budget rows assigned to sections cannot cross boundaries
- **Database-Level Enforcement**: Check constraints prevent overspending
- **Audit Trail**: Complete tracking of all budget operations

---

## The 5 Official Sections

### 1. ROAD_ASPHALT (نظارت راه و آسفالت)
**Username:** `admin_road_14`  
**Responsibility:** Roads, asphalt, pavements, sidewalks

**Keywords:**
- آسفالت (asphalt)
- روکش (coating)
- معابر (streets)
- پیاده (pedestrian/sidewalk)
- جدول (curb)
- کانیو (gutter)
- لکه (pothole)
- ترمیم حفاری (excavation repair)
- قیر (bitumen)
- تراش (milling)
- زیرسازی (subbase)

**Example Budget Items:**
- آسفالت و روکش معابر اصلی منطقه
- لکه‌گیری و ترمیم حفاری معابر
- بتن‌ریزی و زیرسازی پیاده‌رو
- اجرای جدول و کانیوو در معابر

---

### 2. ELECTRICAL (تاسیسات برق)
**Username:** `admin_elec_14`  
**Responsibility:** Electrical systems, lighting, power infrastructure

**Keywords:**
- روشنایی (lighting)
- برق (electricity)
- نور (light)
- چراغ (lamp)
- LED
- پروژکتور (projector/floodlight)
- کابل (cable)
- تاسیسات برقی (electrical installations)

**Example Budget Items:**
- تعمیر و نگهداری روشنایی معابر و پارک‌ها
- نصب و راه‌اندازی چراغ LED در خیابان‌ها
- نصب پروژکتور در پارک‌های عمومی
- تعویض کابل و تاسیسات برقی

---

### 3. MECHANICAL (تاسیسات مکانیکی)
**Username:** `admin_mech_14`  
**Responsibility:** Mechanical systems, water, irrigation, pumps

**Keywords:**
- آبیاری (irrigation)
- چاه (well)
- پمپ (pump)
- منبع (reservoir)
- هیدرانت (hydrant)
- آبنما (fountain)
- تاسیسات مکانیکی (mechanical installations)
- لوله (pipe)
- مخزن (tank)
- سپتیک (septic)

**Example Budget Items:**
- تاسیسات مکانیکی و آبیاری فضای سبز
- تعمیر و نگهداری پمپ و منبع آب
- احداث شبکه فاضلاب و مخزن سپتیک
- نصب هیدرانت و آبنما در میدان‌ها

---

### 4. SUPERVISION (نظارت ابنیه)
**Username:** `admin_civil_14`  
**Responsibility:** Building construction, structures, supervision

**Keywords:**
- احداث (construction)
- ساختمان (building)
- ابنیه (buildings/structures)
- پل (bridge)
- سازه (structure)
- دیوار (wall)
- سوله (shed/hangar)
- اسکلت (skeleton/frame)
- فرهنگی (cultural)
- ورزشی (sports)
- سرویس بهداشتی (sanitary service)

**Example Budget Items:**
- احداث سرویس بهداشتی عمومی
- احداث پل عابر پیاده
- ساخت دیوار حائل و سازه نگهبان
- احداث سوله ورزشی

---

### 5. TECHNICAL (نظام فنی و عمومی)
**Username:** `admin_tech_14`  
**Responsibility:** Technical services, design, consultation (Fallback section)

**Keywords:**
- نظارت (supervision)
- طراحی (design)
- نقشه (map/plan)
- مشاوره (consultation)
- آزمایشگاه (laboratory)
- مطالعات (studies)

**Example Budget Items:**
- نظارت و مطالعات فنی پروژه‌های عمرانی
- طراحی و نقشه‌برداری پروژه‌های جدید
- مشاوره و بازرسی کیفیت پروژه‌ها
- آزمایشگاه کنترل کیفیت مصالح

**Note:** This section also serves as the **fallback** for any budget items that don't match any keywords.

---

## Classification Algorithm

### How It Works

```python
For each budget row:
    1. Extract text: budget_code + description
    2. Calculate score for each section:
       score = count of matching keywords
    3. Assign to section with highest score
    4. If no matches (score = 0), assign to TECHNICAL (fallback)
```

### Examples

#### Example 1: Clear Match
**Budget Row:** `آسفالت و روکش معابر اصلی منطقه`

**Scoring:**
- ROAD_ASPHALT: 3 (آسفالت, روکش, معابر)
- ELECTRICAL: 0
- MECHANICAL: 0
- SUPERVISION: 0
- TECHNICAL: 0

**Result:** Assigned to ROAD_ASPHALT ✓

---

#### Example 2: Multiple Matches
**Budget Row:** `احداث شبکه فاضلاب و مخزن سپتیک`

**Scoring:**
- ROAD_ASPHALT: 0
- ELECTRICAL: 0
- MECHANICAL: 3 (فاضلاب, مخزن, سپتیک)
- SUPERVISION: 1 (احداث)
- TECHNICAL: 0

**Result:** Assigned to MECHANICAL ✓ (highest score)

---

#### Example 3: Fallback
**Budget Row:** `خرید تجهیزات اداری`

**Scoring:**
- ROAD_ASPHALT: 0
- ELECTRICAL: 0
- MECHANICAL: 0
- SUPERVISION: 0
- TECHNICAL: 0

**Result:** Assigned to TECHNICAL ✓ (fallback)

---

## Usage Guide

### Prerequisites

1. **Database**: Ensure PostgreSQL/SQLite is running
2. **CSV File**: Prepare budget data in CSV format
3. **Python Environment**: Install dependencies

### CSV Format

The script expects a CSV file with the following columns:

| Column Name | Persian Name | Required | Description |
|------------|-------------|----------|-------------|
| `budget_code` or `کد بودجه` | کد بودجه | Yes | Budget code (e.g., "11020401") |
| `description` or `شرح ردیف` | شرح ردیف | Yes | Budget line description |
| `approved_1403` or `مصوب 1403` | مصوب 1403 | Yes | Approved amount (in Rials) |

**Example CSV:**
```csv
کد بودجه,شرح ردیف,مصوب 1403
11020401,آسفالت و روکش معابر اصلی منطقه,5000000000
11020402,تعمیر و نگهداری روشنایی معابر و پارک‌ها,2500000000
```

### Running the Script

#### 1. Preview Mode (Recommended First Run)
```bash
python scripts/seed_region14_segmented.py --dry-run
```

**Output:**
- Shows what will be created
- Displays classification results
- No database changes

#### 2. Execute Import
```bash
python scripts/seed_region14_segmented.py
```

**Output:**
- Creates all sections, users, activities, budget rows
- Commits to database
- Shows summary report

#### 3. Custom CSV File
```bash
python scripts/seed_region14_segmented.py --csv path/to/your/file.csv
```

#### 4. Verification Only
```bash
python scripts/seed_region14_segmented.py --verify
```

**Output:**
- Checks existing segmentation
- Shows distribution statistics
- No changes

---

## Output Report

### Summary Report Example

```
================================================================================
SEEDING SUMMARY REPORT
================================================================================
Status: IMPORT COMPLETED

Structural Components:
  • Section OrgUnits Created: 5
  • Admin Users Created: 5

Budget Components:
  • Total Budget Rows Processed: 20
  • Activities Created: 20
  • BudgetRows Created: 20
  • ActivityConstraints Created: 20
  • Skipped: 0

Classification Results:
  • نظارت راه و آسفالت: 4 items
  • تاسیسات برق: 4 items
  • تاسیسات مکانیکی: 4 items
  • نظارت ابنیه: 4 items
  • نظام فنی و عمومی: 4 items
  • Fallback (no keywords): 0 items

================================================================================
Section Admin Credentials:
================================================================================
  • admin_road_14
    Name: Admin - Road & Asphalt (Region 14)
    Password: Tehran@1403 (MUST CHANGE)
  
  • admin_elec_14
    Name: Admin - Electrical Systems (Region 14)
    Password: Tehran@1403 (MUST CHANGE)
  
  • admin_mech_14
    Name: Admin - Mechanical Systems (Region 14)
    Password: Tehran@1403 (MUST CHANGE)
  
  • admin_civil_14
    Name: Admin - Building Supervision (Region 14)
    Password: Tehran@1403 (MUST CHANGE)
  
  • admin_tech_14
    Name: Admin - Technical & General (Region 14)
    Password: Tehran@1403 (MUST CHANGE)
================================================================================
```

---

## Verification

### Database Verification

The script automatically verifies the segmentation:

```
================================================================================
SEGMENTATION VERIFICATION
================================================================================
✓ Region: منطقه چهارده (ID: 1)

Section Distribution:
  • نظارت راه و آسفالت:
    - OrgUnit ID: 101
    - Budget Rows: 4
    - Total Budget: 9,800,000,000 Rials
    - Admin: admin_road_14 (ID: 201)
  
  • تاسیسات برق:
    - OrgUnit ID: 102
    - Budget Rows: 4
    - Total Budget: 6,500,000,000 Rials
    - Admin: admin_elec_14 (ID: 202)
  
  [... other sections ...]
================================================================================
```

### Manual Verification

```sql
-- Check section distribution
SELECT 
    ou.title as section_name,
    COUNT(br.id) as budget_count,
    SUM(br.approved_amount) as total_budget
FROM org_units ou
LEFT JOIN budget_rows br ON br.org_unit_id = ou.id
WHERE ou.parent_id = (SELECT id FROM org_units WHERE code = '14')
GROUP BY ou.id, ou.title;

-- Check user access
SELECT 
    u.username,
    u.full_name,
    ou.title as section
FROM users u
JOIN org_units ou ON u.default_section_id = ou.id
WHERE u.username LIKE 'admin_%_14';

-- Check activity constraints
SELECT 
    sa.code as activity_code,
    sa.title as activity_title,
    ac.budget_code_pattern,
    br.budget_coding
FROM subsystem_activities sa
JOIN activity_constraints ac ON ac.subsystem_activity_id = sa.id
JOIN budget_rows br ON br.activity_id = sa.id
WHERE sa.code LIKE 'CW_%'
LIMIT 10;
```

---

## Security Considerations

### Default Password
**Password:** `Tehran@1403`  
**⚠️ WARNING:** All admin users MUST change their password on first login!

### Access Control
- Each admin can only access their section's budget rows
- RBAC enforced at application level
- Database constraints prevent cross-section transactions

### Audit Trail
- All budget operations logged in `budget_transactions` table
- Transaction history tracked in `workflow_logs`
- Immutable accounting records in `journal_snapshots`

---

## Troubleshooting

### Issue: CSV File Not Found
**Error:** `FileNotFoundError: CSV file not found`

**Solution:**
```bash
# Option 1: Place CSV at default location
cp your_file.csv scripts/region14_civil_items.csv

# Option 2: Specify custom path
python scripts/seed_region14_segmented.py --csv /path/to/your/file.csv
```

---

### Issue: Encoding Problems
**Error:** `UnicodeDecodeError`

**Solution:**
- Ensure CSV is UTF-8 encoded
- Open CSV in Excel and save as "CSV UTF-8 (Comma delimited)"

---

### Issue: All Items Going to Fallback
**Problem:** All budget items classified as TECHNICAL

**Solution:**
- Check CSV column names match expected format
- Ensure descriptions contain Persian keywords
- Review classification algorithm in script

---

### Issue: Duplicate Budget Codes
**Error:** `IntegrityError: UNIQUE constraint failed`

**Solution:**
```bash
# Check for duplicates in CSV
python -c "
import csv
from collections import Counter
with open('scripts/region14_civil_items.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    codes = [row['کد بودجه'] for row in reader if row.get('کد بودجه')]
    duplicates = [code for code, count in Counter(codes).items() if count > 1]
    if duplicates:
        print('Duplicates found:', duplicates)
    else:
        print('No duplicates')
"
```

---

## Customization

### Adding New Keywords

To improve classification accuracy, edit the `SECTION_KEYWORDS` dictionary in the script:

```python
SECTION_KEYWORDS = {
    "ROAD_ASPHALT": [
        "آسفالت", "روکش", "معابر", "پیاده",
        # Add your custom keywords here
        "جاده", "خیابان‌سازی"
    ],
    # ... other sections
}
```

### Adding New Sections

1. Edit `SECTIONS` dictionary:
```python
SECTIONS = {
    # ... existing sections
    "NEW_SECTION": {
        "code": "R14_NEW",
        "title": "بخش جدید",
        "username": "admin_new_14",
        "full_name": "Admin - New Section (Region 14)",
        "org_type": "SECTION"
    }
}
```

2. Add keywords:
```python
SECTION_KEYWORDS = {
    # ... existing keywords
    "NEW_SECTION": ["keyword1", "keyword2"]
}
```

3. Re-run the script

---

## Best Practices

### 1. Always Preview First
```bash
python scripts/seed_region14_segmented.py --dry-run
```

### 2. Backup Database Before Import
```bash
# SQLite
cp municipality_demo.db municipality_demo.db.backup

# PostgreSQL
pg_dump municipality_db > backup.sql
```

### 3. Review Classification Results
- Check the summary report for fallback count
- If too many items are falling back, add more keywords

### 4. Test with Sample Data
- Start with a small CSV (5-10 rows)
- Verify classification accuracy
- Then import full dataset

### 5. Change Passwords Immediately
```sql
-- After import, remind admins to change passwords
SELECT username, full_name 
FROM users 
WHERE username LIKE 'admin_%_14' 
  AND password_hash LIKE 'pbkdf2%Tehran@1403%';
```

---

## Next Steps

After successful import:

1. **Password Change**: All admins change default password
2. **Access Testing**: Each admin logs in and verifies their budget access
3. **Budget Review**: Finance team reviews classification accuracy
4. **Adjustment**: If needed, manually reassign misclassified items
5. **Production Deployment**: Move to production environment

---

## Support

For issues or questions:
- Review this documentation
- Check the script's inline comments
- Run with `--dry-run` to preview changes
- Use `--verify` to check current state

**Script Location:** `scripts/seed_region14_segmented.py`  
**CSV Template:** `scripts/region14_civil_items.csv`  
**Database:** SQLite (`municipality_demo.db`) or PostgreSQL

---

## Appendix: Database Schema

### Key Tables

#### org_units
- `id`: Primary key
- `title`: Section title (Persian)
- `code`: Section code (e.g., "R14_ROAD")
- `parent_id`: Points to Region 14
- `org_type`: "SECTION"

#### users
- `id`: Primary key
- `username`: e.g., "admin_road_14"
- `password_hash`: PBKDF2 hashed password
- `role`: "ADMIN_L1"
- `admin_level`: 1
- `default_section_id`: Foreign key to org_units

#### budget_rows
- `id`: Primary key
- `activity_id`: Foreign key to subsystem_activities
- `org_unit_id`: Foreign key to org_units (section)
- `budget_coding`: Budget code
- `approved_amount`: BigInteger (Rials)
- `blocked_amount`: BigInteger
- `spent_amount`: BigInteger

#### activity_constraints
- `id`: Primary key
- `subsystem_activity_id`: Foreign key
- `budget_code_pattern`: Exact budget code (1-to-1 lock)
- `constraint_type`: "INCLUDE"
- `is_active`: true

---

## Changelog

### Version 1.0 (2026-01-30)
- Initial release
- 5 section micro-segmentation
- Keyword-based classification
- Strict 1-to-1 mapping
- Zero trust budget control
