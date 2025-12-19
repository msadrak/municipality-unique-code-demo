"""
Excel Forensics Analysis Script for Hesabdary Information.xlsx
Performs comprehensive profiling of all sheets.
"""
import pandas as pd
import numpy as np
import re
import json
import sys
import os

# Add parent path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

EXCEL_FILE = "Hesabdary Information.xlsx"

def persian_to_english_digits(text):
    """Convert Persian/Arabic digits to English."""
    if pd.isna(text):
        return text
    persian_digits = '۰۱۲۳۴۵۶۷۸۹'
    arabic_digits = '٠١٢٣٤٥٦٧٨٩'
    result = str(text)
    for i, d in enumerate(persian_digits):
        result = result.replace(d, str(i))
    for i, d in enumerate(arabic_digits):
        result = result.replace(d, str(i))
    return result

def has_mixed_digits(text):
    """Check if text contains both Persian and English digits."""
    if pd.isna(text):
        return False
    text = str(text)
    has_english = bool(re.search(r'[0-9]', text))
    has_persian = bool(re.search(r'[۰-۹٠-٩]', text))
    return has_english and has_persian

def detect_leading_zero_issue(val):
    """Check if value might have lost leading zeros."""
    if pd.isna(val):
        return False
    s = str(val)
    # Check if it's a code-like value that might have lost zeros
    if s.endswith('.0'):
        num = int(float(s))
        if 1 <= num <= 20:  # Zone/region codes range
            return True
    return False

def analyze_sheet(sheet_name, df):
    """Analyze a single sheet and return analysis dict."""
    print(f"\n{'='*60}")
    print(f"Sheet: {sheet_name}")
    print(f"{'='*60}")
    
    analysis = {
        'sheet_name': sheet_name,
        'row_count': len(df),
        'col_count': len(df.columns),
        'columns': [],
        'issues': [],
        'sample_rows': []
    }
    
    print(f"Rows: {len(df)}, Columns: {len(df.columns)}")
    
    # Check for merged cells indicator (multi-row index)
    if isinstance(df.columns, pd.MultiIndex):
        analysis['issues'].append("Multi-level header detected (merged cells)")
    
    # Column analysis
    print("\nColumn Analysis:")
    print("-" * 40)
    
    for col in df.columns:
        col_data = df[col]
        null_count = col_data.isna().sum()
        null_rate = null_count / len(df) * 100 if len(df) > 0 else 0
        
        # Get non-null values for analysis
        non_null = col_data.dropna()
        
        # Detect data type
        dtype = str(col_data.dtype)
        if non_null.empty:
            detected_type = "empty"
        elif pd.api.types.is_numeric_dtype(col_data):
            if all(non_null.apply(lambda x: float(x) == int(float(x)) if pd.notna(x) else True)):
                detected_type = "integer"
            else:
                detected_type = "float"
        else:
            non_null_str = non_null.astype(str)
            if all(non_null_str.str.match(r'^\d+$')):
                detected_type = "numeric_string"
            elif all(non_null_str.str.match(r'^\d{4}/\d{2}/\d{2}$')):
                detected_type = "date_string"
            else:
                detected_type = "text"
        
        # Unique values
        unique_count = non_null.nunique()
        unique_rate = unique_count / len(non_null) * 100 if len(non_null) > 0 else 0
        
        # Key candidate detection
        is_unique_key = unique_count == len(non_null) and null_count == 0
        
        col_info = {
            'name': str(col),
            'dtype': dtype,
            'detected_type': detected_type,
            'null_count': int(null_count),
            'null_rate': round(null_rate, 2),
            'unique_count': int(unique_count),
            'unique_rate': round(unique_rate, 2),
            'is_potential_key': is_unique_key
        }
        
        # Check for Persian digits
        persian_digit_count = 0
        mixed_digit_count = 0
        leading_zero_issue_count = 0
        
        for val in non_null.head(1000):  # Sample first 1000 for performance
            if has_mixed_digits(val):
                mixed_digit_count += 1
            if detect_leading_zero_issue(val):
                leading_zero_issue_count += 1
            if pd.notna(val) and re.search(r'[۰-۹٠-٩]', str(val)):
                persian_digit_count += 1
        
        if persian_digit_count > 0:
            col_info['persian_digits'] = persian_digit_count
            analysis['issues'].append(f"Column '{col}': Contains {persian_digit_count} values with Persian digits")
        
        if mixed_digit_count > 0:
            col_info['mixed_digits'] = mixed_digit_count
            analysis['issues'].append(f"Column '{col}': Contains {mixed_digit_count} values with mixed Persian/English digits")
        
        if leading_zero_issue_count > 0:
            col_info['leading_zero_issues'] = leading_zero_issue_count
            analysis['issues'].append(f"Column '{col}': Potential leading zero loss in {leading_zero_issue_count} values")
        
        # Sample values
        sample_vals = non_null.head(5).tolist()
        col_info['sample_values'] = [str(v)[:50] for v in sample_vals]
        
        analysis['columns'].append(col_info)
        
        key_indicator = " 🔑" if is_unique_key else ""
        print(f"  {col}: {detected_type} | nulls: {null_rate:.1f}% | uniques: {unique_count}{key_indicator}")
    
    # Check for duplicates based on potential key columns
    if len(df) > 0:
        # Find code-like columns
        code_cols = [c for c in df.columns if any(kw in str(c).lower() for kw in ['code', 'کد', 'شماره', 'id'])]
        if code_cols:
            for code_col in code_cols:
                dup_count = len(df) - df[code_col].nunique()
                if dup_count > 0 and df[code_col].notna().sum() > 0:
                    analysis['issues'].append(f"Column '{code_col}': {dup_count} duplicate values detected")
    
    # Check for inconsistent formats in code columns
    for col in df.columns:
        col_str = str(col).lower()
        if any(kw in col_str for kw in ['zone', 'منطقه', 'code', 'کد']):
            formats = set()
            for val in df[col].dropna().head(100):
                s = str(val).strip()
                if s.replace('.0', '').isdigit():
                    formats.add('numeric')
                elif s.startswith('0') and s[1:].isdigit():
                    formats.add('zero_padded')
                elif re.match(r'منطقه\s*\d+', s):
                    formats.add('text_with_number')
                else:
                    formats.add('other')
            if len(formats) > 1:
                analysis['issues'].append(f"Column '{col}': Inconsistent code formats: {formats}")
    
    # Sample rows (sanitized)
    if len(df) > 0:
        sample_df = df.head(10)
        analysis['sample_rows'] = sample_df.apply(
            lambda row: {str(k): str(v)[:100] if pd.notna(v) else None for k, v in row.items()}, 
            axis=1
        ).tolist()
    
    return analysis

def main():
    print("="*60)
    print("EXCEL FORENSICS ANALYSIS")
    print(f"File: {EXCEL_FILE}")
    print("="*60)
    
    # Load all sheets
    print("\nLoading Excel file (this may take a while for large files)...")
    try:
        xls = pd.ExcelFile(EXCEL_FILE)
        sheet_names = xls.sheet_names
        print(f"\nFound {len(sheet_names)} sheets:")
        for i, name in enumerate(sheet_names):
            print(f"  {i+1}. {name}")
    except Exception as e:
        print(f"ERROR loading file: {e}")
        return
    
    all_analyses = []
    
    for sheet_name in sheet_names:
        try:
            df = pd.read_excel(EXCEL_FILE, sheet_name=sheet_name)
            analysis = analyze_sheet(sheet_name, df)
            all_analyses.append(analysis)
        except Exception as e:
            print(f"\nERROR reading sheet '{sheet_name}': {e}")
            all_analyses.append({
                'sheet_name': sheet_name,
                'error': str(e)
            })
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    total_rows = sum(a.get('row_count', 0) for a in all_analyses)
    print(f"Total sheets: {len(sheet_names)}")
    print(f"Total rows (all sheets): {total_rows}")
    
    # All issues
    print("\nAll Issues Found:")
    print("-" * 40)
    issue_count = 0
    for a in all_analyses:
        for issue in a.get('issues', []):
            print(f"  [{a['sheet_name']}] {issue}")
            issue_count += 1
    if issue_count == 0:
        print("  No critical issues detected.")
    
    # Save full analysis to JSON
    output_file = "scripts/hesabdary_analysis.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_analyses, f, ensure_ascii=False, indent=2, default=str)
    print(f"\nFull analysis saved to: {output_file}")
    
    # Print key candidates per sheet
    print("\n" + "="*60)
    print("POTENTIAL KEY COLUMNS")
    print("="*60)
    for a in all_analyses:
        if 'columns' in a:
            keys = [c['name'] for c in a['columns'] if c.get('is_potential_key')]
            if keys:
                print(f"  {a['sheet_name']}: {', '.join(keys)}")

if __name__ == "__main__":
    main()
