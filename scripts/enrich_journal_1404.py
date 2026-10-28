"""Deterministic, blank-only native journal enrichment and OOXML-preserving delivery."""
from __future__ import annotations
import argparse,csv,hashlib,json,re,zipfile,xml.etree.ElementTree as ET
from collections import Counter,defaultdict
from pathlib import Path
from xml.sax.saxutils import escape,quoteattr
import openpyxl

NS='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
ROW=re.compile(rb'<row\b[^>]*>.*?</row>',re.S)
CELL=re.compile(rb'<c\b[^>]*?(?:/>|>.*?</c>)',re.S)
ADDR=re.compile(rb'\br="([A-Z]+)(\d+)"')
VALUE=re.compile(rb'<v>(.*?)</v>',re.S)
TARGETS=['X','Y','Z','AA','AB','AC','AD','AE','AF','AG','AH','AI','AJ','AK','AL','AM','AN','AO','AP','AQ']
FIELDS=dict(zip(TARGETS,['کد طبقه','عنوان طبقه','کد کل','عنوان کل','کد معین','عنوان معین','کد واحد سازمانی','عنوان واحد سازمانی','کد مرکز هزینه سطح اول','عنوان مرکز هزینه سطح اول','کد مرکز هزینه سطح دوم','عنوان مرکز هزینه سطح دوم','شناسه شخص','نام شخص','کد بانک','نام بانک','شناسه قرارداد','عنوان قرارداد','شناسه پروژه','عنوان پروژه']))
MAIN='xl/worksheets/sheet1.xml'
BUDGET='بودجه 1404 + مراکز هزینه'
UNIT='واحد سازمانی'
BANK='حسابهای بانکی'
AUDIT=['source_row','target_column','field','old_value','new_value','reference_file','reference_sheet','reference_row','match_key','method','status','confidence','reason']
DIGITS=str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩','01234567890123456789')

def norm(v):
 return ' '.join(str(v or '').translate(DIGITS).replace('ي','ی').replace('ك','ک').replace('\u200c',' ').replace('\xa0',' ').split())
def is_blank(v):
 return v is None or (isinstance(v,str) and not v.strip())
def load_shared(z):
 root=ET.fromstring(z.read('xl/sharedStrings.xml'))
 return [''.join(e.itertext()) for e in root]
def iter_raw_rows(z,path):
 with z.open(path) as f:
  buf=b''
  while chunk:=f.read(4*1024*1024):
   buf+=chunk;end=0
   for m in ROW.finditer(buf):
    raw=m.group();yield int(re.search(rb'<row\b[^>]*\br="(\d+)"',raw)[1]),raw;end=m.end()
   buf=buf[end:]
  for m in ROW.finditer(buf):
   raw=m.group();yield int(re.search(rb'<row\b[^>]*\br="(\d+)"',raw)[1]),raw

def decode_row(raw,shared):
 out={}
 for m in CELL.finditer(raw):
  cell=m.group();a=ADDR.search(cell)
  if not a:continue
  v=VALUE.search(cell);col=a[1].decode()
  if b't="s"' in cell:out[col]=shared[int(v[1])] if v else None
  elif b't="inlineStr"' in cell:
   e=ET.fromstring(cell);out[col]=''.join(t.text or '' for t in e.iter() if t.tag.split('}')[-1]=='t')
  elif v:out[col]=v[1].decode()
  else:out[col]=None
 return out

def colnum(col):
 n=0
 for c in col:n=n*26+ord(c)-64
 return n

def inline_cell(address,value,style='7'):
 # Always text for identifiers: retain reference representation and leading zeros.
 return ('<c r='+quoteattr(address)+' s='+quoteattr(style)+' t="inlineStr"><is><t xml:space="preserve">'+escape(str(value))+'</t></is></c>').encode('utf-8')

def mutate_row(raw,rn,changes):
 bycol={c['target_column']:c for c in changes};matches=list(CELL.finditer(raw));parts=[];pos=0;remaining=dict(bycol)
 for m in matches:
  old=m.group();col=ADDR.search(old)[1].decode();parts.append(raw[pos:m.start()])
  # Insert absent cells in correct column order without touching existing XML.
  for newcol in sorted([k for k in remaining if colnum(k)<colnum(col)],key=colnum):
   parts.append(inline_cell(newcol+str(rn),remaining.pop(newcol)['new_value']))
  if col in remaining:
   style=re.search(rb'\bs="(\d+)"',old)
   parts.append(inline_cell(col+str(rn),remaining.pop(col)['new_value'],style[1].decode() if style else '7'))
  else:parts.append(old)
  pos=m.end()
 tail=raw[pos:];close=tail.rfind(b'</row>')
 parts.append(tail[:close])
 for col in sorted(remaining,key=colnum):parts.append(inline_cell(col+str(rn),remaining[col]['new_value']))
 parts.append(tail[close:]);return b''.join(parts)

def csvwriter(path,headers):
 f=path.open('w',encoding='utf-8-sig',newline='');w=csv.DictWriter(f,fieldnames=headers);w.writeheader();return f,w

def reference_register(source,wb,extras):
 rows=[]
 for s in wb:
  count=sum(any(not is_blank(x) for x in row) for row in s.values) if s.title not in (wb.sheetnames[0],BANK) else (s.max_row-5 if s.title==wb.sheetnames[0] else s.max_row-1)
  rows.append({'filename':source.name,'version':'1404 source, unversioned','worksheet':s.title,'record_count':count,'identifiers':'Original columns; source XML row is unique lineage locator','purpose':'Source journal' if s.title==wb.sheetnames[0] else 'Native internal reference','authority_status':'Native workbook reference; no separate committee approval claimed','methodology':'Exact identifier/name or validated native composite; never document-only CC join','path':str(source)})
 for item in extras:
  p=Path(item['path'])
  if not p.exists():
   rows.append({'filename':p.name,'version':item.get('version','unknown'),'worksheet':'MISSING','record_count':0,'identifiers':'','purpose':item['purpose'],'authority_status':'UNAVAILABLE','methodology':'No automatic assignment','path':str(p)});continue
  if p.suffix.lower()!='.xlsx':continue
  ew=openpyxl.load_workbook(p,read_only=True,data_only=True)
  for s in ew:
   # Actual populated records, excluding header; include diagnostics without treating as master.
   n=0;header=None
   for row in s.values:
    if any(not is_blank(v) for v in row):
     if header is None:header=row
     else:n+=1
   rows.append({'filename':p.name,'version':item.get('version','unversioned'),'worksheet':s.title,'record_count':n,'identifiers':' | '.join(str(x) for x in (header or ()) if x is not None)[:30000],'purpose':item['purpose'],'authority_status':item['authority'],'methodology':'Diagnostic / supplemental analytical evidence only; no assignment authority','path':str(p)})
  ew.close()
 return rows

def semantic_gate(v,br):
 if v.get('X')!='6':return 'CONFLICT','Non-expense accounting class: expense CC mapping blocked'
 i=v.get('I');typ=norm(br[2]);desc=norm(br[1]);subject=norm(br[3]);sub=norm(br[4]);name=norm(br[8]);l1=norm(br[6])
 if 'تصمیم کارشناسی' in typ:return 'PROPOSED_MATCH','Native reference itself requires expert decision'
 if ('جبران خدمات' in name or 'منابع انسانی' in l1) and i in {'112','114','115'}:return 'CONFLICT','Contracted/transfer service is not direct municipal employee payroll'
 if ('احداث' in name or 'توسعه و تکمیل ساختمان' in name) and any(t in desc for t in ['کرایه','اجاره','تخفیف','کمک به افراد','تجهیزات اداری']):return 'CONFLICT','Rental, relief or office equipment cannot authorize building construction'
 if 'مالی، خزانه' in name and not any(t in desc for t in ['مالی','بانک','خزانه','حسابداری','حسابرسی']):return 'PROPOSED_MATCH','Treasury center lacks finance-specific financial-line evidence'
 if 'تدارکات' in name and any(t in desc+subject for t in ['احداث','آبراهه','ترافیک','آبیاری','فضای سبز','تملک','فرهنگی']):return 'PROPOSED_MATCH','Specialized service/capital line mapped to generic procurement needs domain approval'
 if 'ورزش' in name and any(t in desc+sub for t in ['موزه','خانه های علمی','کتابخانه']):return 'CONFLICT','Cultural/scientific facility is not a verified sporting facility'
 if i in {'111','112','114','115','116','117','132'} and 'سرمایه' in typ:return 'CONFLICT','Operating/transfer account versus capital budget line'
 if i in {'121','122','123','126','127'} and typ=='جاری':return 'CONFLICT','Capital/land account versus current budget line'
 if i=='111' and not ('حقوق' in subject or 'حقوق' in desc or 'مزایا' in desc):return 'CONFLICT','Payroll account versus non-payroll budget semantics'
 if i=='116' and subject not in {'رفاهیات','دیون'}:return 'CONFLICT','Social welfare account versus unrelated budget semantics'
 if i in {'114','115'} and not any(t in desc+subject for t in ['کمک','یارانه','حمایت','پرداخت']):return 'CONFLICT','Transfer account lacks transfer-compatible budget evidence'
 if any(t in desc for t in ['کمک به سازمان','کمک به شرکت']) and ('جبران خدمات' in name or 'منابع انسانی' in l1):return 'CONFLICT','Affiliated-organization support is not direct municipal payroll'
 if any(t in desc for t in ['کمک به سازمان','کمک به شرکت']) and any(t in name for t in ['احداث','نگهداری','پایانه']):return 'PROPOSED_MATCH','Affiliated support cannot authorize direct service execution center'
 if 'تملک' in desc and 'تدارکات' in name:return 'CONFLICT','Land acquisition assigned to general procurement'
 if subject=='سایر' and ('تدارکات' in name or 'املاک' in name):return 'PROPOSED_MATCH','Generic fallback classification lacks validated service domain'
 if i=='131' and subject!='دیون':return 'CONFLICT','Prior-year commitments require a validated debt budget line'
 if i=='132' and not any(t in desc for t in ['تسهیلات','وام','سود','بازپرداخت']):return 'CONFLICT','Loan repayment account versus incompatible budget semantics'
 n=norm(v.get('N'))
 for token in ['بانک','مالیات']:
  if token in n and token not in desc+subject+sub:return 'CONFLICT','Account '+token+' context conflicts with reference financial line'
 return None,'Accounting class, financial-line type, domain and existing dimensions validated'

def enrich(source,outdir,extras):
 outdir.mkdir(parents=True,exist_ok=True)
 wb=openpyxl.load_workbook(source,read_only=True,data_only=True)
 budgets=defaultdict(list);name1=defaultdict(list);name2=defaultdict(list);unitnames=defaultdict(list);unitcodes=defaultdict(list)
 for rn,row in enumerate(wb[BUDGET].values,1):
  if rn<3 or is_blank(row[0]):continue
  br=tuple('' if x is None else str(x) for x in row)
  budgets[norm(br[0])].append((rn,br));name1[norm(br[6])].append((rn,br));name2[norm(br[8])].append((rn,br))
 for rn,row in enumerate(wb[UNIT].values,1):
  if rn<3 or is_blank(row[1]):continue
  code=str(row[1]);title=str(row[2]);unitnames[norm(title)].append((rn,code,title));unitcodes[norm(code)].append((rn,code,title))
 banktitles={}
 for rn,row in enumerate(wb[BANK].values,1):
  if rn>1 and len(row)>2 and not is_blank(row[2]):banktitles.setdefault(norm(row[2]),(rn,str(row[2])))
 register=reference_register(source,wb,extras)
 wb.close()
 af,aw=csvwriter(outdir/'audit_fill.csv',AUDIT)
 uf,uw=csvwriter(outdir/'unresolved_review.csv',['source_row','source_document_id','region','document_no','account','account_name','classification','budget_code','existing_unit','existing_cc1','existing_cc2','person_name','pending_fields','statuses','reason','candidate_reference_rows','required_decision'])
 cf,cw=csvwriter(outdir/'existing_conflicts.csv',['source_row','fields','status','reason','original_values'])
 bf,bw=csvwriter(outdir/'qa_budget_cc.csv',['kind','budget_code','source_rows','distinct_cc','journal_row','reason','candidate_assignments'])
 for code,rs in budgets.items():
  ccset={tuple(norm(x) for x in r[5:9]) for _,r in rs}
  exact=Counter(tuple(r) for _,r in rs)
  if len(ccset)>1 or len(rs)>1:
   bw.writerow({'kind':'AMBIGUOUS' if len(ccset)>1 else 'DUPLICATE_MAPPING','budget_code':code,'source_rows':','.join(str(n) for n,_ in rs),'distinct_cc':len(ccset),'reason':'Different mappings retained' if len(ccset)>1 else 'Repeated same CC association; financial descriptions retained','candidate_assignments':json.dumps([{'row':n,'description':r[1],'type':r[2],'cc':r[5:9]} for n,r in rs],ensure_ascii=False)})
 counters={c:Counter() for c in TARGETS};initial=Counter({c:0 for c in TARGETS});added=Counter({c:0 for c in TARGETS});base=Counter();classes=Counter();existing_bad=Counter();sample_buckets=defaultdict(list);examples=[];docset=set();person_variants=defaultdict(set)
 # Existing person names have no real Person ID in this journal: A is an account/document composite, never AJ.
 with zipfile.ZipFile(source) as zi:
  shared=load_shared(zi)
  output=outdir/'Accounting_Journal_1404_Desired_State_Enriched_v1.xlsx'
  if output.exists():raise FileExistsError('Do not overwrite versioned deliverable: '+str(output))
  patched=outdir/'journal_patched.xml'
  with patched.open('wb') as po,zi.open(MAIN) as stream:
   buf=b'';processed=0
   while chunk:=stream.read(4*1024*1024):
    buf+=chunk;end=0
    for m in ROW.finditer(buf):
     po.write(buf[end:m.start()]);raw=m.group();rn=int(re.search(rb'<row\b[^>]*\br="(\d+)"',raw)[1]);end=m.end()
     if rn<6:po.write(raw);continue
     v=decode_row(raw,shared);base['rows']+=1;classes[(v.get('X'),v.get('Y'))]+=1;docset.add((v.get('C'),v.get('E')))
     cellxml={ADDR.search(c.group())[1].decode():c.group() for c in CELL.finditer(raw)}
     pending=[c for c in TARGETS if is_blank(v.get(c)) and b'<f' not in cellxml.get(c,b'')]
     for c in TARGETS:initial[c]+=not is_blank(v.get(c)) or b'<f' in cellxml.get(c,b'')
     statuses={c:'NO_EVIDENCE' for c in pending};reasons={};changes=[]
     def apply(col,new,sheet,ref,key,method,status,reason):
      if col not in pending or is_blank(new):return
      rec=dict(zip(AUDIT,[rn,col,FIELDS[col],'',str(new),source.name,sheet,ref,key,method,status,'VERIFIED_DETERMINISTIC',reason]))
      changes.append(rec);statuses[col]=status;added[col]+=1;aw.writerow(rec)
      if len(examples)<50:examples.append(rec)
     def conflict(fields,reason):
      existing_bad[reason]+=1;cw.writerow({'source_row':rn,'fields':','.join(fields),'status':'CONFLICT','reason':reason,'original_values':json.dumps({c:v.get(c) for c in fields},ensure_ascii=False)})
     # Unit code/name pair: native master only, no service-owner-to-unit substitution.
     un=unitnames.get(norm(v.get('AE')),[]);uc=unitcodes.get(norm(v.get('AD')),[])
     if not is_blank(v.get('AE')):
      if len({x[1] for x in un})==1:
       ur,code,title=un[0]
       if not is_blank(v.get('AD')) and norm(v.get('AD'))!=norm(code):conflict(['AD','AE'],'Existing unit code/name mismatch')
       else:apply('AD',code,UNIT,'B'+str(ur),'unit_name='+norm(v.get('AE')),'native_unit_name_to_code','EXACT_MATCH','Unique normalized native unit name to existing native code')
      else:
       if 'AD' in pending:statuses['AD']='AMBIGUOUS' if un else 'CONFLICT'
       if not un:conflict(['AE'],'Existing unit title absent from native master (numeric titles are not units)')
     elif len(uc)==1:
      ur,code,title=uc[0];apply('AE',title,UNIT,'C'+str(ur),'unit_code='+norm(v.get('AD')),'native_unit_identifier_lookup','EXACT_MATCH','Existing native code uniquely identifies unit title')
     elif not is_blank(v.get('AD')):statuses['AE']='CONFLICT' if 'AE' in pending else statuses.get('AE','CONFLICT')
     # Independent baseline, using source-defined class 6 only.
     bk=norm(v.get('W'));rs=budgets.get(bk,[]);ccset={tuple(norm(x) for x in r[5:9]) for _,r in rs}
     if v.get('X')=='6':
      base['expense']+=1
      base['mapped' if rs else ('unusable' if bk in ('','NULL','0') else 'unmapped')]+=1
      if rs:base['unique' if len(ccset)==1 else 'ambiguous']+=1
     if rs and v.get('X')!='6':
      base['nonexpense_budget_collision']+=1
      if v.get('X')=='4':base['revenue_budget_collision']+=1
      for c in ['AF','AG','AH','AI']:
       if c in pending:statuses[c]='CONFLICT'
      bw.writerow({'kind':'NONEXPENSE_BUDGET_COLLISION','budget_code':bk,'source_rows':','.join(str(n) for n,_ in rs),'distinct_cc':len(ccset),'journal_row':rn,'reason':'Budget-only join blocked; accounting class='+str(v.get('X'))})
     chosen=None;gate_reason='';method='native_budget_account_composite';matchstatus='VALIDATED_COMPOSITE'
     if v.get('X')=='6':
      compatible=[];rejections=[]
      for brn,br in rs:
       status,why=semantic_gate(v,br)
       if status is None:compatible.append((brn,br))
       else:rejections.append((status,why))
      # Stronger existing names can narrow multi-CC candidates; never overwrite them.
      narrowed=[(n,r) for n,r in compatible if (is_blank(v.get('AG')) or norm(v['AG'])==norm(r[6])) and (is_blank(v.get('AI')) or norm(v['AI'])==norm(r[8]))]
      distinct={tuple(norm(x) for x in r[5:9]) for _,r in narrowed}
      if len(distinct)==1:
       chosen=narrowed[0];gate_reason='Accounting class 6 + account '+str(v.get('I'))+' + native budget '+bk+'; '+semantic_gate(v,chosen[1])[1]
      elif rs:
       status='AMBIGUOUS' if len(distinct)>1 else ('CONFLICT' if compatible else ('CONFLICT' if any(x[0]=='CONFLICT' for x in rejections) else 'PROPOSED_MATCH'))
       gate_reason='Multiple compatible cost centers' if len(distinct)>1 else ('Existing CC name conflicts with native budget candidates' if compatible else '; '.join(sorted({x[1] for x in rejections})))
       for c in ['AF','AG','AH','AI']:
        if c in pending:statuses[c]=status
       bw.writerow({'kind':status,'budget_code':bk,'source_rows':','.join(str(n) for n,_ in rs),'distinct_cc':len(distinct),'journal_row':rn,'reason':gate_reason,'candidate_assignments':json.dumps([{'row':n,'cc':r[5:9]} for n,r in rs],ensure_ascii=False)})
      # Recover codes from existing native CC names if no budget link; not an inferred service assignment.
      elif not is_blank(v.get('AG')) or not is_blank(v.get('AI')):
       candidates=name2.get(norm(v.get('AI')),[]) if not is_blank(v.get('AI')) else name1.get(norm(v.get('AG')),[])
       candidates=[(n,r) for n,r in candidates if (is_blank(v.get('AG')) or norm(v['AG'])==norm(r[6]))]
       for col,idx,rc,namecol in [('AF',5,'F','AG'),('AH',7,'H','AI')]:
        pool=(name1 if col=='AF' else name2).get(norm(v.get(namecol)),[])
        codes={norm(r[idx]) for _,r in pool}
        if not is_blank(v.get(namecol)) and len(codes)==1:
         cn,cr=pool[0];method='native_existing_name_to_code';matchstatus='EXACT_MATCH'
         apply(col,cr[idx],BUDGET,rc+str(cn),'class=6;existing_name='+norm(v.get(namecol)),method,matchstatus,'Recover native code for preserved existing name; not a new financial-line assignment')
        elif col in pending and not is_blank(v.get(namecol)):
         statuses[col]='AMBIGUOUS' if pool else 'CONFLICT'
      if chosen:
       cn,cr=chosen
       for col,idx,rc in [('AF',5,'F'),('AG',6,'G'),('AH',7,'H'),('AI',8,'I')]:
        apply(col,cr[idx],BUDGET,rc+str(cn),'fiscal=1404;class=6;account='+str(v.get('I'))+';budget='+bk+';existing_cc1='+norm(v.get('AG'))+';existing_cc2='+norm(v.get('AI')),method,matchstatus,gate_reason)
     # Validate preexisting native names without coercing numeric contamination.
     for col,index in [('AG',name1),('AI',name2)]:
      if not is_blank(v.get(col)) and norm(v[col]) not in index:conflict([col],'Existing cost-center title absent from native master')
     if v.get('X')!='6' and (not is_blank(v.get('AG')) or not is_blank(v.get('AI'))):conflict(['AG','AI'],'Preexisting expense center on non-expense row requires review; preserved')
     # Bank name from structured account head O, independently validated account P in native bank sheet C.
     bankref=banktitles.get(norm(v.get('P')))
     if v.get('I')=='611' and v.get('J') not in {'020','030','040'} and bankref and not is_blank(v.get('O')):
      brn,_=bankref
      apply('AM',v['O'], 'کدینگ جامع 1404 شهرداری','O'+str(rn),'native_account='+str(v.get('H'))+';bank_account='+norm(v.get('P')),'native_bank_account_title','VALIDATED_COMPOSITE','Structured bank account head O; verified account title P matches native bank reference '+BANK+'!C'+str(brn)+'; no fabricated bank ID')
     # Project applicability requires authority: absence cannot prove NOT_APPLICABLE.
     for c in ['AJ','AL','AN','AO','AP','AQ']:
      if c in pending:reasons[c]='Verified dimension identifier master/link unavailable; descriptions and source composite A are not IDs'
     for c,st in statuses.items():counters[c][st]+=1
     unresolved={c:st for c,st in statuses.items() if st not in {'EXACT_MATCH','VALIDATED_COMPOSITE'}}
     if unresolved:
      uw.writerow({'source_row':rn,'source_document_id':v.get('B'),'region':v.get('C'),'document_no':v.get('E'),'account':v.get('H'),'account_name':v.get('N'),'classification':v.get('Y'),'budget_code':v.get('W'),'existing_unit':v.get('AE'),'existing_cc1':v.get('AG'),'existing_cc2':v.get('AI'),'person_name':v.get('AK'),'pending_fields':','.join(unresolved),'statuses':json.dumps(unresolved,ensure_ascii=False),'reason':gate_reason or 'No authoritative direct evidence for remaining dimensions','candidate_reference_rows':','.join(str(n) for n,_ in rs),'required_decision':'Provide verified person/bank/contract/project masters and role links; approve ambiguous financial-line/domain mapping; numeric existing titles need source correction'})
     if changes:
      cr=chosen[1] if chosen else None
      entry={'source_row':rn,'source_values':{k:v.get(k) for k in ['B','C','E','H','I','J','N','O','P','T','W','X','Y','AD','AE','AF','AG','AH','AI','AK']},'changes':changes,'reference_budget':dict(zip(['budget_code','description','expense_type','subject','subsubject','l1_code','l1_name','l2_code','l2_name','owner'],cr)) if cr else None}
      text=norm(' '.join(str(v.get(k) or '') for k in ['N','O','P','T'])+' '+' '.join(c['new_value'] for c in changes))
      strata={'payroll':['حقوق','کارکنان','دستمزد'],'urban_services':['نظافت','پسماند','فضای سبز'],'construction':['احداث','عمران','آسفالت'],'culture':['فرهنگ','ورزش'],'traffic':['ترافیک','حمل و نقل'],'grants':['کمک','یارانه'],'administration':['اداری','پشتیبانی','مدیریت'],'project':['پروژه','طرح'],'contract':['قرارداد','پیمان'],'revenue_boundary':['درآمد','عوارض']}
      keys=[key for key,terms in strata.items() if any(t in text for t in terms)]
      keys+=['method:'+c['method'] for c in changes]
      for key in set(keys):
       if len(sample_buckets[key])<18:sample_buckets[key].append(entry)
      po.write(mutate_row(raw,rn,changes))
     else:po.write(raw)
     processed+=1
     if processed%100000==0:print('Processed',processed,'added',sum(added.values()),flush=True)
    buf=buf[end:]
   po.write(buf)
  af.close();uf.close();cf.close();bf.close()
  unique_sample={e['source_row']:e for bucket in sample_buckets.values() for e in bucket}
  sample=list(unique_sample.values())
  stats={'rows':base['rows'],'target_columns':20,'initial_population':dict(initial),'added':dict(added),'final_population':{c:initial[c]+added[c] for c in TARGETS},'status_counts':{c:dict(counters[c]) for c in TARGETS},'baseline':dict(base),'classifications':[{'code':k[0],'name':k[1],'rows':n} for k,n in classes.items()],'unique_region_document_pairs':len(docset),'initial_empty':20*base['rows']-sum(initial.values()),'new_cells':sum(added.values()),'initial_completion':sum(initial.values())/(20*base['rows']),'final_completion':(sum(initial.values())+sum(added.values()))/(20*base['rows']),'existing_inconsistency_occurrences':sum(existing_bad.values()),'inconsistency_reasons':dict(existing_bad),'output':str(output.resolve()),'source':str(source),'missing_sources':['Verified Person Master','Verified global Bank ID master','Verified Contract Master and role links','Verified Project Master and applicability rules'],'governance':'Native source references support reconstruction within this workbook; no proposed CC or historical event rules authorized'}
  for filename,data in [('stats.json',stats),('semantic_sample.json',sample),('source_register.json',register),('examples.json',examples)]:
   (outdir/filename).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
  cross=[]
  for code,rs in budgets.items():
   for rn,br in rs:cross.append([code,br[5],br[6],br[7],br[8],'','','NO_EVIDENCE','No approved native-to-proposed CC crosswalk; no CC substitution',source.name,BUDGET,rn])
  report_specs=[]
  summary=[]
  for c in TARGETS:
   n=initial[c];cnt=counters[c]
   summary.append([c,FIELDS[c],n,base['rows']-n,cnt['EXACT_MATCH'],cnt['VALIDATED_COMPOSITE'],cnt['PROPOSED_MATCH'],cnt['AMBIGUOUS'],cnt['NO_EVIDENCE'],cnt['CONFLICT'],cnt['NOT_APPLICABLE'],base['rows']-n-added[c],n/base['rows'],(n+added[c])/base['rows']])
  report_specs.append(('QA_Fill_Summary',['Column','Field','Initially populated','Initially empty','Exact matches added','Composite matches added','Proposed matches','Ambiguous cases','No evidence','Conflict','Not applicable','Remaining empty','Initial completion rate','Final completion rate'],summary))
  report_specs.append(('Audit_Fill',AUDIT,outdir/'audit_fill.csv'))
  report_specs.append(('QA_Budget_CC',None,outdir/'qa_budget_cc.csv'))
  report_specs.append(('CC_Crosswalk',['Budget code','Native L1 code','Native L1 name','Native L2 code','Native L2 name','Proposed CC ID','Proposed title','Status','Governance','Source file','Source sheet','Source row'],cross))
  report_specs.append(('Unresolved_Review',None,outdir/'unresolved_review.csv'))
  report_specs.append(('Existing_Conflicts',None,outdir/'existing_conflicts.csv'))
  report_specs.append(('Source_Register',list(register[0]),[[r.get(k,'') for k in register[0]] for r in register]))
  executive=[['موضوع','نتیجه / تصمیم لازم'],['دامنه',str(base['rows'])+' ردیف و ۲۰ ستون؛ فقط سلول‌های خالی تکمیل شد.'],['تکمیل',str(sum(added.values()))+' سلول؛ پوشش از '+format(stats['initial_completion'],'.2%')+' به '+format(stats['final_completion'],'.2%')],['مراکز هزینه',str(sum(added[c] for c in ['AF','AG','AH','AI']))+' سلول؛ ماهیت حساب، نوع بودجه، دامنه و نام‌های موجود کنترل شد.'],['واحد سازمانی',str(added['AD'])+' کد و '+str(added['AE'])+' عنوان؛ فقط مرجع داخلی واحد سازمانی.'],['اشخاص','شناسه شخص ساخته نشد؛ ستون A کلید مرکب حساب/سند است و جایگزین شناسه شخص نیست. مرجع معتبر شناسه و نقش لازم است.'],['بانک',str(added['AM'])+' نام بانک از سرفصل ساختاری و حساب بانکی تأییدشده؛ کد جهانی بانک ساخته نشد.'],['قرارداد و پروژه','بدون مرجع شناسه و پیوند معتبر، تکمیل خودکار انجام نشد. نبود داده به معنای عدم کاربرد نیست.'],['مغایرت‌های موجود',str(sum(existing_bad.values()))+' رخداد مغایرت؛ همه مقادیر موجود و فرمول‌ها حفظ شدند.'],['تفکیک کدگذاری','کدهای بومی بودجه با CC پیشنهادی متفاوت‌اند. کراس‌واک مصوب یافت نشد؛ شناسه پیشنهادی به دفتر منتقل نشد.'],['حاکمیت','رویداد×مرکز هزینه تاریخی OBSERVED — NOT AUTHORIZED است؛ تصویب کاردینالیتی و قواعد با کمیته و آقای خداپرست.'],['کنترل مستقل','نتیجه کنترل پس از تولید در QA_Controls و verification.json درج می‌شود؛ سلامت مالی با آمادگی نهایی ERP یکسان نیست.'],['تصمیم لازم','تأیید خطوط مبهم/پیشنهادی، اصلاح عناوین عددی، تأمین داده مرجع اشخاص/بانک/قرارداد/پروژه و قواعد عدم کاربرد.']]
  report_specs.append(('Executive_Summary',executive[0],executive[1:]))
  report_specs.append(('Baseline_Metrics',['Metric','Actual'],list(base.items())))
  package_reports(zi,output,patched,report_specs)
  patched.unlink()
  print(json.dumps(stats,ensure_ascii=False,indent=2),flush=True)
 return output

def sheet_xml(headers,rows):
 yield ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="'+NS+'"><sheetViews><sheetView rightToLeft="1" workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><sheetData>').encode()
 from itertools import chain
 for rn,row in enumerate(chain([headers],rows),1):
  yield ('<row r="'+str(rn)+'">').encode()
  for ci,value in enumerate(row,1):
   if value is None:continue
   from openpyxl.utils import get_column_letter
   yield inline_cell(get_column_letter(ci)+str(rn),value,'17' if rn==1 else '7')
  yield b'</row>'
 yield b'</sheetData></worksheet>'

def package_reports(zi,output,patched,specs):
 # Copy ALL original members verbatim at payload level; append standalone report sheets.
 workbook=zi.read('xl/workbook.xml');rels=zi.read('xl/_rels/workbook.xml.rels');types=zi.read('[Content_Types].xml')
 maxsheet=max(int(s.get('sheetId')) for s in ET.fromstring(workbook).find('{'+NS+'}sheets'))
 ids={e.get('Id') for e in ET.fromstring(rels)}
 additions=[];reladds=[];typeadds=[]
 with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as zo:
  for item in zi.infolist():
   if item.filename in {'xl/workbook.xml','xl/_rels/workbook.xml.rels','[Content_Types].xml'}:continue
   import copy
   with zo.open(copy.copy(item),'w',force_zip64=True) as dest:
    if item.filename==MAIN:
     with patched.open('rb') as f:
      for chunk in iter(lambda:f.read(4*1024*1024),b''):dest.write(chunk)
    else:
     with zi.open(item) as f:
      for chunk in iter(lambda:f.read(4*1024*1024),b''):dest.write(chunk)
  report_no=100
  for name,headers,data in specs:
   infile=None
   if isinstance(data,Path):
    infile=data.open(encoding='utf-8-sig',newline='');reader=csv.reader(infile);headers=next(reader);data=reader
   report_no+=1;sheetid=maxsheet+report_no;rid='enrichment'+str(report_no);member='xl/worksheets/enrichment'+str(report_no)+'.xml'
   additions.append('<sheet name='+quoteattr(name)+' sheetId='+quoteattr(str(sheetid))+' r:id='+quoteattr(rid)+'/>')
   reladds.append('<Relationship Id='+quoteattr(rid)+' Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target='+quoteattr('worksheets/enrichment'+str(report_no)+'.xml')+'/>')
   typeadds.append('<Override PartName='+quoteattr('/'+member)+' ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>')
   with zo.open(member,'w',force_zip64=True) as stream:
    for chunk in sheet_xml(headers,data):stream.write(chunk)
   if infile:infile.close()
  zo.writestr('xl/workbook.xml',workbook.replace(b'</sheets>',''.join(additions).encode()+b'</sheets>'))
  zo.writestr('xl/_rels/workbook.xml.rels',rels.replace(b'</Relationships>',''.join(reladds).encode()+b'</Relationships>'))
  zo.writestr('[Content_Types].xml',types.replace(b'</Types>',''.join(typeadds).encode()+b'</Types>'))

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--outdir',type=Path,required=True);p.add_argument('--extras',type=Path);a=p.parse_args()
 extras=json.loads(a.extras.read_text(encoding='utf-8')) if a.extras else []
 enrich(a.source,a.outdir,extras)
if __name__=='__main__':main()
