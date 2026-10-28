"""Integrate independently measured eligibility and financial totals."""
import json,sqlite3
from collections import Counter
from decimal import Decimal
import openpyxl
from audit_journal_1404_independent import ROOT,V1,SOURCE,TARGET,norm,blank,hashfile

def main():
 m=json.loads((ROOT/'independent_metrics.json').read_text(encoding='utf-8'))
 db=sqlite3.connect(ROOT/'journal_records.sqlite');totals=Counter();eligible=Counter();verified=Counter();rowcount=0;bankheads=Counter()
 org=json.loads((ROOT/'org_person_metrics.json').read_text(encoding='utf-8')) if (ROOT/'org_person_metrics.json').exists() else {}
 semantic=json.loads((ROOT/'semantic_metrics.json').read_text(encoding='utf-8')) if (ROOT/'semantic_metrics.json').exists() else {}
 strict_cc=semantic.get('counts',{}).get('applied_NO_DETECTED_CONTRADICTION',None)
 for rn,original,enriched,applied in db.execute('SELECT source_row,original,enriched,applied FROM journal'):
  a=json.loads(original);b=json.loads(enriched);rowcount+=1
  for side,v in [('source',a),('enriched',b)]:
   for col in ['Q','R']:
    try:totals[side+'_'+col]+=Decimal(v.get(col) or '0')
    except Exception:totals[side+'_invalid_amount']+=1
  # Presence establishes observed dimension evidence, not universal applicability rules.
  if not blank(a.get('AD')) or not blank(a.get('AE')):eligible['Organizational Unit']+=1
  if a.get('X')=='6':eligible['Cost Center']+=1
  if not blank(a.get('AJ')) and not blank(a.get('AK')):eligible['Person']+=1;verified['Person']+=1
  if a.get('I')=='611' and a.get('J') not in {'020','030','040'} and 'بانک' in norm(a.get('O')):
   eligible['Bank']+=1
   if not blank(b.get('AM')) and norm(b.get('AM'))==norm(a.get('O')):verified['Bank']+=1
  if a.get('X')=='6' and not blank(b.get('AF')) and not blank(b.get('AH')):verified['Cost Center']+=1
 db.close()
 dimensions=['Organizational Unit','Cost Center','Person','Bank','Contract','Project']
 book=openpyxl.Workbook();ws=book.active;ws.title='Eligibility_and_Coverage';ws.sheet_view.rightToLeft=True
 ws.append(['Dimension','Positive source-evidence applicable records','Verified populated eligible records','Explicit not applicable','Applicability unknown','Verified eligible completion rate','Overall physical pair completion','Authority limitation','Physically populated eligible records','Source-supported or no-objection records','Source-supported rate NOT authoritative approval'])
 # Organizational computed coverage is taken from separate formula audit, not formula presence.
 validunit=org.get('counts',{}).get('valid_recomputed_code_and_name',0)
 verified['Organizational Unit']=validunit
 physical=dict(verified)
 verified['Person']=None
 # Names/IDs exist, but no authoritative person/role master verifies identity consistency.
 if strict_cc is not None:verified['Cost Center']=strict_cc
 verified['Bank']=m.get('bank_evidence',{}).get('NAME_ACCOUNT_MEMBERSHIP_SUPPORTED',0)
 source_supported=dict(verified)
 verified['Cost Center']=None
 # Full-scan no-objection is reported separately, not promoted to approved domain eligibility.
 # Even no detected contradiction is source-evidence validation, not published ERP authority.
 for d in dimensions:
  ep=eligible[d];vp=verified[d]
  note={'Organizational Unit':'Cached and independently recomputed VLOOKUP validity reported separately; document-level ambiguity may block authority','Cost Center':'Expense classification establishes candidate eligibility, not approved mandatory CC cardinality; coding presence not semantic approval','Person':'Existing native ID/name pairs; conflicts require master verification; no universal person-role rule','Bank':'Bank-account ledger lines only; bank NAME presence is not Bank Master ID completion','Contract':'No verified transaction-to-contract ID link or applicability rule','Project':'No verified transaction-to-project ID link or applicability rule'}[d]
  pair={'Organizational Unit':min(m['final_population'].get('AD',0),m['final_population'].get('AE',0)),'Cost Center':min(m['final_population'].get('AF',0),m['final_population'].get('AH',0)),'Person':min(m['final_population'].get('AJ',0),m['final_population'].get('AK',0)),'Bank':min(m['final_population'].get('AL',0),m['final_population'].get('AM',0)),'Contract':0,'Project':0}[d]
  ws.append([d,ep,vp,0,rowcount-ep,vp/ep if ep and vp is not None else None,pair/rowcount,note,physical.get(d,0),source_supported.get(d),source_supported.get(d)/ep if ep and source_supported.get(d) is not None else None])
 for row in range(2,8):ws.cell(row,6).number_format='0.00%';ws.cell(row,7).number_format='0.00%'
 overall=book.create_sheet('Overall_Column_Coverage');overall.append(['Column','Original populated','Final populated','Added','Initial rate','Final rate'])
 for c in TARGET:overall.append([c,m['initial_population'].get(c,0),m['final_population'].get(c,0),m['added'].get(c,0),m['initial_population'].get(c,0)/rowcount,m['final_population'].get(c,0)/rowcount])
 amounts=book.create_sheet('Financial_Integrity');amounts.append(['Metric','Actual'])
 for k,v in totals.items():amounts.append([k,str(v)])
 amounts.append(['Source debit/credit equals output',totals['source_Q']==totals['enriched_Q'] and totals['source_R']==totals['enriched_R']])
 book.save(ROOT/'Dimension_Eligibility_and_Coverage.xlsx')
 result={'rows':rowcount,'eligible':dict(eligible),'populated_native_eligible':dict(verified),'physically_populated_eligible':physical,'source_supported_or_no_objection':source_supported,'explicit_not_applicable':0,'financial_totals':{k:str(v) for k,v in totals.items()},'limitations':'Observed dimension evidence is not an approved universal applicability rule. CC no-objection count does not establish verified financial-domain eligibility. Bank name validation is not Bank ID validation; person role identity unverified.'}
 (ROOT/'eligibility_metrics.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
