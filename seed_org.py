import os
import sys
import pandas as pd

# Make sure we can import "app" when running as a standalone script
sys.path.append(os.getcwd())

from app.database import SessionLocal, engine
from app import models

EXCEL_FILE = "org_structure.xlsx"

# ---------------------------
# Remapping Logic
# ---------------------------
ZONE_CODE_MAP = {
    16: 19,   # Nazhvan: Org=16 → Budget=19
    17: 20,   # Central HQ: Org=17 → Budget=20
    19: 190,  # Deputies that were 19 → 190 to avoid collision
    20: 200,  # Deputies that were 20 → 200 to avoid collision
}

def remap_zone_code(code_int):
    """
    Apply the Nazhvan/Central/Deputy remapping.
    Any code not in the map is returned as-is.
    """
    if code_int is None:
        return None
    return ZONE_CODE_MAP.get(code_int, code_int)

# ---------------------------
# Helper functions
# ---------------------------

def clean_str(val):
    """Normalize Excel cell to a clean string or None."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip()
    if not s or s.lower() == "nan":
        return None
    return s


def normalize_zone_code(val):
    """
    Extract a clean numeric zone code as string.
    '01' -> '1', '1.0' -> '1', '  16 ' -> '16'.
    If no digits exist, returns None.
    """
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip()
    if not s:
        return None
    digits = "".join(ch for ch in s if ch.isdigit())
    if not digits:
        return None
    # remove leading zeros but keep at least one digit
    return str(int(digits))


def is_region(code_val):
    """
    Check if given code value belongs to a Region (1–16).
    Works with stuff like '01', '1', '16', '16.0', etc.
    """
    if code_val is None:
        return False
    s = str(code_val).strip()
    if not s:
        return False
    digits = "".join(ch for ch in s if ch.isdigit())
    if not digits:
        return False
    try:
        n = int(digits)
        return 1 <= n <= 16
    except Exception:
        return False


def get_org_type_value(name: str):
    """
    Try to use models.OrgType enum if it exists, otherwise fall back to raw string.
    """
    OrgType = getattr(models, "OrgType", None)
    if OrgType is None:
        # Enum not defined or different version → just use plain strings
        return name
    # Map friendly names to enum members
    mapping = {
        "Hozeh": getattr(OrgType, "HOZEH", None),
        "Department": getattr(OrgType, "DEPARTMENT", None),
        "Section": getattr(OrgType, "SECTION", None),
    }
    member = mapping.get(name)
    return member.value if member is not None else name


# ---------------------------
# Main seeding logic
# ---------------------------

def seed_org_units():
    print("\n--- START SEEDING: ORG STRUCTURE (TEMPLATE CLONING + REMAPPING) ---\n")

    if not os.path.exists(EXCEL_FILE):
        print(f"❌ Error: File '{EXCEL_FILE}' not found next to this script.")
        return

    # Ensure tables exist
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Pre-resolve org_type values
    ORG_HOZEH = get_org_type_value("Hozeh")
    ORG_DEPT = get_org_type_value("Department")
    ORG_SECTION = get_org_type_value("Section")

    try:
        # -------------------------
        # 1) Clear old data
        # -------------------------
        print("Cleaning old OrgUnit / SpecialAction data...")
        try:
            # Delete children first (FK to org_units)
            db.query(models.SpecialAction).delete()
            db.query(models.OrgUnit).delete()
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"⚠️  Clean error (ignored, but DB might be dirty): {e}")

        # -------------------------
        # 2) Read & preprocess Excel
        # -------------------------
        print("Reading Excel file...")
        df = pd.read_excel(EXCEL_FILE)

        # Drop completely empty rows
        df = df.dropna(how="all")

        # Remove header row if present (e.g., first col = 'حوزه متولی')
        if len(df) > 0:
            first_cell = clean_str(df.iloc[0, 0])
            if first_cell in ("حوزه متولی", "کد حوزه", "کد منطقه"):
                df = df.iloc[1:, :]

        df = df.reset_index(drop=True)

        # Work copy with ONLY zone code & name forward-filled (for merged cells)
        work = df.copy()
        work.iloc[:, 0] = work.iloc[:, 0].ffill()  # Zone code
        work.iloc[:, 1] = work.iloc[:, 1].ffill()  # Zone name

        # Convenience columns
        work["zone_code_raw"] = work.iloc[:, 0].apply(clean_str)
        work["zone_name"] = work.iloc[:, 1].apply(clean_str)
        work["dept"] = work.iloc[:, 2].apply(clean_str)   # Department (سطح اداره)
        work["section"] = work.iloc[:, 3].apply(clean_str)  # Section (سطح قسمت)

        # -------------------------
        # 3) Build Region‑1 template
        # -------------------------
        print("Extracting Region‑1 template (Departments & Sections)...")

        # Flag which rows belong to Region codes (1–16)
        region_mask = work["zone_code_raw"].apply(is_region)

        # First row where we hit a non‑Region zone (e.g., 17 = شهرداری مرکزی, Deputies)
        non_region_idxs = work.index[
            (~region_mask) & work["zone_code_raw"].notna()
        ]
        template_end_idx = (
            int(non_region_idxs.min()) if len(non_region_idxs) > 0 else len(work)
        )

        # All rows from top until that index compose the Region template block
        template_block = work.iloc[:template_end_idx]

        template_structure: dict[str, list[str]] = {}
        current_dept = None

        for _, row in template_block.iterrows():
            d_title = row["dept"]
            s_title = row["section"]

            # Skip completely empty lines
            if not d_title and not s_title:
                continue

            # New department?
            if d_title:
                current_dept = d_title
                if current_dept not in template_structure:
                    template_structure[current_dept] = []

            # Section belongs to the last seen department
            if s_title and current_dept:
                if s_title not in template_structure[current_dept]:
                    template_structure[current_dept].append(s_title)

        template_dept_count = len(template_structure)
        template_sec_count = sum(len(v) for v in template_structure.values())
        print(
            f"Template extracted: {template_dept_count} departments, "
            f"{template_sec_count} sections."
        )

        if template_dept_count == 0:
            print("❌ Template is empty. Check Excel layout / sheet name.")
            return

        # -------------------------
        # 4) Discover all Zones (Regions + Deputies)
        # -------------------------
        print("Discovering unique zones (Regions + Deputies/Other)...")

        zone_pairs = (
            work[["zone_code_raw", "zone_name"]]
            .dropna(subset=["zone_code_raw", "zone_name"])
            .drop_duplicates()
        )

        total_zones = 0
        total_depts = 0
        total_sections = 0

        for _, z in zone_pairs.iterrows():
            raw_code = z["zone_code_raw"]
            z_title = z["zone_name"]

            norm_code = normalize_zone_code(raw_code)
            if not norm_code or not z_title:
                continue

            # --- REMAPPING LOGIC HERE ---
            orig_code_int = int(norm_code)
            mapped_code_int = remap_zone_code(orig_code_int)
            code_for_db = str(mapped_code_int)

            # -----------------------------------
            # 4.a) Create Zone root (Hozeh level)
            # -----------------------------------
            zone_unit = models.OrgUnit(
                title=z_title,
                code=str(code_for_db), # Ensure string
                org_type=ORG_HOZEH,
                parent_id=None,
            )
            db.add(zone_unit)
            db.commit()
            db.refresh(zone_unit)
            total_zones += 1

            # -----------------------------------
            # 4.b) Decision: Region vs Deputy/Other
            # -----------------------------------
            if is_region(norm_code):
                # -------------------------------
                # Scenario 1: Region (1–16)
                # Clone Region‑1 template 1:1
                # -------------------------------
                dept_counter = 1
                for dept_name, sections in template_structure.items():
                    # Department Code: 01, 02, ...
                    d_code = f"{dept_counter:02d}"
                    
                    dept_unit = models.OrgUnit(
                        title=dept_name,
                        code=d_code,
                        org_type=ORG_DEPT,
                        parent_id=zone_unit.id,
                    )
                    db.add(dept_unit)
                    db.commit()
                    db.refresh(dept_unit)
                    total_depts += 1
                    dept_counter += 1

                    # Sections under this dept
                    sect_counter = 1
                    for sect_name in sections:
                        s_code = f"{sect_counter:02d}"
                        sect_unit = models.OrgUnit(
                            title=sect_name,
                            code=s_code,
                            org_type=ORG_SECTION,
                            parent_id=dept_unit.id,
                        )
                        db.add(sect_unit)
                        total_sections += 1
                        sect_counter += 1

                db.commit()

            else:
                # -------------------------------
                # Scenario 2: Deputy / Other
                # Use explicit rows for this zone
                # -------------------------------
                zone_rows = work[work["zone_code_raw"] == raw_code]

                # Avoid duplicate departments/sections within the same zone
                dept_cache = {}  # dept_title -> OrgUnit
                seen_sections = set()  # (parent_id, section_title)

                current_dept_unit = None
                
                # We need to track counters for this zone
                dept_counter = 1
                # For sections, we need a counter per department. 
                # We can store it in a dict: dept_id -> next_sect_code
                sect_counters = {} 

                for _, row in zone_rows.iterrows():
                    d_title = row["dept"]
                    s_title = row["section"]

                    if not d_title and not s_title:
                        continue

                    # If a department cell is filled, (re)locate/create department
                    if d_title:
                        dept_unit = dept_cache.get(d_title)
                        if dept_unit is None:
                            d_code = f"{dept_counter:02d}"
                            dept_unit = models.OrgUnit(
                                title=d_title,
                                code=d_code,
                                org_type=ORG_DEPT,
                                parent_id=zone_unit.id,
                            )
                            db.add(dept_unit)
                            db.commit()
                            db.refresh(dept_unit)
                            dept_cache[d_title] = dept_unit
                            total_depts += 1
                            dept_counter += 1
                            
                            # Initialize section counter for this new dept
                            sect_counters[dept_unit.id] = 1
                            
                        current_dept_unit = dept_unit

                    # Section: if we have a current department, hang under it;
                    # otherwise, it’s a direct child of the zone
                    if s_title:
                        parent_id = (
                            current_dept_unit.id if current_dept_unit else zone_unit.id
                        )
                        key = (parent_id, s_title)
                        if key in seen_sections:
                            continue
                        
                        # Get next code
                        if parent_id not in sect_counters:
                             sect_counters[parent_id] = 1
                        
                        s_code = f"{sect_counters[parent_id]:02d}"
                        sect_counters[parent_id] += 1

                        sect_unit = models.OrgUnit(
                            title=s_title,
                            code=s_code,
                            org_type=ORG_SECTION,
                            parent_id=parent_id,
                        )
                        db.add(sect_unit)
                        seen_sections.add(key)
                        total_sections += 1

                db.commit()
            
            print(f"Zone {orig_code_int} → stored as {code_for_db} ({z_title})")

        print("\n--- SEEDING COMPLETED ---")
        print(f"✅ Zones created:      {total_zones}")
        print(f"✅ Departments created:{total_depts}")
        print(f"✅ Sections created:   {total_sections}")
        print("Expected: 16 Regions * ~20+ depts each + Deputies → 300+ departments.\n")

    except Exception as e:
        db.rollback()
        print(f"❌ CRITICAL ERROR DURING SEEDING: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_org_units()
