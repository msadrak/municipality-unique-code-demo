"""Independently verify every audit source cell and protected-file hashes."""
import csv,json,re,sqlite3,zipfile
from collections import Counter,defaultdict
from audit_journal_1404_independent import ROOT,V1,SOURCE,rows,cells,shared,hashfile

def run():
 failures=[];counts=Counter();db=sqlite3.connect(ROOT/'journal_records.sqlite')
 with zipfile.ZipFile(SOURCE) as z:
  ss=shared(z);bud={rn:cells(raw,ss)[0] for rn,raw in rows(z,'xl/worksheets/sheet5.xml')};unit={rn:cells(raw,ss)[0] for rn,raw in rows(z,'xl/worksheets/sheet4.xml')}
  for rn,oj,ej,aj in db.execute('SELECT source_row,original,enriched,applied FROM journal'):
   original=json.loads(oj);enriched=json.loads(ej)
   for r in json.loads(aj):
    counts['entries']+=1;target=r['target_column'];ref=r['reference_row'];m=re.fullmatch(r'([A-Z]+)(\d+)',ref)
    if not m:failures.append([rn,target,'invalid reference']);continue
    col,num=m.group(1),int(m.group(2));value=None
    if r['reference_file']!=SOURCE.name:failures.append([rn,target,'unexpected reference file'])
    if r['reference_sheet']=='بودجه 1404 + مراکز هزینه':
     value=bud.get(num,{}).get(col);expected={'AF':'F','AG':'G','AH':'H','AI':'I'}.get(target)
     if col!=expected:failures.append([rn,target,'wrong target/reference column'])
     counts['native_budget_refs']+=1
    elif target=='AM' and r['reference_sheet']=='کدینگ جامع 1404 شهرداری' and ref=='O'+str(rn):value=original.get('O');counts['same_row_bank_refs']+=1
    elif r['reference_sheet']=='واحد سازمانی':value=unit.get(num,{}).get(col)
    else:failures.append([rn,target,'unsupported reference'])
    if value!=r['new_value'] or enriched.get(target)!=value:failures.append([rn,target,'reference/audit/output mismatch'])
 db.close()
 before=json.loads((ROOT/'v1_preservation_before.json').read_text(encoding='utf-8'));hashes={p:hashfile(__import__('pathlib').Path(p)) for p in before}
 for p,h in before.items():
  if hashes[p]!=h:failures.append([p,'protected source/v1 changed'])
 result={'counts':dict(counts),'protected_files':len(before),'hashes_unchanged':not any(hashes[p]!=before[p] for p in before),'failures':failures,'assessment':'ACCEPTABLE' if not failures else 'NOT YET ACCEPTABLE'}
 (ROOT/'independent_entry_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False,indent=2))
 if failures:raise RuntimeError('Independent entry verification failed')
if __name__=='__main__':run()
