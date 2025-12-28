"""
Cost Center Forensics Script
=============================
Analyzes the CostCenterRef table to reveal the *nature* of the data.

This helps detect semantic errors, such as accidentally importing:
- Personnel list (آقای، خانم)
- Contractors list (شرکت، موسسه)
- Instead of real Cost Centers (پروژه، احداث)

Usage:
    python scripts/cost_center_forensics.py
"""

import sys
import os
import random
from collections import Counter

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app import models

# Persian stop words to exclude from keyword analysis
PERSIAN_STOP_WORDS = {
    'و', 'از', 'به', 'در', 'که', 'این', 'را', 'با', 'است', 'برای',
    'آن', 'یک', 'تا', 'بر', 'هم', 'نیز', 'ها', 'های', 'ای', 'می',
    'شد', 'شده', 'کرد', 'دارد', 'بود', 'یا', 'هر', 'باید', 'اما',
    'کنند', 'شود', 'مورد', 'بین', 'پس', 'اگر', 'همه', 'چه', 'خود',
    '-', '–', '/', '(', ')', '،', '.', ':', '؟', '!', '"', "'",
}


def get_code_length_distribution(codes: list) -> dict:
    """Calculate distribution of code lengths."""
    length_counts = Counter(len(str(code).strip()) for code in codes if code)
    total = sum(length_counts.values())
    distribution = {}
    for length, count in sorted(length_counts.items()):
        percentage = (count / total * 100) if total > 0 else 0
        distribution[length] = {
            'count': count,
            'percentage': round(percentage, 1)
        }
    return distribution


def extract_keywords(titles: list, top_n: int = 10) -> list:
    """Extract top N most frequent words from titles, excluding stop words."""
    word_counter = Counter()
    
    for title in titles:
        if not title:
            continue
        # Split by whitespace and common delimiters
        words = str(title).replace('-', ' ').replace('–', ' ').replace('/', ' ').split()
        for word in words:
            word = word.strip().strip('()[]{}،.؟!:;')
            if word and word not in PERSIAN_STOP_WORDS and len(word) > 1:
                word_counter[word] += 1
    
    return word_counter.most_common(top_n)


def interpret_keywords(keywords: list) -> str:
    """Provide interpretation based on detected keywords."""
    keyword_text = ' '.join(word for word, _ in keywords).lower()
    
    personnel_indicators = ['آقای', 'خانم', 'کارمند', 'پرسنل', 'نیرو', 'استخدام']
    contractor_indicators = ['شرکت', 'موسسه', 'پیمانکار', 'مناقصه', 'قرارداد']
    cost_center_indicators = ['پروژه', 'احداث', 'عمرانی', 'تعمیر', 'نگهداری', 'ساخت', 'اجرا']
    
    personnel_score = sum(1 for ind in personnel_indicators if ind in keyword_text)
    contractor_score = sum(1 for ind in contractor_indicators if ind in keyword_text)
    cost_center_score = sum(1 for ind in cost_center_indicators if ind in keyword_text)
    
    interpretations = []
    if personnel_score > 0:
        interpretations.append(f"⚠️  PERSONNEL DATA DETECTED (score: {personnel_score})")
    if contractor_score > 0:
        interpretations.append(f"⚠️  CONTRACTOR DATA DETECTED (score: {contractor_score})")
    if cost_center_score > 0:
        interpretations.append(f"✅  COST CENTER DATA DETECTED (score: {cost_center_score})")
    
    if not interpretations:
        return "⚠️  UNABLE TO CLASSIFY - Manual inspection required"
    
    return '\n'.join(interpretations)


def run_forensics():
    """Main forensics function."""
    print("=" * 70)
    print("🔍 COST CENTER FORENSICS REPORT")
    print("=" * 70)
    
    db = SessionLocal()
    
    try:
        # Fetch all data
        all_records = db.query(models.CostCenterRef).all()
        
        if not all_records:
            print("\n❌ NO DATA FOUND in CostCenterRef table!")
            print("   The table is empty. Please check your import process.")
            return
        
        codes = [r.code for r in all_records]
        titles = [r.title for r in all_records]
        
        # ============================================================
        # 1. STATISTICAL SUMMARY
        # ============================================================
        print("\n" + "─" * 70)
        print("📊 1. STATISTICAL SUMMARY")
        print("─" * 70)
        
        print(f"\n   Total Rows: {len(all_records):,}")
        
        # Code length distribution
        print("\n   Code Length Distribution:")
        code_lengths = get_code_length_distribution(codes)
        for length, stats in code_lengths.items():
            bar = "█" * int(stats['percentage'] / 5)  # Simple visual bar
            print(f"      {length:2d} digits: {stats['count']:5,} rows ({stats['percentage']:5.1f}%) {bar}")
        
        # ============================================================
        # 2. KEYWORD EXTRACTION & ANALYSIS
        # ============================================================
        print("\n" + "─" * 70)
        print("🔤 2. KEYWORD EXTRACTION (Top 10 Words)")
        print("─" * 70)
        
        keywords = extract_keywords(titles, top_n=10)
        print("\n   Most Frequent Words in 'title' Column:")
        for i, (word, count) in enumerate(keywords, 1):
            bar = "█" * min(int(count / 3), 30)  # Cap bar length
            print(f"      {i:2d}. '{word}' - {count:,} occurrences {bar}")
        
        # Interpretation
        print("\n   📋 INTERPRETATION:")
        interpretation = interpret_keywords(keywords)
        for line in interpretation.split('\n'):
            print(f"      {line}")
        
        # ============================================================
        # 3. RANDOM SAMPLING
        # ============================================================
        print("\n" + "─" * 70)
        print("🎲 3. RANDOM SAMPLE (15 Records)")
        print("─" * 70)
        
        sample_size = min(15, len(all_records))
        random_sample = random.sample(all_records, sample_size)
        
        print("\n   Sample of actual data:")
        print("   " + "-" * 66)
        print(f"   {'Code':<15} | {'Title':<50}")
        print("   " + "-" * 66)
        for record in random_sample:
            code = str(record.code or '').strip()[:14]
            title = str(record.title or '').strip()[:48]
            print(f"   {code:<15} | {title:<50}")
        print("   " + "-" * 66)
        
        # ============================================================
        # FINAL VERDICT
        # ============================================================
        print("\n" + "=" * 70)
        print("📋 FINAL VERDICT")
        print("=" * 70)
        
        # Simple heuristics for verdict
        has_single_digit_codes = any(L < 3 for L in code_lengths.keys())
        has_long_codes = any(L > 10 for L in code_lengths.keys())
        multiple_code_lengths = len(code_lengths) > 2
        
        issues = []
        if multiple_code_lengths:
            issues.append("Multiple code length patterns detected (inconsistent data sources)")
        if has_single_digit_codes:
            issues.append("Very short codes detected (potential data quality issue)")
        if has_long_codes:
            issues.append("Very long codes detected (may indicate wrong data type)")
        
        if issues:
            print("\n   ⚠️  POTENTIAL ISSUES DETECTED:")
            for issue in issues:
                print(f"      → {issue}")
        else:
            print("\n   ✅  No obvious structural issues detected.")
        
        print("\n   💡 RECOMMENDATION: Review the random sample above to verify")
        print("      the data represents actual Cost Centers.")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    run_forensics()
