#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
export_clean_counterparties.py (v3 - Safety-First)
===================================================

A robust, SAFETY-FIRST entity resolution pipeline for Persian/Farsi
accounting counterparties.

Key Principles:
1. NO hard-delete except explicit EXCLUDE decisions or strict patterns
2. Prefer labeling + audit sheets over deletion
3. Avoid O(N²) - use blocking with hard caps
4. KEEP_SEPARATE decisions act as merge locks
5. Full audit trail in output sheets

Author: Senior Data Engineer (Entity Resolution Specialist)
Python: 3.10+
Dependencies: pandas, openpyxl (rapidfuzz optional for faster fuzzy matching)
"""

from __future__ import annotations

import json
import os
import re
import shutil
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

# Try rapidfuzz for faster fuzzy matching, fall back to difflib
try:
    from rapidfuzz import fuzz as rf_fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    from difflib import SequenceMatcher
    RAPIDFUZZ_AVAILABLE = False

# =============================================================================
# CONFIGURATION
# =============================================================================

# Paths
SOURCE_EXCEL_PATH = Path(r"f:\Freelancing_Project\KalaniProject\municipality_demo\data\reports\Uniqe Person_Company.xlsx")
DECISIONS_JSON_PATH = Path(r"C:\Users\Dour_Andish\.gemini\antigravity\brain\592da352-7d36-4150-8edd-0b906c5f22bb\entity_resolution_decisions.json")
OUTPUT_EXCEL_PATH = Path(r"f:\Freelancing_Project\KalaniProject\municipality_demo\data\reports\Clean_Unique_Counterparties_v4.xlsx")

# Cleanup mode: "archive" | "delete" | "none"
CLEANUP_MODE = "archive"

# Thresholds
AUTO_MERGE_THRESHOLD = 0.97  # Very strict - only near-identical
REVIEW_LOW_THRESHOLD = 0.90  # Below this, not even reviewed
MAX_BLOCK_ITEMS = 250        # Skip fuzzy if block too large
MAX_TOTAL_FUZZY_COMPARISONS = 200_000  # Global cap

# Token frequency threshold: tokens appearing in >2% of names are stopwords
TOKEN_FREQUENCY_THRESHOLD = 0.02

# =============================================================================
# TOKEN LISTS (Tunable Constants)
# =============================================================================

# Legal form tokens - removable for matching (but kept in canonical)
LEGAL_TOKENS = {
    "شرکت", "شركت", "موسسه", "مؤسسه", "سهامی", "سهامي",
    "تعاونی", "تعاوني", "هلدینگ", "هلدينگ", "گروه",
    "پیمانکاری", "پيمانكاري", "تولیدی", "توليدي",
    "خدماتی", "خدماتي", "بازرگانی", "بازرگاني",
    "صنایع", "صنايع", "صنعتی", "صنعتي",
}

# Person title tokens - removable for matching
PERSON_TITLES = {
    "آقای", "آقاي", "اقای", "اقاي", "آقا",
    "خانم", "خانوم",
    "دکتر", "دكتر",
    "مهندس",
    "حاج", "حاجی", "حاجي",
    "سید", "سيد", "سیده", "سيده",
}

# Generic organization words - removable for matching
GENERIC_ORG_WORDS = {
    "سازمان", "اداره", "مدیریت", "مديريت",
    "معاونت", "واحد",
}

# PROTECT tokens - NEVER remove (identity-bearing)
PROTECT_TOKENS = {
    "بانک", "بانك", "بیمه", "بيمه",
    "شهرداری", "شهرداري", "دانشگاه",
    "بیمارستان", "بيمارستان", "صندوق",
}

# Accounting tokens - for scoring only, never hard-delete
ACCOUNTING_TOKENS = {
    "هزینه", "هزينه", "درآمد", "مخارج",
    "حقوق", "دستمزد", "تنخواه", "جاری", "جاري",
    "متفرقه", "بستانکار", "بستانكار", "بدهکار", "بدهكار",
    "بدهکاران", "بدهكاران", "بستانکاران", "بستانكاران",
    "حساب", "ذخیره", "ذخيره", "اندوخته",
    "استهلاک", "استهلاك", "پیش پرداخت", "پيش پرداخت",
    "دریافتنی", "دريافتني", "پرداختنی", "پرداختني",
    "فروش", "خرید", "خريد", "مالیات", "ماليات",
    "عوارض", "جرائم", "جرایم",
}

# Noise tokens to exclude from token sets
NOISE_TOKENS = {"و", "یا", "يا", "با", "در", "از", "به", "تا"}

# =============================================================================
# STRICT HARD-DELETE PATTERNS (anchored, very conservative)
# =============================================================================

HARD_DELETE_PATTERNS = [
    re.compile(r"^\d+$"),                           # digits only
    re.compile(r"^(سال|ماه)\s*\d{2,4}$"),          # year/month markers
    re.compile(r"^\d{4}$"),                         # 4-digit year
    re.compile(r"^(پروژه|احداث|ساخت|تکمیل|بازسازی)\b", re.UNICODE),  # project verbs
]

# =============================================================================
# NORMALIZATION
# =============================================================================

# Arabic → Persian letter mapping (آ preserved)
AR2FA_MAP = {
    "ي": "ی", "ك": "ک", "ة": "ه", "ؤ": "و", "إ": "ا", "أ": "ا",
    "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4",
    "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9",
}

# For matching keys only (also normalize آ → ا)
AR2FA_MATCHING = AR2FA_MAP.copy()
AR2FA_MATCHING["آ"] = "ا"

DIACRITICS_RE = re.compile(r"[\u064b-\u065f\u0670\u06d6-\u06ed]")
TATWEEL_RE = re.compile(r"\u0640")
ZWNJ = "\u200c"
PUNCT_RE = re.compile(r"[^\w\s\u0600-\u06FF]")


def normalize_canonical(text: str) -> str:
    """Normalize for canonical display (preserves آ)."""
    if pd.isna(text) or not str(text).strip():
        return ""
    s = str(text).strip()
    for ar, fa in AR2FA_MAP.items():
        s = s.replace(ar, fa)
    s = DIACRITICS_RE.sub("", s)
    s = TATWEEL_RE.sub("", s)
    s = s.replace(ZWNJ, " ")
    s = s.replace("–", " ").replace("—", " ").replace("-", " ")
    s = PUNCT_RE.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalize_for_matching(text: str) -> str:
    """Normalize for matching (آ → ا, lowercase)."""
    s = normalize_canonical(text)
    for ar, fa in AR2FA_MATCHING.items():
        s = s.replace(ar, fa)
    return s.lower()


# =============================================================================
# TOKEN PROCESSING
# =============================================================================

def tokenize(text: str) -> list[str]:
    """Tokenize normalized text."""
    s = normalize_canonical(text)
    return [t for t in s.split() if t and t not in NOISE_TOKENS]


def compute_base_name(name: str) -> str:
    """
    Compute base name for matching.
    Removes LEGAL_TOKENS + PERSON_TITLES + GENERIC_ORG_WORDS but keeps PROTECT_TOKENS.
    """
    tokens = tokenize(name)
    if not tokens:
        return ""
    
    has_protect = any(t in PROTECT_TOKENS for t in tokens)
    if has_protect:
        # Only remove person titles if has protect token
        cleaned = [t for t in tokens if t not in PERSON_TITLES]
    else:
        removable = LEGAL_TOKENS | PERSON_TITLES | GENERIC_ORG_WORDS
        cleaned = [t for t in tokens if t not in removable]
    
    return " ".join(cleaned) if cleaned else " ".join(tokens)


def compute_base_compact(base_name: str) -> str:
    """Base name without spaces for comparison."""
    return normalize_for_matching(base_name).replace(" ", "")


def is_significant_token(token: str, freq_ratio: float) -> bool:
    """Check if token is significant for blocking."""
    if len(token) < 3:
        return False
    if token in LEGAL_TOKENS | GENERIC_ORG_WORDS | PERSON_TITLES:
        return False
    if token.isdigit():
        return False
    if freq_ratio > TOKEN_FREQUENCY_THRESHOLD:
        return False
    return True


# =============================================================================
# HARD DELETE CHECK
# =============================================================================

def should_hard_delete(name: str, explicit_excludes: set[str]) -> tuple[bool, str]:
    """
    Returns (should_delete, reason).
    Only True for explicit EXCLUDE decisions or strict patterns.
    """
    norm = normalize_canonical(name)
    
    # Check explicit EXCLUDE from decisions
    if norm in explicit_excludes:
        return True, "explicit_exclude_decision"
    
    # Check strict patterns
    for pattern in HARD_DELETE_PATTERNS:
        if pattern.match(norm):
            return True, f"pattern:{pattern.pattern}"
    
    return False, ""


# =============================================================================
# NON-COUNTERPARTY SCORING (label, don't delete)
# =============================================================================

def compute_non_counterparty_score(
    name: str,
    base_compact: str,
    has_shenaseh: bool,
    occurrence_count: int
) -> tuple[int, list[str]]:
    """
    Compute non-counterparty score (0-100).
    Higher = more likely non-counterparty.
    Returns (score, reasons).
    """
    score = 0
    reasons = []
    tokens = set(tokenize(name))
    norm = normalize_canonical(name)
    
    # +20 per accounting token (cap +60)
    acc_count = len(tokens & ACCOUNTING_TOKENS)
    if acc_count > 0:
        score += min(20 * acc_count, 60)
        reasons.append(f"accounting_tokens:{acc_count}")
    
    # +20 if starts with accounting token
    first_token = tokenize(name)[0] if tokenize(name) else ""
    if first_token in ACCOUNTING_TOKENS:
        score += 20
        reasons.append("starts_with_accounting")
    
    # +20 if very short base
    if len(base_compact) <= 3:
        score += 20
        reasons.append("very_short")
    
    # -40 if has PROTECT_TOKENS
    if tokens & PROTECT_TOKENS:
        score -= 40
        reasons.append("has_protect_token")
    
    # -40 if has LEGAL_TOKENS
    if tokens & LEGAL_TOKENS:
        score -= 40
        reasons.append("has_legal_token")
    
    # -40 if valid shenaseh
    if has_shenaseh:
        score -= 40
        reasons.append("has_shenaseh")
    
    # -20 if frequent
    if occurrence_count >= 10:
        score -= 20
        reasons.append("frequent")
    
    return max(0, min(100, score)), reasons


def classify_non_counterparty(score: int) -> str:
    """Classify based on score."""
    if score >= 60:
        return "POTENTIAL_NON_COUNTERPARTY"
    elif score >= 40:
        return "NEEDS_REVIEW"
    else:
        return "COUNTERPARTY"


# =============================================================================
# ENTITY TYPE CLASSIFICATION
# =============================================================================

def classify_entity_type(name: str) -> tuple[str, str, str]:
    """
    Returns (type, confidence, reason).
    """
    tokens = set(tokenize(name))
    
    # Strong: legal tokens
    if tokens & LEGAL_TOKENS or tokens & PROTECT_TOKENS:
        return "COMPANY", "HIGH", "legal_or_protect_token"
    
    # Strong: person titles
    if tokens & PERSON_TITLES:
        return "PERSON", "HIGH", "person_title"
    
    # Weak heuristic: 2-4 tokens, no digits
    norm = normalize_canonical(name)
    toks = norm.split()
    if 2 <= len(toks) <= 4 and not re.search(r"\d", norm):
        if all(len(t) >= 2 for t in toks):
            return "PERSON", "LOW", "name_heuristic"
    
    return "UNKNOWN", "LOW", "no_signals"


# =============================================================================
# UNION-FIND (DSU)
# =============================================================================

class UnionFind:
    """Union-Find with merge locks and method tracking."""
    
    def __init__(self, items: list[str]):
        self.parent = {x: x for x in items}
        self.rank = {x: 0 for x in items}
        self.methods = defaultdict(set)
        self.locks: set[frozenset[str]] = set()  # KEEP_SEPARATE locks
    
    def add_lock(self, a: str, b: str):
        """Add KEEP_SEPARATE lock between a and b."""
        self.locks.add(frozenset([a, b]))
    
    def is_locked(self, a: str, b: str) -> bool:
        """Check if a and b are locked (KEEP_SEPARATE)."""
        return frozenset([a, b]) in self.locks
    
    def find(self, x: str) -> str:
        if x not in self.parent:
            self.parent[x] = x
            self.rank[x] = 0
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        # Path compression
        while self.parent[x] != root:
            next_x = self.parent[x]
            self.parent[x] = root
            x = next_x
        return root
    
    def union(self, a: str, b: str, method: str) -> bool:
        """Union a and b. Returns False if locked or already same."""
        if self.is_locked(a, b):
            return False
        
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            self.methods[ra].add(method)
            return False
        
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        self.methods[ra].update(self.methods[rb])
        self.methods[ra].add(method)
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1
        return True
    
    def get_methods(self, x: str) -> set[str]:
        return self.methods.get(self.find(x), set())


# =============================================================================
# SIMILARITY
# =============================================================================

def compute_similarity(a: str, b: str) -> float:
    """Compute similarity ratio [0, 1]."""
    a_norm = normalize_for_matching(a)
    b_norm = normalize_for_matching(b)
    
    if RAPIDFUZZ_AVAILABLE:
        return rf_fuzz.token_set_ratio(a_norm, b_norm) / 100.0
    else:
        return SequenceMatcher(None, a_norm, b_norm).ratio()


# =============================================================================
# CLEANUP
# =============================================================================

def cleanup_old_outputs(report_dir: Path, mode: str) -> list[str]:
    """
    Clean up old output files.
    Returns list of actions taken.
    """
    actions = []
    
    if mode == "none":
        return actions
    
    # Patterns to clean
    patterns = [
        "Clean_Unique_Counterparties*.xlsx",
        "Clean_Unique_Counterparties*.csv",
        "Entity_Resolution_Decisions*.xlsx",
    ]
    
    # Explicitly protect source file
    source_name = SOURCE_EXCEL_PATH.name
    
    files_to_process = []
    for pattern in patterns:
        for f in report_dir.glob(pattern):
            if f.name == source_name:
                continue  # Never touch source
            if f.name == OUTPUT_EXCEL_PATH.name and mode != "delete":
                continue  # Don't archive the file we're about to write
            files_to_process.append(f)
    
    if not files_to_process:
        return actions
    
    if mode == "archive":
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_dir = report_dir / "_archive" / timestamp
        archive_dir.mkdir(parents=True, exist_ok=True)
        
        for f in files_to_process:
            dest = archive_dir / f.name
            try:
                shutil.move(str(f), str(dest))
                actions.append(f"archived: {f.name} -> {dest}")
            except Exception as e:
                actions.append(f"failed to archive {f.name}: {e}")
    
    elif mode == "delete":
        for f in files_to_process:
            try:
                f.unlink()
                actions.append(f"deleted: {f.name}")
            except Exception as e:
                actions.append(f"failed to delete {f.name}: {e}")
    
    return actions


# =============================================================================
# DATACLASS
# =============================================================================

@dataclass
class NameStats:
    originals: set = field(default_factory=set)
    count: int = 0
    kol_values: set = field(default_factory=set)
    moein_values: set = field(default_factory=set)
    shenaseh_values: set = field(default_factory=set)
    base_name: str = ""
    base_compact: str = ""
    entity_type: str = "UNKNOWN"
    entity_confidence: str = "LOW"
    entity_reason: str = ""
    non_cp_score: int = 0
    non_cp_reasons: list = field(default_factory=list)
    counterparty_flag: str = "COUNTERPARTY"


# =============================================================================
# MAIN PIPELINE
# =============================================================================

def main():
    """Main entry point."""
    # Fix Windows console encoding
    import sys
    import io
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    print("=" * 70)
    print("Clean Unique Counterparties Export (v3 - Safety-First)")
    print("=" * 70)
    
    audit_log = {
        "start_time": datetime.now().isoformat(),
        "config": {
            "auto_merge_threshold": AUTO_MERGE_THRESHOLD,
            "review_threshold": REVIEW_LOW_THRESHOLD,
            "max_block_items": MAX_BLOCK_ITEMS,
            "max_fuzzy_comparisons": MAX_TOTAL_FUZZY_COMPARISONS,
            "cleanup_mode": CLEANUP_MODE,
            "rapidfuzz_available": RAPIDFUZZ_AVAILABLE,
        },
        "cleanup_actions": [],
        "stats": {},
        "performance": {},
    }
    
    # -------------------------------------------------------------------------
    # STEP 0: Cleanup
    # -------------------------------------------------------------------------
    print(f"\n[0/8] Cleaning up old outputs (mode={CLEANUP_MODE})...")
    report_dir = OUTPUT_EXCEL_PATH.parent
    cleanup_actions = cleanup_old_outputs(report_dir, CLEANUP_MODE)
    audit_log["cleanup_actions"] = cleanup_actions
    print(f"      Actions: {len(cleanup_actions)}")
    for action in cleanup_actions[:5]:
        print(f"        - {action}")
    
    # -------------------------------------------------------------------------
    # STEP 1: Load Decisions
    # -------------------------------------------------------------------------
    print("\n[1/8] Loading decisions...")
    
    explicit_merges = []  # (a, b)
    explicit_excludes = set()
    keep_separate = []  # (a, b)
    needs_review_pairs = []  # (a, b)
    
    if DECISIONS_JSON_PATH.exists():
        try:
            with open(DECISIONS_JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            for d in data.get("decisions", []):
                decision = d.get("decision", "")
                a = normalize_canonical(d.get("a_raw", ""))
                b = normalize_canonical(d.get("b_raw", ""))
                
                if decision == "MERGE" and a and b:
                    explicit_merges.append((a, b))
                elif decision in {"EXCLUDE", "EXCLUDE_NON_COUNTERPARTY"}:
                    if a:
                        explicit_excludes.add(a)
                    if b:
                        explicit_excludes.add(b)
                elif decision == "KEEP_SEPARATE" and a and b:
                    keep_separate.append((a, b))
                elif decision == "NEEDS_REVIEW" and a and b:
                    needs_review_pairs.append((a, b, "decision_needs_review"))
            
            print(f"      Merges: {len(explicit_merges)}")
            print(f"      Excludes: {len(explicit_excludes)}")
            print(f"      Keep_Separate: {len(keep_separate)}")
            print(f"      Needs_Review: {len(needs_review_pairs)}")
        except Exception as e:
            print(f"      Warning: {e}")
    else:
        print("      No decisions file found.")
    
    audit_log["stats"]["explicit_merges"] = len(explicit_merges)
    audit_log["stats"]["explicit_excludes"] = len(explicit_excludes)
    audit_log["stats"]["keep_separate_locks"] = len(keep_separate)
    
    # -------------------------------------------------------------------------
    # STEP 2: Load Source Data
    # -------------------------------------------------------------------------
    print("\n[2/8] Loading source Excel...")
    print(f"      Path: {SOURCE_EXCEL_PATH}")
    
    df = pd.read_excel(SOURCE_EXCEL_PATH)
    print(f"      Rows: {len(df):,}")
    
    # Find columns
    col_keywords = {
        "tafsili": ["تفصیلی", "تفصيلي", "تفضیلی", "تفضيلي", "tafsili", "name", "نام"],
        "kol": ["کل"],
        "moein": ["معین", "معين"],
        "shenaseh": ["شناسه"],
    }
    
    def find_col(keywords):
        for c in df.columns:
            cs = str(c).lower()
            for kw in keywords:
                if kw.lower() in cs:
                    return c
        return None
    
    tafsili_col = find_col(col_keywords["tafsili"])
    kol_col = find_col(col_keywords["kol"])
    moein_col = find_col(col_keywords["moein"])
    shenaseh_col = find_col(col_keywords["shenaseh"])
    
    if not tafsili_col:
        print("ERROR: Could not find Tafsili column!")
        return
    
    # Avoid false positive for کل
    if kol_col and "کلاسه" in str(kol_col):
        kol_col = None
    
    print(f"      Tafsili: {tafsili_col}")
    print(f"      Kol: {kol_col}, Moein: {moein_col}, Shenaseh: {shenaseh_col}")
    
    audit_log["stats"]["total_rows"] = len(df)
    
    # -------------------------------------------------------------------------
    # STEP 3: Aggregate by Normalized Name
    # -------------------------------------------------------------------------
    print("\n[3/8] Aggregating by normalized name...")
    
    name_stats: dict[str, NameStats] = {}
    hard_deleted: list[tuple[str, str]] = []  # (name, reason)
    
    for _, row in df.iterrows():
        raw = row.get(tafsili_col)
        if pd.isna(raw) or not str(raw).strip():
            continue
        
        norm = normalize_canonical(str(raw))
        if not norm:
            continue
        
        # Check hard delete
        should_delete, reason = should_hard_delete(norm, explicit_excludes)
        if should_delete:
            hard_deleted.append((norm, reason))
            continue
        
        if norm not in name_stats:
            name_stats[norm] = NameStats()
        
        stats = name_stats[norm]
        stats.originals.add(str(raw).strip())
        stats.count += 1
        
        if kol_col and pd.notna(row.get(kol_col)):
            stats.kol_values.add(str(row.get(kol_col)).strip())
        if moein_col and pd.notna(row.get(moein_col)):
            stats.moein_values.add(str(row.get(moein_col)).strip())
        if shenaseh_col and pd.notna(row.get(shenaseh_col)):
            sh = str(row.get(shenaseh_col)).strip()
            if sh and sh != "nan":
                stats.shenaseh_values.add(sh)
    
    all_names = list(name_stats.keys())
    print(f"      Unique names: {len(all_names):,}")
    print(f"      Hard deleted: {len(hard_deleted)}")
    
    audit_log["stats"]["unique_names"] = len(all_names)
    audit_log["stats"]["hard_deleted"] = len(hard_deleted)
    
    # Compute derived fields
    for name in all_names:
        stats = name_stats[name]
        stats.base_name = compute_base_name(name)
        stats.base_compact = compute_base_compact(stats.base_name)
        
        # Entity type
        etype, econf, ereason = classify_entity_type(name)
        stats.entity_type = etype
        stats.entity_confidence = econf
        stats.entity_reason = ereason
        
        # Non-counterparty score
        has_sh = bool(stats.shenaseh_values)
        score, reasons = compute_non_counterparty_score(
            name, stats.base_compact, has_sh, stats.count
        )
        stats.non_cp_score = score
        stats.non_cp_reasons = reasons
        stats.counterparty_flag = classify_non_counterparty(score)
    
    # -------------------------------------------------------------------------
    # STEP 4: Compute Token Frequencies (for blocking)
    # -------------------------------------------------------------------------
    print("\n[4/8] Computing token frequencies...")
    
    token_counts = defaultdict(int)
    for name in all_names:
        for tok in set(tokenize(name)):
            token_counts[tok] += 1
    
    n_names = len(all_names)
    significant_tokens = {}
    for name in all_names:
        sig_toks = []
        for tok in tokenize(name):
            freq_ratio = token_counts[tok] / n_names if n_names > 0 else 0
            if is_significant_token(tok, freq_ratio):
                sig_toks.append(tok)
        significant_tokens[name] = sig_toks
    
    # -------------------------------------------------------------------------
    # STEP 5: Build Clusters (Union-Find)
    # -------------------------------------------------------------------------
    print("\n[5/8] Building clusters...")
    
    dsu = UnionFind(all_names)
    
    # Stage 0: Apply KEEP_SEPARATE locks
    for a, b in keep_separate:
        if a in name_stats and b in name_stats:
            dsu.add_lock(a, b)
    print(f"      Stage 0 (locks): {len(keep_separate)}")
    
    # Stage 1: Explicit MERGE
    merge_count_1 = sum(
        1 for a, b in explicit_merges
        if a in name_stats and b in name_stats and dsu.union(a, b, "decisions")
    )
    print(f"      Stage 1 (decisions): {merge_count_1}")
    
    # Stage 2: Exact normalized (already aggregated, skip)
    
    # Stage 3: Base-name matching
    base_to_names = defaultdict(list)
    for name in all_names:
        b = name_stats[name].base_name
        if b and len(b.split()) >= 1:
            base_to_names[b].append(name)
    
    merge_count_3 = 0
    for base, names in base_to_names.items():
        if len(names) < 2:
            continue
        # Skip very short bases
        if len(base.split()) == 1 and len(base) <= 3:
            continue
        first = names[0]
        for other in names[1:]:
            if dsu.union(first, other, "base"):
                merge_count_3 += 1
    print(f"      Stage 3 (base): {merge_count_3}")
    
    # Stage 4: Shenaseh-based
    if shenaseh_col:
        shenaseh_to_names = defaultdict(list)
        for name in all_names:
            for sh in name_stats[name].shenaseh_values:
                # Valid shenaseh: >= 5 digits and not common codes
                if len(sh) >= 5 and sh not in {"106", "10600", "10601"}:
                    shenaseh_to_names[sh].append(name)
        
        merge_count_4 = 0
        for sh, names in shenaseh_to_names.items():
            if 2 <= len(names) <= 10:
                first = names[0]
                for other in names[1:]:
                    if dsu.union(first, other, "shenaseh"):
                        merge_count_4 += 1
        print(f"      Stage 4 (shenaseh): {merge_count_4}")
    
    # Stage 5: Fuzzy matching with blocking
    print("      Stage 5 (fuzzy): building blocks...")
    
    # Build blocks: key = (first 2-3 chars of base_compact, one significant token)
    blocks = defaultdict(list)
    for name in all_names:
        bc = name_stats[name].base_compact
        if len(bc) < 2:
            continue
        prefix = bc[:3] if len(bc) >= 3 else bc[:2]
        sig_toks = significant_tokens.get(name, [])
        if sig_toks:
            for tok in sig_toks[:2]:  # Use first 2 significant tokens
                key = (prefix, tok)
                blocks[key].append(name)
        else:
            # Fallback: just prefix
            blocks[(prefix, "")] .append(name)
    
    merge_count_5 = 0
    skipped_blocks = 0
    total_comparisons = 0
    fuzzy_review = []
    
    for key, names in blocks.items():
        if len(names) > MAX_BLOCK_ITEMS:
            skipped_blocks += 1
            # Add all pairs in this block to needs_review
            for i in range(min(5, len(names))):
                for j in range(i + 1, min(10, len(names))):
                    fuzzy_review.append({
                        "Name_A": names[i],
                        "Name_B": names[j],
                        "Score": 0.0,
                        "Reason": "block_too_large",
                    })
            continue
        
        if len(names) < 2:
            continue
        
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                if total_comparisons >= MAX_TOTAL_FUZZY_COMPARISONS:
                    break
                
                a, b = names[i], names[j]
                if dsu.find(a) == dsu.find(b):
                    continue
                
                total_comparisons += 1
                
                base_a = name_stats[a].base_name
                base_b = name_stats[b].base_name
                if not base_a or not base_b:
                    continue
                
                score = compute_similarity(base_a, base_b)
                
                if score >= AUTO_MERGE_THRESHOLD:
                    if dsu.union(a, b, "fuzzy_high"):
                        merge_count_5 += 1
                elif score >= REVIEW_LOW_THRESHOLD:
                    fuzzy_review.append({
                        "Name_A": a,
                        "Name_B": b,
                        "Score": round(score, 4),
                        "Reason": "fuzzy_between_thresholds",
                    })
            
            if total_comparisons >= MAX_TOTAL_FUZZY_COMPARISONS:
                print(f"      WARNING: Hit max fuzzy comparisons cap!")
                break
        
        if total_comparisons >= MAX_TOTAL_FUZZY_COMPARISONS:
            break
    
    print(f"      Stage 5 (fuzzy auto): {merge_count_5}")
    print(f"      Fuzzy comparisons: {total_comparisons:,}")
    print(f"      Skipped blocks: {skipped_blocks}")
    print(f"      Fuzzy review pairs: {len(fuzzy_review)}")
    
    audit_log["performance"] = {
        "fuzzy_comparisons": total_comparisons,
        "skipped_blocks": skipped_blocks,
        "fuzzy_review_pairs": len(fuzzy_review),
    }
    
    # -------------------------------------------------------------------------
    # STEP 6: Build Final Results
    # -------------------------------------------------------------------------
    print("\n[6/8] Building final results...")
    
    # Group by cluster
    clusters = defaultdict(list)
    for name in all_names:
        clusters[dsu.find(name)].append(name)
    
    master_rows = []
    potential_noncp_rows = []
    needs_review_entities = []
    
    for root, members in clusters.items():
        # Aggregate
        total_count = sum(name_stats[m].count for m in members)
        all_originals = set().union(*(name_stats[m].originals for m in members))
        all_kol = set().union(*(name_stats[m].kol_values for m in members))
        all_moein = set().union(*(name_stats[m].moein_values for m in members))
        all_shenaseh = set().union(*(name_stats[m].shenaseh_values for m in members))
        
        # Determine entity type (majority vote, prefer COMPANY)
        types = [name_stats[m].entity_type for m in members]
        if "COMPANY" in types:
            final_type = "COMPANY"
            final_conf = "HIGH"
        elif "PERSON" in types:
            final_type = "PERSON"
            final_conf = max(name_stats[m].entity_confidence for m in members if name_stats[m].entity_type == "PERSON")
        else:
            final_type = "UNKNOWN"
            final_conf = "LOW"
        
        # Counterparty flag (worst case in cluster)
        cp_flags = [name_stats[m].counterparty_flag for m in members]
        if "POTENTIAL_NON_COUNTERPARTY" in cp_flags:
            final_cp_flag = "POTENTIAL_NON_COUNTERPARTY"
        elif "NEEDS_REVIEW" in cp_flags:
            final_cp_flag = "NEEDS_REVIEW"
        else:
            final_cp_flag = "COUNTERPARTY"
        
        # Max non-cp score
        max_ncp_score = max(name_stats[m].non_cp_score for m in members)
        
        # Select canonical
        def canonical_score(m):
            has_legal = bool(set(tokenize(m)) & LEGAL_TOKENS)
            return (name_stats[m].count, 1 if has_legal else 0, len(m))
        
        canonical = max(members, key=canonical_score)
        base = name_stats[canonical].base_name
        
        # Variants preview
        variants_sorted = sorted(all_originals, key=lambda x: (-len(x), x))[:15]
        variants_str = " | ".join(variants_sorted)
        if len(all_originals) > 15:
            variants_str += f" ... (+{len(all_originals) - 15})"
        
        # Merge method
        methods = dsu.get_methods(canonical)
        merge_method = ",".join(sorted(methods)) if methods else "exact"
        
        # Reasons
        all_reasons = []
        for m in members:
            all_reasons.extend(name_stats[m].non_cp_reasons)
        reasons_str = "; ".join(set(all_reasons))
        
        row = {
            "Unique_ID": 0,
            "Canonical_Name": canonical,
            "Base_Name": base,
            "Entity_Type": final_type,
            "Entity_Type_Confidence": final_conf,
            "Occurrence_Count": total_count,
            "Variant_Count": len(all_originals),
            "Shenaseh_Count": len(all_shenaseh),
            "Sample_Kol": next(iter(all_kol), "") if all_kol else "",
            "Sample_Moein": next(iter(all_moein), "") if all_moein else "",
            "Variants": variants_str,
            "Merge_Method": merge_method,
            "Counterparty_Flag": final_cp_flag,
            "NonCounterparty_Score": max_ncp_score,
            "Reasons": reasons_str,
        }
        
        master_rows.append(row)
        
        if final_cp_flag == "POTENTIAL_NON_COUNTERPARTY":
            potential_noncp_rows.append(row.copy())
        elif final_cp_flag == "NEEDS_REVIEW":
            needs_review_entities.append(row.copy())
    
    # Create DataFrames
    master_df = pd.DataFrame(master_rows)
    master_df = master_df.sort_values(
        ["Counterparty_Flag", "Occurrence_Count"],
        ascending=[True, False]
    ).reset_index(drop=True)
    master_df["Unique_ID"] = range(1, len(master_df) + 1)
    
    print(f"      Clusters: {len(clusters)}")
    print(f"      Master rows: {len(master_df)}")
    print(f"      Potential non-CP: {len(potential_noncp_rows)}")
    print(f"      Needs review entities: {len(needs_review_entities)}")
    
    audit_log["stats"]["clusters"] = len(clusters)
    audit_log["stats"]["master_rows"] = len(master_df)
    audit_log["stats"]["potential_noncp"] = len(potential_noncp_rows)
    
    # -------------------------------------------------------------------------
    # STEP 7: Build Review Sheet
    # -------------------------------------------------------------------------
    print("\n[7/8] Building review sheet...")
    
    # Combine all review items
    review_rows = []
    
    # Decision-based needs review pairs
    for a, b, reason in needs_review_pairs:
        if a in name_stats and b in name_stats:
            review_rows.append({
                "Name_A": a,
                "Name_B": b,
                "Base_A": name_stats[a].base_name,
                "Base_B": name_stats[b].base_name,
                "Score": 1.0,  # Explicit
                "Reason": reason,
                "A_Type": name_stats[a].entity_type,
                "B_Type": name_stats[b].entity_type,
            })
    
    # Fuzzy review pairs
    for item in fuzzy_review:
        a, b = item["Name_A"], item["Name_B"]
        review_rows.append({
            "Name_A": a,
            "Name_B": b,
            "Base_A": name_stats[a].base_name if a in name_stats else "",
            "Base_B": name_stats[b].base_name if b in name_stats else "",
            "Score": item["Score"],
            "Reason": item["Reason"],
            "A_Type": name_stats[a].entity_type if a in name_stats else "",
            "B_Type": name_stats[b].entity_type if b in name_stats else "",
        })
    
    # Entities flagged NEEDS_REVIEW
    for row in needs_review_entities:
        review_rows.append({
            "Name_A": row["Canonical_Name"],
            "Name_B": "",
            "Base_A": row["Base_Name"],
            "Base_B": "",
            "Score": 0,
            "Reason": "entity_needs_review",
            "A_Type": row["Entity_Type"],
            "B_Type": "",
        })
    
    review_df = pd.DataFrame(review_rows) if review_rows else pd.DataFrame()
    print(f"      Review rows: {len(review_df)}")
    
    # -------------------------------------------------------------------------
    # STEP 8: Quality Gates & Audit
    # -------------------------------------------------------------------------
    print("\n[8/8] Quality gates & export...")
    
    # Entity type distribution
    type_counts = master_df["Entity_Type"].value_counts().to_dict()
    audit_log["stats"]["by_entity_type"] = type_counts
    print("\n      Entity Types:")
    for t, c in type_counts.items():
        print(f"        {t}: {c:,}")
    
    # Counterparty flag distribution
    flag_counts = master_df["Counterparty_Flag"].value_counts().to_dict()
    audit_log["stats"]["by_counterparty_flag"] = flag_counts
    print("\n      Counterparty Flags:")
    for f, c in flag_counts.items():
        print(f"        {f}: {c:,}")
    
    # Top 30 by occurrence
    top30 = master_df.nlargest(30, "Occurrence_Count")[["Canonical_Name", "Entity_Type", "Occurrence_Count"]].to_dict("records")
    audit_log["top30_by_occurrence"] = top30
    print("\n      Top 10 by Occurrence:")
    for row in top30[:10]:
        print(f"        {row['Occurrence_Count']:>6}  {row['Canonical_Name'][:50]}")
    
    # Missed merge detector
    print("\n      Checking for potential missed merges...")
    master_df["_base_compact"] = master_df["Base_Name"].apply(compute_base_compact)
    dup_bases = master_df["_base_compact"].value_counts()
    dup_bases = dup_bases[dup_bases > 1]
    
    suspicious_duplicates = []
    if len(dup_bases) > 0:
        print(f"      WARNING: {len(dup_bases)} base names appear multiple times")
        for base, cnt in dup_bases.head(20).items():
            if base:
                examples = master_df[master_df["_base_compact"] == base]["Canonical_Name"].tolist()[:3]
                suspicious_duplicates.append({"base": base, "count": cnt, "examples": examples})
                print(f"        '{base}' ({cnt}x): {examples[:2]}")
    else:
        print("      No obvious missed merges detected.")
    
    audit_log["suspicious_duplicates"] = suspicious_duplicates
    master_df = master_df.drop(columns=["_base_compact"])
    
    # Potential non-CP sheet
    potential_noncp_df = pd.DataFrame(potential_noncp_rows) if potential_noncp_rows else pd.DataFrame()
    if not potential_noncp_df.empty:
        potential_noncp_df = potential_noncp_df.sort_values("Occurrence_Count", ascending=False)
    
    # Top 50 potential non-CP for verification
    if not potential_noncp_df.empty:
        top50_noncp = potential_noncp_df.head(50)[["Canonical_Name", "Occurrence_Count", "Reasons"]].to_dict("records")
        audit_log["top50_potential_noncp"] = top50_noncp
        print("\n      Top 10 Potential Non-Counterparty (verify no vital data):")
        for row in top50_noncp[:10]:
            print(f"        {row['Occurrence_Count']:>6}  {row['Canonical_Name'][:50]}")
    
    # Build audit log DataFrame
    audit_rows = []
    for key, val in audit_log.items():
        if isinstance(val, dict):
            for k, v in val.items():
                audit_rows.append({"Category": key, "Key": k, "Value": str(v)[:500]})
        elif isinstance(val, list):
            audit_rows.append({"Category": key, "Key": "count", "Value": len(val)})
            for i, item in enumerate(val[:20]):
                audit_rows.append({"Category": key, "Key": f"item_{i}", "Value": str(item)[:500]})
        else:
            audit_rows.append({"Category": key, "Key": "", "Value": str(val)[:500]})
    
    audit_df = pd.DataFrame(audit_rows)
    
    # Export
    print(f"\n      Exporting to {OUTPUT_EXCEL_PATH}...")
    
    # Reorder master columns
    master_cols = [
        "Unique_ID", "Canonical_Name", "Base_Name", "Entity_Type", "Entity_Type_Confidence",
        "Occurrence_Count", "Variant_Count", "Shenaseh_Count", "Sample_Kol", "Sample_Moein",
        "Variants", "Merge_Method", "Counterparty_Flag", "NonCounterparty_Score", "Reasons"
    ]
    master_df = master_df[[c for c in master_cols if c in master_df.columns]]
    
    with pd.ExcelWriter(OUTPUT_EXCEL_PATH, engine="openpyxl") as writer:
        master_df.to_excel(writer, sheet_name="Master", index=False)
        
        if not review_df.empty:
            review_df.to_excel(writer, sheet_name="Needs_Review", index=False)
        
        if not potential_noncp_df.empty:
            potential_noncp_df.to_excel(writer, sheet_name="Potential_NonCounterparty", index=False)
        
        audit_df.to_excel(writer, sheet_name="Audit_Log", index=False)
    
    print("\n" + "=" * 70)
    print("SUCCESS!")
    print("=" * 70)
    print(f"Output: {OUTPUT_EXCEL_PATH}")
    print(f"Master: {len(master_df):,} counterparties")
    print(f"Needs_Review: {len(review_df):,} items")
    print(f"Potential_NonCounterparty: {len(potential_noncp_df):,} items")
    print(f"Hard deleted: {len(hard_deleted)}")


if __name__ == "__main__":
    main()
