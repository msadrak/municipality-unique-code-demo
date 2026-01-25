import json

# Load and format candidate pairs for strict analysis
with open(r"f:\Freelancing_Project\KalaniProject\municipality_demo\data\reports\candidate_pairs.json", 'r', encoding='utf-8') as f:
    data = json.load(f)

output = []

# Print all pairs in the required format for analysis
for i, p in enumerate(data['candidate_pairs']):
    # Calculate shared shenaseh
    shared = set(p['a_shenaseh']) & set(p['b_shenaseh'])
    common_codes = {'106'}
    rare_shared = shared - common_codes
    
    pair_info = {
        "pair_id": f"P{str(i+1).zfill(6)}",
        "a": {
            "tafsili_norm": p['a'],
            "tafsili_raw": p['a_originals'][0] if p['a_originals'] else p['a'],
            "top_kol": p['a_top_kol'],
            "top_moein": p['a_top_moein'],
            "shenaseh_values": p['a_shenaseh'],
            "joze_examples": p['a_joze_samples'],
            "frequency": p['a_count']
        },
        "b": {
            "tafsili_norm": p['b'],
            "tafsili_raw": p['b_originals'][0] if p['b_originals'] else p['b'],
            "top_kol": p['b_top_kol'],
            "top_moein": p['b_top_moein'],
            "shenaseh_values": p['b_shenaseh'],
            "joze_examples": p['b_joze_samples'],
            "frequency": p['b_count']
        },
        "precomputed_similarity": {
            "token_set_ratio": round(p['similarity_score'] / 100, 2)
        },
        "shared_shenaseh": list(shared),
        "rare_shared_shenaseh": list(rare_shared)
    }
    output.append(pair_info)

# Write to file 
with open(r"C:\Users\Dour_Andish\.gemini\antigravity\brain\592da352-7d36-4150-8edd-0b906c5f22bb\all_pairs_formatted.json", 'w', encoding='utf-8') as f:
    json.dump({"candidate_pairs": output}, f, ensure_ascii=False, indent=2)

print(f"Wrote {len(output)} pairs to all_pairs_formatted.json")
