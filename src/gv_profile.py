"""Profiling of a raw CSV before validation (Day 1 evidence)."""
from collections import Counter

import gv_validator as V


def profile(columns, rows, schema):
    cmap = schema["canonical_map"]
    fmt = schema["date_format"]
    n = len(rows)
    missing = {c: sum(1 for r in rows if (r.get(c) or "").strip() == "") for c in columns}

    ids = [(r.get(cmap["record_id"]) or "").strip() for r in rows]
    id_counts = Counter(i for i in ids if i)
    dup_extra = sum(c - 1 for c in id_counts.values() if c > 1)

    nk = {}
    for r in rows:
        wh = (r.get(cmap["warehouse_id"]) or "").strip()
        bt = (r.get(cmap["batch_id"]) or "").strip()
        rc = (r.get(cmap["received"]) or "").strip()
        rid = (r.get(cmap["record_id"]) or "").strip()
        if wh and bt and rc:
            d = V.parse_when(rc, fmt)
            nk.setdefault((wh, bt, d.isoformat() if d else rc), set()).add(rid)
    nk_conflicts = sum(1 for s in nk.values() if len(s) > 1)

    invalid_numeric = 0
    for canon in ("gross", "tare", "net", "moisture"):
        col = cmap[canon]
        for r in rows:
            t = (r.get(col) or "").strip()
            if t and V.parse_number(t) is None:
                invalid_numeric += 1
    invalid_dates = 0
    for canon in ("received", "verified"):
        col = cmap[canon]
        for r in rows:
            t = (r.get(col) or "").strip()
            if t and V.parse_when(t, fmt) is None:
                invalid_dates += 1

    ss, ref = cmap["source_system"], cmap["provenance_ref"]
    prov_complete = sum(1 for r in rows
                        if (r.get(ss) or "").strip() and (r.get(ref) or "").strip())
    sources = Counter((r.get(ss) or "").strip() or "(empty)" for r in rows)
    commodities = Counter((r.get(cmap["commodity"]) or "").strip() or "(empty)" for r in rows)

    return {
        "row_count": n,
        "column_count": len(columns),
        "columns": columns,
        "missing_by_column": missing,
        "duplicate_record_id_extra_rows": dup_extra,
        "natural_key_conflict_groups": nk_conflicts,
        "invalid_numeric_cells": invalid_numeric,
        "invalid_date_cells": invalid_dates,
        "source_reference_complete_rows": prov_complete,
        "source_reference_complete_pct": round(100.0 * prov_complete / n, 1) if n else None,
        "source_system_distribution": dict(sorted(sources.items())),
        "commodity_distribution": dict(sorted(commodities.items())),
    }


def to_markdown(title, prof):
    lines = [f"# Profiling report: {title}", "",
             f"- Rows: {prof['row_count']}",
             f"- Columns: {prof['column_count']}",
             f"- Extra rows sharing an existing record_id: {prof['duplicate_record_id_extra_rows']}",
             f"- Natural-key groups with more than one record_id: {prof['natural_key_conflict_groups']}",
             f"- Non-numeric cells in numeric columns: {prof['invalid_numeric_cells']}",
             f"- Cells that are not valid dates in date columns: {prof['invalid_date_cells']}",
             f"- Rows with source system and source reference both present: "
             f"{prof['source_reference_complete_rows']} ({prof['source_reference_complete_pct']}%)",
             "", "## Missing (empty) cells by column", "", "| Column | Empty |", "|---|---|"]
    for c, m in prof["missing_by_column"].items():
        lines.append(f"| {c} | {m} |")
    lines += ["", "## Source systems", "", "| Source | Rows |", "|---|---|"]
    for s, k in prof["source_system_distribution"].items():
        lines.append(f"| {s} | {k} |")
    lines += ["", "## Commodities", "", "| Commodity | Rows |", "|---|---|"]
    for s, k in prof["commodity_distribution"].items():
        lines.append(f"| {s} | {k} |")
    lines.append("")
    return "\n".join(lines)
