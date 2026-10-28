"""Assemble final workbook: replace sheet1, append Cost_Center_Summary and Cost_Center_Review."""
import json, zipfile, copy, re
from xml.sax.saxutils import escape

SRC = r'C:/Users/sadra/Desktop/دفتر روزنامه 1404 - با اشخاص جدید.xlsx'
DST = r'C:/Users/sadra/Desktop/دفتر_روزنامه_1404_مراکز_هزینه_تکمیل_شده.xlsx'

stats = json.load(open('cc_stats.json', encoding='utf-8'))
review = json.load(open('cc_review.json', encoding='utf-8'))

def sheet_xml(rows):
    out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
           '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
           '<sheetViews><sheetView rightToLeft="1" workbookViewId="0"/></sheetViews><sheetData>']
    for i, row in enumerate(rows, 1):
        out.append(f'<row r="{i}">')
        for j, v in enumerate(row):
            if v is None or v == '': continue
            col = ''
            n = j + 1
            while n: n, r = divmod(n - 1, 26); col = chr(65 + r) + col
            out.append(f'<c r="{col}{i}" t="inlineStr"><is><t xml:space="preserve">{escape(str(v))}</t></is></c>')
        out.append('</row>')
    out.append('</sheetData></worksheet>')
    return ''.join(out).encode('utf-8')

summary_rows = [
    ['شاخص', 'مقدار'],
    ['سطرهای حسابداری دارای مبلغ (Eligible)', stats['eligible']],
    ['سطرهای دارای مرکز هزینه کامل (کد و نام هر دو سطح) قبل از پردازش', stats['pre_complete']],
    ['سطرهای دارای نام که کد آنها تکمیل شد', stats['codes_filled']],
    ['سطرهای فاقد نام که مرکز هزینه آنها تعیین شد', stats['name_filled']],
    ['انتساب‌های احرازشده (Verified)', stats['verified']],
    ['انتساب‌های پیشنهادی (Proposed)', stats['proposed']],
    ['سطرهای حل‌نشده (Unresolved)', stats['unresolved']],
    ['سطرهای کامل پس از پردازش', stats['pre_complete'] + stats['codes_filled'] + stats['name_filled']],
    ['درصد پوشش نهایی (نسبت به سطرهای دارای مبلغ)',
     f"{100*(stats['pre_complete']+stats['codes_filled']+stats['name_filled'])/max(1,stats['eligible']):.2f}%"],
    ['یادداشت', 'انتساب‌های پیشنهادی در شیت Cost_Center_Review جهت بازبینی ارائه شده‌اند و مصوبه رسمی تلقی نمی‌شوند.'],
]
review_rows = [['سطر مبدأ', 'شرح سند', 'مرکز هزینه پیشنهادی', 'دلیل عدم قطعیت', 'شواهد', 'وضعیت بازبینی']]
review_rows += review

zin = zipfile.ZipFile(SRC)
with zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED) as zout:
    for item in zin.infolist():
        name = item.filename
        if name == 'xl/worksheets/sheet1.xml':
            with open('sheet1_new.xml', 'rb') as f, zout.open(copy.copy(item), 'w') as o:
                while True:
                    b = f.read(8 * 1024 * 1024)
                    if not b: break
                    o.write(b)
        elif name == 'xl/workbook.xml':
            data = zin.read(name).decode('utf-8')
            data = data.replace('</sheets>',
                '<sheet name="Cost_Center_Summary" sheetId="106" r:id="rId106"/>'
                '<sheet name="Cost_Center_Review" sheetId="107" r:id="rId107"/></sheets>')
            zout.writestr(copy.copy(item), data)
        elif name == 'xl/_rels/workbook.xml.rels':
            data = zin.read(name).decode('utf-8')
            data = data.replace('</Relationships>',
                '<Relationship Id="rId106" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet_cc1.xml"/>'
                '<Relationship Id="rId107" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet_cc2.xml"/>'
                '</Relationships>')
            zout.writestr(copy.copy(item), data)
        elif name == '[Content_Types].xml':
            data = zin.read(name).decode('utf-8')
            data = data.replace('</Types>',
                '<Override PartName="/xl/worksheets/sheet_cc1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                '<Override PartName="/xl/worksheets/sheet_cc2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                '</Types>')
            zout.writestr(copy.copy(item), data)
        elif name == 'xl/calcChain.xml':
            continue  # drop calc chain; Excel rebuilds it
        else:
            with zin.open(item) as f, zout.open(copy.copy(item), 'w') as o:
                while True:
                    b = f.read(8 * 1024 * 1024)
                    if not b: break
                    o.write(b)
    zout.writestr('xl/worksheets/sheet_cc1.xml', sheet_xml(summary_rows))
    zout.writestr('xl/worksheets/sheet_cc2.xml', sheet_xml(review_rows))
zin.close()
print('written', DST)
