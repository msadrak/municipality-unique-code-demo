# -*- coding: utf-8 -*-
import sys
import os
import io

# Add parent dir to path to find app module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set encoding for Windows console
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.database import SessionLocal
from app import models

def main():
    db = SessionLocal()
    
    print("=== Civil Section (Supervision / نظارت ابنیه) Data ===\n")
    
    # OrgUnit 9 is the Civil/Supervision section
    budget_rows = db.query(models.BudgetRow).filter(models.BudgetRow.org_unit_id == 9).all()
    
    if not budget_rows:
        print("No budget rows found for Civil Section (OrgUnit 9).")
        return

    print(f"Found {len(budget_rows)} Budget Rows:\n")
    
    for br in budget_rows:
        activity = db.query(models.SubsystemActivity).filter(models.SubsystemActivity.id == br.activity_id).first()
        
        print(f"--------------------------------------------------")
        print(f"Activity: {activity.title}")
        print(f"  > Code: {activity.code}")
        print(f"  > ID:   {activity.id}")
        print(f"\nBudget Row:")
        print(f"  > Description: {br.description}")
        try:
            # handle case where budget_coding relationship might be used or direct code
            code = br.budget_coding.code if hasattr(br, 'budget_coding') and br.budget_coding else 'N/A'
        except:
             code = "N/A"
        
        print(f"  > Budget Code: {code}") 
        print(f"  > Amount:      {br.approved_amount:,.0f} Rials")
        print(f"--------------------------------------------------\n")

if __name__ == "__main__":
    main()
