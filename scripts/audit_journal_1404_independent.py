"""Independent streaming audit; never writes original or v1 files."""
import csv,hashlib,json,re,sqlite3,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter,defaultdict
from itertools import zip_longest
import openpyxl
NS='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
TARGET=[openpyxl.utils.get_column_letter(i) for i in range(24,44)]
ROW=re.compile(rb'<row\b[^>]*>.*?</row>',re.S)
CELL=re.compile(rb'<c\b[^>]*?(?:/>|>.*?</c>)',re.S)
REF=re.compile(rb'\br="([A-Z]+)(\d+)"')
SOURCE=Path('C:/Users/sadra/Desktop/دفتر روزنامه 1404 - با اشخاص جدید.xlsx')
V1=Path('data/deliverables/journal_1404_enrichment_final')
ROOT=Path('data/deliverables/journal_1404_enrichment_v1_independent_audit')
def norm(v):return ' '.join(str(v or '').replace('ي','ی').replace('ك','ک').replace('\u200c',' ').replace('\xa0',' ').split())
def blank(v):return v is None or (isinstance(v,str) and not v.strip())
def shared(z):return [''.join(s.itertext()) for s in ET.fromstring(z.read('xl/sharedStrings.xml'))]
def rows(z,path='xl/worksheets/sheet1.xml'):
 with z.open(path) as f:
  buf=b''
  while chunk:=f.read(4*1024*1024):
   buf+=chunk;end=0
   for m in ROW.finditer(buf):
    raw=m.group();yield int(re.search(rb'<row\b[^>]*\br="(\d+)"',raw)[1]),raw;end=m.end()
   buf=buf[end:]
def cells(raw,strings):
 vals={};xml={}
 for m in CELL.finditer(raw):
  c=m.group();col=REF.search(c)[1].decode();xml[col]=c
  value=re.search(rb'<v>(.*?)</v>',c,re.S)
  if b't="s"' in c:vals[col]=strings[int(value[1])] if value else None
  elif b't="inlineStr"' in c:vals[col]=''.join(e.text or '' for e in ET.fromstring(c).iter() if e.tag.split('}')[-1]=='t')
  else:vals[col]=value[1].decode() if value else None
 return vals,xml
def hashfile(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def writer(name,headers):
 f=(ROOT/name).open('w',encoding='utf-8-sig',newline='');w=csv.DictWriter(f,fieldnames=headers);w.writeheader();return f,w
def historical_gate(v,r):
 # Independently reconstructed v1 gates, only to explain transitions; not approval.
 i=v.get('I');typ=norm(r[2]);desc=norm(r[1]);sub=norm(r[4]);subject=norm(r[3]);name=norm(r[8]);l1=norm(r[6])
 if 'تصمیم کارشناسی' in typ:return 'PROPOSED_MATCH','REFERENCE_REQUIRES_EXPERT_DECISION'
 if ('جبران خدمات' in name or 'منابع انسانی' in l1) and i in {'112','114','115'}:return 'CONFLICT','CONTRACT_TRANSFER_NOT_DIRECT_PAYROLL'
 if 'احداث' in name and any(t in desc for t in ['کرایه','اجاره','تخفیف','کمک به افراد','تجهیزات اداری']):return 'CONFLICT','RENTAL_RELIEF_EQUIPMENT_NOT_CONSTRUCTION'
 if 'مالی، خزانه' in name and not any(t in desc for t in ['مالی','بانک','خزانه','حسابداری','حسابرسی']):return 'PROPOSED_MATCH','NONFINANCE_TO_TREASURY_REFERENCE'
 if 'تدارکات' in name and any(t in desc+subject for t in ['احداث','آبراهه','ترافیک','آبیاری','فضای سبز','تملک','فرهنگی']):return 'PROPOSED_MATCH','SPECIALIZED_DOMAIN_TO_GENERIC_PROCUREMENT'
 if 'ورزش' in name and any(t in desc+sub for t in ['موزه','خانه های علمی','کتابخانه']):return 'CONFLICT','CULTURAL_FACILITY_TO_SPORT_REFERENCE'
 if i in {'111','112','114','115','116','117','132'} and 'سرمایه' in typ:return 'CONFLICT','OPERATING_ACCOUNT_CAPITAL_REFERENCE'
 if i in {'121','122','123','126','127'} and typ=='جاری':return 'CONFLICT','CAPITAL_ACCOUNT_OPERATING_REFERENCE'
 if i=='111' and not any(t in desc+subject for t in ['حقوق','مزایا']):return 'CONFLICT','PAYROLL_ACCOUNT_NONPAYROLL_REFERENCE'
 if i=='116' and subject not in {'رفاهیات','دیون'}:return 'CONFLICT','BENEFITS_ACCOUNT_UNRELATED_REFERENCE'
 if i in {'114','115'} and not any(t in desc+subject for t in ['کمک','یارانه','حمایت','پرداخت']):return 'CONFLICT','TRANSFER_ACCOUNT_INCOMPATIBLE_REFERENCE'
 if any(t in desc for t in ['کمک به سازمان','کمک به شرکت']) and ('جبران خدمات' in name or 'منابع انسانی' in l1):return 'CONFLICT','AFFILIATED_SUPPORT_NOT_DIRECT_PAYROLL'
 if any(t in desc for t in ['کمک به سازمان','کمک به شرکت']) and any(t in name for t in ['احداث','نگهداری','پایانه']):return 'PROPOSED_MATCH','AFFILIATED_SUPPORT_NOT_DIRECT_EXECUTION'
 if 'تملک' in desc and 'تدارکات' in name:return 'CONFLICT','LAND_TO_PROCUREMENT_REFERENCE'
 if subject=='سایر' and ('تدارکات' in name or 'املاک' in name):return 'PROPOSED_MATCH','GENERIC_FALLBACK_DOMAIN'
 if i=='131' and subject!='دیون':return 'CONFLICT','PRIOR_COMMITMENT_NONDEBT_REFERENCE'
 if i=='132' and not any(t in desc for t in ['تسهیلات','وام','سود','بازپرداخت']):return 'CONFLICT','LOAN_REPAYMENT_UNRELATED_REFERENCE'
 for token in ['بانک','مالیات']:
  if token in norm(v.get('N')) and token not in desc+subject+sub:return 'CONFLICT','ACCOUNT_CONTEXT_REFERENCE_MISMATCH_'+token
 return None,'V1_GATES_PASSED_NOT_ERP_AUTHORIZATION'
def run():
 ROOT.mkdir(parents=True,exist_ok=True)
 output=V1/'Accounting_Journal_1404_Desired_State_Enriched_v1.xlsx'
 protected={str(p):hashfile(p) for p in [SOURCE]+list(V1.iterdir()) if p.is_file()}
 (ROOT/'v1_preservation_before.json').write_text(json.dumps(protected,indent=2),encoding='utf-8')
 wb=openpyxl.load_workbook(SOURCE,read_only=True,data_only=True)
 budgets=defaultdict(list);bankrefs=defaultdict(list)
 for rn,r in enumerate(wb['بودجه 1404 + مراکز هزینه'].values,1):
  if rn>=3 and not blank(r[0]):budgets[norm(r[0])].append((rn,tuple('' if x is None else str(x) for x in r)))
 for rn,r in enumerate(wb['حسابهای بانکی'].values,1):
  if rn>=2 and len(r)>2 and not blank(r[2]):bankrefs[norm(r[2])].append(rn)
 wb.close()
 audit=defaultdict(list);unresolved={}
 with (V1/'audit_fill.csv').open(encoding='utf-8-sig',newline='') as f:
  for r in csv.DictReader(f):audit[int(r['source_row'])].append(r)
 with (V1/'unresolved_review.csv').open(encoding='utf-8-sig',newline='') as f:
  for r in csv.DictReader(f):unresolved[int(r['source_row'])]=json.loads(r['statuses'])
 db=sqlite3.connect(ROOT/'journal_records.sqlite')
 db.execute('CREATE TABLE journal(source_row INTEGER PRIMARY KEY,original TEXT,enriched TEXT,applied TEXT,unresolved TEXT)')
 files=[]
 def new(name,headers):
  f,w=writer(name,headers);files.append(f);return w
 coverage=new('Cost_Center_Coverage_Reconciliation.csv',['source_row','account_class','account','account_name','budget_code','initial_population','candidate_rows','candidate_cc','candidate_evidence','candidate_gate_decisions','final_status','applied_columns','existing_cc1','existing_cc2','exclusion_reason','corrective_mapping_possible','expert_review_required'])
 conflict=new('Conflict_Root_Cause_Analysis.csv',['source_row','account_class','budget_code','conflict_type','root_reason','existing_cc1','existing_cc2','candidate_rows','evidence','historical_usage_assessment','corrective_mapping_possible','expert_review_required'])
 bank=new('Bank_Assignment_Validation.csv',['source_row','target','new_value','actual_source_field','same_record','account_hierarchy','bank_account_title','account_reference_rows','genuine_bank_evidence','account_detail_consistency','evidence_type','original_status','independent_classification','assessment','limitations'])
 methods=new('Applied_Match_Classification_Audit.csv',['source_row','target','old_status','old_method','independent_classification','authority','assessment','reason'])
 count=Counter();initial=Counter();final=Counter();added=Counter();transition=Counter();roots=Counter();bankcnt=Counter();methodcnt=Counter();docs=set();fail=[];batches=[]
 with zipfile.ZipFile(SOURCE) as zs,zipfile.ZipFile(output) as ze:
  s1=shared(zs);s2=shared(ze)
  for left,right in zip_longest(rows(zs),rows(ze)):
   if left is None or right is None or left[0]!=right[0]:raise RuntimeError('Row population/order changed')
   rn,raw=left;rr=right[1]
   if rn<6:
    if raw!=rr:fail.append([rn,'header changed'])
    continue
   a,xa=cells(raw,s1);b,xb=cells(rr,s2);count['rows']+=1;docs.add((a.get('C'),a.get('E')))
   changes=audit.pop(rn,[]);states=unresolved.pop(rn,{})
   changeindex={r['target_column']:r for r in changes}
   actualchanged={c for c in set(xa)|set(xb) if xa.get(c)!=xb.get(c)}
   if len(changeindex)!=len(changes) or actualchanged!=set(changeindex):fail.append([rn,'audit/change set mismatch'])
   for c in TARGET:
    initial[c]+=not blank(a.get(c)) or b'<f' in xa.get(c,b'')
    final[c]+=not blank(b.get(c)) or b'<f' in xb.get(c,b'')
   for c in actualchanged:
    r=changeindex.get(c)
    if c not in TARGET or not blank(a.get(c)) or b'<f' in xa.get(c,b'') or not r or b.get(c)!=r['new_value']:fail.append([rn,c,'unsafe/unaudited change'])
    added[c]+=1
   for c in ['Q','R']:
    if xa.get(c)!=xb.get(c):fail.append([rn,c,'amount changed'])
   for r in changes:
    cl='SAME_ROW_STRUCTURED_FIELD_PROPAGATION' if r['target_column']=='AM' else 'CONTEXT_FILTERED_NATIVE_REFERENCE_LOOKUP'
    methodcnt[cl]+=1
    methods.writerow(dict(zip(methods.fieldnames,[rn,r['target_column'],r['status'],r['method'],cl,'Native source evidence; no approved ERP master relationship','ACCEPTABLE WITH REVIEW','Bank propagation is not Bank Master lookup; CC reference code recovery does not itself prove financial domain authorization'])))
   rs=budgets.get(norm(a.get('W')),[]);ccdistinct={tuple(norm(x) for x in r[5:9]) for _,r in rs}
   initialpop='INITIAL_UNIQUE' if len(ccdistinct)==1 else 'INITIAL_AMBIGUOUS' if rs else 'UNUSABLE_BUDGET' if norm(a.get('W')) in ('','NULL','0') else 'BUDGET_NOT_FOUND'
   decisions=[{'reference_row':n,'status':historical_gate(a,r)[0] or 'V1_GATE_ELIGIBLE','reason':historical_gate(a,r)[1]} for n,r in rs]
   cchanges=[r for r in changes if r['target_column'] in ['AF','AG','AH','AI']]
   if a.get('X')=='6':
    count['expense']+=1
    end='APPLIED' if cchanges else states.get('AF','NO_EVIDENCE')
    transition[(initialpop,end)]+=1
    reason='Native composite/name filtering accepted by v1; independently subject to financial semantic audit' if cchanges else '; '.join(sorted({d['reason'] for d in decisions if d['status']!='V1_GATE_ELIGIBLE'})) or ('Existing name contradicts all eligible reference candidates' if rs else 'No budget link; no authorized replacement')
    coverage.writerow(dict(zip(coverage.fieldnames,[rn,a.get('X'),a.get('H'),a.get('N'),a.get('W'),initialpop,','.join(str(n) for n,_ in rs),json.dumps([r[5:9] for _,r in rs],ensure_ascii=False),json.dumps([{'row':n,'title':r[1],'type':r[2],'subject':r[3],'owner':r[9]} for n,r in rs],ensure_ascii=False),json.dumps(decisions,ensure_ascii=False),end,','.join(r['target_column'] for r in cchanges),a.get('AG'),a.get('AI'),reason,'Possible only with validated line/domain/reference correction' if not cchanges else 'No automatic correction established','YES' if not cchanges else 'SEMANTIC_REVIEW'])))
   if 'CONFLICT' in states.values():
    count['conflict_rows']+=1
    if a.get('X')=='4':kind='REVENUE_EXPENSE_INCOMPATIBILITY';why='Revenue account already has expense-center title matching expense budget reference'
    elif any(d['status']=='CONFLICT' for d in decisions):kind='NATIVE_REFERENCE_SEMANTIC_INCONSISTENCY';why='; '.join(sorted({d['reason'] for d in decisions if d['status']=='CONFLICT'}))
    elif len(ccdistinct)>1:kind='COMPETING_REFERENCE_MAPPINGS_OR_EXISTING_NAME_CONTRADICTION';why='Existing source CC does not select a validated accounting-compatible candidate'
    elif rs:kind='EXISTING_CC_NAME_CONTRADICTS_REFERENCE';why='Existing name conflicts with accounting-compatible native budget mapping'
    else:kind='INCOMPLETE_ACCOUNT_REFERENCE_CONTEXT';why='Insufficient authoritative evidence to resolve'
    roots[kind]+=1
    conflict.writerow(dict(zip(conflict.fieldnames,[rn,a.get('X'),a.get('W'),kind,why,a.get('AG'),a.get('AI'),','.join(str(n) for n,_ in rs),json.dumps({'account':a.get('H'),'N':a.get('N'),'O':a.get('O'),'P':a.get('P'),'candidates':decisions},ensure_ascii=False),'UNDETERMINED_HISTORICAL_USAGE: no field-usage policy proves legitimate usage; repeated budget-only reference association is consistent with systematic source enrichment, not authorization' if a.get('X')=='4' else 'Native reference/domain or existing-name conflict','Expert/source-owner correction possible; no safe automatic overwrite','YES'])))
   for r in changes:
    if r['target_column']!='AM':continue
    references=bankrefs.get(norm(a.get('P')),[]);genuine=a.get('I')=='611' and a.get('J') not in {'020','030','040'} and 'بانک' in norm(a.get('O'));same=r['reference_row']=='O'+str(rn) and a.get('O')==b.get('AM')
    # A bank account title can confirm account membership but not a global Bank Master ID.
    consistency='REVIEW_NO_BANK_TOKEN' if not genuine else 'NAME_ACCOUNT_MEMBERSHIP_SUPPORTED'
    tokens=[t for t in norm(a.get('O')).split() if t not in {'بانک','بانکها'}]
    tokenmatch=any(t in norm(a.get('P')) for t in tokens)
    if genuine and not tokenmatch:consistency='REVIEW_ACCOUNT_TITLE_NO_MATCHING_BANK_NAME_TOKEN'
    evidence='SAME_ROW_ACCOUNT_HEAD_PLUS_NATIVE_ACCOUNT_TITLE_REFERENCE' if references else 'SAME_ROW_ONLY'
    assessment='ACCEPTABLE WITH REVIEW' if same and genuine and references else 'NOT YET ACCEPTABLE'
    bankcnt[evidence]+=1;bankcnt[consistency]+=1
    bank.writerow(dict(zip(bank.fieldnames,[rn,'AM',b.get('AM'),'O'+str(rn),same,a.get('H'),a.get('P'),','.join(str(n) for n in references),genuine,consistency,evidence,r['status'],'SAME_ROW_STRUCTURED_FIELD_PROPAGATION',assessment,'Not authoritative Bank Master lookup; no bank ID validated; account-title token check is supporting evidence only'])))
   batches.append((rn,json.dumps(a,ensure_ascii=False),json.dumps(b,ensure_ascii=False),json.dumps(changes,ensure_ascii=False),json.dumps(states)))
   if len(batches)>=5000:db.executemany('INSERT INTO journal VALUES(?,?,?,?,?)',batches);db.commit();batches=[]
  db.executemany('INSERT INTO journal VALUES(?,?,?,?,?)',batches);db.commit();db.close()
  if audit or unresolved:fail.append(['orphan audit/unresolved records',len(audit),len(unresolved)])
  for item in zs.infolist():
   if item.filename in {'xl/worksheets/sheet1.xml','xl/workbook.xml','xl/_rels/workbook.xml.rels','[Content_Types].xml'}:continue
   if zs.read(item.filename)!=ze.read(item.filename):fail.append([item.filename,'source member changed'])
 for f in files:f.close()
 result={'measured':dict(count),'initial_population':dict(initial),'final_population':dict(final),'added':dict(added),'transitions':[{'initial':k[0],'final':k[1],'rows':n} for k,n in sorted(transition.items())],'conflict_types':dict(roots),'bank_evidence':dict(bankcnt),'independent_match_classes':dict(methodcnt),'unique_region_document_pairs':len(docs),'preservation_failures':fail,'source_hashes_before':protected}
 (ROOT/'independent_metrics.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({k:v for k,v in result.items() if k!='source_hashes_before'},ensure_ascii=False,indent=2),flush=True)
 if fail:raise RuntimeError('Independent integrity failure')
if __name__=='__main__':run()
