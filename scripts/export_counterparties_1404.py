#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
export_counterparties_1404.py
=============================

Entity resolution for اطلاعات حسابداری1404.xlsx
Same algorithm as export_clean_counterparties.py (v3 Safety-First)
with additional column for سرفصل کلی (TitkNam).
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

try:
    from rapidfuzz import fuzz as rf_fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    from difflib import SequenceMatcher
    RAPIDFUZZ_AVAILABLE = False

# =============================================================================
# CONFIGURATION
# =============================================================================

SOURCE_EXCEL_PATH = Path(r"f:\Freelancing_Project\KalaniProject\municipality_demo\data\reports\اطلاعات حسابداری1404.xlsx")
OUTPUT_EXCEL_PATH = Path(r"f:\Freelancing_Project\KalaniProject\municipality_demo\data\reports\Clean_Counterparties_1404.xlsx")

# Column mappings for this file
TAFSILI_COL = "شرح سرفصل حساب تفضیلی"  # Person/Company names
JOZV_COL = "شرح سرفصل حساب جزء"        # Contract/Project
KOL_NAME_COL = "TitkNam"                # سرفصل کل name
KOL_NO_COL = "TitkNo"                   # سرفصل کل number
MOEIN_COL = "شرح سرفصل حساب معین"       # معین

# Thresholds
AUTO_MERGE_THRESHOLD = 0.97
REVIEW_LOW_THRESHOLD = 0.90
MAX_BLOCK_ITEMS = 250
MAX_TOTAL_FUZZY_COMPARISONS = 200_000
TOKEN_FREQUENCY_THRESHOLD = 0.02

# =============================================================================
# TOKEN LISTS
# =============================================================================

LEGAL_TOKENS = {
    "شرکت", "شركت", "موسسه", "مؤسسه", "سهامی", "سهامي",
    "تعاونی", "تعاوني", "هلدینگ", "هلدينگ", "گروه",
    "پیمانکاری", "پيمانكاري", "تولیدی", "توليدي",
    "خدماتی", "خدماتي", "بازرگانی", "بازرگاني",
    "صنایع", "صنايع", "صنعتی", "صنعتي",
}

PERSON_TITLES = {
    "آقای", "آقاي", "اقای", "اقاي", "آقا",
    "خانم", "خانوم", "دکتر", "دكتر",
    "مهندس", "حاج", "حاجی", "حاجي",
    "سید", "سيد", "سیده", "سيده",
}

GENERIC_ORG_WORDS = {"سازمان", "اداره", "مدیریت", "مديريت", "معاونت", "واحد"}

PROTECT_TOKENS = {
    "بانک", "بانك", "بیمه", "بيمه",
    "شهرداری", "شهرداري", "دانشگاه",
    "بیمارستان", "بيمارستان", "صندوق",
}

ACCOUNTING_TOKENS = {
    "هزینه", "هزينه", "درآمد", "مخارج", "حقوق", "دستمزد",
    "تنخواه", "جاری", "جاري", "متفرقه",
    "بستانکار", "بستانكار", "بدهکار", "بدهكار",
    "بدهکاران", "بدهكاران", "بستانکاران", "بستانكاران",
    "حساب", "ذخیره", "ذخيره", "اندوخته",
    "استهلاک", "استهلاك", "پیش پرداخت", "پيش پرداخت",
    "دریافتنی", "دريافتني", "پرداختنی", "پرداختني",
    "فروش", "خرید", "خريد", "مالیات", "ماليات", "عوارض",
}

NOISE_TOKENS = {"و", "یا", "يا", "با", "در", "از", "به", "تا"}

HARD_DELETE_PATTERNS = [
    re.compile(r"^\d+$"),
    re.compile(r"^(سال|ماه)\s*\d{2,4}$"),
    re.compile(r"^\d{4}$"),
    re.compile(r"^(پروژه|احداث|ساخت|تکمیل|بازسازی)\b", re.UNICODE),
]

# =============================================================================
# NORMALIZATION
# =============================================================================

AR2FA_MAP = {
    "ي": "ی", "ك": "ک", "ة": "ه", "ؤ": "و", "إ": "ا", "أ": "ا",
    "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4",
    "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9",
}

AR2FA_MATCHING = AR2FA_MAP.copy()
AR2FA_MATCHING["آ"] = "ا"

DIACRITICS_RE = re.compile(r"[\u064b-\u065f\u0670\u06d6-\u06ed]")
TATWEEL_RE = re.compile(r"\u0640")
ZWNJ = "\u200c"
PUNCT_RE = re.compile(r"[^\w\s\u0600-\u06FF]")


def normalize_canonical(text: str) -> str:
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
    s = normalize_canonical(text)
    for ar, fa in AR2FA_MATCHING.items():
        s = s.replace(ar, fa)
    return s.lower()


# =============================================================================
# TOKEN PROCESSING
# =============================================================================

def tokenize(text: str) -> list[str]:
    s = normalize_canonical(text)
    return [t for t in s.split() if t and t not in NOISE_TOKENS]


def compute_base_name(name: str) -> str:
    tokens = tokenize(name)
    if not tokens:
        return ""
    has_protect = any(t in PROTECT_TOKENS for t in tokens)
    if has_protect:
        cleaned = [t for t in tokens if t not in PERSON_TITLES]
    else:
        removable = LEGAL_TOKENS | PERSON_TITLES | GENERIC_ORG_WORDS
        cleaned = [t for t in tokens if t not in removable]
    return " ".join(cleaned) if cleaned else " ".join(tokens)


def compute_base_compact(base_name: str) -> str:
    return normalize_for_matching(base_name).replace(" ", "")


def is_significant_token(token: str, freq_ratio: float) -> bool:
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

def should_hard_delete(name: str) -> tuple[bool, str]:
    norm = normalize_canonical(name)
    for pattern in HARD_DELETE_PATTERNS:
        if pattern.match(norm):
            return True, f"pattern:{pattern.pattern}"
    return False, ""


# =============================================================================
# NON-COUNTERPARTY SCORING
# =============================================================================

def compute_non_counterparty_score(
    name: str, base_compact: str, occurrence_count: int
) -> tuple[int, list[str]]:
    score = 0
    reasons = []
    tokens = set(tokenize(name))
    
    acc_count = len(tokens & ACCOUNTING_TOKENS)
    if acc_count > 0:
        score += min(20 * acc_count, 60)
        reasons.append(f"accounting_tokens:{acc_count}")
    
    first_token = tokenize(name)[0] if tokenize(name) else ""
    if first_token in ACCOUNTING_TOKENS:
        score += 20
        reasons.append("starts_with_accounting")
    
    if len(base_compact) <= 3:
        score += 20
        reasons.append("very_short")
    
    if tokens & PROTECT_TOKENS:
        score -= 40
        reasons.append("has_protect_token")
    
    if tokens & LEGAL_TOKENS:
        score -= 40
        reasons.append("has_legal_token")
    
    if occurrence_count >= 10:
        score -= 20
        reasons.append("frequent")
    
    return max(0, min(100, score)), reasons


def classify_non_counterparty(score: int) -> str:
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
    tokens = set(tokenize(name))
    if tokens & LEGAL_TOKENS or tokens & PROTECT_TOKENS:
        return "COMPANY", "HIGH", "legal_or_protect_token"
    if tokens & PERSON_TITLES:
        return "PERSON", "HIGH", "person_title"
    norm = normalize_canonical(name)
    toks = norm.split()
    if 2 <= len(toks) <= 4 and not re.search(r"\d", norm):
        if all(len(t) >= 2 for t in toks):
            return "PERSON", "LOW", "name_heuristic"
    return "UNKNOWN", "LOW", "no_signals"


# =============================================================================
# UNION-FIND
# =============================================================================

class UnionFind:
    def __init__(self, items: list[str]):
        self.parent = {x: x for x in items}
        self.rank = {x: 0 for x in items}
        self.methods = defaultdict(set)
    
    def find(self, x: str) -> str:
        if x not in self.parent:
            self.parent[x] = x
            self.rank[x] = 0
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:
            next_x = self.parent[x]
            self.parent[x] = root
            x = next_x
        return root
    
    def union(self, a: str, b: str, method: str) -> bool:
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
    a_norm = normalize_for_matching(a)
    b_norm = normalize_for_matching(b)
    if RAPIDFUZZ_AVAILABLE:
        return rf_fuzz.token_set_ratio(a_norm, b_norm) / 100.0
    else:
        return SequenceMatcher(None, a_norm, b_norm).ratio()


# =============================================================================
# DATACLASS
# =============================================================================

@dataclass
class NameStats:
    originals: set = field(default_factory=set)
    count: int = 0
    kol_names: set = field(default_factory=set)   # سرفصل کل names
    kol_numbers: set = field(default_factory=set)  # سرفصل کل numbers
    moein_values: set = field(default_factory=set)
    jozv_values: set = field(default_factory=set)  # Contract/Project
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
    import sys
    import io
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    print("=" * 70)
    print("Entity Resolution for اطلاعات حسابداری 1404")
    print("=" * 70)
    
    # -------------------------------------------------------------------------
    # STEP 1: Load Source Data
    # -------------------------------------------------------------------------
    print("\n[1/6] Loading source Excel...")
    print(f"      Path: {SOURCE_EXCEL_PATH}")
    
    df = pd.read_excel(SOURCE_EXCEL_PATH)
    print(f"      Rows: {len(df):,}")
    print(f"      Columns: {list(df.columns)[:8]}...")
    
    # Verify columns exist
    if TAFSILI_COL not in df.columns:
        print(f"ERROR: Column '{TAFSILI_COL}' not found!")
        return
    
    print(f"      Tafsili: {TAFSILI_COL}")
    print(f"      Kol Name: {KOL_NAME_COL}")
    print(f"      Jozv: {JOZV_COL}")
    
    # -------------------------------------------------------------------------
    # STEP 2: Aggregate by Normalized Name
    # -------------------------------------------------------------------------
    print("\n[2/6] Aggregating by normalized name...")
    
    name_stats: dict[str, NameStats] = {}
    hard_deleted: list[tuple[str, str]] = []
    
    for _, row in df.iterrows():
        raw = row.get(TAFSILI_COL)
        if pd.isna(raw) or not str(raw).strip():
            continue
        
        norm = normalize_canonical(str(raw))
        if not norm:
            continue
        
        # Check hard delete
        should_delete, reason = should_hard_delete(norm)
        if should_delete:
            hard_deleted.append((norm, reason))
            continue
        
        if norm not in name_stats:
            name_stats[norm] = NameStats()
        
        stats = name_stats[norm]
        stats.originals.add(str(raw).strip())
        stats.count += 1
        
        # Collect سرفصل کل
        if KOL_NAME_COL in df.columns and pd.notna(row.get(KOL_NAME_COL)):
            stats.kol_names.add(str(row.get(KOL_NAME_COL)).strip())
        if KOL_NO_COL in df.columns and pd.notna(row.get(KOL_NO_COL)):
            stats.kol_numbers.add(str(int(row.get(KOL_NO_COL))))
        
        # Collect معین
        if MOEIN_COL in df.columns and pd.notna(row.get(MOEIN_COL)):
            stats.moein_values.add(str(row.get(MOEIN_COL)).strip())
        
        # Collect جزء (contracts)
        if JOZV_COL in df.columns and pd.notna(row.get(JOZV_COL)):
            jozv = str(row.get(JOZV_COL)).strip()
            if len(jozv) > 3:  # Skip very short values
                stats.jozv_values.add(jozv[:100])  # Truncate long values
    
    all_names = list(name_stats.keys())
    print(f"      Unique names: {len(all_names):,}")
    print(f"      Hard deleted: {len(hard_deleted)}")
    
    # Compute derived fields
    for name in all_names:
        stats = name_stats[name]
        stats.base_name = compute_base_name(name)
        stats.base_compact = compute_base_compact(stats.base_name)
        etype, econf, ereason = classify_entity_type(name)
        stats.entity_type = etype
        stats.entity_confidence = econf
        stats.entity_reason = ereason
        score, reasons = compute_non_counterparty_score(name, stats.base_compact, stats.count)
        stats.non_cp_score = score
        stats.non_cp_reasons = reasons
        stats.counterparty_flag = classify_non_counterparty(score)
    
    # -------------------------------------------------------------------------
    # STEP 3: Build Clusters
    # -------------------------------------------------------------------------
    print("\n[3/6] Building clusters...")
    
    dsu = UnionFind(all_names)
    
    # Stage 1: Base-name matching
    base_to_names = defaultdict(list)
    for name in all_names:
        b = name_stats[name].base_name
        if b and len(b.split()) >= 1:
            base_to_names[b].append(name)
    
    merge_count_base = 0
    for base, names in base_to_names.items():
        if len(names) < 2:
            continue
        if len(base.split()) == 1 and len(base) <= 3:
            continue
        first = names[0]
        for other in names[1:]:
            if dsu.union(first, other, "base"):
                merge_count_base += 1
    print(f"      Stage 1 (base): {merge_count_base}")
    
    # Stage 2: Fuzzy matching with blocking
    print("      Stage 2 (fuzzy): building blocks...")
    
    # Compute token frequencies
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
    
    blocks = defaultdict(list)
    for name in all_names:
        bc = name_stats[name].base_compact
        if len(bc) < 2:
            continue
        prefix = bc[:3] if len(bc) >= 3 else bc[:2]
        sig_toks = significant_tokens.get(name, [])
        if sig_toks:
            for tok in sig_toks[:2]:
                blocks[(prefix, tok)].append(name)
        else:
            blocks[(prefix, "")].append(name)
    
    merge_count_fuzzy = 0
    skipped_blocks = 0
    total_comparisons = 0
    fuzzy_review = []
    
    for key, names in blocks.items():
        if len(names) > MAX_BLOCK_ITEMS:
            skipped_blocks += 1
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
                        merge_count_fuzzy += 1
                elif score >= REVIEW_LOW_THRESHOLD:
                    fuzzy_review.append({
                        "Name_A": a, "Name_B": b,
                        "Base_A": base_a, "Base_B": base_b,
                        "Score": round(score, 4),
                        "Reason": "fuzzy_between_thresholds",
                    })
            
            if total_comparisons >= MAX_TOTAL_FUZZY_COMPARISONS:
                break
        if total_comparisons >= MAX_TOTAL_FUZZY_COMPARISONS:
            break
    
    print(f"      Stage 2 (fuzzy): {merge_count_fuzzy}")
    print(f"      Fuzzy comparisons: {total_comparisons:,}")
    print(f"      Skipped blocks: {skipped_blocks}")
    print(f"      Review pairs: {len(fuzzy_review)}")
    
    # -------------------------------------------------------------------------
    # STEP 4: Build Final Results
    # -------------------------------------------------------------------------
    print("\n[4/6] Building final results...")
    
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
        all_kol_names = set().union(*(name_stats[m].kol_names for m in members))
        all_kol_numbers = set().union(*(name_stats[m].kol_numbers for m in members))
        all_moein = set().union(*(name_stats[m].moein_values for m in members))
        all_jozv = set().union(*(name_stats[m].jozv_values for m in members))
        
        # Entity type
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
        
        # Counterparty flag
        cp_flags = [name_stats[m].counterparty_flag for m in members]
        if "POTENTIAL_NON_COUNTERPARTY" in cp_flags:
            final_cp_flag = "POTENTIAL_NON_COUNTERPARTY"
        elif "NEEDS_REVIEW" in cp_flags:
            final_cp_flag = "NEEDS_REVIEW"
        else:
            final_cp_flag = "COUNTERPARTY"
        
        max_ncp_score = max(name_stats[m].non_cp_score for m in members)
        
        # Canonical selection
        def canonical_score(m):
            has_legal = bool(set(tokenize(m)) & LEGAL_TOKENS)
            return (name_stats[m].count, 1 if has_legal else 0, len(m))
        
        canonical = max(members, key=canonical_score)
        base = name_stats[canonical].base_name
        
        # Variants preview
        variants_sorted = sorted(all_originals, key=lambda x: (-len(x), x))[:10]
        variants_str = " | ".join(variants_sorted)
        if len(all_originals) > 10:
            variants_str += f" ... (+{len(all_originals) - 10})"
        
        # Kol names preview
        kol_names_sorted = sorted(all_kol_names)[:5]
        kol_names_str = " | ".join(kol_names_sorted)
        if len(all_kol_names) > 5:
            kol_names_str += f" (+{len(all_kol_names) - 5})"
        
        # Kol numbers
        kol_numbers_str = ", ".join(sorted(all_kol_numbers)[:10])
        
        # Jozv (contracts) preview
        jozv_sorted = sorted(all_jozv, key=len)[:3]
        jozv_str = " | ".join([j[:50] for j in jozv_sorted])
        if len(all_jozv) > 3:
            jozv_str += f" ... (+{len(all_jozv) - 3})"
        
        # Merge method
        methods = dsu.get_methods(canonical)
        merge_method = ",".join(sorted(methods)) if methods else "exact"
        
        row = {
            "Unique_ID": 0,
            "Canonical_Name": canonical,
            "Base_Name": base,
            "Entity_Type": final_type,
            "Entity_Type_Conf": final_conf,
            "Occurrence_Count": total_count,
            "Variant_Count": len(all_originals),
            "Kol_Names": kol_names_str,           # سرفصل کل - NEW!
            "Kol_Numbers": kol_numbers_str,       # کد سرفصل کل - NEW!
            "Sample_Moein": next(iter(all_moein), "") if all_moein else "",
            "Contract_Sample": jozv_str,          # نمونه قرارداد - NEW!
            "Contract_Count": len(all_jozv),
            "Variants": variants_str,
            "Merge_Method": merge_method,
            "Counterparty_Flag": final_cp_flag,
            "NonCP_Score": max_ncp_score,
        }
        
        master_rows.append(row)
        
        if final_cp_flag == "POTENTIAL_NON_COUNTERPARTY":
            potential_noncp_rows.append(row.copy())
        elif final_cp_flag == "NEEDS_REVIEW":
            needs_review_entities.append(row.copy())
    
    # Create DataFrame
    master_df = pd.DataFrame(master_rows)
    master_df = master_df.sort_values(
        ["Counterparty_Flag", "Occurrence_Count"],
        ascending=[True, False]
    ).reset_index(drop=True)
    master_df["Unique_ID"] = range(1, len(master_df) + 1)
    
    print(f"      Clusters: {len(clusters)}")
    print(f"      Master rows: {len(master_df)}")
    print(f"      Potential non-CP: {len(potential_noncp_rows)}")
    print(f"      Needs review: {len(needs_review_entities)}")
    
    # -------------------------------------------------------------------------
    # STEP 5: Quality Gates
    # -------------------------------------------------------------------------
    print("\n[5/6] Quality gates...")
    
    type_counts = master_df["Entity_Type"].value_counts()
    print("\n      Entity Types:")
    for t, c in type_counts.items():
        print(f"        {t}: {c:,}")
    
    print("\n      Top 15 by Occurrence:")
    top15 = master_df.nlargest(15, "Occurrence_Count")[["Canonical_Name", "Entity_Type", "Occurrence_Count", "Kol_Names"]]
    for _, row in top15.iterrows():
        print(f"        {row['Occurrence_Count']:>6}  [{row['Entity_Type'][:4]}]  {row['Canonical_Name'][:40]}  | {row['Kol_Names'][:30]}")
    
    # Check for "نیک اندیش"
    nik_matches = master_df[master_df["Canonical_Name"].str.contains("نیک", na=False)]
    print(f"\n      Entries containing 'نیک': {len(nik_matches)}")
    for _, row in nik_matches.iterrows():
        print(f"        - {row['Canonical_Name']}")
    
    # -------------------------------------------------------------------------
    # STEP 6: Export
    # -------------------------------------------------------------------------
    print("\n[6/6] Exporting to Excel...")
    
    # Reorder columns
    column_order = [
        "Unique_ID", "Canonical_Name", "Base_Name", "Entity_Type", "Entity_Type_Conf",
        "Occurrence_Count", "Variant_Count",
        "Kol_Names", "Kol_Numbers",  # سرفصل کل
        "Sample_Moein", "Contract_Sample", "Contract_Count",
        "Variants", "Merge_Method", "Counterparty_Flag", "NonCP_Score"
    ]
    master_df = master_df[[c for c in column_order if c in master_df.columns]]
    
    with pd.ExcelWriter(OUTPUT_EXCEL_PATH, engine="openpyxl") as writer:
        master_df.to_excel(writer, sheet_name="Master", index=False)
        
        if fuzzy_review:
            review_df = pd.DataFrame(fuzzy_review)
            review_df.to_excel(writer, sheet_name="Needs_Review", index=False)
        
        if potential_noncp_rows:
            noncp_df = pd.DataFrame(potential_noncp_rows)
            noncp_df.to_excel(writer, sheet_name="Potential_NonCounterparty", index=False)
    
    print("\n" + "=" * 70)
    print("SUCCESS!")
    print("=" * 70)
    print(f"Output: {OUTPUT_EXCEL_PATH}")
    print(f"Master: {len(master_df):,} counterparties")
    print(f"Needs_Review: {len(fuzzy_review):,} pairs")
    print(f"Potential_NonCP: {len(potential_noncp_rows):,} items")


if __name__ == "__main__":
    main()
