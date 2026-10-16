"""Independent second implementation of the row rules (standalone, imports nothing from src/).

It is written from the rule table in docs/design_note.md and deliberately uses its own parsing,
its own column names and a different code structure (sets of rule tags per row, no shared code).
Run alone:  python3 -I tests/independent_verifier.py
It writes reports/independent_results_v1.json and _v2.json and prints counts.
"""
import csv
import datetime as dt
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")

REF = dt.date(2026, 10, 15)
KNOWN = {"SRC-WMS-A": "ACTIVE", "SRC-WMS-B": "ACTIVE", "SRC-MANUAL": "ACTIVE", "SRC-LEGACY": "DEPRECATED"}
CROPS = ("WHEAT", "RICE", "MAIZE", "SOYBEAN", "CHICKPEA")

LAYOUT = {
    "S1": dict(net="net_kg", wet="moisture_pct", rcv="received_date", ver="last_verified_date",
               ref="source_ref", grade=None, tz=False),
    "S2": dict(net="net_weight_kg", wet="moisture_percent", rcv="received_at", ver="last_verified_at",
               ref="provenance_ref", grade="quality_grade", tz=True),
}


def as_float(s):
    try:
        x = float(s)
    except ValueError:
        return None
    return x if x == x and abs(x) != float("inf") else None


def as_day(s, tz):
    pat = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}" if tz else r"\d{4}-\d{2}-\d{2}"
    if not re.fullmatch(pat, s):
        return None
    try:
        return dt.date(int(s[0:4]), int(s[5:7]), int(s[8:10]))
    except ValueError:
        return None


def classify_file(path, schema):
    L = LAYOUT[schema]
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    # natural key -> set of ids
    groups = {}
    for r in rows:
        k = (r["warehouse_id"].strip(), r["batch_id"].strip(), r[L["rcv"]].strip()[:10])
        if all(k):
            groups.setdefault(k, set()).add(r["record_id"].strip())
    ids_seen = []
    out = []
    for n, r in enumerate(rows, start=1):
        g = {k: (v or "").strip() for k, v in r.items()}
        bad, unres, warn = set(), set(), set()
        # GV-01 required
        need = ["record_id", "warehouse_id", "commodity", "batch_id", "gross_kg", "tare_kg",
                L["net"], L["wet"], L["rcv"]] + ([L["grade"]] if L["grade"] else [])
        if any(g[c] == "" for c in need):
            bad.add("GV-01")
        # GV-02 formats
        gross, tare, net, wet = (as_float(g["gross_kg"]), as_float(g["tare_kg"]),
                                 as_float(g[L["net"]]), as_float(g[L["wet"]]))
        for raw, val in ((g["gross_kg"], gross), (g["tare_kg"], tare), (g[L["net"]], net), (g[L["wet"]], wet)):
            if raw != "" and val is None:
                bad.add("GV-02")
        rcv, ver = as_day(g[L["rcv"]], L["tz"]), as_day(g[L["ver"]], L["tz"])
        if g[L["rcv"]] != "" and rcv is None:
            bad.add("GV-02")
        if g[L["ver"]] != "" and ver is None:
            bad.add("GV-02")
        # GV-03 domain
        if g["commodity"] != "" and g["commodity"] not in CROPS:
            bad.add("GV-03")
        if wet is not None and (wet < 0 or wet > 40):
            bad.add("GV-03")
        if gross is not None and gross <= 0:
            bad.add("GV-03")
        if tare is not None and tare < 0:
            bad.add("GV-03")
        if gross is not None and tare is not None and tare >= gross:
            bad.add("GV-03")
        if net is not None and net < 0:
            bad.add("GV-03")
        if L["grade"] and g[L["grade"]] != "" and g[L["grade"]] not in ("A", "B", "C"):
            bad.add("GV-03")
        # GV-04 consistency
        if gross is not None and tare is not None and net is not None:
            gap = abs(net - gross + tare)
            if gap > 5.0:
                bad.add("GV-04")
            elif gap > 0.5 + 1e-9:
                warn.add("GV-04")
        # GV-05 duplicates
        if g["record_id"] and g["record_id"] in ids_seen:
            bad.add("GV-05")
        ids_seen.append(g["record_id"])
        # GV-06 natural key
        k = (g["warehouse_id"], g["batch_id"], g[L["rcv"]][:10])
        if all(k) and len(groups.get(k, ())) > 1:
            unres.add("GV-06")
        # GV-07 provenance
        if g["source_system"] == "" or g[L["ref"]] == "":
            bad.add("GV-07")
        # GV-08 registry
        if g["source_system"] != "":
            st = KNOWN.get(g["source_system"])
            if st is None:
                unres.add("GV-08")
            elif st == "DEPRECATED":
                warn.add("GV-08")
        # GV-09 / GV-10 freshness
        if g[L["ver"]] == "":
            unres.add("GV-10")
        elif ver is not None and (REF - ver).days > 90:
            warn.add("GV-09")
        # GV-11 dates
        if rcv is not None and rcv > REF:
            bad.add("GV-11")
        if rcv is not None and ver is not None and ver < rcv:
            bad.add("GV-11")
        # GV-12 moisture
        if wet is not None and 14 < wet <= 40:
            warn.add("GV-12")
        status = "REJECTED" if bad else "UNRESOLVED" if unres else "WARNING" if warn else "ACCEPTED"
        out.append({"row_number": n, "record_id": g["record_id"], "status": status,
                    "rules": sorted(bad | unres | warn)})
    return out


def summarize(results):
    c = {"ACCEPTED": 0, "WARNING": 0, "UNRESOLVED": 0, "REJECTED": 0}
    for r in results:
        c[r["status"]] += 1
    return c


def main():
    reports = os.path.join(ROOT, "reports")
    os.makedirs(reports, exist_ok=True)
    for tag, fname, schema in (("v1", "warehouse_stock_v1.csv", "S1"), ("v2", "warehouse_stock_v2.csv", "S2")):
        res = classify_file(os.path.join(DATA, fname), schema)
        with open(os.path.join(reports, f"independent_results_{tag}.json"), "w") as fh:
            json.dump({"label": "Independent second implementation", "total_rows": len(res),
                       "counts": summarize(res), "records": res}, fh, indent=2)
            fh.write("\n")
        print(tag, len(res), summarize(res))


if __name__ == "__main__":
    main()
