import json
import pandas as pd
import os

# Define paths
json_path = r"C:\Users\Dour_Andish\.gemini\antigravity\brain\592da352-7d36-4150-8edd-0b906c5f22bb\entity_resolution_decisions.json"
output_excel_path = r"f:\Freelancing_Project\KalaniProject\municipality_demo\data\reports\Entity_Resolution_Decisions.xlsx"

# Ensure output directory exists (though it should already)
os.makedirs(os.path.dirname(output_excel_path), exist_ok=True)

try:
    # Load JSON data
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    decisions = data.get('decisions', [])

    if not decisions:
        print("No decisions found in the JSON file.")
        exit()

    # Flatten evidence list for Excel
    for d in decisions:
        if 'evidence' in d and isinstance(d['evidence'], list):
            d['evidence'] = "; ".join(d['evidence'])

    # Create DataFrame
    df = pd.DataFrame(decisions)

    # Reorder columns for better readability if they exist
    preferred_order = [
        "pair_id", "decision", "confidence", "canonical_name",
        "a_raw", "a_type",
        "b_raw", "b_type", 
        "evidence"
    ]
    # Filter only columns that exist in the dataframe
    cols = [c for c in preferred_order if c in df.columns] + [c for c in df.columns if c not in preferred_order]
    df = df[cols]

    # Write to Excel
    df.to_excel(output_excel_path, index=False)
    print(f"Successfully exported {len(df)} decisions to {output_excel_path}")

except Exception as e:
    print(f"Error converting to Excel: {e}")
