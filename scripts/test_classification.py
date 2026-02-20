"""
Region 14 Classification Tester
================================
Standalone utility to test the keyword classification logic
without touching the database.

Usage:
    python test_classification.py                    # Interactive mode
    python test_classification.py --test "text"      # Test specific text
    python test_classification.py --analyze file.csv # Analyze CSV file
"""
import sys
import io
from pathlib import Path
from typing import Dict, List
from collections import defaultdict

# Fix encoding for Windows console
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except:
        pass

# Keywords dictionary (same as main script)
SECTION_KEYWORDS = {
    "ROAD_ASPHALT": [
        "آسفالت", "روکش", "معابر", "پیاده", "جدول", "کانیو", 
        "لکه", "ترمیم حفاری", "قیر", "تراش", "زیرسازی", "خیابان",
        "کوچه", "پیاده‌رو", "جداول", "بتن"
    ],
    "ELECTRICAL": [
        "روشنایی", "برق", "نور", "چراغ", "LED", "پروژکتور", 
        "کابل", "تاسیسات برقی", "لامپ", "سیم", "الکتریکی"
    ],
    "MECHANICAL": [
        "آبیاری", "چاه", "پمپ", "منبع", "هیدرانت", "آبنما", 
        "تاسیسات مکانیکی", "لوله", "مخزن", "سپتیک", "فاضلاب",
        "آب", "شبکه", "تصفیه"
    ],
    "SUPERVISION": [
        "احداث", "ساختمان", "ابنیه", "پل", "سازه", "دیوار", 
        "سوله", "اسکلت", "فرهنگی", "ورزشی", "سرویس بهداشتی",
        "بتن", "آرماتور", "فونداسیون", "سقف", "ساخت"
    ],
    "TECHNICAL": [
        "نظارت", "طراحی", "نقشه", "مشاوره", "آزمایشگاه", 
        "مطالعات", "کنترل", "بازرسی", "مدیریت", "هماهنگی"
    ]
}

SECTION_NAMES = {
    "ROAD_ASPHALT": "نظارت راه و آسفالت",
    "ELECTRICAL": "تاسیسات برق",
    "MECHANICAL": "تاسیسات مکانیکی",
    "SUPERVISION": "نظارت ابنیه",
    "TECHNICAL": "نظام فنی و عمومی"
}


def classify_text(text: str) -> tuple:
    """
    Classify text and return (section_key, score, matched_keywords).
    
    Returns:
        tuple: (section_key, score, list of matched keywords)
    """
    text_lower = text.lower()
    
    scores = {}
    matches = {}
    
    for section_key, keywords in SECTION_KEYWORDS.items():
        score = 0
        matched = []
        for keyword in keywords:
            if keyword in text_lower:
                score += 1
                matched.append(keyword)
        scores[section_key] = score
        matches[section_key] = matched
    
    max_score = max(scores.values())
    
    if max_score == 0:
        return "TECHNICAL", 0, []
    
    winner = max(scores.items(), key=lambda x: x[1])[0]
    return winner, scores[winner], matches[winner]


def print_classification_result(text: str, budget_code: str = ""):
    """Print detailed classification results."""
    print("\n" + "=" * 80)
    print("CLASSIFICATION TEST")
    print("=" * 80)
    
    if budget_code:
        print(f"Budget Code: {budget_code}")
    print(f"Text: {text}")
    print()
    
    # Classify
    section_key, score, matched = classify_text(text)
    
    # Show all scores
    print("Score by Section:")
    print("-" * 80)
    
    for key in SECTION_KEYWORDS.keys():
        section_name = SECTION_NAMES[key]
        test_score = classify_text(text)[0] == key
        
        # Calculate score for this section
        text_lower = text.lower()
        section_score = sum(1 for kw in SECTION_KEYWORDS[key] if kw in text_lower)
        section_matches = [kw for kw in SECTION_KEYWORDS[key] if kw in text_lower]
        
        status = "✓ WINNER" if key == section_key else ""
        
        print(f"  {section_name}: {section_score} points {status}")
        if section_matches:
            print(f"    Matched: {', '.join(section_matches)}")
    
    print()
    print("-" * 80)
    
    if score == 0:
        print(f"RESULT: {SECTION_NAMES[section_key]} (FALLBACK - no keywords matched)")
    else:
        print(f"RESULT: {SECTION_NAMES[section_key]} ({score} keywords matched)")
        print(f"Matched Keywords: {', '.join(matched)}")
    
    print("=" * 80)


def interactive_mode():
    """Run in interactive mode."""
    print("\n" + "=" * 80)
    print("REGION 14 CLASSIFICATION TESTER - INTERACTIVE MODE")
    print("=" * 80)
    print("\nTest budget descriptions to see which section they'll be assigned to.")
    print("Type 'quit' or 'exit' to stop.\n")
    
    while True:
        try:
            text = input("Enter budget description (or 'quit'): ").strip()
            
            if text.lower() in ['quit', 'exit', 'q']:
                print("\nExiting...")
                break
            
            if not text:
                continue
            
            print_classification_result(text)
        
        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except EOFError:
            break


def analyze_csv(csv_path: Path):
    """Analyze a CSV file and show classification distribution."""
    import csv
    
    print("\n" + "=" * 80)
    print("CSV FILE ANALYSIS")
    print("=" * 80)
    print(f"File: {csv_path}")
    print()
    
    if not csv_path.exists():
        print(f"ERROR: File not found: {csv_path}")
        return
    
    # Read CSV
    rows = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    
    print(f"Total rows: {len(rows)}")
    print()
    
    # Classify each row
    distribution = defaultdict(list)
    fallback_count = 0
    
    for idx, row in enumerate(rows):
        # Try to find description column
        description = None
        for key in row.keys():
            if key in ['شرح ردیف', 'description', 'شرح']:
                description = row[key]
                break
        
        if not description:
            continue
        
        budget_code = None
        for key in row.keys():
            if key in ['کد بودجه', 'budget_code', 'کد']:
                budget_code = row[key]
                break
        
        # Classify
        section_key, score, matched = classify_text(description)
        
        distribution[section_key].append({
            'index': idx,
            'budget_code': budget_code,
            'description': description,
            'score': score,
            'matched': matched
        })
        
        if score == 0:
            fallback_count += 1
    
    # Print distribution
    print("=" * 80)
    print("CLASSIFICATION DISTRIBUTION")
    print("=" * 80)
    print()
    
    for section_key in SECTION_KEYWORDS.keys():
        count = len(distribution[section_key])
        percentage = (count / len(rows) * 100) if rows else 0
        section_name = SECTION_NAMES[section_key]
        
        print(f"{section_name}: {count} items ({percentage:.1f}%)")
        
        # Show first 3 examples
        if distribution[section_key]:
            print("  Examples:")
            for item in distribution[section_key][:3]:
                code = item['budget_code'] or 'N/A'
                desc = item['description'][:60] + "..." if len(item['description']) > 60 else item['description']
                print(f"    - [{code}] {desc}")
                if item['matched']:
                    print(f"      Keywords: {', '.join(item['matched'][:5])}")
        print()
    
    print("-" * 80)
    print(f"Fallback assignments (no keywords): {fallback_count}")
    print()
    
    if fallback_count > 0:
        print("Items with no keyword matches:")
        for item in distribution['TECHNICAL'][:5]:
            if item['score'] == 0:
                code = item['budget_code'] or 'N/A'
                print(f"  - [{code}] {item['description']}")
        
        if fallback_count > 5:
            print(f"  ... and {fallback_count - 5} more")
    
    print("=" * 80)


def run_examples():
    """Run example classifications."""
    examples = [
        ("11020401", "آسفالت و روکش معابر اصلی منطقه"),
        ("11020402", "تعمیر و نگهداری روشنایی معابر و پارک‌ها"),
        ("11020403", "تاسیسات مکانیکی و آبیاری فضای سبز"),
        ("11020404", "احداث سرویس بهداشتی عمومی"),
        ("11020405", "نظارت و مطالعات فنی پروژه‌های عمرانی"),
        ("11020406", "خرید تجهیزات اداری"),  # Fallback example
    ]
    
    print("\n" + "=" * 80)
    print("EXAMPLE CLASSIFICATIONS")
    print("=" * 80)
    
    for code, desc in examples:
        section_key, score, matched = classify_text(desc)
        section_name = SECTION_NAMES[section_key]
        
        print()
        print(f"Budget: {code}")
        print(f"Description: {desc}")
        print(f"→ Assigned to: {section_name}")
        if score > 0:
            print(f"  Matched keywords: {', '.join(matched)}")
        else:
            print(f"  (Fallback - no keywords matched)")
        print("-" * 80)


def print_keyword_reference():
    """Print keyword reference table."""
    print("\n" + "=" * 80)
    print("KEYWORD REFERENCE")
    print("=" * 80)
    print()
    
    for section_key, keywords in SECTION_KEYWORDS.items():
        section_name = SECTION_NAMES[section_key]
        print(f"{section_name}:")
        print(f"  Keywords ({len(keywords)}): {', '.join(keywords)}")
        print()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test Region 14 Classification Logic",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python test_classification.py
  
  # Test specific text
  python test_classification.py --test "آسفالت و روکش معابر"
  
  # Analyze CSV file
  python test_classification.py --analyze region14_civil_items.csv
  
  # Show example classifications
  python test_classification.py --examples
  
  # Show keyword reference
  python test_classification.py --keywords
        """
    )
    
    parser.add_argument(
        '--test',
        type=str,
        help='Test a specific text string'
    )
    
    parser.add_argument(
        '--analyze',
        type=str,
        help='Analyze a CSV file'
    )
    
    parser.add_argument(
        '--examples',
        action='store_true',
        help='Show example classifications'
    )
    
    parser.add_argument(
        '--keywords',
        action='store_true',
        help='Show keyword reference'
    )
    
    args = parser.parse_args()
    
    if args.test:
        print_classification_result(args.test)
    
    elif args.analyze:
        csv_path = Path(args.analyze)
        analyze_csv(csv_path)
    
    elif args.examples:
        run_examples()
    
    elif args.keywords:
        print_keyword_reference()
    
    else:
        # Interactive mode
        interactive_mode()


if __name__ == "__main__":
    main()
