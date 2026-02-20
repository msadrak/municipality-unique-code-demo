# Region 14 Deployment Scripts

## Quick Start

### 1. Test Classification (No Database)
```bash
# Test with sample data
python scripts/test_classification.py --examples

# Test your own text
python scripts/test_classification.py --test "آسفالت و روکش معابر"

# Analyze your CSV before importing
python scripts/test_classification.py --analyze scripts/region14_civil_items.csv
```

### 2. Preview Import (No Changes)
```bash
python scripts/seed_region14_segmented.py --dry-run
```

### 3. Execute Import
```bash
python scripts/seed_region14_segmented.py
```

### 4. Verify Results
```bash
python scripts/seed_region14_segmented.py --verify
```

---

## File Overview

### Core Scripts

| File | Purpose | Database Access |
|------|---------|-----------------|
| `seed_region14_segmented.py` | Main seeding script | Yes (writes) |
| `test_classification.py` | Classification tester | No |
| `region14_civil_items.csv` | Sample budget data | N/A |

### Documentation

| File | Purpose |
|------|---------|
| `REGION14_SEGMENTATION_GUIDE.md` | Complete guide |
| `README_REGION14.md` | This file (quick reference) |

---

## The 5 Sections

### Visual Reference

```
┌─────────────────────────────────────────────────────────────┐
│                       منطقه چهارده                          │
│                      (Region 14)                            │
└────────────┬────────────────────────────────────────────────┘
             │
             ├─── نظارت راه و آسفالت (ROAD_ASPHALT)
             │    User: admin_road_14
             │    Keywords: آسفالت, روکش, معابر, پیاده...
             │
             ├─── تاسیسات برق (ELECTRICAL)
             │    User: admin_elec_14
             │    Keywords: روشنایی, برق, چراغ, LED...
             │
             ├─── تاسیسات مکانیکی (MECHANICAL)
             │    User: admin_mech_14
             │    Keywords: آبیاری, پمپ, چاه, منبع...
             │
             ├─── نظارت ابنیه (SUPERVISION)
             │    User: admin_civil_14
             │    Keywords: احداث, ساختمان, پل, سازه...
             │
             └─── نظام فنی و عمومی (TECHNICAL)
                  User: admin_tech_14
                  Keywords: نظارت, طراحی, مشاوره...
                  (Also: FALLBACK for unmatched items)
```

---

## Classification Examples

### Example 1: Road Work
**Input:** `آسفالت و روکش معابر اصلی منطقه`

**Analysis:**
- ROAD_ASPHALT: 3 points (آسفالت ✓, روکش ✓, معابر ✓)
- ELECTRICAL: 0 points
- MECHANICAL: 0 points
- SUPERVISION: 0 points
- TECHNICAL: 0 points

**Result:** → ROAD_ASPHALT ✓

---

### Example 2: Lighting
**Input:** `تعمیر و نگهداری روشنایی معابر و پارک‌ها`

**Analysis:**
- ROAD_ASPHALT: 1 point (معابر ✓)
- ELECTRICAL: 1 point (روشنایی ✓)
- MECHANICAL: 0 points
- SUPERVISION: 0 points
- TECHNICAL: 0 points

**Result:** → ELECTRICAL ✓ (first match wins in tie)

---

### Example 3: Water Systems
**Input:** `تاسیسات مکانیکی و آبیاری فضای سبز`

**Analysis:**
- ROAD_ASPHALT: 0 points
- ELECTRICAL: 0 points
- MECHANICAL: 2 points (تاسیسات مکانیکی ✓, آبیاری ✓)
- SUPERVISION: 0 points
- TECHNICAL: 0 points

**Result:** → MECHANICAL ✓

---

### Example 4: Building Construction
**Input:** `احداث سرویس بهداشتی عمومی`

**Analysis:**
- ROAD_ASPHALT: 0 points
- ELECTRICAL: 0 points
- MECHANICAL: 0 points
- SUPERVISION: 2 points (احداث ✓, سرویس بهداشتی ✓)
- TECHNICAL: 0 points

**Result:** → SUPERVISION ✓

---

### Example 5: Technical Services
**Input:** `نظارت و مطالعات فنی پروژه‌های عمرانی`

**Analysis:**
- ROAD_ASPHALT: 0 points
- ELECTRICAL: 0 points
- MECHANICAL: 0 points
- SUPERVISION: 0 points
- TECHNICAL: 2 points (نظارت ✓, مطالعات ✓)

**Result:** → TECHNICAL ✓

---

### Example 6: Fallback
**Input:** `خرید تجهیزات اداری`

**Analysis:**
- ROAD_ASPHALT: 0 points
- ELECTRICAL: 0 points
- MECHANICAL: 0 points
- SUPERVISION: 0 points
- TECHNICAL: 0 points

**Result:** → TECHNICAL ✓ (FALLBACK)

---

## Workflow

### Phase 1: Preparation
```bash
# 1. Prepare your CSV file
# Columns: کد بودجه, شرح ردیف, مصوب 1403

# 2. Test classification accuracy
python scripts/test_classification.py --analyze your_file.csv

# 3. Review distribution (adjust keywords if needed)
```

### Phase 2: Preview
```bash
# 4. Run dry-run to preview changes
python scripts/seed_region14_segmented.py --dry-run --csv your_file.csv

# 5. Review output carefully
#    - Check section distribution
#    - Verify no errors
#    - Confirm fallback count is acceptable
```

### Phase 3: Execute
```bash
# 6. Backup database
cp municipality_demo.db municipality_demo.db.backup

# 7. Execute import
python scripts/seed_region14_segmented.py --csv your_file.csv

# 8. Verify results
python scripts/seed_region14_segmented.py --verify
```

### Phase 4: Post-Import
```bash
# 9. Test admin logins
python scripts/test_login_cli.py admin_road_14 Tehran@1403

# 10. Change passwords immediately!
```

---

## Keyword Reference (Quick)

### ROAD_ASPHALT (نظارت راه و آسفالت)
آسفالت • روکش • معابر • پیاده • جدول • کانیو • لکه • ترمیم حفاری • قیر • تراش • زیرسازی

### ELECTRICAL (تاسیسات برق)
روشنایی • برق • نور • چراغ • LED • پروژکتور • کابل • تاسیسات برقی

### MECHANICAL (تاسیسات مکانیکی)
آبیاری • چاه • پمپ • منبع • هیدرانت • آبنما • تاسیسات مکانیکی • لوله • مخزن • سپتیک • فاضلاب

### SUPERVISION (نظارت ابنیه)
احداث • ساختمان • ابنیه • پل • سازه • دیوار • سوله • اسکلت • فرهنگی • ورزشی • سرویس بهداشتی

### TECHNICAL (نظام فنی و عمومی)
نظارت • طراحی • نقشه • مشاوره • آزمایشگاه • مطالعات

---

## Common Issues

### Issue: High Fallback Rate
**Problem:** Too many items assigned to TECHNICAL (fallback)

**Solution:**
1. Review fallback items: `python scripts/test_classification.py --analyze your_file.csv`
2. Add missing keywords to `SECTION_KEYWORDS` in the script
3. Re-run dry-run to verify improvement

---

### Issue: Wrong Section Assignment
**Problem:** Item classified incorrectly

**Solution:**
1. Check keyword matches: `python scripts/test_classification.py --test "your description"`
2. Either:
   - Add specific keywords to correct section
   - OR manually reassign after import (via SQL)

```sql
-- Manual reassignment (if needed)
UPDATE budget_rows 
SET org_unit_id = (SELECT id FROM org_units WHERE code = 'R14_ELEC')
WHERE budget_coding = '11020402';
```

---

### Issue: CSV Encoding Error
**Problem:** `UnicodeDecodeError` when reading CSV

**Solution:**
```python
# Re-save CSV with UTF-8 encoding
import pandas as pd
df = pd.read_excel('your_file.xlsx')
df.to_csv('region14_civil_items.csv', index=False, encoding='utf-8-sig')
```

---

## Admin Credentials

After import, use these credentials for testing:

| Username | Section | Password | Status |
|----------|---------|----------|--------|
| `admin_road_14` | Road & Asphalt | `Tehran@1403` | ⚠️ Must change |
| `admin_elec_14` | Electrical | `Tehran@1403` | ⚠️ Must change |
| `admin_mech_14` | Mechanical | `Tehran@1403` | ⚠️ Must change |
| `admin_civil_14` | Building Supervision | `Tehran@1403` | ⚠️ Must change |
| `admin_tech_14` | Technical & General | `Tehran@1403` | ⚠️ Must change |

---

## Database Queries

### Check Section Distribution
```sql
SELECT 
    ou.title as section_name,
    COUNT(br.id) as budget_count,
    SUM(br.approved_amount) as total_budget,
    u.username as admin_user
FROM org_units ou
LEFT JOIN budget_rows br ON br.org_unit_id = ou.id
LEFT JOIN users u ON u.default_section_id = ou.id
WHERE ou.parent_id = (SELECT id FROM org_units WHERE code = '14')
GROUP BY ou.id, ou.title, u.username
ORDER BY ou.title;
```

### Find Specific Budget Item
```sql
SELECT 
    br.budget_coding,
    br.description,
    ou.title as section,
    sa.code as activity_code
FROM budget_rows br
JOIN org_units ou ON br.org_unit_id = ou.id
JOIN subsystem_activities sa ON br.activity_id = sa.id
WHERE br.budget_coding = '11020401';
```

### List All Constraints
```sql
SELECT 
    sa.code as activity_code,
    sa.title as activity_title,
    ac.budget_code_pattern,
    ou.title as section
FROM activity_constraints ac
JOIN subsystem_activities sa ON ac.subsystem_activity_id = sa.id
JOIN budget_rows br ON br.activity_id = sa.id
JOIN org_units ou ON br.org_unit_id = ou.id
WHERE sa.code LIKE 'CW_%'
LIMIT 20;
```

---

## Performance Notes

### Expected Runtime
- **CSV Reading:** < 1 second
- **Classification:** ~0.1 second per row
- **Database Operations:** ~0.5 second per row
- **Total (100 rows):** ~60 seconds

### Optimization Tips
1. Use `--dry-run` first to catch errors early
2. Import in batches if CSV is very large (>1000 rows)
3. Add database indexes if needed (script does this automatically)

---

## Security Checklist

- [ ] Database backed up before import
- [ ] CSV file reviewed for sensitive data
- [ ] Classification accuracy verified (dry-run)
- [ ] Import executed successfully
- [ ] All admin passwords changed immediately
- [ ] User access tested for each section
- [ ] Audit logs reviewed

---

## Support

**Script Issues:**
1. Check this README
2. Review `REGION14_SEGMENTATION_GUIDE.md` for detailed docs
3. Run `test_classification.py` to debug classification

**Database Issues:**
1. Check database connectivity
2. Verify tables exist: `python -c "from app import models; print('OK')"`
3. Review error messages in script output

**Classification Issues:**
1. Use `test_classification.py --analyze` to review
2. Add keywords as needed
3. Re-run with updated script

---

## Next Steps

After successful import:

1. ✓ Verify section distribution
2. ✓ Test admin logins
3. ✓ Change all passwords
4. ✓ Review classification accuracy
5. ✓ Perform sample transactions
6. ✓ Document any adjustments
7. ✓ Move to production

---

## File Locations

```
municipality_demo/
├── scripts/
│   ├── seed_region14_segmented.py     ← Main script
│   ├── test_classification.py         ← Testing tool
│   ├── region14_civil_items.csv       ← Sample data
│   ├── REGION14_SEGMENTATION_GUIDE.md ← Full guide
│   └── README_REGION14.md             ← This file
└── municipality_demo.db                ← Database
```

---

## Version Info

**Script Version:** 1.0  
**Date:** 2026-01-30  
**Author:** Senior Backend Engineer & Data Architect  
**Python:** 3.8+  
**Database:** SQLite / PostgreSQL

---

## Quick Commands Reference

```bash
# Test classification
python scripts/test_classification.py --examples

# Analyze CSV
python scripts/test_classification.py --analyze region14_civil_items.csv

# Dry run import
python scripts/seed_region14_segmented.py --dry-run

# Execute import
python scripts/seed_region14_segmented.py

# Verify
python scripts/seed_region14_segmented.py --verify

# Test login
python scripts/test_login_cli.py admin_road_14 Tehran@1403
```

---

**End of README**
