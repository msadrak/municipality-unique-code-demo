"""Phase 1 — load the eight source workbooks losslessly into SQLite (work area, not a master).

sanad_raw / hesab_raw keep every cell exactly as read (padding included) plus source file/sheet/row identity.
"""
import sqlite3, os, hashlib, json, sys
import openpyxl
sys.path.insert(0, os.path.dirname(__file__))
from common import *

SANAD_COLS = ['Sanad_Num', 'Date', 'Des', 'Kol', 'Moeen', 'Tafsili1', 'Tafsili2', 'Bed', 'Bes', 'HCode', 'Sharh', 'Field1',
              'Field2', 'Field3', 'Field4', 'Field5', 'CodeVahed', 'CodeMarkaz', 'CodePerson', 'NameVahed']
HESAB_COLS = ['Name', 'Tabageh', 'Gorooh', 'Kol', 'Moeen', 'Tafsili1', 'Tafsili2', 'HaveChild', 'HCode', 'Kind', 'Type', 'P', 'LatinName']

os.makedirs(WORK, exist_ok=True)
if os.path.exists(DB):
    os.remove(DB)
con = sqlite3.connect(DB)
cur = con.cursor()
cur.execute('CREATE TABLE inventory(org,fy,kind,file,sheet,sha256,bytes,header_json,header_ok,data_rows,cell_types_json)')
cur.execute(f'CREATE TABLE sanad_raw(rid INTEGER PRIMARY KEY, org,fy,src_file,src_sheet,src_row,{",".join(SANAD_COLS)})')
cur.execute(f'CREATE TABLE hesab_raw(rid INTEGER PRIMARY KEY, org,fy,src_file,src_sheet,src_row,{",".join(HESAB_COLS)})')

for org in ORGS:
    for fy in YEARS:
        for kind, cols, tbl in (('Hesab', HESAB_COLS, 'hesab_raw'), ('Sanad', SANAD_COLS, 'sanad_raw')):
            p = src_path(org, fy, kind)
            sha = hashlib.sha256(open(p, 'rb').read()).hexdigest()
            wb = openpyxl.load_workbook(p, read_only=True)
            assert len(wb.worksheets) == 1
            ws = wb.worksheets[0]
            it = ws.iter_rows(values_only=True)
            hdr = list(next(it))
            types = {}
            n = 0
            rows = []
            for i, r in enumerate(it, start=2):
                if all(c is None for c in r):
                    continue
                n += 1
                for c in r:
                    types[type(c).__name__] = types.get(type(c).__name__, 0) + 1
                rows.append((org, fy, f'{ORGS[org][1]}/{fy}/{kind}.xlsx', ws.title, i) + tuple(r))
            ph = ','.join('?' * (5 + len(cols)))
            cur.executemany(f'INSERT INTO {tbl}(org,fy,src_file,src_sheet,src_row,{",".join(cols)}) VALUES({ph})', rows)
            cur.execute('INSERT INTO inventory VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                        (org, fy, kind, f'{ORGS[org][1]}/{fy}/{kind}.xlsx', ws.title, sha, os.path.getsize(p), json.dumps(hdr),
                         int(hdr == cols), n, json.dumps(types)))
            print(org, fy, kind, n, hdr == cols, types)
con.commit()
con.close()
