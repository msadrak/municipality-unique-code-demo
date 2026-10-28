"""Add independently measured classification/historical usage taxonomy, not inferred fixes."""
import csv,json,sqlite3
from collections import Counter,defaultdict
from audit_journal_1404_independent import ROOT,SOURCE,norm,blank
import openpyxl

def main():
 db=sqlite3.connect(ROOT/'journal_records.sqlite');hist=Counter();classes=defaultdict(set);risky=[]
 # Source-defined account classes observed consistently; cannot prove source classifications approved.
 for rn,raw in db.execute('SELECT source_row,original FROM journal'):
  a=json.loads(raw);classes[(a.get('I'),a.get('J'))].add(a.get('X'))
 wb=openpyxl.load_workbook(SOURCE,read_only=True,data_only=True);budget=defaultdict(list)
 for rn,r in enumerate(wb['بودجه 1404 + مراکز هزینه'].values,1):
  if rn>=3 and r[0] is not None:budget[norm(r[0])].append(r)
 wb.close()
 with (ROOT/'Revenue_Field_Usage_Investigation.csv').open('w',encoding='utf-8-sig',newline='') as f:
  fields=['source_row','classification','account_code','account_title','budget_code','existing_cc1','existing_cc2','same_budget_native_pair_match','account_class_consistent_with_same_account','historical_field_usage_status','reference_relationship_status','required_evidence'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for rn,raw,unres in db.execute('SELECT source_row,original,unresolved FROM journal'):
   a=json.loads(raw)
   if a.get('X')!='4' or (blank(a.get('AG')) and blank(a.get('AI'))):continue
   rs=budget.get(norm(a.get('W')),[]);matching=any(norm(a.get('AG'))==norm(r[6]) and norm(a.get('AI'))==norm(r[8]) for r in rs)
   consistent=len(classes[(a.get('I'),a.get('J'))])==1
   hist['revenue_existing_cc']+=1;hist['exact_budget_reference_pair']+=matching;hist['source_account_class_consistent']+=consistent
   w.writerow(dict(zip(fields,[rn,a.get('X'),a.get('H'),a.get('N'),a.get('W'),a.get('AG'),a.get('AI'),matching,consistent,'UNDETERMINED: no dated field-use policy or original assignment approval','EXPENSE_REFERENCE_ON_REVENUE_IS_NOT_AUTHORIZED','Source-owner field specification, original enrichment formula/history, approved revenue-center versus cost-center rule, accounting-class approval; do not erase source values'])))
 # Requested taxonomy categories include zero/unproven, not invented explanations.
 m=json.loads((ROOT/'independent_metrics.json').read_text(encoding='utf-8'))
 taxonomy=dict(m['conflict_types']);taxonomy.update({'INCORRECT_OR_OUTDATED_SOURCE_CLASSIFICATION_PROVEN':0,'LEGITIMATE_HISTORICAL_FIELD_USAGE_PROVEN':0,'OTHER_DOCUMENTED_CONFLICTS':0})
 result={'revenue_investigation':dict(hist),'conflict_taxonomy':taxonomy,'source_account_class_inconsistent_keys':[list(k) for k,v in classes.items() if len(v)>1],'limitations':'Observed consistent source classifications are not independent chart-of-accounts approval; erroneous vs legitimate historical field usage cannot be decided without source-owner policy/history.'}
 (ROOT/'conflict_taxonomy_metrics.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False,indent=2))
 db.close()
if __name__=='__main__':main()
