import os
import re
import openpyxl
import pandas as pd
import numpy as np

print("Starting cost center classification and generation script...")

# Load datasets
path_b = r'C:\Users\sadra\Downloads\مراکز هزینه طبق بودجه.xlsx'
path_cc = r'C:\Users\sadra\Downloads\cost center .xlsx'
path_act = r'C:\Users\sadra\Downloads\activity.xlsx'
path_org = r'C:\Users\sadra\Downloads\آمار پست های معاونتها-1405.xlsx'

df_b = pd.read_excel(path_b, sheet_name='انتقال کل مراکز هزینه 1404')
df_cc = pd.read_excel(path_cc, sheet_name='اولیه', header=1)
df_cc.columns = ['کد بودجه', 'شرح ردیف', 'نوع هزینه', 'کد سطح 1', 'عنوان سطح 1', 'کد سطح 2', 'عنوان سطح 2', 'متولی']
df_act = pd.read_excel(path_act, sheet_name='نحلیل فعالیت برای زیرموضوع')

print(f"Loaded: df_b={len(df_b)} rows, df_cc={len(df_cc)} rows, df_act={len(df_act)} rows")

# Clean text strings
for col in df_b.columns:
    df_b[col] = df_b[col].fillna('').astype(str).str.strip()

for col in df_cc.columns:
    df_cc[col] = df_cc[col].fillna('').astype(str).str.strip()

# Build mapping of budget code and description to topic/subtopic
topic_dict = {}
for _, r in df_b.iterrows():
    c = r['کد بودجه']
    d = r['شرح ردیف'].replace('\u200c', ' ').strip()
    topic_dict[(c, d)] = (r['موضوع'], r['زیرموضوع'])

code_topic_dict = {}
for _, r in df_b.iterrows():
    c = r['کد بودجه']
    if c not in code_topic_dict:
        code_topic_dict[c] = (r['موضوع'], r['زیرموضوع'])

print(f"Built topic lookup: {len(topic_dict)} specific pairs, {len(code_topic_dict)} code entries")
