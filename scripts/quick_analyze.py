import pandas as pd

file = r'f:\Freelancing_Project\KalaniProject\municipality_demo\data\reports\تملک دارایی سرمایه ای.xlsx'
xls = pd.ExcelFile(file)

print('=== SHEETS ===')
for s in xls.sheet_names:
    df = pd.read_excel(xls, sheet_name=s)
    print(f'{s}: {len(df)} rows, {len(df.columns)} cols')

print('\n=== COLUMNS ===')
df = pd.read_excel(xls, sheet_name=xls.sheet_names[0])
for i,c in enumerate(df.columns):
    print(f'{i}: {c}')

# Save to CSV for easier viewing
df.to_csv(r'f:\Freelancing_Project\KalaniProject\municipality_demo\scripts\capital_budget_sample.csv', index=False, encoding='utf-8-sig')
print('\nSaved sample to capital_budget_sample.csv')
