"""T08 — independent reconstruction of the 18 T07 evidence rows that came from one-to-one amount pairing.

Status of this module (read before using its output):
- The T07 pairing code was not stored and T07 kept only counts (sheet «تطابق‌های_مبلغی» and the EV rows of
  «شواهد_و_نمونه‌ها»), not the paired line identifiers. A line-by-line comparison with T07 is therefore impossible.
- This module re-implements the rules T07 *documented* (report §3 and §5; AM-01..AM-16; EV row definitions):
  one-to-one pairing inside a document, equal amount, tiers T3 shared cheque/reference number > T2 same
  party code or same narration > T1 adjacent source row > T0 amount only; shared number takes precedence.
- It is a new, independent reconstruction. Equal counts mean the documented rule is reproducible at count
  level; they do not prove that the original code produced the same lines. Rows whose definition needs no
  pairing judgement (EV-011, EV-016, EV-077 and the bank-equality splits) are labelled separately.

Inputs are read-only (lines loaded by t08_observe.load_lines plus narration/Field1 from the in-memory copy).
"""
from __future__ import annotations

import collections
import re

PERSIAN = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
NUM = re.compile(r"\d{5,}")

DETERMINISTIC = "تعریف مکتوب قطعی"
PAIRING = "جفت‌سازی"

# EV row -> (event, sector, kind, how the line set is formed)
EV_RULES = {
    "EV-010": ("PFE-010", "Terminals", DETERMINISTIC, "همهٔ سطرهای TT-NE-15 روی ۱۱۳-۱-۴، به‌جز سطرهایی که با خروج بانک هم‌مبلغ در همان سند جفت می‌شوند (C-08)"),
    "EV-011": ("PFE-011", "Terminals", DETERMINISTIC, "همهٔ سطرهای TT-NE-15 روی ۱۱۳-۱-۸"),
    "EV-012": ("PFE-012", "Terminals", PAIRING, "AM-06: بستانکار مطالبهٔ FE-60 با بدهکار بانک بدون برچسب، یک‌به‌یک در همان سند (هر دو سطر)"),
    "EV-013": ("PFE-012", "Terminals", PAIRING, "AM-10: چند بستانکار مطالبهٔ هم‌شرح که جمعشان برابر یک بدهکار بانک باقی‌مانده است"),
    "EV-014": ("PFE-013", "Terminals", PAIRING, "AM-05: بدهکار پیش‌دریافت APPLY_PREPAYMENT با بستانکار مطالبهٔ FE-60 (هر دو سطر)"),
    "EV-015": ("PFE-014", "Terminals", PAIRING, "AM-09: بستانکار مطالبهٔ FE-60 با بدهکار ۲۱۲-۶-۵ یا ۲۱۲-۶-۲ (هر دو سطر)"),
    "EV-016": ("PFE-015", "Terminals", DETERMINISTIC, "سطرهای ۴۱۳-۱-۳، ۲۱۱-۱-۱-x و ۲۱۱-۱-۷-۴ در سه سند دارای بستانکار ۴۱۳-۱-۳"),
    "EV-019": ("PFE-018", "Terminals", PAIRING, "AM-02: بستانکار ۱۱۳-۶ CLEAR_COLLECTED با بدهکار بانک بدون برچسب (هر دو سطر)"),
    "EV-022": ("PFE-020", "Terminals", PAIRING, "AM-04: بدهکار پیش‌دریافت جفت‌شده با بستانکار ۱۱۳-۷ (فقط سطر پیش‌دریافت)"),
    "EV-075": ("PFE-051", "Terminals", DETERMINISTIC, "بدهکار ۲۱۱-۱-۷-۴ (TT-NE-11) که خروج بانک هم‌مبلغ در همان سند ندارد"),
    "EV-077": ("PFE-052", "Terminals", DETERMINISTIC, "همهٔ بستانکارهای ۲۱۱-۱-۷-۴"),
    "EV-083": ("PFE-055", "Terminals", DETERMINISTIC, "بدهکار ۲۱۱-۱-۷-۴ (TT-NE-11) با خروج بانک هم‌مبلغ در همان سند"),
    "EV-132": ("PFE-080", "Taxi", PAIRING, "AM-11: بدهکار و بستانکار FE-68 هم‌مبلغ در یک حساب و یک سند با همان کد طرف‌حساب"),
    "EV-133": ("PFE-080", "Terminals", PAIRING, "AM-11: همان قاعده در پایانه‌ها"),
    "EV-136": ("PFE-083", "Terminals", PAIRING, "TT-NE-11 روی ۲۱۱-۱-۶-۲۰ و ۲۱۱-۱-۱-x، بیرون از سه سند کارگزاری و بیرون از جفت‌های AM-07"),
    "EV-164": ("PFE-101", "Terminals", PAIRING, "AM-07 و AM-08: بستانکار مطالبهٔ FE-60 با بدهکار ۲۱۱-۱-۱-x یا بدهکار مطالبه (هر دو سطر)"),
    "EV-169": ("PFE-104", "Terminals", PAIRING, "AM-12: بستانکار ۲۱۱-۱-۱-۳ یا ۵ بدون برچسب با بدهکار بانک (هر دو سطر)"),
    "EV-170": ("PFE-105", "Terminals", PAIRING, "AM-03: بستانکار ۱۱۳-۶ CLEAR_COLLECTED بدون بانک با بدهکار پیش‌دریافت (هر دو سطر)"),
}


def _refs(text, f1, exclude):
    out = set()
    for src in (text or "", str(f1 or "") if str(f1 or "").strip().isdigit() else ""):
        for m in NUM.findall(src.translate(PERSIAN)):
            v = m.lstrip("0")
            if v and v not in exclude:
                out.add(v)
    return out


def _norm(text):
    t = (text or "").translate(PERSIAN).replace("ي", "ی").replace("ك", "ک").replace("\u200c", " ")
    return " ".join(t.split())


def reconstruct(mem, lines):
    """Return (sets per EV id, tier counts per AM id, notes)."""
    extra = {}
    for sid, sharh, f1, src_row in mem.execute("select sid, coalesce(sharh_norm, sharh, ''), f1, src_row from sanad"):
        extra[sid] = (sharh, f1, src_row)
    events = dict(mem.execute("select sid, coalesce(own_event, '') from line_event"))
    actions = dict(mem.execute("select sid, coalesce(lifecycle_action, '') from line_event"))
    # organisation bank-account numbers must not count as shared references
    exclude = set()
    for (h, name) in mem.execute("select hcode, name from hesab where hcode like '111-%' or hcode like '113-6-%' or hcode like '211-5-%'"):
        for part in h.split("-"):
            if len(part) >= 5 and part.isdigit():
                exclude.add(part.lstrip("0"))
        for m in NUM.findall((name or "").translate(PERSIAN)):
            exclude.add(m.lstrip("0"))
    constant = collections.defaultdict(set)  # party codes seen on bank lines are not counterparties
    for sid, l in lines.items():
        if l["bank"] and l["person"]:
            constant[l["org"]].add(l["person"])

    rec = {}
    for sid, l in lines.items():
        if l["kind"] != "REGULAR":
            continue
        sharh, f1, src_row = extra[sid]
        rec[sid] = dict(sid=sid, org=l["org"], doc=l["doc"], row=src_row, h=l["h"], dr=l["dr"], amt=l["amt"],
                        person=l["person"] if l["person"] not in constant[l["org"]] else None,
                        refs=_refs(sharh, f1, exclude), text=_norm(sharh), ev=events.get(sid, ""),
                        act=actions.get(sid, ""))
    by_doc = collections.defaultdict(list)
    for r in rec.values():
        by_doc[r["doc"]].append(r)

    used = set()
    tiers = {}

    def tier_ok(t, a, b):
        if t == "T3":
            return bool(a["refs"] & b["refs"])
        if t == "T2":
            return (a["person"] is not None and a["person"] == b["person"]) or (len(a["text"]) >= 3 and a["text"] == b["text"])
        if t == "T1":
            return abs(a["row"] - b["row"]) == 1
        return True

    def pair(am, left_pred, right_pred, mark=True):
        pairs = []
        counts = collections.Counter()
        for doc, rows in by_doc.items():
            lefts = sorted((r for r in rows if r["sid"] not in used and left_pred(r)), key=lambda r: r["row"])
            rights = [r for r in rows if r["sid"] not in used and right_pred(r)]
            if not lefts or not rights:
                continue
            taken = set()
            for t in ("T3", "T2", "T1", "T0"):
                for a in lefts:
                    if a["sid"] in taken:
                        continue
                    cands = [b for b in rights if b["sid"] not in taken and b["amt"] == a["amt"] and b["sid"] != a["sid"]
                             and tier_ok(t, a, b)]
                    if cands:
                        b = min(cands, key=lambda b: abs(b["row"] - a["row"]))
                        taken |= {a["sid"], b["sid"]}
                        pairs.append((a["sid"], b["sid"], t))
                        counts[t] += 1
        if mark:
            for a, b, _ in pairs:
                used.add(a)
                used.add(b)
        tiers[am] = dict(pairs=len(pairs), **counts)
        return pairs

    T = lambda r: r["org"] == "Terminals"
    bank_dr = lambda r: T(r) and r["h"].startswith("111-") and r["dr"] and not r["ev"]
    bank_cr = lambda r: T(r) and r["h"].startswith("111-") and not r["dr"]
    cc = lambda r: T(r) and r["h"].startswith("113-6-") and not r["dr"] and r["act"] == "CLEAR_COLLECTED"
    ap = lambda r: T(r) and r["h"] == "213-2-4-2" and r["dr"] and r["act"] == "APPLY_PREPAYMENT"
    r7 = lambda r: T(r) and r["h"].startswith("113-7") and not r["dr"]
    claim_cr = lambda r: T(r) and (r["h"].startswith("113-1-4-") or r["h"].startswith("113-1-8-")) and not r["dr"] and r["ev"] == "FE-60"
    d211 = lambda r: T(r) and r["h"].startswith("211-1-1-") and r["dr"] and r["ev"] == "TT-NE-11"
    claim_dr = lambda r: T(r) and (r["h"].startswith("113-1-4-") or r["h"].startswith("113-1-8-")) and r["dr"] and r["ev"] in ("FE-68", "TT-NE-15")
    dep_dr = lambda r: T(r) and (r["h"].startswith("212-6-5") or r["h"].startswith("212-6-2")) and r["dr"] and r["ev"] in ("TT-NE-18", "FE-18")
    x211 = lambda r: T(r) and r["h"] in ("211-1-1-3", "211-1-1-5") and not r["dr"] and not r["ev"]

    # AM-11 (neutral FE-68 pairs): Dr and Cr of equal amount in the same account and document. T07 kept the
    # pairs with the same party code as PFE-080 and reported the rest (different party) separately.
    am11 = []
    am11_other = 0
    for doc, rows in by_doc.items():
        fe = [r for r in rows if r["ev"] == "FE-68"]
        if len(fe) < 2:
            continue
        taken = set()
        for same_party in (True, False):
            for a in sorted((r for r in fe if r["dr"]), key=lambda r: r["row"]):
                if a["sid"] in taken:
                    continue
                cands = [b for b in fe if not b["dr"] and b["sid"] not in taken and b["h"] == a["h"] and b["amt"] == a["amt"]
                         and ((a["person"] or "") == (b["person"] or "")) == same_party]
                if cands:
                    b = min(cands, key=lambda b: abs(b["row"] - a["row"]))
                    taken |= {a["sid"], b["sid"]}
                    if same_party:
                        am11.append((a["sid"], b["sid"], "T2"))
                    else:
                        am11_other += 2
    tiers["AM-11"] = dict(pairs=len(am11), T2=len(am11), other_lines=am11_other)
    am02 = pair("AM-02", cc, bank_dr)
    am03 = pair("AM-03", cc, ap)
    am04 = pair("AM-04", r7, ap)
    am05 = pair("AM-05", ap, claim_cr)
    am06 = pair("AM-06", claim_cr, bank_dr)
    am07 = pair("AM-07", claim_cr, d211)
    am08 = pair("AM-08", claim_cr, claim_dr)
    am09 = pair("AM-09", claim_cr, dep_dr)
    # AM-10: several same-narration claim lines summing to one remaining bank line
    am10 = []
    for doc, rows in by_doc.items():
        groups = collections.defaultdict(list)
        for r in rows:
            if r["sid"] not in used and claim_cr(r) and r["text"]:
                groups[r["text"]].append(r)
        banks = [r for r in rows if r["sid"] not in used and bank_dr(r)]
        for g in groups.values():
            if len(g) < 2:
                continue
            total = sum(r["amt"] for r in g)
            hit = next((b for b in banks if b["amt"] == total and b["sid"] not in used), None)
            if hit:
                am10 += [r["sid"] for r in g] + [hit["sid"]]
                used.update(am10)
    tiers["AM-10"] = dict(lines=len(am10))
    am12 = pair("AM-12", x211, bank_dr)
    # bank-equality splits used by deterministic rows
    tt15 = lambda r: T(r) and r["ev"] == "TT-NE-15" and r["h"].startswith("113-1-4-") and r["dr"]
    c08 = pair("C-08", tt15, bank_cr, mark=False)
    vat_dr = lambda r: T(r) and r["h"] == "211-1-7-4" and r["dr"] and r["ev"] == "TT-NE-11"
    v83 = pair("EV-083", vat_dr, bank_cr, mark=False)

    both = lambda ps: sorted({s for a, b, _ in ps for s in (a, b)})
    term_reg = [r for r in rec.values() if T(r)]
    brokerage_docs = {r["doc"] for r in term_reg if r["h"].startswith("413-1-3") and not r["dr"]}
    c08_lines = {a for a, _, _ in c08}
    v83_lines = {a for a, _, _ in v83}
    am07_211 = {b for _, b, _ in am07}
    sets = {
        "EV-010": sorted(r["sid"] for r in term_reg if r["ev"] == "TT-NE-15" and r["h"].startswith("113-1-4") and r["sid"] not in c08_lines),
        "EV-011": sorted(r["sid"] for r in term_reg if r["ev"] == "TT-NE-15" and r["h"].startswith("113-1-8")),
        "EV-012": both(am06),
        "EV-013": sorted(am10),
        "EV-014": both(am05),
        "EV-015": both(am09),
        "EV-016": sorted(r["sid"] for r in term_reg if r["doc"] in brokerage_docs and (
            (r["h"].startswith("413-1-3") and not r["dr"]) or (r["h"].startswith("211-1-1-") and r["dr"])
            or (r["h"] == "211-1-7-4" and not r["dr"]))),
        "EV-019": both(am02),
        "EV-022": sorted(b for _, b, _ in am04),
        "EV-075": sorted(r["sid"] for r in term_reg if vat_dr(r) and r["sid"] not in v83_lines),
        "EV-077": sorted(r["sid"] for r in term_reg if r["h"] == "211-1-7-4" and not r["dr"]),
        "EV-083": sorted(v83_lines),
        "EV-132": both([p for p in am11 if rec[p[0]]["org"] == "Taxi"]),
        "EV-133": both([p for p in am11 if rec[p[0]]["org"] == "Terminals"]),
        "EV-136": sorted(r["sid"] for r in term_reg if r["ev"] == "TT-NE-11" and (r["h"] == "211-1-6-20" or r["h"].startswith("211-1-1-"))
                         and r["doc"] not in brokerage_docs and r["sid"] not in am07_211),
        "EV-164": both(am07) + both(am08),
        "EV-169": both(am12),
        "EV-170": both(am03),
    }
    return sets, tiers
