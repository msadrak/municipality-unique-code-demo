"""Record which journal rows carry Cost Center names (AG/AI) in the ORIGINAL source journal (provenance of AF:AI)."""
import openpyxl, pickle
SRC = 'C:/Users/sadra/Desktop/دفتر روزنامه 1404 - با اشخاص جدید.xlsx'
OUT = 'H:/Freelancing_Project/KalaniProject/municipality_demo/data/work/fe_model/source_cc_names.pkl'
wb = openpyxl.load_workbook(SRC, read_only=True)
rows = {}
for k, r in enumerate(wb['کدینگ جامع 1404 شهرداری'].iter_rows(min_row=6, min_col=32, max_col=35, values_only=True), start=6):
    if any(v not in (None, '', 'NULL') for v in r): rows[k] = tuple(r)
wb.close()
pickle.dump(rows, open(OUT, 'wb'))
print(len(rows))
