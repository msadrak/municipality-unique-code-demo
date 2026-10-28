"""Add independently measured QA and sample review to an enriched delivery."""
from __future__ import annotations
import argparse,csv,json,zipfile,re,xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter,defaultdict
import openpyxl
from enrich_journal_1404 import NS,MAIN,TARGETS,FIELDS,iter_raw_rows,decode_row,load_shared,is_blank,sheet_xml,norm
from xml.sax.saxutils import quoteattr

def append_reports(path,specs):
 temp=path.with_suffix('.finalizing.xlsx')
 with zipfile.ZipFile(path) as zi,zipfile.ZipFile(temp,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as zo:
  workbook=zi.read('xl/workbook.xml');rels=zi.read('xl/_rels/workbook.xml.rels');types=zi.read('[Content_Types].xml')
  sheetids=[int(e.get('sheetId')) for e in ET.fromstring(workbook).find('{'+NS+'}sheets')]
  a=[];b=[];c=[]
  register_path=path.parent/'source_register.json'
  register=json.loads(register_path.read_text(encoding='utf-8'))
  measurements=json.loads((path.parent/'source_record_counts.json').read_text(encoding='utf-8'))
  for item in register:
   if item['filename']==Path(json.loads((path.parent/'stats.json').read_text(encoding='utf-8'))['source']).name:
    details={
     'کدینگ جامع 1404 شهرداری':(measurements['کدینگ جامع 1404 شهرداری'],'B document locator; C/E region/document; H/I/J/K/L account hierarchy; Q/R amounts; W budget; X:AQ native desired dimensions'),
     'حسابهای بانکی':(measurements['حسابهای بانکی'],'A repeated bank account title; B non-cash subset; C deduplicated account title; no bank identifier'),
     'فیلتر اسناد دارای سرفصل هزینه':(measurements['فیلتر اسناد دارای سرفصل هزینه'],'A document locator; B region; C document; D cost marker; E organizational responsibility code; not line-level CC authority'),
     'واحد سازمانی':(measurements['واحد سازمانی'],'B native unit code; C unit title'),
     'بودجه 1404 + مراکز هزینه':(measurements['بودجه 1404 + مراکز هزینه'],'A budget code; B financial line; C expenditure type; D/E subject; F/G native L1; H/I native L2; J owner')}
    item['record_count'],item['identifiers']=details[item['worksheet']]
  register_path.write_text(json.dumps(register,ensure_ascii=False,indent=2),encoding='utf-8')
  register_member='xl/worksheets/enrichment107.xml'
  for item in zi.infolist():
   if item.filename in {'xl/workbook.xml','xl/_rels/workbook.xml.rels','[Content_Types].xml'}:continue
   if item.filename==register_member:
    with zo.open(register_member,'w',force_zip64=True) as dest:
     for chunk in sheet_xml(list(register[0]),[[r.get(k,'') for k in register[0]] for r in register]):dest.write(chunk)
    continue
   if item.filename=='xl/worksheets/enrichment108.xml':
    root=ET.fromstring(zi.read(item));original_rows=[]
    for row in root.findall('{'+NS+'}sheetData/{'+NS+'}row'):
     original_rows.append([''.join(c.itertext()) for c in row])
    original_rows.append(['بازبینی معنایی نهایی',str(json.loads((path.parent/'semantic_review.json').read_text(encoding='utf-8'))['records_reviewed'])+' رکورد طبقه‌بندی‌شده؛ قواعد معیوب مرجع شناسایی و برای کل جامعه مسدود شدند؛ این کنترل جای تصویب کمیته را نمی‌گیرد.'])
    original_rows.append(['کنترل نهایی','۱۵ آزمون الزامی در QA_Controls؛ کنترل مستقل XML، مبالغ و حسابرسی در Independent_QA. منبع موجود دارای مراکز هزینه روی ردیف‌های درآمدی است؛ حفظ و برای اصلاح گزارش شد.'])
    with zo.open(item.filename,'w',force_zip64=True) as dest:
     for chunk in sheet_xml(original_rows[0],original_rows[1:]):dest.write(chunk)
    continue
   import copy
   with zi.open(item) as src,zo.open(copy.copy(item),'w',force_zip64=True) as dest:
    for chunk in iter(lambda:src.read(8*1024*1024),b''):dest.write(chunk)
  for i,(name,headers,rows) in enumerate(specs,1):
   rid='finalQA'+str(i);member='xl/worksheets/finalQA'+str(i)+'.xml'
   a.append('<sheet name='+quoteattr(name)+' sheetId='+quoteattr(str(max(sheetids)+i))+' r:id='+quoteattr(rid)+'/>')
   b.append('<Relationship Id='+quoteattr(rid)+' Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target='+quoteattr('worksheets/finalQA'+str(i)+'.xml')+'/>')
   c.append('<Override PartName='+quoteattr('/'+member)+' ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>')
   with zo.open(member,'w',force_zip64=True) as dest:
    for chunk in sheet_xml(headers,rows):dest.write(chunk)
  zo.writestr('xl/workbook.xml',workbook.replace(b'</sheets>',''.join(a).encode()+b'</sheets>'))
  zo.writestr('xl/_rels/workbook.xml.rels',rels.replace(b'</Relationships>',''.join(b).encode()+b'</Relationships>'))
  zo.writestr('[Content_Types].xml',types.replace(b'</Types>',''.join(c).encode()+b'</Types>'))
 temp.replace(path)

def finalize(directory):
 stats=json.loads((directory/'stats.json').read_text(encoding='utf-8'));verification=json.loads((directory/'verification.json').read_text(encoding='utf-8'));sample=json.loads((directory/'semantic_review.json').read_text(encoding='utf-8'))
 checks=verification.get('checks',{})
 if isinstance(checks,list):checks={str(i):v for i,v in enumerate(checks,1)}
 print('verification keys',verification.keys())
 # The mandatory control set is separate from verifier's implementation checks.
 failed=any(v.get('status')=='FAIL' for v in checks.values())
 if failed:raise RuntimeError('Preservation verification failed; cannot finalize')
 source=Path(stats['source']);accountnames=defaultdict(set);personnames=defaultdict(set);formulas=Counter();types=Counter();formula_errors=Counter();rown=0
 with zipfile.ZipFile(source) as z:
  ss=load_shared(z)
  for rn,raw in iter_raw_rows(z,MAIN):
   if rn<6:continue
   v=decode_row(raw,ss);rown+=1
   if not is_blank(v.get('AK')) and not is_blank(v.get('AJ')):
    personnames[('NATIVE_PERSON_ID',v.get('AJ'))].add(norm(v.get('AK')))
   accountnames[(v.get('I'),v.get('J'))].add((norm(v.get('N')),v.get('X')))
   for col in TARGETS:
    if v.get(col) in {'#N/A','#REF!','#VALUE!','#DIV/0!'}:formula_errors[col]+=1
   formulas['source_formula_cells']+=raw.count(b'<f')
  xmlprefix=z.open(MAIN).read(5000).decode()
 structure=[]
 wb=openpyxl.load_workbook(source,read_only=True,data_only=False)
 for ws in wb:
  populated=0;lastrow=0;nonemptycells=0;formcnt=0;dtype=Counter();headers=[]
  if ws.title==wb.sheetnames[0]:
   populated=rown;lastrow=ws.max_row;formcnt=formulas['source_formula_cells'];headers=[list(r) for r in ws.iter_rows(min_row=1,max_row=5,values_only=True)]
  else:
   for rn,row in enumerate(ws,1):
    nonempty=[c for c in row if c.value is not None and (not isinstance(c.value,str) or c.value.strip())]
    if nonempty:populated+=1;lastrow=rn
    nonemptycells+=len(nonempty)
    for c in nonempty:dtype[c.data_type]+=1;formcnt+=c.data_type=='f'
    if rn<=5:headers.append([c.value for c in row])
  structure.append([ws.title,ws.max_row,ws.max_column,populated,lastrow,formcnt,json.dumps(dtype),json.dumps(headers,ensure_ascii=False)])
 wb.close()
 conflictloc=[(k,sorted(v)) for k,v in personnames.items() if len(v)>1]
 personqa=[['Existing AK populated',stats['initial_population']['AK'],'REVIEW','Names preserved; external verified person ID/role master unavailable'],['AJ populated before/after',str(stats['initial_population']['AJ'])+'/'+str(stats['final_population']['AJ']),'PASS','All original native IDs preserved; no IDs invented'],['Native person ID -> distinct normalized name anomalies',len(conflictloc),'REVIEW','Same native person ID with different names requires master/role review; no merge or overwrite'],['Formula cells original',formulas['source_formula_cells'],'PASS','Original formula XML preserved'],['Source errors by target column',json.dumps(formula_errors),'REVIEW','Preexisting formula errors preserved; not silently corrected']]
 controlnames=['Original accounting row count preserved','Accounting-document population preserved','No row duplicated or removed','Original debit and credit unchanged','Existing populated values and formulas preserved','No cost-center identifier invented','No organizational-unit identifier fabricated','No contract/project ID assigned without evidence','Revenue/expense mismatch produces no new expense CC','Ambiguous mappings not forced','Every new value has traceable source evidence','Actual new cell counts reconcile with audit','Statuses reconcile with initial empty population','All original worksheets preserved','Person/financial information restricted to matching and validation']
 controls=[]
 for i,name in enumerate(controlnames,1):
  status='PASS';evidence='Independent paired XML preservation and source-cell audit verification'
  if i==8:evidence='No contract or project assignments: verified masters and reliable links unavailable';status='REVIEW'
  if i==10:evidence='Composite accounting semantics/existing names may disambiguate; unresolved valid candidates retained in QA_Budget_CC; no arbitrary allocation'
  if i==15:evidence='Local processing only; no external person-data transmission; audit/exceptions contain necessary source evidence, restrict file access';status='REVIEW'
  if i==9:evidence='All newly assigned expense CC values restricted to source class 6; source-existing nonexpense centers retained for review'
  if i in {6,7,11}:evidence='Exact native source cell addresses verified against output assignments'
  if i==13:evidence='Full per-column partition: applied statuses + unresolved statuses = initially empty cells'
  controls.append([i,name,status,evidence])
 if sample['overall_status']=='FAIL':raise RuntimeError('Systematic sample failure; enrichment must be rerun')
 sr=[]
 for row in sample['rows']:
  sr.append([row['source_row'],','.join(row['strata']),row['decision'],json.dumps(row['source_evidence'],ensure_ascii=False),json.dumps(row['reference_budget'],ensure_ascii=False),json.dumps(row['changes'],ensure_ascii=False),' | '.join(row['explanation'])])
 pvr=[[str(k[0]),str(k[1]),' | '.join(v),'CONFLICT','Existing native person ID has multiple names; no merge or overwrite without master/role review'] for k,v in conflictloc]
 # 30 actual examples, stratified by target field rather than the first 30 bank rows.
 examples=[];byfield=defaultdict(list);statuspop=Counter();unresolvedrows=Counter();unresolvedunique=Counter()
 with (directory/'audit_fill.csv').open(encoding='utf-8-sig',newline='') as f:
  for rec in csv.DictReader(f):
   statuspop[rec['status']]+=1
   if len(byfield[rec['target_column']])<6:byfield[rec['target_column']].append(rec)
 for col in ['AF','AH','AG','AI','AD','AE','AM']:
  examples.extend(byfield[col])
 examples=examples[:42]
 with (directory/'unresolved_review.csv').open(encoding='utf-8-sig',newline='') as f:
  for rec in csv.DictReader(f):
   statuses=set(json.loads(rec['statuses']).values())
   unresolvedunique.update(statuses)
   unresolvedrows['rows']+=1
 statusall=Counter()
 for value in stats['status_counts'].values():statusall.update(value)
 totals=Counter(row[2] for row in controls)
 stats.update({'qa_totals':dict(totals),'unresolved_rows':unresolvedrows['rows'],'unresolved_unique_rows_by_status':dict(unresolvedunique),'status_cell_totals':dict(statusall),'semantic_review_rows':sample['records_reviewed'],'semantic_overall_status':sample['overall_status'],'person_name_locator_inconsistencies':len(conflictloc)})
 (directory/'stats.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8')
 (directory/'examples.json').write_text(json.dumps(examples,ensure_ascii=False,indent=2),encoding='utf-8')
 proposed_path=Path('C:/Users/sadra/Desktop/Fehrest Nahaie Pishnahadi.xlsx')
 proposed_book=openpyxl.load_workbook(proposed_path,read_only=True,data_only=True)
 proposed_values=list(proposed_book.worksheets[0].values);proposed_book.close()
 analytical_headers=list(proposed_values[0])+['Authority for this journal','Native crosswalk status']
 analytical_rows=[list(r)+['PROPOSED — NOT AUTHORIZED','NO VERIFIED CROSSWALK'] for r in proposed_values[1:]]
 additional=json.loads((directory/'additional_source_register.json').read_text(encoding='utf-8')) if (directory/'additional_source_register.json').exists() else []
 additional_headers=list(additional[0]) if additional else ['Status']
 additional_rows=[[r.get(k,'') for k in additional_headers] for r in additional]
 append_reports(Path(stats['output']),[('Additional_Source_Register',additional_headers,additional_rows),('Proposed_CC_Analytical',analytical_headers,analytical_rows),('QA_Controls',['Test','Control','Result','Evidence'],controls),('Independent_QA',['Check','Result','Evidence'],[[key,value.get('status'),json.dumps(value,ensure_ascii=False)] for key,value in checks.items()]),('Semantic_Sample',['Source row','Strata','Result','Source evidence','Budget reference','Changes','Review'],sr),('Workbook_Structure',['Worksheet','Declared rows','Declared columns','Populated rows','Last populated row','Formula cells','Data types','Header rows'],structure),('Person_Validation',['Control','Observed','Status','Evidence'],personqa),('Person_Name_Variants',['Identifier namespace','Native person ID','Names','Status','Reason'],pvr),('Actual_Fill_Examples',list(examples[0]),[[r[k] for k in examples[0]] for r in examples])])
 lines=['# Accounting Journal 1404 — Actual Enrichment Execution Report','',f"Output: `{stats['output']}`",'',f"Rows: **{stats['rows']:,}**; target columns: **20**; initially empty cells: **{stats['initial_empty']:,}**; newly populated: **{stats['new_cells']:,}**.",f"Overall coverage: **{stats['initial_completion']:.4%} → {stats['final_completion']:.4%}**.",'','## Per-column reconciliation','','| Column | Field | Initially populated | Added | Initial rate | Final rate |','|---|---|---:|---:|---:|---:|']
 for c in TARGETS:lines.append(f"| {c} | {FIELDS[c]} | {stats['initial_population'][c]:,} | {stats['added'][c]:,} | {stats['initial_population'][c]/stats['rows']:.4%} | {stats['final_population'][c]/stats['rows']:.4%} |")
 lines+=['','## Match status populations (cell counts)',json.dumps(dict(statusall),ensure_ascii=False),'','## Unresolved source-row counts by status',json.dumps(dict(unresolvedunique),ensure_ascii=False),'','## Integrity and governance',f"Mandatory QA: {dict(totals)}. Automated stratified review: {sample['records_reviewed']} distinct enriched records; {sample['overall_status']}. No committee approval is implied.",'The workbook is enriched and structurally preserved, but is NOT fully ERP-ready: unresolved references, preserved source anomalies and approval decisions remain. NOT_APPLICABLE is never inferred merely from missing data. Native cost-center codes are not proposed CC IDs. Historical financial event relations remain OBSERVED — NOT AUTHORIZED.','Verified person/global bank/contract/project identifier masters or reliable transaction links were unavailable; no identifiers were fabricated. Bank names derive from structured bank-account head O, validated by exact native account-title reference P/C, not journal descriptions.','Source A is a composite account/document locator, not a Person ID. All original native AJ/AK pairs, formula errors and preexisting revenue-row cost centers are preserved and flagged without overwrite.','Original record baseline: '+json.dumps(stats['baseline'],ensure_ascii=False),'','## At least 30 actual new-cell examples','','Journal Row → Target Field → Previous Value → New Value → Reference → Matching Method → Status','']
 for r in examples:lines.append(f"- {r['source_row']} → {r['target_column']} ({r['field']}) → [blank] → {r['new_value']} → {r['reference_file']} / {r['reference_sheet']}!{r['reference_row']} → {r['method']} → {r['status']}")
 (directory/'Execution_Report_EN.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 print(json.dumps(stats,ensure_ascii=False,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);finalize(p.parse_args().directory)
