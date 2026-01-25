"""
اسکریپت Import بودجه
=====================

این اسکریپت برای import داده‌های بودجه از فایل اکسل استفاده می‌شود.

نحوه استفاده:
    python import_budget_new.py path/to/budget.xlsx

یا در حالت پیش‌نمایش:
    python import_budget_new.py path/to/budget.xlsx --preview
"""

import sys
import argparse
from app.adapters import BudgetAdapter


def main():
    parser = argparse.ArgumentParser(description="Import بودجه از اکسل")
    parser.add_argument("file", help="مسیر فایل اکسل")
    parser.add_argument("--sheet", "-s", help="نام شیت", default=None)
    parser.add_argument("--preview", "-p", action="store_true", help="فقط پیش‌نمایش")
    parser.add_argument("--limit", "-l", type=int, default=10, help="تعداد سطرهای پیش‌نمایش")
    
    args = parser.parse_args()
    
    print(f"\n📂 فایل: {args.file}")
    print("-" * 50)
    
    adapter = BudgetAdapter(args.file, sheet_name=args.sheet)
    
    if args.preview:
        print("\n🔍 حالت پیش‌نمایش:")
        items = adapter.preview(limit=args.limit)
        
        if not items:
            print("❌ هیچ آیتم معتبری پیدا نشد!")
            if adapter.errors:
                print("\nخطاها:")
                for err in adapter.errors:
                    print(f"  - {err}")
            return
        
        print(f"\nستون‌های شناسایی شده: {adapter.column_mapping}")
        print(f"\nتعداد آیتم‌های معتبر: {len(items)}")
        print("\nنمونه داده‌ها:")
        
        for i, item in enumerate(items[:args.limit], 1):
            print(f"\n  [{i}] کد: {item['budget_code']}")
            print(f"      شرح: {item['description'][:50]}..." if len(item.get('description', '')) > 50 else f"      شرح: {item.get('description', '-')}")
            print(f"      مصوب: {item.get('allocated_1403', 0):,.0f} ریال")
    else:
        print("\n⚙️ در حال import...")
        results = adapter.import_to_db(dry_run=False)
        
        print(f"\n✅ نتایج:")
        print(f"   - موفق: {results['success']}")
        print(f"   - بروزرسانی: {results['updated']}")
        print(f"   - رد شده: {results['skipped']}")
        print(f"   - خطا: {results['failed']}")
        
        if results['errors']:
            print("\n❌ خطاها:")
            for err in results['errors'][:5]:
                print(f"   - {err}")


if __name__ == "__main__":
    main()
