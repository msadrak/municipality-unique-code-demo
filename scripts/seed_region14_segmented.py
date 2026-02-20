"""
Region 14 Micro-Segmentation Seeding Script
============================================
Section-Based Isolation with Intelligent Keyword Classification

This script implements a sophisticated budget classification system that:
1. Reads the Region 14 budget CSV file
2. Classifies each row into 5 specialized Civil Sections using keyword scoring
3. Creates isolated OrgUnits for each section
4. Generates dedicated admin users for each section
5. Ensures strict 1-to-1 mapping of Budget Rows to Activities
6. Locks activities to their specific budget codes via ActivityConstraints

THE 5 OFFICIAL SECTIONS:
------------------------
1. ROAD_ASPHALT (نظارت راه و آسفالت) - admin_road_14
2. ELECTRICAL (تاسیسات برق) - admin_elec_14
3. MECHANICAL (تاسیسات مکانیکی) - admin_mech_14
4. SUPERVISION (نظارت ابنیه) - admin_civil_14
5. TECHNICAL (نظام فنی/عمومی) - admin_tech_14 [FALLBACK]

Architecture: Micro-Segmentation Strategy for Maximum Isolation
"""
import sys
import io
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Fix encoding for Windows console
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except:
        pass

import csv
import argparse
from datetime import datetime
from typing import Dict, Tuple, Optional, List
from collections import defaultdict

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app import models
from app.auth_utils import hash_password, verify_password

# Ensure all tables exist
models.Base.metadata.create_all(bind=engine)

# ============================================
# CONFIGURATION
# ============================================

# CSV File Location (adjust path as needed)
CSV_FILE = Path(__file__).parent / "region14_civil_items.csv"

# Region Configuration
REGION_CODE = "14"
REGION_NAME = "منطقه چهارده"
SUBSYSTEM_CODE = "CIVIL_WORKS"
SUBSYSTEM_TITLE = "عمران و طرح‌ها"

# Admin Configuration
DEFAULT_ADMIN_PASSWORD = "Tehran@1403"  # Must be changed on first login

# ============================================
# SECTION DEFINITIONS
# ============================================

SECTIONS = {
    "ROAD_ASPHALT": {
        "code": "R14_ROAD",
        "title": "نظارت راه و آسفالت",
        "username": "admin_road_14",
        "full_name": "Admin - Road & Asphalt (Region 14)",
        "org_type": "SECTION"
    },
    "ELECTRICAL": {
        "code": "R14_ELEC",
        "title": "تاسیسات برق",
        "username": "admin_elec_14",
        "full_name": "Admin - Electrical Systems (Region 14)",
        "org_type": "SECTION"
    },
    "MECHANICAL": {
        "code": "R14_MECH",
        "title": "تاسیسات مکانیکی",
        "username": "admin_mech_14",
        "full_name": "Admin - Mechanical Systems (Region 14)",
        "org_type": "SECTION"
    },
    "SUPERVISION": {
        "code": "R14_CIVIL",
        "title": "نظارت ابنیه",
        "username": "admin_civil_14",
        "full_name": "Admin - Building Supervision (Region 14)",
        "org_type": "SECTION"
    },
    "TECHNICAL": {
        "code": "R14_TECH",
        "title": "نظام فنی و عمومی",
        "username": "admin_tech_14",
        "full_name": "Admin - Technical & General (Region 14)",
        "org_type": "SECTION"
    }
}

# ============================================
# KEYWORD CLASSIFICATION ENGINE
# ============================================

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


class BudgetClassifier:
    """
    Intelligent budget classification engine using keyword scoring.
    
    Algorithm:
    1. Extract text content from budget row (code + description)
    2. Calculate score for each section based on keyword matches
    3. Assign to section with highest score
    4. Fallback to TECHNICAL if no keywords match
    """
    
    def __init__(self, keywords_dict: Dict[str, List[str]]):
        self.keywords_dict = keywords_dict
        self.stats = defaultdict(int)
    
    def classify(self, budget_code: str, description: str) -> str:
        """
        Classify a budget row into one of the 5 sections.
        
        Args:
            budget_code: Budget code (may contain hints)
            description: Budget line description (main classification source)
            
        Returns:
            Section key (e.g., "ROAD_ASPHALT", "ELECTRICAL", etc.)
        """
        if not description:
            description = ""
        
        # Combine text for analysis
        text = f"{budget_code} {description}".lower()
        
        # Calculate scores for each section
        scores = {}
        for section_key, keywords in self.keywords_dict.items():
            score = 0
            for keyword in keywords:
                if keyword in text:
                    score += 1
            scores[section_key] = score
        
        # Find winner (highest score)
        max_score = max(scores.values())
        
        if max_score == 0:
            # No keywords matched - assign to TECHNICAL (fallback)
            winner = "TECHNICAL"
            self.stats['fallback_assignments'] += 1
        else:
            # Get section with highest score
            winner = max(scores.items(), key=lambda x: x[1])[0]
        
        self.stats[f'assigned_to_{winner}'] += 1
        return winner
    
    def get_stats(self) -> Dict[str, int]:
        """Return classification statistics."""
        return dict(self.stats)


# ============================================
# DATABASE OPERATIONS
# ============================================

_ACTIVITY_HAS_ORG_UNIT = None


def activity_org_unit_supported(db: Session) -> bool:
    """Check if subsystem_activities has org_unit_id column."""
    global _ACTIVITY_HAS_ORG_UNIT
    if _ACTIVITY_HAS_ORG_UNIT is None:
        inspector = inspect(db.get_bind())
        columns = {col["name"] for col in inspector.get_columns("subsystem_activities")}
        _ACTIVITY_HAS_ORG_UNIT = "org_unit_id" in columns
    return _ACTIVITY_HAS_ORG_UNIT

def get_or_create_region(db: Session) -> int:
    """Get or create the Region 14 parent OrgUnit."""
    region = db.query(models.OrgUnit).filter(
        models.OrgUnit.code == REGION_CODE,
        models.OrgUnit.org_type == "ZONE"
    ).first()
    
    if region:
        return region.id
    
    region = models.OrgUnit(
        title=REGION_NAME,
        code=REGION_CODE,
        org_type="ZONE"
    )
    db.add(region)
    db.flush()
    print(f"  [CREATED] Region: {REGION_NAME} (ID: {region.id})")
    return region.id


def get_or_create_subsystem(db: Session) -> int:
    """Get or create the Civil Works subsystem."""
    subsystem = db.query(models.Subsystem).filter(
        models.Subsystem.code == SUBSYSTEM_CODE
    ).first()
    
    if subsystem:
        return subsystem.id
    
    subsystem = models.Subsystem(
        code=SUBSYSTEM_CODE,
        title=SUBSYSTEM_TITLE,
        icon="construction",
        is_active=True,
        order=14,
        attachment_type="upload"
    )
    db.add(subsystem)
    db.flush()
    print(f"  [CREATED] Subsystem: {SUBSYSTEM_TITLE} (ID: {subsystem.id})")
    return subsystem.id


def create_section_org_unit(
    db: Session,
    section_key: str,
    parent_id: int
) -> Tuple[int, bool]:
    """
    Create an OrgUnit for a section.
    
    Returns:
        (org_unit_id, was_created)
    """
    section_config = SECTIONS[section_key]
    
    # Check if exists
    existing = db.query(models.OrgUnit).filter(
        models.OrgUnit.code == section_config["code"]
    ).first()
    
    if existing:
        return existing.id, False
    
    # Create new section OrgUnit
    org_unit = models.OrgUnit(
        title=section_config["title"],
        code=section_config["code"],
        parent_id=parent_id,
        org_type=section_config["org_type"]
    )
    db.add(org_unit)
    db.flush()
    
    return org_unit.id, True


def create_section_admin_user(
    db: Session,
    section_key: str,
    org_unit_id: int,
    subsystem_id: int,
    default_zone_id: Optional[int] = None
) -> Tuple[int, bool, bool]:
    """
    Create an Admin L1 user for a section.
    
    Returns:
        (user_id, was_created, was_updated)
    """
    section_config = SECTIONS[section_key]
    username = section_config["username"]
    
    # Check if user exists
    existing = db.query(models.User).filter(
        models.User.username == username
    ).first()
    
    if existing:
        updated = False

        # Ensure default password is consistent
        if not verify_password(DEFAULT_ADMIN_PASSWORD, existing.password_hash or ""):
            existing.password_hash = hash_password(DEFAULT_ADMIN_PASSWORD)
            updated = True

        # Ensure correct role + level + org defaults
        if existing.role != "ADMIN_L1":
            existing.role = "ADMIN_L1"
            updated = True
        if existing.admin_level != 1:
            existing.admin_level = 1
            updated = True
        if existing.default_section_id != org_unit_id:
            existing.default_section_id = org_unit_id
            updated = True
        if default_zone_id and existing.default_zone_id != default_zone_id:
            existing.default_zone_id = default_zone_id
            updated = True

        # Ensure subsystem responsibility includes target subsystem
        current_subsystems = set(existing.managed_subsystem_ids or [])
        if subsystem_id not in current_subsystems:
            current_subsystems.add(subsystem_id)
            existing.managed_subsystem_ids = sorted(current_subsystems)
            updated = True

        if not existing.is_active:
            existing.is_active = True
            updated = True

        # Ensure RBAC access exists
        access_exists = db.query(models.UserSubsystemAccess).filter(
            models.UserSubsystemAccess.user_id == existing.id,
            models.UserSubsystemAccess.subsystem_id == subsystem_id
        ).first()
        if not access_exists:
            access = models.UserSubsystemAccess(
                user_id=existing.id,
                subsystem_id=subsystem_id
            )
            db.add(access)
            updated = True

        if updated:
            db.flush()

        return existing.id, False, updated
    
    # Create new admin user
    user = models.User(
        username=username,
        password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
        full_name=section_config["full_name"],
        role="ADMIN_L1",
        admin_level=1,
        default_section_id=org_unit_id,
        managed_subsystem_ids=[subsystem_id],
        is_active=True
    )
    db.add(user)
    db.flush()
    
    # Grant subsystem access (RBAC)
    access = models.UserSubsystemAccess(
        user_id=user.id,
        subsystem_id=subsystem_id
    )
    db.add(access)
    db.flush()
    
    return user.id, True, False


def ensure_section_subsystem_access(
    db: Session,
    section_id: int,
    subsystem_id: int
) -> bool:
    """Ensure SectionSubsystemAccess exists."""
    existing = db.query(models.SectionSubsystemAccess).filter(
        models.SectionSubsystemAccess.section_id == section_id,
        models.SectionSubsystemAccess.subsystem_id == subsystem_id
    ).first()

    if existing:
        return False

    access = models.SectionSubsystemAccess(
        section_id=section_id,
        subsystem_id=subsystem_id
    )
    db.add(access)
    db.flush()
    return True


def create_unique_activity(
    db: Session,
    subsystem_id: int,
    budget_code: str,
    description: str,
    row_index: int,
    section_key: str,
    org_unit_id: Optional[int] = None
) -> Tuple[int, bool]:
    """
    Create a UNIQUE SubsystemActivity for this budget line.
    
    Strategy: Each budget line gets its own activity to prevent fund shifting.
    Activity code includes section key for isolation.
    
    Returns:
        (activity_id, was_created)

    Note:
        If the SubsystemActivity table has an org_unit_id column, it will be set.
    """
    # Generate unique code with section prefix
    section_prefix = section_key[:4].upper()  # ROAD, ELEC, MECH, SUPE, TECH
    activity_code = f"CW_{section_prefix}_{budget_code}_{row_index}"
    
    # Check if exists
    existing = db.query(models.SubsystemActivity).filter(
        models.SubsystemActivity.code == activity_code
    ).first()
    
    if existing:
        return existing.id, False
    
    # Create unique activity
    activity = models.SubsystemActivity(
        subsystem_id=subsystem_id,
        code=activity_code,
        title=description[:200] if description else f"Budget {budget_code} - {section_key}",
        is_active=True,
        frequency=models.ActivityFrequency.YEARLY,
        requires_file_upload=True
    )
    db.add(activity)
    db.flush()

    # Optional: persist org_unit_id if schema supports it
    if org_unit_id and activity_org_unit_supported(db):
        db.execute(
            text(
                "UPDATE subsystem_activities SET org_unit_id = :org_unit_id WHERE id = :activity_id"
            ),
            {"org_unit_id": org_unit_id, "activity_id": activity.id}
        )
    
    return activity.id, True


def create_budget_row(
    db: Session,
    activity_id: int,
    budget_code: str,
    description: str,
    approved_amount: float,
    org_unit_id: int
) -> Tuple[int, bool]:
    """
    Create BudgetRow (Zero Trust model) linked to activity and section.
    
    Returns:
        (budget_row_id, was_created)
    """
    # Check if exists
    existing = db.query(models.BudgetRow).filter(
        models.BudgetRow.budget_coding == budget_code,
        models.BudgetRow.org_unit_id == org_unit_id
    ).first()
    
    if existing:
        return existing.id, False
    
    # Convert to integer (Rials)
    approved = int(approved_amount) if approved_amount else 0
    
    budget_row = models.BudgetRow(
        activity_id=activity_id,
        org_unit_id=org_unit_id,  # Section-specific isolation
        budget_coding=budget_code,
        description=description[:500] if description else "",
        approved_amount=approved,
        blocked_amount=0,
        spent_amount=0,
        fiscal_year="1403"
    )
    db.add(budget_row)
    db.flush()
    
    return budget_row.id, True


def create_activity_constraint(
    db: Session,
    activity_id: int,
    budget_code: str
) -> Tuple[int, bool]:
    """
    Create ActivityConstraint for STRICT 1-to-1 locking.
    
    This constraint ensures the activity can ONLY use this specific budget code.
    
    Returns:
        (constraint_id, was_created)
    """
    # Check if exists
    existing = db.query(models.ActivityConstraint).filter(
        models.ActivityConstraint.subsystem_activity_id == activity_id,
        models.ActivityConstraint.budget_code_pattern == budget_code
    ).first()
    
    if existing:
        return existing.id, False
    
    constraint = models.ActivityConstraint(
        subsystem_activity_id=activity_id,
        budget_code_pattern=budget_code,  # Exact match (not a pattern)
        constraint_type="INCLUDE",
        description=f"Micro-segmentation: Activity locked to budget {budget_code}",
        is_active=True,
        priority=100  # High priority
    )
    db.add(constraint)
    db.flush()
    
    return constraint.id, True


# ============================================
# CSV PROCESSING
# ============================================

def read_csv_file(csv_path: Path) -> List[Dict]:
    """
    Read the CSV file and return list of budget rows.
    
    Expected columns (adjust based on actual CSV):
    - 'کد بودجه' or 'budget_code': Budget code
    - 'شرح ردیف' or 'description': Description
    - 'مصوب 1403' or 'approved_1403': Approved amount
    
    Returns:
        List of dictionaries with normalized keys
    """
    rows = []
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            # Normalize keys (handle both Persian and English column names)
            normalized = {}
            
            for key, value in row.items():
                if key in ['کد بودجه', 'budget_code', 'کد']:
                    normalized['budget_code'] = value.strip() if value else None
                elif key in ['شرح ردیف', 'description', 'شرح']:
                    normalized['description'] = value.strip() if value else None
                elif key in ['مصوب 1403', 'approved_1403', 'مصوب']:
                    try:
                        # Remove thousand separators and convert
                        clean_value = value.replace(',', '').replace('،', '').strip()
                        normalized['approved_amount'] = float(clean_value) if clean_value else 0
                    except (ValueError, AttributeError):
                        normalized['approved_amount'] = 0
            
            # Only include rows with valid budget code
            if normalized.get('budget_code'):
                rows.append(normalized)
    
    return rows


# ============================================
# MAIN SEEDING LOGIC
# ============================================

def seed_region14_segmented(db: Session, csv_path: Path, dry_run: bool = False) -> Dict:
    """
    Main seeding function: Micro-segmentation with keyword classification.
    
    Steps:
    1. Load CSV data
    2. Create parent structures (Region, Subsystem)
    3. Create 5 section OrgUnits
    4. Create 5 admin users (one per section)
    5. Classify each budget row using keyword scoring
    6. Create Activity, BudgetRow, and Constraint for each row
    7. Report statistics
    """
    
    stats = {
        'total_rows': 0,
        'sections_created': 0,
        'users_created': 0,
        'users_updated': 0,
        'section_access_created': 0,
        'activities_created': 0,
        'budget_rows_created': 0,
        'constraints_created': 0,
        'skipped': 0,
        'errors': []
    }
    
    print("\n" + "=" * 80)
    print("REGION 14 MICRO-SEGMENTATION SEEDER")
    print("Section-Based Isolation with Keyword Classification")
    print("=" * 80)
    print(f"Mode: {'DRY RUN (Preview)' if dry_run else 'LIVE (Committing)'}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Step 1: Load CSV data
    print("\n[1/7] Loading CSV data...")
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    budget_rows = read_csv_file(csv_path)
    stats['total_rows'] = len(budget_rows)
    print(f"  ✓ Loaded {len(budget_rows)} budget rows")
    
    # Step 2: Create parent structures
    print("\n[2/7] Creating parent structures...")
    region_id = get_or_create_region(db)
    subsystem_id = get_or_create_subsystem(db)
    print(f"  ✓ Region ID: {region_id}")
    print(f"  ✓ Subsystem ID: {subsystem_id}")
    
    # Step 3: Create section OrgUnits
    print("\n[3/7] Creating section OrgUnits...")
    section_map = {}  # section_key -> org_unit_id
    
    for section_key in SECTIONS.keys():
        org_id, created = create_section_org_unit(db, section_key, region_id)
        section_map[section_key] = org_id
        
        if created:
            stats['sections_created'] += 1
            section_title = SECTIONS[section_key]['title']
            print(f"  [NEW] {section_key}: {section_title} (ID: {org_id})")
        else:
            section_title = SECTIONS[section_key]['title']
            print(f"  [EXISTS] {section_key}: {section_title} (ID: {org_id})")
    
    # Step 4: Create admin users
    print("\n[4/7] Creating section admin users...")
    user_map = {}  # section_key -> user_id
    
    for section_key in SECTIONS.keys():
        org_id = section_map[section_key]
        user_id, created, updated = create_section_admin_user(
            db,
            section_key,
            org_id,
            subsystem_id,
            default_zone_id=region_id
        )
        user_map[section_key] = user_id
        
        if created:
            stats['users_created'] += 1
            username = SECTIONS[section_key]['username']
            print(f"  [NEW] {username} (ID: {user_id})")
            print(f"        Password: {DEFAULT_ADMIN_PASSWORD}")
        elif updated:
            stats['users_updated'] += 1
            username = SECTIONS[section_key]['username']
            print(f"  [UPDATED] {username} (ID: {user_id})")
            print(f"        Password: {DEFAULT_ADMIN_PASSWORD}")
        else:
            username = SECTIONS[section_key]['username']
            print(f"  [EXISTS] {username} (ID: {user_id})")

        # Ensure section-to-subsystem mapping exists
        if ensure_section_subsystem_access(db, org_id, subsystem_id):
            stats['section_access_created'] += 1
    
    # Step 5: Initialize classifier
    print("\n[5/7] Initializing keyword classifier...")
    classifier = BudgetClassifier(SECTION_KEYWORDS)
    print(f"  ✓ Loaded {sum(len(kw) for kw in SECTION_KEYWORDS.values())} keywords")
    
    # Step 6: Process each budget row
    print("\n[6/7] Processing budget rows with classification...")
    
    classification_stats = defaultdict(int)
    
    for idx, row in enumerate(budget_rows):
        try:
            budget_code = row.get('budget_code')
            description = row.get('description', '')
            approved_amount = row.get('approved_amount', 0)
            
            if not budget_code:
                stats['skipped'] += 1
                continue
            
            # CLASSIFY: Determine which section this belongs to
            section_key = classifier.classify(budget_code, description)
            classification_stats[section_key] += 1
            org_unit_id = section_map[section_key]
            
            # CREATE: Activity -> BudgetRow -> Constraint
            activity_id, activity_created = create_unique_activity(
                db, subsystem_id, budget_code, description, idx, section_key, org_unit_id=org_unit_id
            )
            
            budget_row_id, budget_created = create_budget_row(
                db, activity_id, budget_code, description, approved_amount, org_unit_id
            )
            
            constraint_id, constraint_created = create_activity_constraint(
                db, activity_id, budget_code
            )
            
            # Update stats
            if activity_created:
                stats['activities_created'] += 1
            if budget_created:
                stats['budget_rows_created'] += 1
            if constraint_created:
                stats['constraints_created'] += 1
            
            # Progress indicator
            if (idx + 1) % 10 == 0:
                print(f"  Processed {idx + 1}/{len(budget_rows)} rows...")
        
        except Exception as e:
            error_msg = f"Row {idx} (Budget: {budget_code}): {str(e)}"
            stats['errors'].append(error_msg)
            print(f"  [ERROR] {error_msg}")
    
    # Step 7: Finalize
    print("\n[7/7] Finalizing...")
    if dry_run:
        print("  [DRY RUN] Rolling back all changes...")
        db.rollback()
    else:
        print("  [COMMIT] Saving all changes to database...")
        db.commit()
    
    # Add classification stats to main stats
    stats['classification'] = dict(classification_stats)
    stats['classifier_stats'] = classifier.get_stats()
    
    return stats


def print_summary_report(stats: Dict, dry_run: bool):
    """Print a comprehensive summary report."""
    print("\n" + "=" * 80)
    print("SEEDING SUMMARY REPORT")
    print("=" * 80)
    print(f"Status: {'DRY RUN COMPLETED' if dry_run else 'IMPORT COMPLETED'}")
    print()
    
    print("Structural Components:")
    print(f"  • Section OrgUnits Created: {stats['sections_created']}")
    print(f"  • Admin Users Created: {stats['users_created']}")
    print(f"  • Admin Users Updated: {stats['users_updated']}")
    print(f"  • Section Access Links Created: {stats['section_access_created']}")
    print()
    
    print("Budget Components:")
    print(f"  • Total Budget Rows Processed: {stats['total_rows']}")
    print(f"  • Activities Created: {stats['activities_created']}")
    print(f"  • BudgetRows Created: {stats['budget_rows_created']}")
    print(f"  • ActivityConstraints Created: {stats['constraints_created']}")
    print(f"  • Skipped: {stats['skipped']}")
    print()
    
    print("Classification Results:")
    for section_key in SECTIONS.keys():
        count = stats['classification'].get(section_key, 0)
        section_title = SECTIONS[section_key]['title']
        print(f"  • {section_title}: {count} items")
    
    fallback = stats['classifier_stats'].get('fallback_assignments', 0)
    print(f"  • Fallback (no keywords): {fallback} items")
    print()
    
    if stats['errors']:
        print(f"⚠ Errors Encountered: {len(stats['errors'])}")
        for error in stats['errors'][:5]:
            print(f"  - {error}")
        if len(stats['errors']) > 5:
            print(f"  ... and {len(stats['errors']) - 5} more")
        print()
    
    print("=" * 80)
    print("Section Admin Credentials:")
    print("=" * 80)
    for section_key, config in SECTIONS.items():
        print(f"  • {config['username']}")
        print(f"    Name: {config['full_name']}")
        print(f"    Password: {DEFAULT_ADMIN_PASSWORD} (MUST CHANGE)")
    print("=" * 80)


def verify_segmentation(db: Session):
    """Verify the segmentation after import."""
    print("\n" + "=" * 80)
    print("SEGMENTATION VERIFICATION")
    print("=" * 80)
    
    region = db.query(models.OrgUnit).filter(
        models.OrgUnit.code == REGION_CODE
    ).first()
    
    if not region:
        print("✗ Region 14 not found!")
        return
    
    print(f"✓ Region: {region.title} (ID: {region.id})")
    print()
    
    print("Section Distribution:")
    for section_key, config in SECTIONS.items():
        section = db.query(models.OrgUnit).filter(
            models.OrgUnit.code == config['code']
        ).first()
        
        if section:
            budget_count = db.query(models.BudgetRow).filter(
                models.BudgetRow.org_unit_id == section.id
            ).count()
            
            total_budget = db.query(models.BudgetRow).filter(
                models.BudgetRow.org_unit_id == section.id
            ).all()
            
            total_amount = sum(br.approved_amount for br in total_budget)
            
            user = db.query(models.User).filter(
                models.User.username == config['username']
            ).first()
            
            print(f"  • {config['title']}:")
            print(f"    - OrgUnit ID: {section.id}")
            print(f"    - Budget Rows: {budget_count}")
            print(f"    - Total Budget: {total_amount:,} Rials")
            print(f"    - Admin: {config['username']} (ID: {user.id if user else 'N/A'})")
        else:
            print(f"  ✗ {config['title']}: NOT FOUND")
    
    print("=" * 80)


# ============================================
# CLI ENTRY POINT
# ============================================

def main():
    parser = argparse.ArgumentParser(
        description="Region 14 Micro-Segmentation Seeder",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview what will be created (recommended first run)
  python seed_region14_segmented.py --dry-run
  
  # Execute the import with default CSV location
  python seed_region14_segmented.py
  
  # Specify custom CSV file
  python seed_region14_segmented.py --csv path/to/custom.csv
  
  # Verify existing segmentation
  python seed_region14_segmented.py --verify
        """
    )
    
    parser.add_argument(
        '--csv',
        type=str,
        default=str(CSV_FILE),
        help=f'Path to CSV file (default: {CSV_FILE})'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without committing to database'
    )
    
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify existing segmentation (no changes)'
    )
    
    args = parser.parse_args()
    
    # Connect to database
    db = SessionLocal()
    
    try:
        if args.verify:
            # Verification mode only
            verify_segmentation(db)
            return 0
        
        # Execute seeding
        csv_path = Path(args.csv)
        stats = seed_region14_segmented(db, csv_path, dry_run=args.dry_run)
        
        # Print summary
        print_summary_report(stats, args.dry_run)
        
        # Verify if not dry run
        if not args.dry_run:
            verify_segmentation(db)
        
        return 0
    
    except FileNotFoundError as e:
        print("\n" + "=" * 80)
        print("[ERROR] CSV File Not Found")
        print("=" * 80)
        print(f"{e}")
        print()
        print("Please ensure the CSV file exists at:")
        print(f"  {CSV_FILE}")
        print()
        print("Or specify a custom path with --csv argument")
        print("=" * 80)
        return 1
    
    except Exception as e:
        print("\n" + "=" * 80)
        print("[FATAL ERROR] Seeding Failed")
        print("=" * 80)
        print(f"Error: {str(e)}")
        print()
        import traceback
        traceback.print_exc()
        db.rollback()
        return 1
    
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
