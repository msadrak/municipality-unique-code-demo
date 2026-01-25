import pandas as pd
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app import models

# Ensure tables exist
models.Base.metadata.create_all(bind=engine)

def import_data():
    file_path = "_شهرداری مرکزی گزارش دفتر مرکزی1403.xlsx"
    print(f"Reading {file_path}...")
    
    # Read Excel file
    # Using openpyxl engine for .xlsx files
    try:
        df = pd.read_excel(file_path, engine='openpyxl')
        print("Columns found:", df.columns.tolist())
        
        # Filter out rows where Budget Code is null or 'NULL'
        # Column is 'BodgetNo' based on analysis
        budget_col = 'BodgetNo'
        
        if budget_col in df.columns:
            print(f"Filtering nulls in column: {budget_col}")
            initial_count = len(df)
            # Filter out actual NaNs and string 'NULL'
            df = df[df[budget_col].notna()]
            df = df[df[budget_col].astype(str).str.upper() != 'NULL']
            print(f"Filtered {initial_count - len(df)} rows with null/NULL {budget_col}. Remaining: {len(df)}")
        else:
            print(f"WARNING: Column {budget_col} not found. Available: {df.columns.tolist()}")
            
    except Exception as e:
        print(f"Error reading Excel: {e}")
        return

    print("Data loaded into DataFrame. Starting import...")
    
    db = SessionLocal()
    
    try:
        # 1. Extract and Seed Reference Data
        print("Extracting reference data...")
        
        # Budgets
        unique_budgets = df['BodgetNo'].dropna().unique()
        print(f"Found {len(unique_budgets)} unique budgets.")
        for b_code in unique_budgets:
            b_code_str = str(b_code)
            if b_code_str.upper() == 'NULL': continue
            
            exists = db.query(models.BudgetRef).filter_by(budget_code=b_code_str, zone_raw='20').first()
            if not exists:
                db.add(models.BudgetRef(
                    zone_raw='20',
                    budget_code=b_code_str,
                    title=f"Budget {b_code_str}", # No title in file
                    row_type='Current' # Default
                ))
        
        # Cost Centers (using RadJNam as proxy for now, or TitJNam)
        # User asked for Cost Center. Let's use RadJNam (Beneficiary) as Cost Center title for demo
        unique_costs = df['RadJNam'].dropna().unique()
        print(f"Found {len(unique_costs)} unique cost centers.")
        for i, c_title in enumerate(unique_costs):
            c_title_str = str(c_title).strip()
            if c_title_str.upper() == 'NULL': continue
            
            # Generate sequential code
            code = f"CC-{i+1:04d}"
            
            # We check if title exists
            exists = db.query(models.CostCenterRef).filter_by(title=c_title_str).first()
            if not exists:
                db.add(models.CostCenterRef(
                    code=code,
                    title=c_title_str
                ))

        # Financial Events (TypDesc)
        unique_events = df['TypDesc'].dropna().unique()
        print(f"Found {len(unique_events)} unique events.")
        for i, e_title in enumerate(unique_events):
            e_title_str = str(e_title).strip()
            if e_title_str.upper() == 'NULL': continue
            
            # Generate sequential code
            code = f"EVT-{i+1:03d}"
            
            exists = db.query(models.FinancialEventRef).filter_by(title=e_title_str).first()
            if not exists:
                db.add(models.FinancialEventRef(
                    code=code,
                    title=e_title_str
                ))
        
        db.commit()
        print("Reference data seeded.")

        # 2. Import Documents
        print("Clearing existing documents...")
        db.query(models.FinancialDocument).delete()
        db.commit()

        count = 0
        for index, row in df.iterrows():
            # Extract fields based on new file columns
            # AreaNo, DocNo, TitJNam, RadJNam, FinYear
            
            zone_code = str(row.get('AreaNo', ''))
            doc_number = row.get('DocNo', 0)
            
            # Description
            desc_parts = []
            if pd.notna(row.get('TitJNam')) and str(row.get('TitJNam')) != 'NULL':
                desc_parts.append(str(row.get('TitJNam')))
            if pd.notna(row.get('TypDesc')) and str(row.get('TypDesc')) != 'NULL':
                desc_parts.append(str(row.get('TypDesc')))
            description = " - ".join(desc_parts)
            
            # Beneficiary
            raw_ben = str(row.get('RadJNam', ''))
            beneficiary = raw_ben if raw_ben != 'NULL' else ''
            
            # Amount
            debit = str(row.get('DebitAmnt', '0'))
            credit = str(row.get('CreditAmnt', '0'))
            amount = debit if float(debit) > 0 else credit
            
            budget_code = str(row.get('BodgetNo', ''))
            if budget_code.upper() == 'NULL': budget_code = None

            # Create record
            doc = models.FinancialDocument(
                zone_code=zone_code,
                doc_number=doc_number,
                description=description[:500],
                beneficiary=beneficiary,
                amount=amount,
                debit=debit,
                credit=credit,
                budget_code=budget_code,
                date_str=str(row.get('FinYear', '1403')),
                
                # New Columns for Test Mode
                rad_code=str(row.get('RadJNo')) if pd.notna(row.get('RadJNo')) else None,
                tit_code=str(row.get('TitTNo')) if pd.notna(row.get('TitTNo')) else None,
                tit_title=str(row.get('TitTNam')) if pd.notna(row.get('TitTNam')) else None,
                opr_code=str(row.get('OprCod')) if pd.notna(row.get('OprCod')) else None,
                requests=str(row.get('Requests')) if pd.notna(row.get('Requests')) else None
            )
            
            db.add(doc)
            count += 1
            
            if count % 1000 == 0:
                print(f"Imported {count} records...")
                
        db.commit()
        print(f"Successfully imported {count} records.")
        
    except Exception as e:
        print(f"Error importing data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    import_data()
