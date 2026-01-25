import pandas as pd

file = r'f:\Freelancing_Project\KalaniProject\municipality_demo\data\reports\تملک دارایی سرمایه ای.xlsx'
output_path = r'f:\Freelancing_Project\KalaniProject\municipality_demo\scripts'

# Load data
df = pd.read_excel(file, sheet_name='سرمایه ای')

# Analysis file
with open(f'{output_path}/budget_analysis.txt', 'w', encoding='utf-8') as f:
    f.write('=== CAPITAL BUDGET ANALYSIS ===\n\n')
    f.write(f'Total rows: {len(df)}\n')
    f.write(f'Total columns: {len(df.columns)}\n\n')
    
    f.write('=== COLUMN NAMES ===\n')
    for i, c in enumerate(df.columns):
        f.write(f'{i}: {c}\n')
    
    f.write('\n=== UNIQUE VALUES IN منطقه COLUMN ===\n')
    regions = df['منطقه'].unique()
    for r in regions:
        count = len(df[df['منطقه'] == r])
        f.write(f'{r}: {count} rows\n')
    
    # Check for Region 14
    f.write('\n=== REGION 14 CHECK ===\n')
    for r in regions:
        if '14' in str(r) or '۱۴' in str(r) or 'چهارده' in str(r):
            f.write(f'FOUND: {r}\n')
    
    # Filter Region 14
    r14_filter = df['منطقه'].astype(str).str.contains('14|۱۴', regex=True, na=False)
    r14_df = df[r14_filter]
    f.write(f'\nRegion 14 rows found: {len(r14_df)}\n')
    
    if len(r14_df) > 0:
        f.write('\n=== REGION 14 ACTIVITY TYPES (نوع) ===\n')
        for t in r14_df['نوع'].unique():
            f.write(f'- {t}\n')
        
        f.write('\n=== REGION 14 BUDGET CODES SAMPLE ===\n')
        for _, row in r14_df.head(20).iterrows():
            f.write(f"{row['کد بودجه']}: {row['شرح ردیف']}\n")

# Export Region 14 data
if len(r14_df) > 0:
    r14_df.to_excel(f'{output_path}/Region14_Capital_Budget.xlsx', index=False)
    print(f'Exported {len(r14_df)} Region 14 rows to Region14_Capital_Budget.xlsx')

print('Analysis complete. See budget_analysis.txt')
