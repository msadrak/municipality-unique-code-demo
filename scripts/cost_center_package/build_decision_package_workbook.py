import sys
import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import pandas as pd
import numpy as np

print("=== STARTING DECISION PACKAGE WORKBOOK BUILDER (15 SHEETS) ===")

output_excel = r'C:\Users\sadra\Downloads\بسته_تصمیم_گیری_مراکز_هزینه_شهرداری_اصفهان.xlsx'
md_report_path = r'docs/cost-centers/گزارش_پیشنهادی_تصویب_مراکز_هزینه.md'

# Load previous files
prev_excel = r'C:\Users\sadra\Downloads\تحلیل_جامع_مراکز_هزینه_و_فعالیت_های_شهرداری_اصفهان.xlsx'
audit_excel = r'C:\Users\sadra\Downloads\ممیزی_نسخه_اول_مدل_مراکز_هزینه.xlsx'

df_dict = pd.read_excel(prev_excel, sheet_name='شناسنامه_مراکز_هزینه')
df_mapped = pd.read_excel(prev_excel, sheet_name='نگاشت_ردیف_های_مالی')
df_s11 = pd.read_excel(audit_excel, sheet_name='مراکز_اصلاح_شده')
df_s3 = pd.read_excel(audit_excel, sheet_name='اعتبارسنجی_متولی')

# Filter out CC-1304 to establish exactly 74 proposed centers
df_74 = df_dict[df_dict['کد مرکز هزینه'] != 'CC-1304'].copy().reset_index(drop=True)
print(f"Total proposed cost centers: {len(df_74)}")

# Status map
from assign_status import status_map

# Load corrected counts and real descriptions
corrected_counts = {}
real_descs = {}
exp_types = {}

# Map corrected descriptions based on second-pass audit
for cc_id in df_74['کد مرکز هزینه']:
    sub = df_mapped[df_mapped['کد مرکز هزینه پیشنهادی'] == cc_id]
    
    # Apply audit corrections for rows that were misrouted in first-pass
    if cc_id == 'CC-105':
        sub = df_mapped[df_mapped['شرح ردیف'].str.contains('حیوانات ناقل بیماری|جانوران موذی', na=False)]
    elif cc_id == 'CC-1405':
        sub = df_mapped[df_mapped['شرح ردیف'].str.contains('حفاظت فیزیکی', na=False)]
    elif cc_id == 'CC-1203':
        sub = df_mapped[df_mapped['شرح ردیف'].str.contains('حسابرسی', na=False)]
    elif cc_id == 'CC-804':
        sub = df_mapped[df_mapped['شرح ردیف'].str.contains('ایمن سازی فضاهای ناایمن|رفع خطر', na=False)]
        
    cnt = len(sub)
    corrected_counts[cc_id] = cnt
    unique_d = sub['شرح ردیف'].dropna().unique().tolist()
    real_descs[cc_id] = unique_d[:8]
    
    t_counts = sub['نوع هزینه'].value_counts()
    if cnt == 0:
        exp_types[cc_id] = 'خدمات پرسنلی درون‌سازمانی (تسهیم ستادی)'
    else:
        top_t = t_counts.index[0]
        if 'سرمایه' in top_t and len(t_counts) > 1 and 'جاری' in str(t_counts.index):
            exp_types[cc_id] = 'ترکیبی (عمدتاً سرمایه‌ای)'
        elif 'جاری' in top_t and len(t_counts) > 1 and 'سرمایه' in str(t_counts.index):
            exp_types[cc_id] = 'ترکیبی (عمدتاً جاری)'
        elif 'سرمایه' in top_t:
            exp_types[cc_id] = 'سرمایه‌ای'
        elif 'جاری' in top_t:
            exp_types[cc_id] = 'جاری'
        else:
            exp_types[cc_id] = top_t

print("Sample counts corrected:", {k: corrected_counts[k] for k in ['CC-101', 'CC-105', 'CC-1405', 'CC-1203', 'CC-804', 'CC-702']})

