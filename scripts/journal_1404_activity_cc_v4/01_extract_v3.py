import openpyxl, pickle, time
from collections import Counter
p = 'C:/Users/sadra/Desktop/دفتر_روزنامه_1404_مراکز_هزینه_فعالیت_محور_v3.xlsx'
t0 = time.time()
wb = openpyxl.load_workbook(p, read_only=True, data_only=False)
ws = wb['کدینگ جامع 1404 شهرداری']
# 0-based indices kept
KEEP = [0, 2, 3, 4, 7, 8, 9, 12, 13, 14, 15, 16, 17, 18, 19, 22, 23, 25, 27, 28, 29, 30, 31, 32, 33, 34]
rows = []
formula_cols = Counter()
excel_row = 5
for r in ws.iter_rows(min_row=6, max_col=43, values_only=True):
    excel_row += 1
    for i, v in enumerate(r):
        if isinstance(v, str) and v.startswith('='):
            formula_cols[i] += 1
    rows.append((excel_row,) + tuple(r[i] if i < len(r) else None for i in KEEP))
wb.close()
pickle.dump({'keep': KEEP, 'rows': rows, 'formula_cols': dict(formula_cols)}, open('zz_v3.pkl', 'wb'))
print('rows', len(rows), 'formula cols', dict(formula_cols), 'secs', round(time.time() - t0))
