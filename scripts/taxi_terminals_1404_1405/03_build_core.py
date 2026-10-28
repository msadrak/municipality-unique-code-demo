"""Phase 1/2 — typed, trimmed, source-identity-preserving core tables derived from the raw tables.

sanad.sid / source_record_id = <ORGCODE>-<FY>-S-<source Excel row 6-digit>   (stable: file + row)
doc_key = <ORGCODE>-<FY>-<Sanad_Num trimmed>   (source-scoped; Sanad_Num is NOT globally unique)
Raw columns stay in sanad_raw; here we only trim padding and cast Bed/Bes (verified all-digit integers).
"""
import sqlite3, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from common import *

con = sqlite3.connect(DB)
cur = con.cursor()
for t in ('sanad', 'hesab'):
    cur.execute(f'DROP TABLE IF EXISTS {t}')
cur.execute('''CREATE TABLE hesab(hid TEXT PRIMARY KEY, org, fy, src_row INT, name, name_norm, tabageh, gorooh, kol, moeen, taf1, taf2,
  have_child INT, hcode, kind, type, p, latin, level INT, parent_hcode, is_leaf INT)''')
cur.execute('''CREATE TABLE sanad(sid TEXT PRIMARY KEY, org, fy, src_file, src_sheet, src_row INT, doc_key, sanad_num, date, date_ok INT,
  des, des_norm, kol, moeen, taf1, taf2, bed INT, bes INT, hcode, sharh, sharh_norm, f1, f2, f3, f4, f5, vahed, markaz, person, name_vahed)''')

hrows = cur.execute('SELECT org,fy,src_row,Name,Tabageh,Gorooh,Kol,Moeen,Tafsili1,Tafsili2,HaveChild,HCode,Kind,Type,P,LatinName FROM hesab_raw ORDER BY rid').fetchall()
out = []
for org, fy, sr, name, tab, gor, kol, moe, t1, t2, hc, hcode, kind, typ, p, latin in hrows:
    kol, moe, t1, t2 = kol.strip(), moe.strip(), t1.strip(), t2.strip()
    # hierarchy level from components (kol / moeen / tafsili1 / tafsili2) -- structural, not semantic
    level = 1 if moe == '0' else (2 if t1 == '0' else (3 if t2 == '0' else 4))
    if level == 1: parent = None
    elif level == 2: parent = f'{kol}-0-0-0'
    elif level == 3: parent = f'{kol}-{moe}-0-0'
    else: parent = f'{kol}-{moe}-{t1}-0'
    out.append((f'{ORGS[org][0]}-{fy}-H-{sr:06d}', org, fy, sr, name.strip(), norm(name), tab.strip(), gor.strip(), kol, moe, t1, t2, int(hc.strip()),
                hcode.strip(), kind.strip(), typ.strip(), p.strip(), None if latin is None else latin.strip(), level, parent, 1 if hc.strip() == '0' else 0))
cur.executemany('INSERT INTO hesab VALUES(' + ','.join('?' * 21) + ')', out)

import re
rows = cur.execute('SELECT org,fy,src_file,src_sheet,src_row,Sanad_Num,Date,Des,Kol,Moeen,Tafsili1,Tafsili2,Bed,Bes,HCode,Sharh,Field1,Field2,Field3,Field4,Field5,CodeVahed,CodeMarkaz,CodePerson,NameVahed FROM sanad_raw ORDER BY rid').fetchall()
def t(v): return None if v is None else str(v).strip()
out = []
for org, fy, sf, ss, sr, num, date, des, kol, moe, t1, t2, bed, bes, hcode, sharh, f1, f2, f3, f4, f5, vah, mar, per, nv in rows:
    num = t(num)
    d = t(date)
    ok = 0
    m = re.fullmatch(r'(\d{4})/(\d{2})/(\d{2})', d or '')
    if m and m.group(1) == fy and 1 <= int(m.group(2)) <= 12 and 1 <= int(m.group(3)) <= (31 if int(m.group(2)) <= 6 else (30 if int(m.group(2)) <= 11 else 30)):
        ok = 1
    out.append((f'{ORGS[org][0]}-{fy}-S-{sr:06d}', org, fy, sf, ss, sr, f'{ORGS[org][0]}-{fy}-{num}', num, d, ok, t(des), norm(des), t(kol), t(moe), t(t1), t(t2),
                int(bed), int(bes), t(hcode), t(sharh), norm(sharh), t(f1), t(f2), t(f3), t(f4), t(f5), t(vah), t(mar), t(per), t(nv)))
cur.executemany('INSERT INTO sanad VALUES(' + ','.join('?' * 30) + ')', out)
for ix in ('CREATE INDEX i_s_doc ON sanad(doc_key)', 'CREATE INDEX i_s_h ON sanad(org,fy,hcode)', 'CREATE INDEX i_s_ofk ON sanad(org,fy,kol,moeen)',
           'CREATE INDEX i_h_h ON hesab(org,fy,hcode)', 'CREATE INDEX i_h_k ON hesab(org,fy,kol,moeen,taf1,taf2)'):
    cur.execute(ix)
con.commit()
print(cur.execute('select count(*) from sanad').fetchone(), cur.execute('select count(*) from hesab').fetchone())
