"""v2.1 manifest writer (shared by 20_docs_v21.py and 21_final_v21.py)."""
import os, json, hashlib

def manifest(OUT, ROOT, NOW):
    LEVEL = lambda rel: ('RESTRICTED' if ('RESTRICTED' in rel) else ('CLIENT_REVIEW' if rel.startswith('client_package/') else 'INTERNAL_TECHNICAL'))
    man = {}
    for root, _, fs in os.walk(OUT):
        for fn in sorted(fs):
            p = os.path.join(root, fn); rel = os.path.relpath(p, OUT).replace('\\', '/')
            if rel.startswith('MANIFEST'): continue
            man[rel] = dict(bytes=os.path.getsize(p), sha256=hashlib.sha256(open(p, 'rb').read()).hexdigest(), version='v2.1', distribution_level=LEVEL(rel), classification='RESTRICTED' if LEVEL(rel) == 'RESTRICTED' else 'NON_RESTRICTED')
    base = f'{ROOT}/data/deliverables/financial_event_discovery/revisions/1404-r20260922-canonical-events-v7.1/financial_event_discovery_1404-r20260922_canonical-events_v7.1.xlsx'
    m = dict(generated_for='Taxi/Terminals FY1404-1405 v2.1 (Verified / Consistent / Client-Handover Ready)', generated_on=NOW, activate_in_production='NO', approved_items=0,
             v1_preserved_at='data/deliverables/taxi_terminals_1404_1405/', v2_preserved_at='data/deliverables/taxi_terminals_1404_1405/revisions/v2/',
             baseline_v71_sha256_current=hashlib.sha256(open(base, 'rb').read()).hexdigest(), baseline_v71_sha256_recorded_in_its_manifest='3561b9817df949b3d3175a74ccc40e7f01cb2fa932bebc03fadb7ace6c6449fa',
             self_referential_exclusions=['MANIFEST_v2.1.json'], notes='No credentials or private absolute paths are listed; paths are relative to the v2.1 revision directory.', files=man)
    json.dump(m, open(f'{OUT}/MANIFEST_v2.1.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
    return m
