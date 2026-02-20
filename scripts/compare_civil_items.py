# -*- coding: utf-8 -*-
import csv
import zipfile
import xml.etree.ElementTree as ET
import sys
import io

# Set UTF-8 encoding for stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Read CSV file
print("="*80)
print("READING CSV FILE (region14_civil_items.csv)")
print("="*80)

csv_items = []
with open('scripts/region14_civil_items.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row.get('کد بودجه'):  # Skip empty rows
            csv_items.append(row)

print(f"\nTotal items in CSV: {len(csv_items)}")
print("\nCSV Items (Budget Codes):")
for i, item in enumerate(csv_items, 1):
    print(f"{i}. {item['کد بودجه']} - {item['شرح ردیف']}")

# Extract budget codes from CSV for comparison
csv_codes = set([item['کد بودجه'].strip() for item in csv_items])

# Read Excel file by unzipping it
print("\n" + "="*80)
print("READING EXCEL FILE (Sarmayei_Region14.xlsx)")
print("="*80)

excel_path = 'data/reports/Sarmayei_Region14.xlsx'

try:
    with zipfile.ZipFile(excel_path, 'r') as zip_ref:
        # Read the shared strings (text values in Excel)
        shared_strings = []
        try:
            with zip_ref.open('xl/sharedStrings.xml') as f:
                tree = ET.parse(f)
                root = tree.getroot()
                ns = {'': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                for si in root.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si'):
                    t = si.find('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t')
                    if t is not None:
                        shared_strings.append(t.text)
        except:
            pass
        
        # Read the worksheet data
        with zip_ref.open('xl/worksheets/sheet1.xml') as f:
            tree = ET.parse(f)
            root = tree.getroot()
            
            rows = []
            ns = {'': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            
            for row_elem in root.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row'):
                row_data = []
                for cell in row_elem.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c'):
                    v = cell.find('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v')
                    t_attr = cell.get('t')
                    
                    if v is not None:
                        if t_attr == 's':  # Shared string
                            try:
                                row_data.append(shared_strings[int(v.text)])
                            except:
                                row_data.append(v.text)
                        else:
                            row_data.append(v.text)
                    else:
                        row_data.append('')
                rows.append(row_data)
            
            print(f"\nFound {len(rows)} rows in Excel (including header)")
            if rows:
                headers = rows[0]
                print(f"Headers: {headers}")
                
                # Print all data
                print("\nAll Excel Data:")
                for i, row in enumerate(rows[1:], 1):
                    if row and any(row):  # Skip empty rows
                        print(f"{i}. {' | '.join(str(cell) for cell in row[:5])}")  # Show first 5 columns
                
                # Try to find code column index
                code_col_idx = None
                for idx, header in enumerate(headers):
                    if header and ('کد' in str(header) or 'code' in str(header).lower()):
                        code_col_idx = idx
                        print(f"\nFound code column at index {idx}: {header}")
                        break
                
                if code_col_idx is not None:
                    excel_codes = []
                    for row in rows[1:]:
                        if row and len(row) > code_col_idx and row[code_col_idx]:
                            excel_codes.append(str(row[code_col_idx]).strip())
                    
                    print(f"\nExcel has {len(excel_codes)} budget items")
                    print(f"CSV has {len(csv_codes)} selected civil items")
                    
                    # Find missing items
                    missing_codes = [code for code in excel_codes if code not in csv_codes]
                    
                    print("\n" + "="*80)
                    print(f"ITEMS IN EXCEL BUT NOT IN CSV: {len(missing_codes)}")
                    print("="*80)
                    
                    for i, row in enumerate(rows[1:], 1):
                        if row and len(row) > code_col_idx and row[code_col_idx]:
                            code = str(row[code_col_idx]).strip()
                            if code in missing_codes:
                                print(f"\n{missing_codes.index(code) + 1}. Code: {code}")
                                for j, cell in enumerate(row[:5]):
                                    if cell and j < len(headers):
                                        print(f"   {headers[j]}: {cell}")
                    
                    print("\n" + "="*80)
                    print("VERIFICATION")
                    print("="*80)
                    print(f"CSV has {len(csv_items)} civil items")
                    print(f"Excel has {len(excel_codes)} total budget items")
                    print(f"Items NOT selected as civil: {len(missing_codes)}")
                    print(f"Check: {len(csv_items)} + {len(missing_codes)} = {len(csv_items) + len(missing_codes)} (Excel total: {len(excel_codes)})")
                    
                    if len(csv_items) == 20:
                        print(f"\nCONFIRMED: Exactly 20 items are selected as civil activities")
                    else:
                        print(f"\nWARNING: Expected 20 civil items, but found {len(csv_items)}")

except Exception as e:
    print(f"Error reading Excel file: {e}")
    import traceback
    traceback.print_exc()
