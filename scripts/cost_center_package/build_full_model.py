import sys
import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import pandas as pd
import numpy as np

print("Loading raw files...")
path_b = r'C:\Users\sadra\Downloads\مراکز هزینه طبق بودجه.xlsx'
path_cc = r'C:\Users\sadra\Downloads\cost center .xlsx'
path_act = r'C:\Users\sadra\Downloads\activity.xlsx'
path_org = r'C:\Users\sadra\Downloads\آمار پست های معاونتها-1405.xlsx'

df_b = pd.read_excel(path_b, sheet_name='انتقال کل مراکز هزینه 1404')
df_cc = pd.read_excel(path_cc, sheet_name='اولیه', header=1)
df_cc.columns = ['کد بودجه', 'شرح ردیف', 'نوع هزینه', 'کد سطح 1', 'عنوان سطح 1', 'کد سطح 2', 'عنوان سطح 2', 'متولی']
df_act = pd.read_excel(path_act, sheet_name='نحلیل فعالیت برای زیرموضوع')

for c in df_b.columns: df_b[c] = df_b[c].fillna('').astype(str).str.strip()
for c in df_cc.columns: df_cc[c] = df_cc[c].fillna('').astype(str).str.strip()

# Build topic mapping
code_to_topic = df_b.drop_duplicates(subset=['کد بودجه'])[['کد بودجه', 'موضوع', 'زیرموضوع']].set_index('کد بودجه')
b_lookup = {}
for _, r in df_b.iterrows():
    key = (r['کد بودجه'], r['شرح ردیف'].replace('\u200c', ' ').strip())
    b_lookup[key] = (r['موضوع'], r['زیرموضوع'])

print(f"Loaded: df_b={len(df_b)}, df_cc={len(df_cc)}")

# Classify each row
# Let's inspect unique rows
print("Starting classification logic...")
