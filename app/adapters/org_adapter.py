"""
Organization Structure Adapter
==============================

آداپتر برای import ساختار سازمانی از فایل‌های اکسل.
"""

import pandas as pd
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app import models
from app.database import SessionLocal


class OrgAdapter:
    """
    آداپتر برای import ساختار سازمانی
    
    ساختار انتظاری:
    - منطقه (Zone) - سطح ۱
    - اداره (Department) - سطح ۲
    - قسمت (Section) - سطح ۳
    """
    
    def __init__(self, file_path: str, sheet_name: Optional[str] = None):
        self.file_path = file_path
        self.sheet_name = sheet_name
        self.df: Optional[pd.DataFrame] = None
        self.errors: List[str] = []
    
    def read_file(self) -> bool:
        """خواندن فایل اکسل"""
        try:
            self.df = pd.read_excel(
                self.file_path,
                sheet_name=self.sheet_name or 0,
                dtype=str
            )
            self.df.dropna(how='all', inplace=True)
            return True
        except Exception as e:
            self.errors.append(f"خطا در خواندن فایل: {e}")
            return False
    
    def import_hierarchical(
        self,
        zone_col: str = "منطقه",
        dept_col: str = "اداره",
        section_col: str = "قسمت"
    ) -> Dict[str, Any]:
        """
        Import ساختار سلسله‌مراتبی از اکسل
        
        Args:
            zone_col: نام ستون منطقه
            dept_col: نام ستون اداره
            section_col: نام ستون قسمت
            
        Returns:
            نتایج import
        """
        results = {"zones": 0, "depts": 0, "sections": 0, "errors": []}
        
        if not self.read_file():
            results["errors"] = self.errors
            return results
        
        db = SessionLocal()
        try:
            # استخراج مقادیر یکتا
            unique_zones = self.df[zone_col].dropna().unique() if zone_col in self.df.columns else []
            
            zone_map = {}  # نگاشت نام منطقه به ID
            
            for zone_name in unique_zones:
                zone_name = str(zone_name).strip()
                if not zone_name:
                    continue
                
                # بررسی وجود
                existing = db.query(models.OrgUnit).filter(
                    models.OrgUnit.title == zone_name,
                    models.OrgUnit.parent_id == None
                ).first()
                
                if existing:
                    zone_map[zone_name] = existing.id
                else:
                    zone = models.OrgUnit(
                        code=str(len(zone_map) + 1).zfill(2),
                        title=zone_name,
                        level=1,
                        parent_id=None
                    )
                    db.add(zone)
                    db.flush()
                    zone_map[zone_name] = zone.id
                    results["zones"] += 1
            
            # اگر ستون اداره و قسمت هم وجود دارد
            if dept_col in self.df.columns:
                dept_map = {}
                
                for idx, row in self.df.iterrows():
                    zone_name = str(row.get(zone_col, "")).strip()
                    dept_name = str(row.get(dept_col, "")).strip()
                    section_name = str(row.get(section_col, "")).strip() if section_col in self.df.columns else ""
                    
                    if not zone_name or not dept_name:
                        continue
                    
                    zone_id = zone_map.get(zone_name)
                    if not zone_id:
                        continue
                    
                    # ایجاد یا پیدا کردن اداره
                    dept_key = f"{zone_name}|{dept_name}"
                    if dept_key not in dept_map:
                        existing_dept = db.query(models.OrgUnit).filter(
                            models.OrgUnit.title == dept_name,
                            models.OrgUnit.parent_id == zone_id
                        ).first()
                        
                        if existing_dept:
                            dept_map[dept_key] = existing_dept.id
                        else:
                            dept = models.OrgUnit(
                                code=str(len([k for k in dept_map if k.startswith(zone_name)]) + 1).zfill(2),
                                title=dept_name,
                                level=2,
                                parent_id=zone_id
                            )
                            db.add(dept)
                            db.flush()
                            dept_map[dept_key] = dept.id
                            results["depts"] += 1
                    
                    # ایجاد قسمت
                    if section_name and section_col in self.df.columns:
                        dept_id = dept_map.get(dept_key)
                        if dept_id:
                            existing_section = db.query(models.OrgUnit).filter(
                                models.OrgUnit.title == section_name,
                                models.OrgUnit.parent_id == dept_id
                            ).first()
                            
                            if not existing_section:
                                section = models.OrgUnit(
                                    code=str(results["sections"] + 1).zfill(3),
                                    title=section_name,
                                    level=3,
                                    parent_id=dept_id
                                )
                                db.add(section)
                                results["sections"] += 1
            
            db.commit()
            
        except Exception as e:
            results["errors"].append(f"خطا: {e}")
            db.rollback()
        finally:
            db.close()
        
        return results
    
    def get_current_structure(self) -> Dict[str, Any]:
        """
        دریافت ساختار سازمانی فعلی از دیتابیس
        
        Returns:
            ساختار درختی سازمان
        """
        db = SessionLocal()
        try:
            zones = db.query(models.OrgUnit).filter(
                models.OrgUnit.parent_id == None
            ).all()
            
            result = []
            for zone in zones:
                zone_data = {
                    "id": zone.id,
                    "code": zone.code,
                    "title": zone.title,
                    "departments": []
                }
                
                depts = db.query(models.OrgUnit).filter(
                    models.OrgUnit.parent_id == zone.id
                ).all()
                
                for dept in depts:
                    dept_data = {
                        "id": dept.id,
                        "code": dept.code,
                        "title": dept.title,
                        "sections": []
                    }
                    
                    sections = db.query(models.OrgUnit).filter(
                        models.OrgUnit.parent_id == dept.id
                    ).all()
                    
                    for section in sections:
                        dept_data["sections"].append({
                            "id": section.id,
                            "code": section.code,
                            "title": section.title
                        })
                    
                    zone_data["departments"].append(dept_data)
                
                result.append(zone_data)
            
            return {"zones": result, "total_zones": len(result)}
            
        finally:
            db.close()
