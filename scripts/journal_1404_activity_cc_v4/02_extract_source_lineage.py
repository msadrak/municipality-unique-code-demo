import sqlite3, pickle, time
t0 = time.time()
con = sqlite3.connect('data/deliverables/journal_1404_enrichment_v1_independent_audit/journal_records.sqlite')
q = """select source_row,
 json_extract(original,'$.AF'), json_extract(original,'$.AG'), json_extract(original,'$.AH'), json_extract(original,'$.AI'),
 json_extract(enriched,'$.AF'), json_extract(enriched,'$.AG'), json_extract(enriched,'$.AH'), json_extract(enriched,'$.AI'),
 json_extract(original,'$.P'), json_extract(original,'$.Q'), json_extract(original,'$.R')
 from journal"""
out = {r[0]: r[1:] for r in con.execute(q)}
pickle.dump(out, open('zz_lineage.pkl', 'wb'))
print(len(out), round(time.time() - t0))
