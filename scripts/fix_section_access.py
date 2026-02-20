# -*- coding: utf-8 -*-
"""
Fix Section-Subsystem Access Mappings
Adds SectionSubsystemAccess entries for all Region 14 sections
"""
import sys
import io
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.database import SessionLocal
from app import models

def main():
    db = SessionLocal()
    
    # Section IDs for Region 14 (from seeding)
    # Section 6: Road, 7: Elec, 8: Mech, 9: Civil/Supervision, 10: Technical
    section_ids = [6, 7, 8, 9, 10]
    
    # Subsystem 3 = CIVIL_WORKS (the one with our activities)
    subsystem_id = 3
    
    print("=== Current Subsystems ===")
    for s in db.query(models.Subsystem).all():
        print(f"  ID:{s.id} Code:{s.code}")
    
    print("\n=== Adding SectionSubsystemAccess entries ===")
    
    for section_id in section_ids:
        # Check if mapping already exists
        existing = db.query(models.SectionSubsystemAccess).filter(
            models.SectionSubsystemAccess.section_id == section_id,
            models.SectionSubsystemAccess.subsystem_id == subsystem_id
        ).first()
        
        if existing:
            print(f"  [EXISTS] Section {section_id} -> Subsystem {subsystem_id}")
        else:
            mapping = models.SectionSubsystemAccess(
                section_id=section_id,
                subsystem_id=subsystem_id
            )
            db.add(mapping)
            print(f"  [ADDED] Section {section_id} -> Subsystem {subsystem_id}")
    
    db.commit()
    
    print("\n=== Verification ===")
    for ssa in db.query(models.SectionSubsystemAccess).all():
        print(f"  Section:{ssa.section_id} -> Subsystem:{ssa.subsystem_id}")
    
    print("\nDone! Refresh the browser to see changes.")
    db.close()

if __name__ == "__main__":
    main()
