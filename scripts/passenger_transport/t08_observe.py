"""T08 observed layer (A): what the Taxi/Terminals ledgers actually carry.

Read-only inputs:
- data/work/taxi_terminals/tt_v21.sqlite (opened mode=ro, copied into memory, indexed there)
- T07 workbook (financial_event_review_v0_1.xlsx): population table, evidence selectors
- T05 workbook (activity_cost_center_review_v0_1.xlsx): only for reference counts

Output: data/work/passenger_transport/t08_observed.json (consumed by t08_build.py).
No source, prior deliverable or application code is modified.
"""
from __future__ import annotations

import collections
import hashlib
import itertools
import json
import re
import sqlite3
import statistics
import sys
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parent))
import t08_pairing  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "data/work/taxi_terminals/tt_v21.sqlite"
T07 = ROOT / "data/deliverables/passenger_transport/financial_event_review_v0_1.xlsx"
T07_MD = ROOT / "docs/project/passenger_transport_financial_event_review_v0_1.md"
T05 = ROOT / "data/deliverables/passenger_transport/activity_cost_center_review_v0_1.xlsx"
OUT = ROOT / "data/work/passenger_transport/t08_observed.json"

REVIEW_KINDS = ("REGULAR", "INTERNAL_SETTLEMENT")
ORG_FA = {"Taxi": "تاکسیرانی", "Terminals": "پایانه‌ها"}
FA_ORG = {v: k for k, v in ORG_FA.items()}
TERMINAL_CODES = {"001", "002", "003", "004", "007"}
HQ_CODES = {"005", "006", "008"}
MONTHS = ["فروردين", "فروردین", "ارديبهشت", "اردیبهشت", "خرداد", "تير", "تیر", "مرداد", "شهريور",
          "شهریور", "مهر", "آبان", "آذر", "دي ماه", "دی ماه", "بهمن", "اسفند"]
TERMINAL_WORDS = ["كاوه", "کاوه", "صفه", "زاينده", "زاینده", "صمديه", "صمدیه", " جي", " جی"]
SV_RE = re.compile("صورت ?وضعيت|صورت ?وضعیت|صورت\u200cوضعيت|صورت\u200cوضعیت")
DIGITS5 = re.compile(r"\d{5,}")
DATE_RE = re.compile(r"^\d{4}/\d{2}/\d{2}$")


def sha16(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def load_memory_db() -> sqlite3.Connection:
    src = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    mem = sqlite3.connect(":memory:")
    src.backup(mem)
    src.close()
    for ddl in (
        "create index ix_s_doc on sanad(doc_key)",
        "create index ix_s_h on sanad(hcode)",
        "create index ix_e_sid on line_event(sid)",
        "create index ix_e_doc on line_event(doc_key)",
        "create index ix_d_doc on doc_class(doc_key)",
    ):
        mem.execute(ddl)
    return mem


def sheet_rows(wb, name):
    rows = list(wb[name].iter_rows(values_only=True))
    return rows[2], [r for r in rows[3:] if r and r[0]]


def present(v) -> bool:
    return v is not None and str(v).strip() not in ("", "NULL")


# ---------------------------------------------------------------- lines
def load_lines(mem):
    bank_docs = {r[0] for r in mem.execute("select distinct doc_key from sanad where hcode like '111-%'")}
    kind = dict(mem.execute("select doc_key, kind from doc_class"))
    lines = {}
    for (sid, org, fy, doc, hcode, bed, bes, sharh, f1, f2, f3, f4, f5, person, vahed, markaz, taf2,
         src_row, sanad_num) in mem.execute(
        """select sid, org, fy, doc_key, trim(hcode), cast(bed as real), cast(bes as real),
                  coalesce(sharh_norm, sharh, ''), f1, f2, f3, f4, f5, person, vahed, markaz, taf2,
                  src_row, sanad_num from sanad"""):
        parts = hcode.split("-")
        sh = sharh or ""
        is_bank = hcode.startswith("111-")
        f2_date = present(f2) and bool(DATE_RE.match(str(f2).strip()))
        lines[sid] = dict(
            org=org, fy=fy, doc=doc, kind=kind.get(doc), h=hcode, acc2="-".join(parts[:2]),
            acc3="-".join(parts[:3]), dr=bed > 0, amt=bed + bes,
            person=str(person).strip() if present(person) else None,
            f1=f1, f3=f3, f5=f5, vahed=vahed if present(vahed) else None,
            markaz=present(markaz), taf2=str(taf2).strip() not in ("", "0", "None"),
            instr=f2_date and not is_bank, bankref=is_bank and f2_date and present(f1),
            n5=bool(DIGITS5.search(sh)), qd="قرارداد" in sh, sv=bool(SV_RE.search(sh)),
            month=any(m in sh for m in MONTHS), docbank=doc in bank_docs, bank=is_bank,
        )
    return lines


def vcat(line) -> str:
    if line["org"] != "Terminals":
        return "TX"
    v = line["vahed"]
    if not v:
        return "MISSING"
    p = v.split("-")
    if p[0] in TERMINAL_CODES:
        return "SUB" if p[1] in ("001", "002") else "TERM"
    if p[0] in HQ_CODES:
        return "HQ"
    return "UNK"


# ---------------------------------------------------------------- section 1
def population_review(wb07):
    hdr, rows = sheet_rows(wb07, "جمعیت_بررسی")
    pop = [dict(zip(hdr, r)) for r in rows]
    total = next(p for p in pop if p["شناسه"] == "PR-07")
    cats = [
        "← مرتبط با رویداد پیشنهادی (شرط حساب)",
        "← مرتبط با رویداد پیشنهادی (جفت\u200cسازی)",
        "← سطر بانک طرف مقابل در سند دارای رویداد",
        "← سطر غیربانکی طرف مقابل در سند دارای رویداد",
        "← انتظامی بدون رویداد",
        "← حل\u200cنشدهٔ بدون برچسب",
    ]
    identity_ok = all(sum(p[c] for c in cats) == p["بدون برچسب v2.1"] for p in pop)
    # Is 10,566 (or the implied 10,941) anywhere in T07, or any natural sum of its sub-groups?
    needles = ["10566", "10,566", "10٬566", "۱۰٬۵۶۶", "۱۰۵۶۶", "10941", "10,941", "10٬941", "۱۰٬۹۴۱", "۱۰۹۴۱"]
    found = []
    for ws in wb07.worksheets:
        for row in ws.iter_rows(values_only=True):
            for v in row:
                if v is not None and any(n in str(v) for n in needles):
                    found.append((ws.title, str(v)[:80]))
    md = T07_MD.read_text(encoding="utf-8")
    found += [("md", n) for n in needles if n in md]
    groups = {}
    for p in pop:
        groups[(p["بخش"], p["سال مالی"])] = [p[c] for c in cats]
    natural_hits = []
    for key, vals in groups.items():
        for n in range(1, len(cats) + 1):
            for combo in itertools.combinations(range(len(cats)), n):
                s = sum(vals[i] for i in combo)
                if s in (10566, 10941):
                    natural_hits.append((key, combo, s))
    return dict(rows=pop, cats=cats, identity_ok=identity_ok, needle_hits=found,
                natural_hits=natural_hits, total=total)


def memo_rows(mem):
    """Reproduce the 90 memo (انتظامی) rows of T07 cohort U-10 and break them down by account."""
    sql = """
    select s.org, s.fy, s.kol||'-'||cast(s.moeen as int)||'-'||cast(s.taf1 as int),
           case when cast(s.bed as real)>0 then 'بدهکار' else 'بستانکار' end,
           count(*), sum(cast(s.bed as real)+cast(s.bes as real)), count(distinct s.doc_key)
    from sanad s join doc_class d on d.doc_key=s.doc_key
    where d.kind in ('REGULAR','INTERNAL_SETTLEMENT') and cast(s.kol as int) in (918,919)
      and not (s.hcode like '918-1-2%' or s.hcode like '918-2-2%' or s.hcode like '919-1-2%')
    group by 1,2,3,4 order by 1,2,3,4"""
    rows = [list(r) for r in mem.execute(sql)]
    usage = [list(r) for r in mem.execute(
        """select s.org, s.kol||'-'||cast(s.moeen as int)||'-'||cast(s.taf1 as int), d.kind, count(*)
           from sanad s join doc_class d on d.doc_key=s.doc_key where cast(s.kol as int) in (918,919)
           group by 1,2,3 order by 1,2,3""")]
    titles = {(o, h): t for o, h, t in mem.execute(
        "select distinct org, hcode, name from hesab where cast(kol as int) in (918,919) and fy='1404'")}
    return dict(rows=rows, usage=usage, titles={f"{o}|{h}": t for (o, h), t in titles.items()})


# ---------------------------------------------------------------- A1 source fields
def field_profile(lines):
    review = [l for l in lines.values() if l["kind"] in REVIEW_KINDS]
    by_org = collections.defaultdict(list)
    for l in review:
        by_org[l["org"]].append(l)
    out = {}
    for org, ls in by_org.items():
        n = len(ls)
        exp = [l for l in ls if l["h"][:3] in ("611", "612", "613")]
        rev = [l for l in ls if l["h"].startswith("413-")]
        bank = [l for l in ls if l["bank"]]
        out[org] = dict(
            n=n,
            person=sum(l["person"] is not None for l in ls),
            markaz=sum(l["markaz"] for l in ls),
            markaz_on_expense=(sum(l["markaz"] for l in exp), len(exp)),
            markaz_on_revenue=(sum(l["markaz"] for l in rev), len(rev)),
            person_on_bank=(sum(l["person"] is not None for l in bank), len(bank)),
            person_codes_on_bank=len({l["person"] for l in bank if l["person"]}),
            bankref_on_bank=(sum(l["bankref"] for l in bank), len(bank)),
            instr=sum(l["instr"] for l in ls),
            qd=sum(l["qd"] for l in ls),
            vahed=collections.Counter(vcat(l) for l in ls),
            distinct_vahed=len({l["vahed"] for l in ls if l["vahed"]}),
        )
    # f1 functionally dependent on person on person-bearing accounts (=> f1 is the party name)
    dep = collections.defaultdict(set)
    for l in review:
        if l["person"] and not l["bank"] and not l["instr"] and l["h"][:3] not in ("611", "612", "613"):
            dep[(l["org"], l["person"])].add(str(l["f1"]))
    conflicts = sum(len(v) > 1 for v in dep.values())
    # Terminals party name embeds unit/terminal (and year) on tenant accounts
    embed = {}
    for prefix in ("113-1-4-", "113-1-8-", "213-2-", "212-6-"):
        names = {}
        for l in review:
            if l["org"] == "Terminals" and l["h"].startswith(prefix) and l["person"]:
                names[l["person"]] = str(l["f1"] or "")
        vals = list(names.values())
        embed[prefix.rstrip("-")] = dict(
            persons=len(vals),
            slash=sum("/" in v for v in vals),
            terminal=sum(any(t in v for t in TERMINAL_WORDS) for v in vals),
            year=sum(bool(re.search(r"/\s*14\d\d", v)) for v in vals),
        )
    # bank transaction type (Field3 on bank lines) - non personal controlled vocabulary
    bank_types = {}
    for org in ("Taxi", "Terminals"):
        c = collections.Counter(str(l["f3"]).strip() for l in review if l["org"] == org and l["bank"] and present(l["f3"]))
        bank_types[org] = c.most_common(8)
    # Taxi expense: Field1 functionally dependent on CodeMarkaz (activity title)
    return dict(by_org=out, f1_person_conflicts=conflicts, f1_person_keys=len(dep), embed=embed,
                bank_types=bank_types)


def vahed_structure(mem):
    rows = mem.execute("select distinct vahed, name_vahed from sanad where org='Terminals' and vahed is not null and vahed<>'NULL'").fetchall()
    cat = collections.Counter()
    kw = collections.Counter()
    for v, n in rows:
        p = v.split("-")
        cat[(p[0], p[1])] += 1
        n = n or ""
        if p[1] == "001" and "غرفه" in n:
            kw["booth_named_غرفه"] += 1
        if p[1] == "003" and ("مشترك" in n or "مشترک" in n):
            kw["shared_named_مشترک"] += 1
    by_cat = collections.Counter()
    for (t, c), k in cat.items():
        by_cat[c if t in TERMINAL_CODES else f"hq:{t}"] += k
    return dict(codes=len(rows), by_category=dict(by_cat), keywords=dict(kw))


# ---------------------------------------------------------------- A2 event profiles
def evidence_selectors(wb07, mem, lines):
    hdr, rows = sheet_rows(wb07, "شواهد_و_نمونه\u200cها")
    ev = [r for r in rows if r[1] == "آمار شواهد"]
    exact, pairing = {}, []
    for r in ev:
        cond = r[8] or ""
        if "جفت\u200cسازی" in cond:
            pairing.append(r)
            continue
        kinds = tuple(k.strip() for k in r[7].split("نوع سند:")[1].replace("،", ",").split(",") if k.strip())
        org = FA_ORG[r[3]]
        sql = (f"select s.sid from sanad s join line_event e on e.sid=s.sid join doc_class d on d.doc_key=s.doc_key "
               f"where s.org=? and d.kind in ({','.join('?' * len(kinds))}) and ({cond})")
        sids = [x[0] for x in mem.execute(sql, (org, *kinds))]
        exact[r[0]] = dict(event=r[2], org=org, t07=int(r[9]), n=len(sids), sids=sids)
    return exact, pairing


def pairing_proxies(lines):
    """Account-pattern proxies for T07 evidence rows that came from one-to-one pairing code.

    The T07 pairing code was not stored, so these supersets only serve to profile which fields the
    involved account roles carry; their counts are reported next to the T07 count, never instead of it.
    """
    term = [(sid, l) for sid, l in lines.items() if l["org"] == "Terminals" and l["kind"] == "REGULAR"]
    docs = collections.defaultdict(list)
    for sid, l in term:
        docs[l["doc"]].append((sid, l))

    cache = {}

    def has(doc, pred):
        key = (doc, pred.__code__)
        if key not in cache:
            cache[key] = any(pred(l) for _, l in docs[doc])
        return cache[key]

    claim = lambda l: l["h"].startswith("113-1-4-") or l["h"].startswith("113-1-8-")
    bank = lambda l: l["h"].startswith("111-")
    defs = {
        "EV-010": ("Dr 113-1-4 و Cr 211-1-1-1/2/5/8 در اسناد دارای Dr 113-1-4",
                   lambda l: (l["h"].startswith("113-1-4-") and l["dr"]) or (
                       l["h"] in ("211-1-1-1", "211-1-1-2", "211-1-1-5", "211-1-1-8") and not l["dr"]
                       and has(l["doc"], lambda x: x["h"].startswith("113-1-4-") and x["dr"]))),
        "EV-011": ("Dr 113-1-8 و Cr 211-1-1-6 در اسناد دارای Dr 113-1-8",
                   lambda l: (l["h"].startswith("113-1-8-") and l["dr"]) or (
                       l["h"] == "211-1-1-6" and not l["dr"]
                       and has(l["doc"], lambda x: x["h"].startswith("113-1-8-") and x["dr"]))),
        "EV-012": ("Cr 113-1-4/8 و Dr بانک در اسناد مشترک",
                   lambda l: (claim(l) and not l["dr"] and has(l["doc"], lambda x: bank(x) and x["dr"])) or (
                       bank(l) and l["dr"] and has(l["doc"], lambda x: claim(x) and not x["dr"]))),
        "EV-013": ("Cr 113-1-4/8 و Dr بانک در اسناد مشترک (همان الگوی EV-012)",
                   lambda l: (claim(l) and not l["dr"] and has(l["doc"], lambda x: bank(x) and x["dr"])) or (
                       bank(l) and l["dr"] and has(l["doc"], lambda x: claim(x) and not x["dr"]))),
        "EV-014": ("Cr 113-1-4/8 و Dr 213-2-4-2 در اسناد مشترک",
                   lambda l: (claim(l) and not l["dr"] and has(l["doc"], lambda x: x["h"] == "213-2-4-2" and x["dr"])) or (
                       l["h"] == "213-2-4-2" and l["dr"] and has(l["doc"], lambda x: claim(x) and not x["dr"]))),
        "EV-015": ("Cr 113-1-4/8 و Dr 212-6-5/212-6-2 در اسناد مشترک",
                   lambda l: (claim(l) and not l["dr"] and has(l["doc"], lambda x: x["acc3"] in ("212-6-5", "212-6-2") and x["dr"])) or (
                       l["acc3"] in ("212-6-5", "212-6-2") and l["dr"] and has(l["doc"], lambda x: claim(x) and not x["dr"]))),
        "EV-016": ("Dr 211-1-1-x، Cr 413-1-3 و Cr 211-1-7-4 در اسناد دارای Cr 413-1-3",
                   lambda l: has(l["doc"], lambda x: x["acc3"] == "413-1-3" and not x["dr"]) and (
                       (l["h"].startswith("211-1-1-") and l["dr"]) or (l["acc3"] == "413-1-3" and not l["dr"])
                       or (l["h"] == "211-1-7-4" and not l["dr"]))),
        "EV-019": ("Cr 113-6 و Dr بانک در اسناد مشترک",
                   lambda l: (l["acc2"] == "113-6" and not l["dr"] and has(l["doc"], lambda x: bank(x) and x["dr"])) or (
                       bank(l) and l["dr"] and has(l["doc"], lambda x: x["acc2"] == "113-6" and not x["dr"]))),
        "EV-022": ("Dr 213-2-4-2 در اسناد دارای Cr 113-7",
                   lambda l: l["h"] == "213-2-4-2" and l["dr"] and has(l["doc"], lambda x: x["acc2"] == "113-7" and not x["dr"])),
        "EV-075": ("Dr 211-1-7-4", lambda l: l["h"] == "211-1-7-4" and l["dr"]),
        "EV-077": ("Cr 211-1-7-4", lambda l: l["h"] == "211-1-7-4" and not l["dr"]),
        "EV-083": ("Dr 211-1-7-4 در اسناد دارای Cr بانک",
                   lambda l: l["h"] == "211-1-7-4" and l["dr"] and has(l["doc"], lambda x: bank(x) and not x["dr"])),
        "EV-136": ("Dr 211-1-1-x و 211-1-6-20 در اسناد دارای Cr بانک، بیرون از اسناد صدور مطالبه",
                   lambda l: (l["h"].startswith("211-1-1-") or l["h"] == "211-1-6-20") and l["dr"]
                   and has(l["doc"], lambda x: bank(x) and not x["dr"]) and not has(l["doc"], lambda x: claim(x) and x["dr"])),
        "EV-164": ("Dr 211-1-1-x و Cr 113-1-4/8 در اسناد صدور مطالبه",
                   lambda l: has(l["doc"], lambda x: claim(x) and x["dr"]) and (
                       (l["h"].startswith("211-1-1-") and l["dr"]) or (claim(l) and not l["dr"]))),
        "EV-169": ("Cr 211-1-1-3/5 و Dr بانک در اسناد مشترک",
                   lambda l: (l["h"] in ("211-1-1-3", "211-1-1-5") and not l["dr"] and has(l["doc"], lambda x: bank(x) and x["dr"])) or (
                       bank(l) and l["dr"] and has(l["doc"], lambda x: x["h"] in ("211-1-1-3", "211-1-1-5") and not x["dr"]))),
        "EV-170": ("Cr 113-6 و Dr 213-2-4-2 در اسناد مشترک",
                   lambda l: (l["acc2"] == "113-6" and not l["dr"] and has(l["doc"], lambda x: x["h"] == "213-2-4-2" and x["dr"])) or (
                       l["h"] == "213-2-4-2" and l["dr"] and has(l["doc"], lambda x: x["acc2"] == "113-6" and not x["dr"]))),
    }
    out = {k: (label, [sid for sid, l in term if pred(l)]) for k, (label, pred) in defs.items()}
    # neutral same-account pairs (PFE-080): equal Dr and Cr in one account and one document
    for ev_id, org in (("EV-132", "Taxi"), ("EV-133", "Terminals")):
        groups = collections.defaultdict(lambda: ([], []))
        for sid, l in lines.items():
            if l["org"] == org and l["kind"] == "REGULAR":
                groups[(l["doc"], l["h"])][0 if l["dr"] else 1].append((sid, l["amt"]))
        sids = []
        for drs, crs in groups.values():
            cr_amts = {a for _, a in crs}
            dr_amts = {a for _, a in drs}
            sids += [s for s, a in drs if a in cr_amts] + [s for s, a in crs if a in dr_amts]
        out[ev_id] = ("بدهکار و بستانکار هم‌مبلغ در یک حساب و یک سند (بدون قید یک‌به‌یک)", sids)
    return out


def drop_other_events(proxies, exact, pairing_rows):
    """Remove proxy lines that T07 selected exactly for a different event."""
    owner = collections.defaultdict(set)
    for d in exact.values():
        for s in d["sids"]:
            owner[s].add(d["event"])
    event_of = {r[0]: r[2] for r in pairing_rows}
    return {k: (label, [s for s in sids if not (owner.get(s, set()) - {event_of.get(k)})])
            for k, (label, sids) in proxies.items()}


def profile(sids, lines):
    ls = [lines[s] for s in sids]
    n = len(ls)
    if not n:
        return dict(n=0)
    pct = lambda k: round(100 * sum(1 for l in ls if l[k]) / n, 1)
    roles = collections.Counter(f"{l['acc3']} {'بد' if l['dr'] else 'بس'}" for l in ls)
    vc = collections.Counter(vcat(l) for l in ls)
    return dict(
        n=n, docs=len({l["doc"] for l in ls}),
        roles=roles.most_common(4), n_roles=len(roles),
        person=round(100 * sum(l["person"] is not None for l in ls) / n, 1),
        persons=len({(l["org"], l["person"]) for l in ls if l["person"]}),
        markaz=pct("markaz"), instr=pct("instr"), bankref=pct("bankref"), docbank=pct("docbank"),
        qd=pct("qd"), sv=pct("sv"), month=pct("month"), n5=pct("n5"), taf2=pct("taf2"),
        vahed={k: round(100 * v / n, 1) for k, v in vc.items()},
    )


def event_profiles(exact, pairing_rows, recon, ev_basis, lines):
    """Profile per (event, sector). Basis: EXACT = T07 SQL selector re-run; DEF = written T07 definition
    re-implemented with equal count; APPROX = independent pairing reconstruction (requires verification)."""
    by_key = collections.defaultdict(lambda: dict(t07=0, sids=set(), ev=[], basis=set(), methods=[]))
    for ev_id, d in exact.items():
        k = (d["event"], d["org"])
        by_key[k]["t07"] += d["t07"]
        by_key[k]["sids"].update(d["sids"])
        by_key[k]["ev"].append(ev_id)
        by_key[k]["basis"].add("EXACT")
    for r in pairing_rows:
        k = (r[2], FA_ORG[r[3]])
        by_key[k]["t07"] += int(r[9])
        by_key[k]["sids"].update(recon[r[0]])
        by_key[k]["ev"].append(r[0])
        by_key[k]["basis"].add(ev_basis[r[0]])
        by_key[k]["methods"].append(f"{r[0]}: {t08_pairing.EV_RULES[r[0]][3]}")
    out = []
    for (event, org), d in sorted(by_key.items()):
        p = profile(sorted(d["sids"]), lines)
        basis = "APPROX" if "APPROX" in d["basis"] else ("DEF" if "DEF" in d["basis"] else "EXACT")
        out.append(dict(event=event, org=org, t07=d["t07"], ev=d["ev"], basis=basis,
                        mixed=len(d["basis"]) > 1, proxy=d["methods"], **p))
    return out


# ---------------------------------------------------------------- A3 relational observations
def relational_observations(mem, lines):
    obs = {}
    reg = [l for l in lines.values() if l["kind"] == "REGULAR"]
    # claims per tenant code per year (Dr 113-1-4 in Terminals)
    per = collections.defaultdict(set)
    for l in reg:
        if l["org"] == "Terminals" and l["h"].startswith("113-1-4-") and l["dr"] and l["person"]:
            per[(l["fy"], l["person"])].add(l["doc"])
    for fy in ("1404", "1405"):
        counts = [len(v) for (y, _), v in per.items() if y == fy]
        if counts:
            obs[f"claims_docs_per_party_{fy}"] = dict(parties=len(counts), median=statistics.median(counts),
                                                      max=max(counts), ge6=sum(c >= 6 for c in counts))
    # tenants per claim document
    per_doc = collections.defaultdict(set)
    for l in reg:
        if l["org"] == "Terminals" and (l["h"].startswith("113-1-4-") or l["h"].startswith("113-1-8-")) and l["dr"] and l["person"]:
            per_doc[l["doc"]].add(l["person"])
    sizes = [len(v) for v in per_doc.values()]
    obs["parties_per_claim_doc"] = dict(docs=len(sizes), median=statistics.median(sizes), max=max(sizes),
                                        ge20=sum(s >= 20 for s in sizes))
    # a party code reused across terminals (vahed first segment) on claim lines
    loc = collections.defaultdict(set)
    sub = collections.defaultdict(set)
    for l in reg:
        if l["org"] == "Terminals" and l["h"].startswith("113-1-4-") and l["person"] and l["vahed"]:
            loc[l["person"]].add(l["vahed"].split("-")[0])
            sub[l["person"]].add(l["vahed"])
    obs["claim_party_locations"] = dict(parties=len(loc), multi_terminal=sum(len(v) > 1 for v in loc.values()),
                                        multi_unit=sum(len(v) > 1 for v in sub.values()))
    units = collections.defaultdict(set)
    for l in reg:
        if l["org"] == "Terminals" and l["h"].startswith("113-1-4-") and l["person"] and l["vahed"]:
            units[l["vahed"]].add(l["person"])
    obs["claim_units_multi_party"] = dict(units=len(units), multi_party=sum(len(v) > 1 for v in units.values()))
    # Terminals expense lines (cost imposed, Dr 113-1-1-x) by location granularity
    exp = [l for l in reg if l["org"] == "Terminals" and l["h"].startswith("113-1-1-") and l["dr"]]
    obs["terminal_expense_location"] = dict(n=len(exp), **collections.Counter(vcat(l) for l in exp))
    # claim-issue and lease-deposit lines selected by account and direction only (independent of any event label)
    cl = [l for l in reg if l["org"] == "Terminals" and (l["h"].startswith("113-1-4-") or l["h"].startswith("113-1-8-")) and l["dr"]]
    obs["claim_issue_lines_location"] = dict(n=len(cl), **collections.Counter(vcat(l) for l in cl))
    dp = [l for l in reg if l["org"] == "Terminals" and l["acc3"] in ("212-6-5", "212-6-7") and not l["dr"]]
    obs["lease_deposit_lines_location"] = dict(n=len(dp), **collections.Counter(vcat(l) for l in dp))
    # statements in Terminals (113-1-1-22/23 contractor services) by location granularity
    st = [l for l in exp if l["h"] in ("113-1-1-22", "113-1-1-23", "113-1-1-5")]
    obs["terminal_contract_service_location"] = dict(n=len(st), **collections.Counter(vcat(l) for l in st))
    st_docs = collections.defaultdict(set)
    for l in st:
        st_docs[l["doc"]].add(l["vahed"].split("-")[0] if l["vahed"] else None)
    obs["terminal_contract_service_docs_multi_location"] = dict(
        docs=len(st_docs), multi=sum(len(v) > 1 for v in st_docs.values()))
    # contract-control memo account usage (918-1-3 / 918-2-3)
    obs["contract_memo_lines"] = mem.execute(
        "select count(*) from sanad where hcode like '918-1-3%' or hcode like '918-2-3%'").fetchone()[0]
    obs["contract_memo_title"] = [list(r) for r in mem.execute(
        "select distinct org, hcode, name from hesab where hcode in ('918-1-3-0','918-2-3-0') and fy='1404'")]
    # Taxi revenue (413-1) lines: party / activity code presence
    tx_rev = [l for l in reg if l["org"] == "Taxi" and l["h"].startswith("413-1-") and not l["dr"]]
    obs["taxi_revenue"] = dict(n=len(tx_rev), person=sum(l["person"] is not None for l in tx_rev),
                               markaz=sum(l["markaz"] for l in tx_rev))
    # payroll lines in Taxi with activity code
    tx_pay = [l for l in reg if l["org"] == "Taxi" and l["h"].startswith("611-") and l["dr"]]
    obs["taxi_payroll_markaz"] = dict(n=len(tx_pay), markaz=sum(l["markaz"] for l in tx_pay))
    # protested / returned cheque accounts
    obs["cheque_accounts"] = [list(r) for r in mem.execute(
        """select s.org, s.kol||'-'||cast(s.moeen as int)||'-'||cast(s.taf1 as int), d.kind, count(*)
           from sanad s join doc_class d on d.doc_key=s.doc_key
           where s.hcode like '113-5-%' or s.hcode like '113-7-%' group by 1,2,3 order by 1,2,3""")]
    return obs


# ---------------------------------------------------------------- accounts (compound key)
# Titles that name a natural person or a private counterparty (reviewed by hand on 2026-10-29).
MASK_TITLE_HCODES = {"211-1-6-36", "211-1-6-43", "211-1-6-44", "211-1-6-45", "211-1-6-47",
                     "212-6-8-3", "212-6-8-4", "116-6-0-0"}
MASKED_TITLE = "[عنوان طرف‌حساب پوشانده شد]"


def mask_title(h: str, title: str) -> str:
    if h in MASK_TITLE_HCODES or "بازنشسته" in (title or "") or "بانشسته" in (title or ""):
        return MASKED_TITLE
    return DIGITS5.sub(lambda m: "••••" + m.group(0)[-3:], title or "")


def mask_hcode(h: str) -> str:
    """Bank-account numbers sit in code segments (111-x-x-<acct>, 211-5-<acct>); keep the last 3 digits."""
    return "-".join("••••" + s[-3:] if len(s) >= 5 and s.isdigit() else s for s in h.split("-"))


def account_list(mem, lines, exact, proxies, pairing_rows):
    titles = {}
    for org, fy, h, t in mem.execute("select org, fy, hcode, title from account_dictionary"):
        titles[(org, fy, h)] = t
    hesab_h = {(org, fy, h.strip()) for org, fy, h in mem.execute("select org, fy, hcode from hesab")}
    use = collections.defaultdict(lambda: dict(n=0, dr=0, cr=0, docs=set(), events=set(), proxy_events=set()))
    sid_events = collections.defaultdict(set)
    for d in exact.values():
        for s in d["sids"]:
            sid_events[s].add(d["event"])
    sid_proxy = collections.defaultdict(set)
    ev_of = {r[0]: r[2] for r in pairing_rows}
    for ev_id, (_, sids) in proxies.items():
        for s in sids:
            sid_proxy[s].add(ev_of[ev_id])
    for sid, l in lines.items():
        if l["kind"] not in REVIEW_KINDS:
            continue
        u = use[(l["org"], l["fy"], l["h"])]
        u["n"] += 1
        u["dr" if l["dr"] else "cr"] += 1
        u["docs"].add(l["doc"])
        u["events"] |= sid_events.get(sid, set())
        u["proxy_events"] |= sid_proxy.get(sid, set()) - sid_events.get(sid, set())
    out = []
    for (org, fy, h), u in sorted(use.items()):
        title = mask_title(h, titles.get((org, fy, h), ""))
        out.append(dict(org=org, fy=fy, h=mask_hcode(h), raw_bank=h.startswith("111-"), title=title,
                        in_hesab=(org, fy, h) in hesab_h, n=u["n"], dr=u["dr"], cr=u["cr"], docs=len(u["docs"]),
                        events=sorted(u["events"]), proxy_events=sorted(u["proxy_events"])))
    return out


def _tokens(title: str) -> set[str]:
    t = (title or "").replace("ي", "ی").replace("ك", "ک").replace("\u200c", " ")
    t = re.sub(r"[\-()/،,.:]", " ", t)
    return {w for w in t.split() if len(w) > 1}


def homonyms(mem):
    """Codes present in both sectors (FY1404) whose titles share less than half of their words.

    Spelling-only differences are ignored; these are the codes for which the (sector, code) key is
    indispensable (cf. E-02 and EA-10 in T07)."""
    rows = mem.execute("""select a.hcode, a.title, b.title from account_dictionary a join account_dictionary b
                          on a.hcode=b.hcode and a.fy='1404' and b.fy='1404' and a.org='Taxi' and b.org='Terminals'
                          where a.title_norm<>b.title_norm""").fetchall()
    out = []
    for h, ta, tb in rows:
        a, b = _tokens(ta), _tokens(tb)
        jac = len(a & b) / len(a | b) if a | b else 1.0
        if jac < 0.5 and not h.startswith("111-") and not h.startswith("113-6-"):
            out.append([h, mask_title(h, ta), mask_title(h, tb), round(jac, 2)])
    return out


def main():
    mem = load_memory_db()
    wb07 = openpyxl.load_workbook(T07, read_only=True, data_only=True)
    lines = load_lines(mem)
    exact, pairing_rows = evidence_selectors(wb07, mem, lines)
    # T08 v0.1 profiled these rows with account-pattern supersets; kept only as lineage of the earlier method
    supersets = drop_other_events(pairing_proxies(lines), exact, pairing_rows)
    recon_sets, recon_tiers = t08_pairing.reconstruct(mem, lines)
    ev_basis, approx = {}, []
    for r in pairing_rows:
        ev_id = r[0]
        event, org, kind, method = t08_pairing.EV_RULES[ev_id]
        n = len(recon_sets[ev_id])
        t07n = int(r[9])
        basis = "DEF" if kind == t08_pairing.DETERMINISTIC and n == t07n else "APPROX"
        ev_basis[ev_id] = basis
        approx.append(dict(ev=ev_id, event=event, org=org, kind=kind, method=method, t07=t07n,
                           superset=len(supersets[ev_id][1]), recon=n, basis=basis))
    recon = {k: (t08_pairing.EV_RULES[k][3], v) for k, v in recon_sets.items()}
    pop = population_review(wb07)
    data = dict(
        hashes=dict(db=sha16(DB), t07=sha16(T07), t05=sha16(T05)),
        population=pop,
        memo=memo_rows(mem),
        fields=field_profile(lines),
        vahed=vahed_structure(mem),
        exact_check=[dict(ev=k, event=v["event"], org=v["org"], t07=v["t07"], n=v["n"]) for k, v in exact.items()],
        approx=approx,
        recon_tiers=recon_tiers,
        profiles=event_profiles(exact, pairing_rows, recon_sets, ev_basis, lines),
        relations=relational_observations(mem, lines),
        accounts=account_list(mem, lines, exact, recon, pairing_rows),
        homonyms=homonyms(mem),
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1, default=list), encoding="utf-8")
    bad = [c for c in data["exact_check"] if c["t07"] != c["n"]]
    print("exact EV rows:", len(data["exact_check"]), "mismatches:", len(bad))
    print("pairing rows (ev, t07, v0.1 superset, reconstruction, basis):",
          [(a["ev"], a["t07"], a["superset"], a["recon"], a["basis"]) for a in approx])
    print("reconstructed tiers:", recon_tiers)
    print("population identity:", pop["identity_ok"], "needle hits:", pop["needle_hits"], "natural hits:", pop["natural_hits"])
    print("memo rows:", sum(r[4] for r in data["memo"]["rows"]))
    print("profiles:", len(data["profiles"]), "accounts:", len(data["accounts"]))


if __name__ == "__main__":
    main()
