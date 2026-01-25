import pandas as pd
import re
import os
from rapidfuzz import process, fuzz
import unicodedata

# Configuration
INPUT_FILE = r"f:\Freelancing_Project\KalaniProject\municipality_demo\data\reports\Uniqe Person_Company.xlsx"
OUTPUT_DIR = r"f:\Freelancing_Project\KalaniProject\municipality_demo\data\reports"
MASTER_LIST_FILE = os.path.join(OUTPUT_DIR, "Master_Counterparty_List.xlsx")
DUPLICATE_REPORT_FILE = os.path.join(OUTPUT_DIR, "Duplicate_Resolution_Report.xlsx")

# Domain Keywords
COMPANY_KEYWORDS = [
    "شرکت", "بانک", "سازمان", "اداره", "موسسه", "تعاونی", "صندوق", "شهرداری",
    "مهندسی", "بازرگانی", "صنایع", "گروه", "تولیدی", "پیمانکاری", "بیمه"
]
INDIVIDUAL_KEYWORDS = [
    "آقای", "خانم", "مهندس", "دکتر"
]

def normalize_text(text):
    if not isinstance(text, str):
        return ""
    
    # 1. Unicode normalization (NFKC)
    text = unicodedata.normalize('NFKC', text)
    
    # 2. Character mapping (Arabic to Persian)
    text = text.replace('ي', 'ی').replace('ك', 'ک').replace('ة', 'ه')
    text = text.replace('آ', 'ا').replace('أ', 'ا').replace('إ', 'ا')
    
    # 3. Remove punctuation/special chars (keep alphanumerics and space)
    text = re.sub(r'[^\w\s]', ' ', text)
    
    # 4. Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def determine_entity_type(name, normalized_name):
    # Check for company keywords
    for keyword in COMPANY_KEYWORDS:
        if keyword in name or keyword in normalized_name:
            return "COMPANY"
            
    # Check for individual keywords
    for keyword in INDIVIDUAL_KEYWORDS:
        if keyword in name or keyword in normalized_name:
            return "INDIVIDUAL"
            
    # Default assumption: If it has more than 1 word and NO company keywords, likely Individual (User Assumption)
    # But usually < 5 words. Long string without keywords might be description or company.
    # Simple heuristic:
    return "UNCERTAIN"

def classify_entity_strict(name, processed):
    if "شرکت" in processed or "بانک" in processed or "سازمان" in processed or "شهرداری" in processed:
        return "COMPANY"
    return "INDIVIDUAL" # Defaulting for now to avoid too many unknowns

def main():
    print("Loading data...")
    try:
        df = pd.read_excel(INPUT_FILE)
    except FileNotFoundError:
        print(f"Error: File not found at {INPUT_FILE}")
        return

    # Map likely column names if headers were weird, but inspections showed:
    # 'شناسه', 'شماره سند', 'سرفصل', 'کل', 'معین', 'تفضیلی', 'جزء'
    # We care mostly about: 'تفضیلی' (Entity Name), 'شناسه' (ID), 'جزء' (Contract context)
    
    target_col = 'تفضیلی'
    id_col = 'شناسه'
    context_col = 'جزء'
    
    if target_col not in df.columns:
        print(f"Critical Error: Column '{target_col}' not found. Available: {df.columns.tolist()}")
        return

    print("Normalizing names...")
    df['normalized_name'] = df[target_col].apply(normalize_text)
    
    # Generate ID for aggregation
    df['row_id'] = df.index

    print("Classifying entities...")
    df['entity_type'] = df.apply(lambda row: classify_entity_strict(str(row[target_col]), str(row['normalized_name'])), axis=1)

    print("Starting deduplication...")
    
    # UNIQUE LIST creation
    unique_entities = df.drop_duplicates(subset=['normalized_name']).copy()
    unique_entities['group_id'] = range(len(unique_entities))
    
    # Create valid name list for fuzzy matching
    # Filter out very short names or garbage
    valid_names = unique_entities[unique_entities['normalized_name'].str.len() > 3]['normalized_name'].tolist()
    
    # Clustering Logic
    # We will map every normalized_name to a "Canonical Name" (the group leader)
    
    # 1. Exact Name Match -> Already handled by unique_entities
    # 2. Logic: Iterate through unique names, find fuzzy matches, assign same Group ID
    
    name_to_group = {row['normalized_name']: row['group_id'] for _, row in unique_entities.iterrows()}
    
    # Reduce search space: only look at names that haven't been merged into a smaller group yet?
    # Simple transitive clustering:
    
    groups = {} # group_id -> list of names
    for name, gid in name_to_group.items():
        if gid not in groups:
            groups[gid] = []
        groups[gid].append(name)
        
    # We will use a Disjoint Set (Union-Find) approach ideally, but let's stick to pairwise merge for simplicity
    # Iterative fuzzy check
    
    processed_names = list(unique_entities['normalized_name'].values)
    
    # Using RapidFuzz Cdist could be faster for N*N but let's do simple process.extract for readability and control
    # Optimization: Sort by length?
    
    merges = [] # (name_a, name_b, score, reason)
    
    # Optimization: Block by first letter? No, spelling errors might affect first letter.
    # Doing full N*N is O(N^2). How many unique entities?
    n_unique = len(unique_entities)
    print(f"Unique normalized names to process: {n_unique}")
    
    # If N is huge (>5000), this will be slow. Let's assume < 5000 for this demo.
    # If > 5000, we'd need blocking.
    
    # Let's verify 'Shenaseh' grouping first (Strong Signal)
    print("Applying Shenaseh (ID) grouping...")
    # Group by Shenaseh
    if id_col in df.columns:
        id_groups = df.groupby(id_col)['normalized_name'].unique()
        for shenaseh, names in id_groups.items():
            if pd.isna(shenaseh) or shenaseh == "":
                continue
            if len(names) > 1:
                # All these names share the same ID -> Merge them
                primary = names[0]
                for other in names[1:]:
                    merges.append((primary, other, 100, f"Same ID: {shenaseh}"))

    # Fuzzy Matching
    # Only compare names that are technically "different" strings
    print("Running fuzzy matching (this may take a moment)...")
    
    # Thresholds
    SCORE_CUTOFF = 88 # High confidence
    
    # We'll use the unique list.
    names_list = unique_entities['normalized_name'].unique()
    
    # To avoid N^2, use rapidfuzz extraction on the whole list?
    # extract returns top N matches.
    
    # Update adj_list based on ID merges so we can skip them in fuzzy?
    # Actually, let's just proceed.
    
    from collections import defaultdict
    # adj_list = defaultdict(set)
    # for n1, n2, _, _ in merges:
    #     adj_list[n1].add(n2)
    #     adj_list[n2].add(n1)

    # Fuzzy step
    if n_unique < 20000: # Safe limit for simple loop
        for i, name in enumerate(names_list):
            if i % 100 == 0:
                print(f"Processed {i}/{len(names_list)}...")
                
            # Find similar
            matches = process.extract(name, names_list, limit=10, scorer=fuzz.ratio, score_cutoff=SCORE_CUTOFF)
            
            for match, score, idx in matches:
                if match == name:
                    continue # self
                
                # We found a match. Add edge.
                merges.append((name, match, score, "Fuzzy Similarity"))

    # Resolve Transitive Groups
    # Union-Find
    parent = {n: n for n in names_list}
    
    def find(n):
        if parent[n] != n:
            parent[n] = find(parent[n])
        return parent[n]
    
    def union(n1, n2):
        root1 = find(n1)
        root2 = find(n2)
        if root1 != root2:
            parent[root2] = root1

    # Apply merges
    for n1, n2, score, reason in merges:
        # If fuzzy, maybe be careful?
        # For now, we trust the high threshold + ID checks
        if n1 in parent and n2 in parent:
            union(n1, n2)
            
    # Assign new Group IDs
    group_map = {}
    current_gid = 1
    
    final_groups = {} # leader -> group_id
    
    for name in names_list:
        root = find(name)
        if root not in final_groups:
            final_groups[root] = current_gid
            current_gid += 1
        group_map[name] = final_groups[root]

    # Map back to main DF
    df['clean_group_id'] = df['normalized_name'].map(group_map)
    df['canonical_name'] = df['normalized_name'].apply(lambda x: find(x))

    print("Generating Reports...")
    
    # Master List: Group by canonical_name/group_id
    # We want: Group ID | Canonical Name | Type | Original Name Variants | Count | IDs Found
    
    master_agg = df.groupby('clean_group_id').agg({
        'canonical_name': 'first',
        'entity_type': 'first', # Heuristic: take first
        target_col: lambda x: list(set(x)), # All variations
        id_col: lambda x: list(set(x.dropna())),
        'row_id': 'count' # Occurrences
    }).rename(columns={'row_id': 'occurrence_count'})
    
    master_agg.to_excel(MASTER_LIST_FILE)
    print(f"Master list saved to: {MASTER_LIST_FILE}")
    
    # Duplicate Resolution Report (Detailed)
    # Filter only groups with > 1 variation of name
    duplicates = master_agg[master_agg[target_col].apply(lambda x: len(x) > 1)]
    duplicates.to_excel(DUPLICATE_REPORT_FILE)
    print(f"Duplicate report saved to: {DUPLICATE_REPORT_FILE}")
    
    print("Done.")

if __name__ == "__main__":
    main()
