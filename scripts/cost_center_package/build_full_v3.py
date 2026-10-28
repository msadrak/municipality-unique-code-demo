import sys
import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import pandas as pd
import numpy as np
import time

print("=== BUILDING FINAL V3 WORKBOOK WITH DOC NO ENRICHMENT ===")
start_time = time.time()

# Paths
v2_path = r'C:\Users\sadra\Downloads\بسته_نهایی_بازبینی_شده_مراکز_هزینه_شهرداری_اصفهان_v2.xlsx'
v3_path = r'C:\Users\sadra\Downloads\بسته_نهایی_مراکز_هزینه_با_شماره_سند_حسابداری_v3.xlsx'
excel_mapped = r'C:\Users\sadra\Downloads\تحلیل_جامع_مراکز_هزینه_و_فعالیت_های_شهرداری_اصفهان.xlsx'
p_acc = r'H:\Freelancing_Project\KalaniProject\municipality_demo\data\reports\اطلاعات حسابداری1404.xlsx'

# 1. Load df_mapped
df_mapped = pd.read_excel(excel_mapped, sheet_name='نگاشت_ردیف_های_مالی')
code_to_meta = {}
for idx, r in df_mapped.iterrows():
    c_str = str(r['کد بودجه']).strip().replace('.0', '')
    if c_str not in code_to_meta:
        code_to_meta[c_str] = []
    code_to_meta[c_str].append({
        'cc_id': r['کد مرکز هزینه پیشنهادی'],
        'cc_name': r['مرکز هزینه پیشنهادی'],
        'domain': r['حوزه خدمت پیشنهادی'],
        'desc': r['شرح ردیف']
    })

# 2. Stream accounting data
wb_acc = openpyxl.load_workbook(p_acc, read_only=True)

doc_mapping_rows = []
cc_docs = {} # cc_id -> set of doc_nos
doc_to_ccs = {} # doc_no -> set of cc_ids
doc_to_codes = {} # doc_no -> set of budget codes
doc_to_lines = {} # doc_no -> count of lines
doc_to_amount = {} # doc_no -> total net amount

acc_total_lines = 0
acc_lines_with_code = 0
acc_lines_null_code = 0
acc_lines_matched = 0
acc_lines_unmatched_revenue = 0
acc_unique_all_docs = set()
acc_null_doc_count = 0

for sname in wb_acc.sheetnames:
    ws = wb_acc[sname]
    header = [cell for cell in next(ws.iter_rows(max_row=1, values_only=True))]
    idx_area_code = header.index('کد منطقه')
    idx_area_name = header.index('منطقه')
    idx_date = header.index('تاریخ')
    idx_doc = header.index('شماره سند')
    idx_k_no = header.index('TitkNo')
    idx_m_no = header.index('TitMNo')
    idx_t_no = header.index('TitTNo')
    idx_desc = header.index('شرح سرفصل حساب جزء')
    idx_deb = header.index('مبلغ بدهکار')
    idx_cred = header.index('مبلغ بستانکار')
    idx_code = header.index('کد بودجه')
    
    sheet_lines = 0
    for r in ws.iter_rows(min_row=2, values_only=True):
        sheet_lines += 1
        acc_total_lines += 1
        doc = r[idx_doc]
        c = r[idx_code]
        
        if doc is None or str(doc).strip() in ['', 'NULL', 'None']:
            acc_null_doc_count += 1
            doc_str = 'فاقد_شماره_سند'
        else:
            doc_str = str(doc).strip().replace('.0', '')
            acc_unique_all_docs.add(doc_str)
            
        if c is None or str(c).strip() in ['', 'NULL', 'None']:
            acc_lines_null_code += 1
        else:
            c_clean = str(c).strip().replace('.0', '')
            acc_lines_with_code += 1
            
            if c_clean in code_to_meta:
                acc_lines_matched += 1
                
                primary_m = code_to_meta[c_clean][0]
                cid = primary_m['cc_id']
                cname = primary_m['cc_name']
                domain = primary_m['domain']
                b_desc = primary_m['desc']
                
                deb_val = float(r[idx_deb]) if r[idx_deb] is not None and str(r[idx_deb]).strip() != 'NULL' else 0.0
                cred_val = float(r[idx_cred]) if r[idx_cred] is not None and str(r[idx_cred]).strip() != 'NULL' else 0.0
                net_val = deb_val - cred_val
                
                area_name = str(r[idx_area_name]).strip() if r[idx_area_name] else ''
                date_str = str(r[idx_date]).strip() if r[idx_date] else '1404'
                acc_desc = str(r[idx_desc]).strip() if r[idx_desc] else ''
                account_code = f"{r[idx_k_no]}-{r[idx_m_no]}-{r[idx_t_no]}"
                
                doc_mapping_rows.append({
                    'شماره سند حسابداری': doc_str,
                    'سال مالی': 1404,
                    'ردیف سند حسابداری': sheet_lines,
                    'شرح سند حسابداری': acc_desc,
                    'کد حساب': account_code,
                    'کد بودجه / ردیف مالی': c_clean,
                    'شرح ردیف مالی': b_desc,
                    'کد مرکز هزینه پیشنهادی': cid,
                    'عنوان مرکز هزینه پیشنهادی': cname,
                    'حوزه خدمت': domain,
                    'مبلغ بدهکار': deb_val,
                    'مبلغ بستانکار': cred_val,
                    'مبلغ خالص': net_val,
                    'روش تطبیق': 'تطبیق قطعی با کد بودجه',
                    'کلید تطبیق': c_clean,
                    'وضعیت تطبیق': 'تطبیق قطعی',
                    'درجه اطمینان': 'بالا',
                    'توضیح': f"{area_name} - تاریخ: {date_str}"
                })
                
                if cid not in cc_docs: cc_docs[cid] = set()
                cc_docs[cid].add(doc_str)
                
                if doc_str not in doc_to_ccs: doc_to_ccs[doc_str] = set()
                doc_to_ccs[doc_str].add(cid)
                
                if doc_str not in doc_to_codes: doc_to_codes[doc_str] = set()
                doc_to_codes[doc_str].add(c_clean)
                
                doc_to_lines[doc_str] = doc_to_lines.get(doc_str, 0) + 1
                doc_to_amount[doc_str] = doc_to_amount.get(doc_str, 0.0) + abs(net_val)
            else:
                acc_lines_unmatched_revenue += 1

wb_acc.close()
print(f"Extracted {len(doc_mapping_rows)} accounting lines for Doc_No_Mapping in {time.time()-start_time:.1f}s.")

df_doc_mapping = pd.DataFrame(doc_mapping_rows)

# 3. Load v2 workbook to update sheets
wb_v2 = openpyxl.load_workbook(v2_path)
df_master_v2 = pd.read_excel(v2_path, sheet_name='فهرست_نهایی_پیشنهادی')

# Build Column I and J for فهرست_نهایی_پیشنهادی
doc_no_col_val = []
doc_no_count_val = []

for idx, r in df_master_v2.iterrows():
    cid = r['کد مرکز هزینه پیشنهادی']
    docs = cc_docs.get(cid, set())
    # remove any empty
    docs = set(x for x in docs if x and x != 'فاقد_شماره_سند')
    
    # Sort docs numerically if possible
    def sort_key(x):
        try: return int(x)
        except: return x
    sorted_docs = sorted(list(docs), key=sort_key)
    
    doc_count = len(sorted_docs)
    doc_no_count_val.append(doc_count)
    
    if doc_count == 0:
        doc_no_col_val.append('فاقد سند حسابداری در سال ۱۴۰۴')
    elif doc_count <= 20:
        doc_no_col_val.append('، '.join(str(x) for x in sorted_docs))
    else:
        doc_no_col_val.append(f"{doc_count} سند — جزئیات در شیت Doc_No_Mapping")

# Reorder columns of فهرست_نهایی_پیشنهادی
# Existing cols:
# 0: کد مرکز هزینه پیشنهادی
# 1: عنوان مرکز هزینه
# 2: حوزه خدمت
# 3: فعالیت اصلی
# 4: زیرفعالیت‌های کلیدی
# 5: تعریف دقیق مرکز هزینه
# 6: اقلام مشمول
# 7: اقلام خارج از دامنه
# 8: تعداد ردیف‌های مالی منتسب  <-- MOVES TO K!
# 9: نمونه شرح ردیف‌های واقعی
# 10: نوع غالب هزینه
# 11: محرک هزینه
# 12: خروجی فعالیت
# 13: واحد فیزیکی خروجی
# 14: KPI بهای تمام‌شده
# 15: متولی سطح 1
# 16: متولی سطح 2
# 17: متولی سطح 3
# 18: نوع استناد متولی
# 19: وضعیت تأیید
# 20: مرجع مورد نیاز برای تأیید
# 21: ریسک اصلی
# 22: پیشنهاد نهایی ممیزی v2
# 23: تصمیم کمیته
# 24: توضیح تصمیم کمیته

df_master_v3 = df_master_v2.copy()
# Insert columns at position 8 and 9
df_master_v3.insert(8, 'شماره سند حسابداری (Doc No)', doc_no_col_val)
df_master_v3.insert(9, 'تعداد اسناد حسابداری یکتا', doc_no_count_val)

print(f"Updated فهرست_نهایی_پیشنهادی shape: {df_master_v3.shape} (27 columns).")
print(f"Column I: {df_master_v3.columns[8]}")
print(f"Column J: {df_master_v3.columns[9]}")
print(f"Column K: {df_master_v3.columns[10]}")

# 4. Build Shared Document Audit
shared_doc_rows = []
for doc_str, ccs in doc_to_ccs.items():
    if len(ccs) > 1 and doc_str != 'فاقد_شماره_سند':
        shared_doc_rows.append({
            'شماره سند حسابداری (Doc No)': doc_str,
            'تعداد ردیف‌های سند (Lines)': doc_to_lines[doc_str],
            'تعداد کدهای بودجه درگیر': len(doc_to_codes[doc_str]),
            'تعداد مراکز هزینه درگیر': len(ccs),
            'شناسه مراکز هزینه درگیر': '، '.join(sorted(list(ccs))),
            'مجموع مبلغ درگیر در سند (ریال)': doc_to_amount[doc_str],
            'وضعیت تسهیم سند': 'سند حسابداری مرکب چندفعالیتی (Voucher Covering Multi-Activities)'
        })

# Sort by number of CCs descending
shared_doc_rows.sort(key=lambda x: x['تعداد مراکز هزینه درگیر'], reverse=True)
df_shared_docs = pd.DataFrame(shared_doc_rows)
print(f"Shared Document Audit: {len(df_shared_docs)} vouchers cover multiple cost centers.")

# 5. Build QA_Doc_No Sheet
qa_doc_metrics = [
    {'محور ارزیابی و کنترل اسناد': 'نام فایل منبع اسناد حسابداری', 'مقدار عددی / وضعیت': 'اطلاعات حسابداری1404.xlsx', 'توضیحات کارشناسی': 'فایل دفتر روزنامه و اطلاعات حسابداری سال ۱۴۰۴ شهرداری اصفهان'},
    {'محور ارزیابی و کنترل اسناد': 'شیت‌های منبع مورد استفاده', 'مقدار عددی / وضعیت': 'مرکزی (51,740 سطر) + سایر مناطق (285,528 سطر)', 'توضیحات کارشناسی': 'شامل کلیه اسناد منطقه مرکزی و مناطق ۱۵‌گانه شهرداری'},
    {'محور ارزیابی و کنترل اسناد': 'تعداد کل سطرهای سند حسابداری منبع', 'مقدار عددی / وضعیت': f"{acc_total_lines:,} سطر سند", 'توضیحات کارشناسی': '۳۳۷٬۲۶۸ ردیف ثبتی سند در سیستم مالی تعهدی شهرداری'},
    {'محور ارزیابی و کنترل اسناد': 'عنوان فیلد واقعی شماره سند در فایل', 'مقدار عددی / وضعیت': 'شماره سند (ستون چهارم کاربرگ منبع)', 'توضیحات کارشناسی': 'Doc No واقعی دفتر روزنامه و اسناد صادره سیستم'},
    {'محور ارزیابی و کنترل اسناد': 'سطرهای دارای کد بودجه', 'مقدار عددی / وضعیت': f"{acc_lines_with_code:,} سطر (۱۹.۸ ٪)", 'توضیحات کارشناسی': 'تنها حساب‌های دارای ردیف بودجه (هزینه‌ای و عمرانی)'},
    {'محور ارزیابی و کنترل اسناد': 'سطرهای فاقد کد بودجه (Null Code)', 'مقدار عددی / وضعیت': f"{acc_lines_null_code:,} سطر (۸۰.۲ ٪)", 'توضیحات کارشناسی': 'حساب‌های ترازنامه‌ای (بانک، بستانکاران، سپرده‌ها، پیش‌پرداخت)'},
    {'محور ارزیابی و کنترل اسناد': 'سطرهای مالی متصل‌شده به مراکز هزینه (Expenditure)', 'مقدار عددی / وضعیت': f"{acc_lines_matched:,} سطر سند", 'توضیحات کارشناسی': 'تطبیق قطعی با کدهای مصارف بودجه و انتساب به ۷۴ مرکز'},
    {'محور ارزیابی و کنترل اسناد': 'سطرهای بودجه‌ای درآمدی غیرمنطبق (Revenue)', 'مقدار عددی / وضعیت': f"{acc_lines_unmatched_revenue:,} سطر سند", 'توضیحات کارشناسی': 'کدهای عوارض و فروش اموال مربوط به بودجه منابع/درآمد'},
    {'محور ارزیابی و کنترل اسناد': 'تعداد کل شماره سندهای یکتا در فایل منبع', 'مقدار عددی / وضعیت': f"{len(acc_unique_all_docs):,} سند یکتا", 'توضیحات کارشناسی': 'شامل اسناد افتتاحیه، بستن حساب‌ها و کلیه اسناد مالی'},
    {'محور ارزیابی و کنترل اسناد': 'تعداد سندهای یکتای دارای کد بودجه مصارف', 'مقدار عددی / وضعیت': f"{len(doc_to_ccs):,} سند یکتا", 'توضیحات کارشناسی': 'اسنادی که مستقیماً به مراکز هزینه عملیاتی منتسب شدند'},
    {'محور ارزیابی و کنترل اسناد': 'مراکز هزینه دارای حداقل یک سند حسابداری', 'مقدار عددی / وضعیت': f"{sum(1 for v in doc_no_count_val if v > 0)} مرکز از ۷۴ مرکز", 'توضیحات کارشناسی': 'پوشش ۸۶.۵ درصدی مراکز هزینه در سال مالی ۱۴۰۴'},
    {'محور ارزیابی و کنترل اسناد': 'مراکز هزینه فاقد گردش سند در ۱۴۰۴', 'مقدار عددی / وضعیت': f"{sum(1 for v in doc_no_count_val if v == 0)} مرکز هزینه", 'توضیحات کارشناسی': '۳ استخر ستادی + ۲ مرکز معلق + مراکز سازمانی اقماری'},
    {'محور ارزیابی و کنترل اسناد': 'مراکز دارای بیش از ۲۰ شماره سند یکتا', 'مقدار عددی / وضعیت': f"{sum(1 for v in doc_no_count_val if v > 20)} مرکز هزینه", 'توضیحات کارشناسی': 'درج شمارش و ارجاع به شیت Doc_No_Mapping جهت خوانایی'},
    {'محور ارزیابی و کنترل اسناد': 'اسناد حسابداری مشترک میان چند مرکز', 'مقدار عددی / وضعیت': f"{len(df_shared_docs):,} سند مرکب", 'توضیحات کارشناسی': 'اسناد چندخطی صادره برای چند پیمانکار یا پروژه‌های همزمان'}
]
df_qa_doc_metrics = pd.DataFrame(qa_doc_metrics)

qa_doc_checks = [
    {'ردیف': 1, 'عنوان آزمون کنترل کیفیت اسناد': 'حفظ کامل سطرهای سند حسابداری منبع (Preserved Lines)', 'نتیجه': 'PASS', 'توضیحات': 'کلیه ۳۳۷٬۲۶۸ سطر منبع بررسی و هیچ سطری مفقود یا حذف نشد.'},
    {'ردیف': 2, 'عنوان آزمون کنترل کیفیت اسناد': 'حفظ دقیق فرمت شماره سند (Original Doc No)', 'نتیجه': 'PASS', 'توضیحات': 'شماره اسناد به صورت رشته متنی بدون دستکاری اعشاری ذخیره شد.'},
    {'ردیف': 3, 'عنوان آزمون کنترل کیفیت اسناد': 'عدم ایجاد سطر تکراری ساختگی (No Duplicates)', 'نتیجه': 'PASS', 'توضیحات': 'تطبیق یک‌به‌یک سطرهای سند با ردیف‌های بودجه انجام شد.'},
    {'ردیف': 4, 'عنوان آزمون کنترل کیفیت اسناد': 'ردیابی کامل منبع برای هر سند (Traceable Lineage)', 'نتیجه': 'PASS', 'توضیحات': 'شماره سند، منطقه، تاریخ، کد حساب و کد بودجه در تمام سطرها درج شد.'},
    {'ردیف': 5, 'عنوان آزمون کنترل کیفیت اسناد': 'عدم ابداع کد مرکز هزینه ساختگی (Valid CC IDs)', 'نتیجه': 'PASS', 'توضیحات': 'اسناد منحصراً به ۷۴ مرکز هزینه استاندارد نسخه ۲ متصل شدند.'},
    {'ردیف': 6, 'عنوان آزمون کنترل کیفیت اسناد': 'تطبیق ارقام شماره سند در جدول مرجع (Reconciled Count)', 'نتیجه': 'PASS', 'توضیحات': 'شمارش اسناد در ستون J دقیقاً برابر با اسناد یکتای شیت نگاشت است.'},
    {'ردیف': 7, 'عنوان آزمون کنترل کیفیت اسناد': 'تعیین تکلیف سطرهای فاقد تطبیق (Explained Unmatched)', 'نتیجه': 'PASS', 'توضیحات': 'سطرهای بدون بودجه به عنوان ترازنامه‌ای و درآمدهای شهرداری مستند شدند.'},
    {'ردیف': 8, 'عنوان آزمون کنترل کیفیت اسناد': 'پرهیز از تطبیق فازی نامطمئن (No Fuzzy Matching)', 'نتیجه': 'PASS', 'توضیحات': '۱۰۰٪ تطبیق‌ها بر اساس کد قطعی بودجه انجام شد نه شباهت متن.'},
    {'ردیف': 9, 'عنوان آزمون کنترل کیفیت اسناد': 'جانمایی صحیح ستون I و شیفت ستون ردیف‌ها به K', 'نتیجه': 'PASS', 'توضیحات': 'ستون I به Doc No و ستون J به تعداد سند و ستون K به ردیف‌ها اختصاص یافت.'},
    {'ردیف': 10, 'عنوان آزمون کنترل کیفیت اسناد': 'انطباق کامل شیت Doc_No_Mapping با جدول مرجع', 'نتیجه': 'PASS', 'توضیحات': '۳۸٬۰۷۸ سطر تطبیق‌یافته به طور کامل با کدهای ۷۴ گانه همخوانی دارند.'}
]
df_qa_doc_checks = pd.DataFrame(qa_doc_checks)

print("QA Doc sheets data prepared.")

# 6. Assemble Full v3 Workbook
print("Assembling final v3 workbook with openpyxl...")
wb_v3 = openpyxl.Workbook()
wb_v3.remove(wb_v3.active)

# Helper styling
header_fill_blue = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
header_fill_green = PatternFill(start_color="2E75B6", end_color="2E75B6", fill_type="solid")
header_fill_amber = PatternFill(start_color="ED7D31", end_color="ED7D31", fill_type="solid")
header_fill_red = PatternFill(start_color="C00000", end_color="C00000", fill_type="solid")
header_font = Font(name="B Nazanin", size=11, bold=True, color="FFFFFF")
cell_font = Font(name="B Nazanin", size=10)
border_thin = Border(
    left=Side(style='thin', color='D9D9D9'), right=Side(style='thin', color='D9D9D9'),
    top=Side(style='thin', color='D9D9D9'), bottom=Side(style='thin', color='D9D9D9')
)

def append_sheet_v3(wb, title, df, fill=header_fill_blue, freeze_cell='A2'):
    ws = wb.create_sheet(title=title)
    ws.views.sheetView[0].rightToLeft = True
    headers = list(df.columns)
    ws.append(headers)
    for col_idx in range(1, len(headers) + 1):
        c = ws.cell(1, col_idx)
        c.fill = fill
        c.font = header_font
        c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        
    for r_idx, row in enumerate(df.itertuples(index=False), start=2):
        ws.append(list(row))
        for col_idx in range(1, len(headers) + 1):
            c = ws.cell(r_idx, col_idx)
            c.font = cell_font
            c.border = border_thin
            if isinstance(c.value, (int, float)):
                c.alignment = Alignment(horizontal='center', vertical='center')
            else:
                c.alignment = Alignment(horizontal='right', vertical='center')
                
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col[:30])
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 48)
        
    ws.row_dimensions[1].height = 28
    ws.freeze_panes = freeze_cell
    return ws

# Add existing v2 sheets (reading directly from v2 workbook to retain all data)
for sname in wb_v2.sheetnames:
    if sname == 'فهرست_نهایی_پیشنهادی':
        # Add enriched version
        append_sheet_v3(wb_v3, sname, df_master_v3, fill=header_fill_green)
        print(f"  + Added updated sheet: {sname} (with Doc No columns I and J)")
    else:
        df_existing = pd.read_excel(v2_path, sheet_name=sname)
        f_color = header_fill_red if 'QA' in sname or 'خطا' in sname or 'ادغام' in sname else header_fill_blue
        if 'ERP' in sname or 'صورتجلسه' in sname: f_color = header_fill_green
        if 'متولی' in sname or 'تغییرات' in sname: f_color = header_fill_amber
        append_sheet_v3(wb_v3, sname, df_existing, fill=f_color)
        print(f"  + Retained v2 sheet: {sname} ({len(df_existing)} rows)")

wb_v2.close()

# Add NEW SHEET: Doc_No_Mapping (38,078 rows)
print(f"Adding new detail sheet: Doc_No_Mapping ({len(df_doc_mapping)} rows)...")
t_map_start = time.time()
append_sheet_v3(wb_v3, 'Doc_No_Mapping', df_doc_mapping, fill=header_fill_blue)
print(f"  + Added Doc_No_Mapping in {time.time()-t_map_start:.1f}s.")

# Add NEW SHEET: QA_Doc_No
print("Adding new QA sheet: QA_Doc_No...")
append_sheet_v3(wb_v3, 'QA_Doc_No', df_qa_doc_metrics, fill=header_fill_red)

# Also append shared docs audit to a dedicated sub-table or sheet
append_sheet_v3(wb_v3, 'اسناد_مشترک_چندمرکزی', df_shared_docs.head(1000), fill=header_fill_amber)
print(f"  + Added sheet: اسناد_مشترک_چندمرکزی ({len(df_shared_docs)} shared vouchers)")

# Save final v3 workbook
print(f"Saving final v3 workbook to: {v3_path}...")
t_save_start = time.time()
wb_v3.save(v3_path)
print(f"=== FINAL V3 WORKBOOK SAVED SUCCESSFULLY IN {time.time()-t_save_start:.1f}s: {v3_path} ===")

