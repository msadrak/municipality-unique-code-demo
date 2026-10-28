"""Extract v4 Cost_Center_Review (row-level CC decisions of the v4 run) for reuse as CC-relationship evidence."""
import openpyxl, pickle, time
V4 = 'C:/Users/sadra/Desktop/دفتر_روزنامه_1404_مراکز_هزینه_فعالیت_محور_v4.xlsx'
OUT = 'H:/Freelancing_Project/KalaniProject/municipality_demo/data/work/fe_model/'
t0 = time.time()
wb = openpyxl.load_workbook(V4, read_only=True)
rows = [tuple(r) for r in wb['Cost_Center_Review'].iter_rows(values_only=True)]
wb.close()
pickle.dump(rows, open(OUT + 'ccreview_v4.pkl', 'wb'))
print(len(rows), rows[0], round(time.time() - t0))
