"""
Budget Excel Analysis Script
==============================
Analyzes expense and capital budget Excel files to extract:
1. Trustee (متولی) mapping for Subsystem configuration
2. Continuous Action detection (نوع ردیف)
3. Action standardization via NLP on شرح column

Usage:
    python scripts/budget_excel_analyzer.py
"""

import pandas as pd
import os
from collections import Counter
from typing import Optional, List, Tuple

# File paths
EXPENSE_BUDGET_FILE = "اعتبارات هزینه ای.xlsx"
CAPITAL_BUDGET_FILE = "تملک دارایی سرمایه ای.xlsx"

# Persian stopwords for action extraction
ACTION_STOPWORDS = {
    'پروژه', 'عملیات', 'اجرای', 'اجرا', 'انجام', 'برنامه', 'طرح',
    'و', 'از', 'به', 'در', 'که', 'این', 'را', 'با', 'برای',
    'آن', 'یک', 'تا', 'بر', 'هم', 'نیز', 'ها', 'های', 'ای',
    '-', '–', '/', '(', ')', '،', '.', ':', '؟', '!',
}


def load_excel_safe(filepath: str) -> Optional[pd.DataFrame]:
    """Load Excel file safely, trying first sheet if default fails."""
    if not os.path.exists(filepath):
        print(f"   ⚠️  File not found: {filepath}")
        return None
    
    try:
        # Try loading first sheet
        df = pd.read_excel(filepath, engine='openpyxl')
        print(f"   ✅ Loaded: {filepath} ({len(df):,} rows, {len(df.columns)} columns)")
        return df
    except Exception as e:
        print(f"   ❌ Error loading {filepath}: {e}")
        return None


def find_column(df: pd.DataFrame, keywords: List[str]) -> Optional[str]:
    """Find a column containing any of the keywords."""
    for col in df.columns:
        col_str = str(col).strip()
        for kw in keywords:
            if kw in col_str:
                return col
    return None


def analyze_trustee(df: pd.DataFrame, file_label: str) -> dict:
    """Analyze the Trustee (متولی) column."""
    print(f"\n   📊 Trustee Analysis for {file_label}:")
    print("   " + "-" * 50)
    
    trustee_col = find_column(df, ['متولی', 'متولي', 'مسئول'])
    
    if not trustee_col:
        print("   ⚠️  No 'متولی' column found!")
        print(f"   Available columns: {list(df.columns)[:10]}...")
        return {}
    
    print(f"   Found column: '{trustee_col}'")
    
    # Get value counts
    value_counts = df[trustee_col].value_counts()
    total = len(df)
    
    result = {}
    print(f"\n   {'Trustee':<40} | {'Count':>8} | {'%':>6}")
    print("   " + "-" * 60)
    for val, count in value_counts.head(15).items():
        val_str = str(val).strip()[:38] if pd.notna(val) else "(Empty)"
        pct = count / total * 100
        print(f"   {val_str:<40} | {count:>8,} | {pct:>5.1f}%")
        result[str(val) if pd.notna(val) else "Empty"] = count
    
    if len(value_counts) > 15:
        print(f"   ... and {len(value_counts) - 15} more unique values")
    
    return result


def analyze_continuous_type(df: pd.DataFrame, file_label: str) -> Tuple[Optional[str], Optional[str]]:
    """Find and analyze the row type column (looking for مستمر)."""
    print(f"\n   🔄 Continuous Action Detection for {file_label}:")
    print("   " + "-" * 50)
    
    # Look for type columns
    type_col = find_column(df, ['نوع ردیف', 'نوع', 'ردیف', 'مستمر'])
    
    if not type_col:
        # Try scanning all columns for 'مستمر' values
        for col in df.columns:
            if df[col].astype(str).str.contains('مستمر', na=False).any():
                type_col = col
                break
    
    if not type_col:
        print("   ⚠️  No row type column found!")
        print(f"   Checked columns: {list(df.columns)}")
        return None, None
    
    print(f"   Found column: '{type_col}'")
    
    value_counts = df[type_col].value_counts()
    
    print(f"\n   {'Value':<30} | {'Count':>8}")
    print("   " + "-" * 45)
    
    continuous_value = None
    for val, count in value_counts.items():
        val_str = str(val).strip()[:28] if pd.notna(val) else "(Empty)"
        print(f"   {val_str:<30} | {count:>8,}")
        
        # Detect the continuous value
        if 'مستمر' in str(val):
            continuous_value = val
    
    if continuous_value:
        print(f"\n   ✅ CONTINUOUS MARKER FOUND: '{continuous_value}'")
    else:
        print("\n   ⚠️  No 'مستمر' value detected in type column")
    
    return type_col, continuous_value


def extract_ngrams(text: str, n: int) -> List[str]:
    """Extract n-word phrases from beginning of text."""
    if not text or pd.isna(text):
        return []
    
    words = str(text).strip().split()
    # Filter stopwords
    words = [w.strip('()[]{}،.؟!:;-') for w in words if w.strip('()[]{}،.؟!:;-') not in ACTION_STOPWORDS]
    
    if len(words) < n:
        return []
    
    # Return first n words as a phrase
    return [' '.join(words[:n])]


def analyze_actions(df: pd.DataFrame, file_label: str, 
                   type_col: Optional[str] = None, 
                   continuous_value: Optional[str] = None) -> dict:
    """Analyze the شرح column for action standardization."""
    print(f"\n   📝 Action Standardization for {file_label}:")
    print("   " + "-" * 50)
    
    desc_col = find_column(df, ['شرح ردیف', 'شرح', 'عنوان', 'توضیحات'])
    
    if not desc_col:
        print("   ⚠️  No description column found!")
        return {}
    
    print(f"   Found column: '{desc_col}'")
    
    # Filter to continuous rows if possible
    analysis_df = df
    if type_col and continuous_value:
        analysis_df = df[df[type_col] == continuous_value]
        print(f"   Filtering to CONTINUOUS rows only: {len(analysis_df):,} rows")
    else:
        print(f"   Analyzing ALL rows: {len(analysis_df):,} rows")
    
    if len(analysis_df) == 0:
        print("   ⚠️  No rows to analyze after filtering!")
        return {}
    
    # Extract 2-word and 3-word phrases
    two_word_phrases = Counter()
    three_word_phrases = Counter()
    
    for desc in analysis_df[desc_col].dropna():
        for phrase in extract_ngrams(desc, 2):
            if phrase:
                two_word_phrases[phrase] += 1
        for phrase in extract_ngrams(desc, 3):
            if phrase:
                three_word_phrases[phrase] += 1
    
    # Print results
    print(f"\n   Top 10 Two-Word Action Phrases:")
    print("   " + "-" * 45)
    for phrase, count in two_word_phrases.most_common(10):
        print(f"   {phrase:<35} | {count:>6}")
    
    print(f"\n   Top 10 Three-Word Action Phrases:")
    print("   " + "-" * 55)
    for phrase, count in three_word_phrases.most_common(10):
        print(f"   {phrase:<45} | {count:>6}")
    
    return {
        'two_word': dict(two_word_phrases.most_common(10)),
        'three_word': dict(three_word_phrases.most_common(10))
    }


def print_column_inventory(df: pd.DataFrame, file_label: str):
    """Print all columns in the DataFrame for reference."""
    print(f"\n   📋 Column Inventory for {file_label}:")
    print("   " + "-" * 50)
    for i, col in enumerate(df.columns, 1):
        sample = df[col].dropna().head(1).values
        sample_str = str(sample[0])[:30] if len(sample) > 0 else "(no data)"
        print(f"   {i:2d}. {str(col)[:25]:<25} | Sample: {sample_str}")


def run_analysis():
    """Main analysis function."""
    print("=" * 70)
    print("📊 BUDGET EXCEL ANALYSIS REPORT")
    print("=" * 70)
    
    files = [
        (EXPENSE_BUDGET_FILE, "Expense Budget (هزینه‌ای)"),
        (CAPITAL_BUDGET_FILE, "Capital Budget (سرمایه‌ای)")
    ]
    
    all_results = {}
    
    for filepath, label in files:
        print(f"\n{'═' * 70}")
        print(f"📁 FILE: {label}")
        print(f"   Path: {filepath}")
        print("═" * 70)
        
        df = load_excel_safe(filepath)
        if df is None:
            continue
        
        # Column inventory
        print_column_inventory(df, label)
        
        # Analysis 1: Trustee Map
        trustee_data = analyze_trustee(df, label)
        
        # Analysis 2: Continuous Type Detection
        type_col, continuous_value = analyze_continuous_type(df, label)
        
        # Analysis 3: Action Standardization
        action_data = analyze_actions(df, label, type_col, continuous_value)
        
        all_results[label] = {
            'trustees': trustee_data,
            'type_column': type_col,
            'continuous_value': continuous_value,
            'actions': action_data
        }
    
    # Summary
    print("\n" + "=" * 70)
    print("📋 SUMMARY & RECOMMENDATIONS")
    print("=" * 70)
    
    for label, data in all_results.items():
        print(f"\n{label}:")
        if data.get('continuous_value'):
            print(f"   ✅ Continuous filter: Column '{data['type_column']}' = '{data['continuous_value']}'")
        else:
            print(f"   ⚠️  No continuous action column detected (may need color reading)")
        
        if data.get('trustees'):
            print(f"   📊 Found {len(data['trustees'])} unique trustees")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    run_analysis()
