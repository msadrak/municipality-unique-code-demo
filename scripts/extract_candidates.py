"""
Extract candidate pairs for entity resolution with full accounting context.
Output: JSON with pairs, their Kol/Moein profiles, Joze samples, and frequencies.
"""
import pandas as pd
import json
import re
import unicodedata
from rapidfuzz import fuzz
from collections import defaultdict

INPUT_FILE = r"f:\Freelancing_Project\KalaniProject\municipality_demo\data\reports\Uniqe Person_Company.xlsx"
OUTPUT_FILE = r"f:\Freelancing_Project\KalaniProject\municipality_demo\data\reports\candidate_pairs.json"

def normalize_text(text):
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize('NFKC', text)
    text = text.replace('ي', 'ی').replace('ك', 'ک').replace('ة', 'ه')
    text = text.replace('آ', 'ا').replace('أ', 'ا').replace('إ', 'ا')
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def main():
    print("Loading data...")
    df = pd.read_excel(INPUT_FILE)
    
    # Identify columns
    tafsili_col = 'تفضیلی'
    joze_col = 'جزء'
    kol_col = 'کل'
    moein_col = 'معین'
    shenaseh_col = 'شناسه'
    
    # Normalize names
    df['normalized'] = df[tafsili_col].apply(normalize_text)
    
    # Build entity profiles: for each unique normalized name, collect context
    entity_profiles = defaultdict(lambda: {
        'original_names': set(),
        'kol_values': [],
        'moein_values': [],
        'joze_samples': [],
        'shenaseh_values': set(),
        'count': 0
    })
    
    for _, row in df.iterrows():
        norm = row['normalized']
        if not norm or len(norm) < 3:
            continue
        
        profile = entity_profiles[norm]
        profile['original_names'].add(str(row[tafsili_col]))
        profile['count'] += 1
        
        if pd.notna(row.get(kol_col)):
            profile['kol_values'].append(str(row[kol_col]))
        if pd.notna(row.get(moein_col)):
            profile['moein_values'].append(str(row[moein_col]))
        if pd.notna(row.get(joze_col)):
            joze = str(row[joze_col])[:100]  # Truncate
            if joze not in profile['joze_samples'] and len(profile['joze_samples']) < 3:
                profile['joze_samples'].append(joze)
        if pd.notna(row.get(shenaseh_col)):
            profile['shenaseh_values'].add(str(row[shenaseh_col]))
    
    # Convert sets to lists for JSON
    for k, v in entity_profiles.items():
        v['original_names'] = list(v['original_names'])
        v['shenaseh_values'] = list(v['shenaseh_values'])
        # Get top Kol/Moein
        v['top_kol'] = max(set(v['kol_values']), key=v['kol_values'].count) if v['kol_values'] else None
        v['top_moein'] = max(set(v['moein_values']), key=v['moein_values'].count) if v['moein_values'] else None
        del v['kol_values']
        del v['moein_values']
    
    # Find candidate pairs (fuzzy similarity > 80 but < 100)
    names = list(entity_profiles.keys())
    print(f"Total unique normalized names: {len(names)}")
    
    candidate_pairs = []
    seen = set()
    
    for i, name_a in enumerate(names):
        if i % 100 == 0:
            print(f"Processing {i}/{len(names)}...")
        
        for j, name_b in enumerate(names):
            if i >= j:
                continue
            
            # Skip if exactly equal (already grouped)
            if name_a == name_b:
                continue
            
            score = fuzz.ratio(name_a, name_b)
            
            # Candidates: similar but not identical
            if 75 <= score < 100:
                pair_key = tuple(sorted([name_a, name_b]))
                if pair_key in seen:
                    continue
                seen.add(pair_key)
                
                profile_a = entity_profiles[name_a]
                profile_b = entity_profiles[name_b]
                
                candidate_pairs.append({
                    'a': name_a,
                    'b': name_b,
                    'similarity_score': score,
                    'a_originals': profile_a['original_names'],
                    'b_originals': profile_b['original_names'],
                    'a_top_kol': profile_a['top_kol'],
                    'b_top_kol': profile_b['top_kol'],
                    'a_top_moein': profile_a['top_moein'],
                    'b_top_moein': profile_b['top_moein'],
                    'a_joze_samples': profile_a['joze_samples'],
                    'b_joze_samples': profile_b['joze_samples'],
                    'a_shenaseh': profile_a['shenaseh_values'],
                    'b_shenaseh': profile_b['shenaseh_values'],
                    'a_count': profile_a['count'],
                    'b_count': profile_b['count']
                })
    
    # Sort by similarity (highest first)
    candidate_pairs.sort(key=lambda x: x['similarity_score'], reverse=True)
    
    print(f"Found {len(candidate_pairs)} candidate pairs")
    
    # Save
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump({'candidate_pairs': candidate_pairs[:50]}, f, ensure_ascii=False, indent=2)  # Top 50
    
    print(f"Saved to {OUTPUT_FILE}")
    
    # Print top 15 for immediate review
    print("\n--- TOP 15 CANDIDATE PAIRS ---")
    for p in candidate_pairs[:15]:
        print(f"\nScore: {p['similarity_score']}")
        print(f"  A: {p['a']} (originals: {p['a_originals'][:2]})")
        print(f"  B: {p['b']} (originals: {p['b_originals'][:2]})")
        print(f"  A Kol/Moein: {p['a_top_kol']}/{p['a_top_moein']} | B Kol/Moein: {p['b_top_kol']}/{p['b_top_moein']}")
        print(f"  A Shenaseh: {p['a_shenaseh'][:2]} | B Shenaseh: {p['b_shenaseh'][:2]}")
        print(f"  A Joze: {p['a_joze_samples'][:1]}")
        print(f"  B Joze: {p['b_joze_samples'][:1]}")

if __name__ == "__main__":
    main()
