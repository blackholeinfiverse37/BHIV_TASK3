"""Deterministic validator for DS-AGRI-STOCK-001 (local practice scenario).

Pure functions, no network, no clock: the reference date is passed in.
Rule IDs GV-01..GV-12 are row rules; GV-13 (schema/column mismatch) is a file rule.
GV-14 (identity/version/count problems) lives in gv_registry_sim.py.
"""
import csv
import datetime as dt
import math
import re

STATUSES = ("ACCEPTED", "WARNING", "UNRESOLVED", "REJECTED")
RANK = {s: i for i, s in enumerate(STATUSES)}

RULES = {
    "GV-01": "Required field missing",
    "GV-02": "Invalid type or format",
    "GV-03": "Invalid value or domain",
    "GV-04": "Net weight inconsistent with gross - tare",
    "GV-05": "Duplicate record_id",
    "GV-06": "Natural-key conflict (different record_id)",
    "GV-07": "Missing provenance",
    "GV-08": "Source not in registry or deprecated",
    "GV-09": "Stale record",
    "GV-10": "Freshness unconfirmed",
    "GV-11": "Impossible dates",
    "GV-12": "Moisture above storage threshold",
    "GV-13": "File columns do not match declared schema",
}

COMMODITIES = {"WHEAT", "RICE", "MAIZE", "SOYBEAN", "CHICKPEA"}
GRADES = {"A", "B", "C"}
NET_TOLERANCE_KG = 0.5      # |net - (gross - tare)| <= this is fine
NET_REJECT_KG = 5.0         # above this is REJECTED, in between is WARNING
MOISTURE_MAX = 40.0
MOISTURE_WARN = 14.0

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DTZ_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$")


def read_csv(path):
    """Return (columns, rows). Rows are dicts keyed by header."""
    with open(path, newline="") as fh:
        reader = csv.DictReader(fh)
        columns = list(reader.fieldnames or [])
        rows = [dict(r) for r in reader]
    return columns, rows


def check_columns(columns, schema):
    """GV-13: compare file header with the schema's column list (exact set and order)."""
    expected = schema["columns"]
    missing = [c for c in expected if c not in columns]
    extra = [c for c in columns if c not in expected]
    return {
        "ok": columns == expected,
        "missing": missing,
        "unexpected": extra,
        "order_differs": (not missing and not extra and columns != expected),
    }


def parse_number(text):
    try:
        value = float(text)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def parse_when(text, fmt):
    """Parse a date (fmt 'date') or offset-aware datetime (fmt 'datetime_tz') to a date. None if invalid."""
    try:
        if fmt == "date":
            return dt.date.fromisoformat(text) if _DATE_RE.match(text) else None
        if fmt == "datetime_tz":
            return dt.datetime.fromisoformat(text).date() if _DTZ_RE.match(text) else None
    except ValueError:
        return None
    return None


def _values(row, cmap):
    out = {}
    for canon, col in cmap.items():
        out[canon] = ((row.get(col) or "").strip()) if col else ""
    return out


def validate_rows(rows, schema, sources, ref_date, stale_days=90):
    """Validate rows. Returns a list of result dicts in row order.

    sources: {source_system: status} from the source registry.
    Status precedence: REJECTED > UNRESOLVED > WARNING > ACCEPTED.
    """
    cmap = schema["canonical_map"]
    fmt = schema["date_format"]
    required = schema["required"]
    vals = [_values(r, cmap) for r in rows]

    # pre-pass: natural-key groups (GV-06)
    groups = {}
    for v in vals:
        if v["warehouse_id"] and v["batch_id"] and v["received"]:
            d = parse_when(v["received"], fmt)
            key = (v["warehouse_id"], v["batch_id"], d.isoformat() if d else v["received"])
            groups.setdefault(key, set()).add(v["record_id"])

    seen_ids = set()
    results = []
    for i, v in enumerate(vals):
        findings = []

        def add(rule, status, canon, message):
            findings.append({"rule": rule, "status": status, "field": cmap.get(canon) or canon,
                             "message": message})

        # GV-01 required
        for canon in required:
            if v[canon] == "":
                add("GV-01", "REJECTED", canon, "required field is empty")

        # GV-02 types
        num = {}
        for canon in ("gross", "tare", "net", "moisture"):
            if v[canon] != "":
                num[canon] = parse_number(v[canon])
                if num[canon] is None:
                    add("GV-02", "REJECTED", canon, f"not a number: {v[canon]!r}")
            else:
                num[canon] = None
        when = {}
        for canon in ("received", "verified"):
            if v[canon] != "":
                when[canon] = parse_when(v[canon], fmt)
                if when[canon] is None:
                    want = "YYYY-MM-DD" if fmt == "date" else "YYYY-MM-DDTHH:MM:SS+HH:MM (offset required)"
                    add("GV-02", "REJECTED", canon, f"invalid date format {v[canon]!r}, expected {want}")
            else:
                when[canon] = None

        # GV-03 domain
        if v["commodity"] and v["commodity"] not in COMMODITIES:
            add("GV-03", "REJECTED", "commodity", f"unknown commodity {v['commodity']!r}")
        if num["moisture"] is not None and not (0 <= num["moisture"] <= MOISTURE_MAX):
            add("GV-03", "REJECTED", "moisture", f"moisture {num['moisture']} outside 0..{MOISTURE_MAX:g}")
        if num["gross"] is not None and num["gross"] <= 0:
            add("GV-03", "REJECTED", "gross", "gross weight must be > 0")
        if num["tare"] is not None and num["tare"] < 0:
            add("GV-03", "REJECTED", "tare", "tare weight must be >= 0")
        if num["gross"] is not None and num["tare"] is not None and num["tare"] >= num["gross"]:
            add("GV-03", "REJECTED", "tare", "tare must be less than gross")
        if num["net"] is not None and num["net"] < 0:
            add("GV-03", "REJECTED", "net", "net weight must be >= 0")
        if cmap.get("grade") and v["grade"] and v["grade"] not in GRADES:
            add("GV-03", "REJECTED", "grade", f"unknown quality grade {v['grade']!r}")

        # GV-04 measurement consistency
        if None not in (num["gross"], num["tare"], num["net"]):
            diff = abs(num["net"] - (num["gross"] - num["tare"]))
            if diff > NET_REJECT_KG:
                add("GV-04", "REJECTED", "net", f"net differs from gross - tare by {diff:.1f} kg")
            elif diff > NET_TOLERANCE_KG + 1e-9:
                add("GV-04", "WARNING", "net", f"net differs from gross - tare by {diff:.1f} kg")

        # GV-05 duplicate record_id (first occurrence stays, later ones are rejected)
        if v["record_id"]:
            if v["record_id"] in seen_ids:
                add("GV-05", "REJECTED", "record_id", "record_id already seen earlier in file")
            seen_ids.add(v["record_id"])

        # GV-06 natural-key conflict
        if v["warehouse_id"] and v["batch_id"] and v["received"]:
            d = parse_when(v["received"], fmt)
            key = (v["warehouse_id"], v["batch_id"], d.isoformat() if d else v["received"])
            if len(groups[key]) > 1:
                add("GV-06", "UNRESOLVED", "batch_id",
                    "same warehouse, batch and receipt date as another record with a different record_id")

        # GV-07 provenance
        if v["source_system"] == "":
            add("GV-07", "REJECTED", "source_system", "provenance missing: source_system empty")
        if v["provenance_ref"] == "":
            add("GV-07", "REJECTED", "provenance_ref", "provenance missing: source reference empty")

        # GV-08 source registry
        if v["source_system"]:
            state = sources.get(v["source_system"])
            if state is None:
                add("GV-08", "UNRESOLVED", "source_system", f"source {v['source_system']!r} not in registry")
            elif state == "DEPRECATED":
                add("GV-08", "WARNING", "source_system", f"source {v['source_system']!r} is deprecated")

        # GV-09 / GV-10 freshness
        if v["verified"] == "":
            add("GV-10", "UNRESOLVED", "verified", "last verification date missing, freshness unconfirmed")
        elif when["verified"] is not None and (ref_date - when["verified"]).days > stale_days:
            age = (ref_date - when["verified"]).days
            add("GV-09", "WARNING", "verified", f"last verified {age} days before reference date (limit {stale_days})")

        # GV-11 impossible dates
        if when["received"] is not None and when["received"] > ref_date:
            add("GV-11", "REJECTED", "received", "receipt date is after the reference date")
        if when["received"] is not None and when["verified"] is not None and when["verified"] < when["received"]:
            add("GV-11", "REJECTED", "verified", "verified before it was received")

        # GV-12 moisture threshold (only for otherwise valid moisture)
        if num["moisture"] is not None and MOISTURE_WARN < num["moisture"] <= MOISTURE_MAX:
            add("GV-12", "WARNING", "moisture", f"moisture {num['moisture']} above {MOISTURE_WARN:g}")

        status = "ACCEPTED"
        for f in findings:
            if RANK[f["status"]] > RANK[status]:
                status = f["status"]
        rules = sorted({f["rule"] for f in findings})
        results.append({
            "row_number": i + 1,
            "record_id": v["record_id"],
            "status": status,
            "rules": rules,
            "findings": findings,
            "provenance": {"source_system": v["source_system"] or None,
                           "source_ref": v["provenance_ref"] or None},
            "freshness": {"last_verified": v["verified"] or None,
                          "stale": "GV-09" in rules,
                          "unconfirmed": "GV-10" in rules},
        })
    return results


def count_by_status(results):
    c = {s: 0 for s in STATUSES}
    for r in results:
        c[r["status"]] += 1
    return c


def validate_file(path, schema, sources, ref_date, stale_days=90):
    """Read and validate one CSV. Returns (report_dict, rows)."""
    columns, rows = read_csv(path)
    col_check = check_columns(columns, schema)
    report = {"schema_version": schema["schema_version"], "column_check": col_check,
              "total_rows": len(rows)}
    if not col_check["ok"]:
        report["records"] = []
        report["counts"] = None
        return report, rows
    results = validate_rows(rows, schema, sources, ref_date, stale_days)
    report["records"] = results
    report["counts"] = count_by_status(results)
    return report, rows
