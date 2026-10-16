#!/usr/bin/env python3
"""Deterministic synthetic data generator for BHIV Task 3 practice.
Scenario: DS-AGRI-STOCK-001 (grain warehouse stock records). 100% synthetic.
Run:  python3 generate_data.py   (re-running produces byte-identical files)
"""
import csv, json, os, random, datetime as dt
from collections import Counter

random.seed(20261015)
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
FX = os.path.join(OUT, "fixtures")
os.makedirs(FX, exist_ok=True)

REF = dt.date(2026, 10, 15)          # reference "today" for freshness rules
STALE_DAYS = 90                      # last_verified older than this => stale
WAREHOUSES = ["WH-NSK-01", "WH-NSK-02", "WH-PUN-01", "WH-NGP-01"]
COMMODITIES = ["WHEAT", "RICE", "MAIZE", "SOYBEAN", "CHICKPEA"]
GOOD_SOURCES = ["SRC-WMS-A", "SRC-WMS-B", "SRC-MANUAL"]

S1_COLS = ["record_id", "warehouse_id", "commodity", "batch_id", "gross_kg", "tare_kg",
           "net_kg", "moisture_pct", "received_date", "last_verified_date",
           "source_system", "source_ref", "unit"]
S2_COLS = ["record_id", "warehouse_id", "commodity", "batch_id", "gross_kg", "tare_kg",
           "net_weight_kg", "moisture_percent", "quality_grade", "received_at",
           "last_verified_at", "source_system", "provenance_ref"]


def f1(x):
    return f"{x:.1f}"


def clean_s1(i):
    wh = WAREHOUSES[i % 4]
    verified = dt.date(2026, 8, 1) + dt.timedelta(days=random.randint(0, 74))
    received = max(dt.date(2026, 6, 1), verified - dt.timedelta(days=random.randint(1, 45)))
    gross = round(random.uniform(2000, 9000), 1)
    tare = round(random.uniform(150, 600), 1)
    src = random.choice(GOOD_SOURCES)
    return {
        "record_id": f"AS1-{i+1:04d}", "warehouse_id": wh,
        "commodity": random.choice(COMMODITIES), "batch_id": f"{wh}-B{i+1:04d}",
        "gross_kg": f1(gross), "tare_kg": f1(tare), "net_kg": f1(round(gross - tare, 1)),
        "moisture_pct": f1(round(random.uniform(8, 13.5), 1)),
        "received_date": received.isoformat(), "last_verified_date": verified.isoformat(),
        "source_system": src, "source_ref": f"{src}/{received:%Y%m%d}/{i+1:05d}", "unit": "kg",
    }


# ---------------- Dataset v1.0.0, schema S1 ----------------
N = 60
rows = [clean_s1(i) for i in range(N)]
labels = {i: ("ACCEPTED", []) for i in range(N)}      # idx -> (status, [rules])
rule_rows = {}                                          # rule tag -> [row idx]


def mark(idx, rule, status, tag=None, **changes):
    rows[idx].update(changes)
    labels[idx] = (status, [rule])
    rule_rows.setdefault(tag or rule, []).append(idx)


mark(5, "GV-01", "REJECTED", commodity="")
mark(6, "GV-01", "REJECTED", gross_kg="")
mark(7, "GV-02", "REJECTED", gross_kg="12O0.5")                       # letter O
mark(8, "GV-03", "REJECTED", moisture_pct="-3.2")
mark(9, "GV-03", "REJECTED", commodity="WHEET")
g = float(rows[10]["gross_kg"])
mark(10, "GV-03", "REJECTED", tare_kg=f1(g + 50), net_kg="-50.0")      # tare > gross
g = float(rows[11]["gross_kg"]); t = float(rows[11]["tare_kg"])
mark(11, "GV-04", "REJECTED", tag="GV-04-large", net_kg=f1(g - t - 85))
g = float(rows[12]["gross_kg"]); t = float(rows[12]["tare_kg"])
mark(12, "GV-04", "WARNING", tag="GV-04-small", net_kg=f1(g - t + 2.4))
mark(15, "GV-07", "REJECTED", source_ref="")
mark(16, "GV-07", "REJECTED", source_system="")
mark(17, "GV-08", "UNRESOLVED", tag="GV-08-unknown", source_system="SRC-GHOST",
     source_ref="SRC-GHOST/20260901/00018")
mark(18, "GV-08", "UNRESOLVED", tag="GV-08-unknown", source_system="SRC-GHOST",
     source_ref="SRC-GHOST/20260902/00019")
for k, idx in enumerate((19, 20, 21)):
    mark(idx, "GV-08", "WARNING", tag="GV-08-deprecated", source_system="SRC-LEGACY",
         source_ref=f"SRC-LEGACY/{rows[idx]['received_date'].replace('-', '')}/{idx+1:05d}")
for idx in (22, 23, 24, 25):
    mark(idx, "GV-09", "WARNING", received_date="2026-03-10", last_verified_date="2026-04-02")
for idx in (26, 27):
    mark(idx, "GV-10", "UNRESOLVED", last_verified_date="")
mark(28, "GV-11", "REJECTED", tag="GV-11-future", received_date="2026-12-05")
mark(29, "GV-11", "REJECTED", tag="GV-11-order", received_date="2026-10-01",
     last_verified_date="2026-09-20")
for idx in (30, 31):
    mark(idx, "GV-12", "WARNING", moisture_pct="15.8")

# GV-05: exact duplicate record_id (later copy rejected, first copy stays ACCEPTED)
dup = dict(rows[3])
rows.append(dup)
labels[len(rows) - 1] = ("REJECTED", ["GV-05"])
rule_rows.setdefault("GV-05", []).extend([3, len(rows) - 1])

# GV-06: natural key (warehouse_id, batch_id, received_date) conflict, different record_id
conf = dict(rows[14])
conf["record_id"] = "AS1-0061"
g = round(float(conf["gross_kg"]) + 310.0, 1); t = float(conf["tare_kg"])
conf.update(gross_kg=f1(g), net_kg=f1(round(g - t, 1)), source_ref=conf["source_ref"] + "-R")
rows.append(conf)
labels[14] = ("UNRESOLVED", ["GV-06"])
labels[len(rows) - 1] = ("UNRESOLVED", ["GV-06"])
rule_rows.setdefault("GV-06", []).extend([14, len(rows) - 1])

with open(os.path.join(OUT, "warehouse_stock_v1.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=S1_COLS)
    w.writeheader(); w.writerows(rows)

# expected outcomes (ground truth from planted defects, 1-based data row number)
with open(os.path.join(OUT, "expected_outcomes_v1.csv"), "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["row_number", "record_id", "expected_status", "expected_rules"])
    for i, r in enumerate(rows):
        st, rl = labels[i]
        w.writerow([i + 1, r["record_id"], st, "|".join(rl)])

# per-rule fixtures (planted rows + one clean control row)
for tag, idxs in rule_rows.items():
    with open(os.path.join(FX, f"fx_{tag}.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=S1_COLS)
        w.writeheader()
        w.writerow(rows[0])  # clean control
        for i in sorted(set(idxs)):
            w.writerow(rows[i])

# ---------------- Dataset v1.1.0, schema S2 ----------------
def iso_dt(d, naive=False):
    return f"{d}T09:30:00" if naive else f"{d}T09:30:00+05:30"


rows2 = []
for i in range(24):
    base = clean_s1(i + 100)
    rows2.append({
        "record_id": f"AS2-{i+1:04d}", "warehouse_id": base["warehouse_id"],
        "commodity": base["commodity"], "batch_id": f"{base['warehouse_id']}-C{i+1:04d}",
        "gross_kg": base["gross_kg"], "tare_kg": base["tare_kg"],
        "net_weight_kg": base["net_kg"], "moisture_percent": base["moisture_pct"],
        "quality_grade": random.choice(["A", "B", "C"]),
        "received_at": iso_dt(base["received_date"]),
        "last_verified_at": iso_dt(base["last_verified_date"]),
        "source_system": base["source_system"],
        "provenance_ref": base["source_ref"].replace("/", "/S2/", 1),
    })
labels2 = {i: ("ACCEPTED", []) for i in range(24)}
rows2[3]["quality_grade"] = "Z";                      labels2[3] = ("REJECTED", ["GV-03"])
rows2[7]["provenance_ref"] = "";                      labels2[7] = ("REJECTED", ["GV-07"])
rows2[11].update(received_at=iso_dt("2026-04-20"), last_verified_at=iso_dt("2026-05-20"))
labels2[11] = ("WARNING", ["GV-09"])
rows2[15]["last_verified_at"] = iso_dt(rows2[15]["last_verified_at"][:10], naive=True)
labels2[15] = ("REJECTED", ["GV-02"])                 # timestamp without timezone offset
rows2[19].update(source_system="SRC-GHOST", provenance_ref="SRC-GHOST/S2/20260905/00020")
labels2[19] = ("UNRESOLVED", ["GV-08"])

with open(os.path.join(OUT, "warehouse_stock_v2.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=S2_COLS)
    w.writeheader(); w.writerows(rows2)
with open(os.path.join(OUT, "expected_outcomes_v2.csv"), "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["row_number", "record_id", "expected_status", "expected_rules"])
    for i, r in enumerate(rows2):
        st, rl = labels2[i]
        w.writerow([i + 1, r["record_id"], st, "|".join(rl)])

# S1-header and S2-header sample rows for schema mismatch fixtures
def write_csv(path, cols, data):
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader(); w.writerows(data)

write_csv(os.path.join(FX, "fx_GV-13_s1_columns.csv"), S1_COLS, [rows[0], rows[1], rows[2]])
write_csv(os.path.join(FX, "fx_GV-13_s2_columns.csv"), S2_COLS, rows2[:3])

write_csv(os.path.join(FX, "fx_all_invalid_s1.csv"), S1_COLS, [rows[5], rows[6], rows[7]])

# ---------------- Reference/config files ----------------
def dump(name, obj, folder=OUT):
    with open(os.path.join(folder, name), "w") as fh:
        json.dump(obj, fh, indent=2); fh.write("\n")

dump("source_registry.json", {
    "_label": "SYNTHETIC local source registry, not a real BHIV/MASTERDB artefact",
    "sources": [
        {"source_system": "SRC-WMS-A", "status": "ACTIVE"},
        {"source_system": "SRC-WMS-B", "status": "ACTIVE"},
        {"source_system": "SRC-MANUAL", "status": "ACTIVE"},
        {"source_system": "SRC-LEGACY", "status": "DEPRECATED"},
    ]})

dump("dataset_catalog.json", {
    "_label": "SIMULATED catalog. Not a MASTERDB contract. Identity, dataset version and schema version are separate keys.",
    "dataset_id": "DS-AGRI-STOCK-001",
    "reference_date": REF.isoformat(), "stale_after_days": STALE_DAYS,
    "versions": [
        {"dataset_version": "1.0.0", "schema_version": "S1", "file": "warehouse_stock_v1.csv",
         "declared_record_count": len(rows)},
        {"dataset_version": "1.1.0", "schema_version": "S2", "file": "warehouse_stock_v2.csv",
         "declared_record_count": len(rows2)},
    ],
    "schema_versions": {
        "S1": {"columns": S1_COLS},
        "S2": {"columns": S2_COLS,
               "breaking_changes_vs_S1": [
                   "net_kg renamed to net_weight_kg", "moisture_pct renamed to moisture_percent",
                   "source_ref renamed to provenance_ref", "received_date/last_verified_date replaced by timezone-aware received_at/last_verified_at",
                   "unit column removed", "quality_grade added (A/B/C, required)"]},
    }})

dump("fx_envelopes.json", {
    "_label": "SIMULATED registration envelopes. expected_* values are planted ground truth for tests.",
    "envelopes": [
        {"id": "ENV-01", "dataset_id": "DS-AGRI-STOCK-001", "dataset_version": "1.0.0", "schema_version": "S1",
         "file": "warehouse_stock_v1.csv", "declared_record_count": len(rows),
         "expected": "REGISTER_OK_WITH_WARNINGS"},
        {"id": "ENV-02", "dataset_id": "DS-AGRI-STOCK-001", "dataset_version": "1.1.0", "schema_version": "S2",
         "file": "warehouse_stock_v2.csv", "declared_record_count": len(rows2),
         "expected": "REGISTER_OK_WITH_WARNINGS"},
        {"id": "ENV-03", "dataset_id": "DS-AGRI-NOPE", "dataset_version": "1.0.0", "schema_version": "S1",
         "file": "warehouse_stock_v1.csv", "declared_record_count": len(rows),
         "expected": "REJECT_UNKNOWN_DATASET_ID"},
        {"id": "ENV-04", "dataset_id": "DS-AGRI-STOCK-001", "dataset_version": None, "schema_version": "S1",
         "file": "warehouse_stock_v1.csv", "declared_record_count": len(rows),
         "expected": "REJECT_MISSING_VERSION"},
        {"id": "ENV-05", "dataset_id": "DS-AGRI-STOCK-001", "dataset_version": "2.0.0", "schema_version": "S1",
         "file": "warehouse_stock_v1.csv", "declared_record_count": len(rows),
         "expected": "REJECT_UNKNOWN_DATASET_VERSION"},
        {"id": "ENV-06", "dataset_id": "DS-AGRI-STOCK-001", "dataset_version": "1.0.0", "schema_version": "S9",
         "file": "warehouse_stock_v1.csv", "declared_record_count": len(rows),
         "expected": "REJECT_UNKNOWN_SCHEMA_VERSION"},
        {"id": "ENV-07", "dataset_id": "DS-AGRI-STOCK-001", "dataset_version": "1.1.0", "schema_version": "S2",
         "file": "fixtures/fx_GV-13_s1_columns.csv", "declared_record_count": 3,
         "expected": "REJECT_SCHEMA_MISMATCH (declares S2, columns are S1)"},
        {"id": "ENV-08", "dataset_id": "DS-AGRI-STOCK-001", "dataset_version": "1.0.0", "schema_version": "S1",
         "file": "fixtures/fx_GV-13_s2_columns.csv", "declared_record_count": 3,
         "expected": "REJECT_SCHEMA_MISMATCH (declares S1, columns are S2)"},
        {"id": "ENV-09", "dataset_id": "DS-AGRI-STOCK-001", "dataset_version": "1.0.0", "schema_version": "S1",
         "file": "warehouse_stock_v1.csv", "declared_record_count": 60,
         "expected": f"REJECT_COUNT_MISMATCH (declared 60, actual {len(rows)})"},
    ]}, FX)

dump("access_policy.json", {
    "_label": "SIMULATED local access model with fake tokens. Not production security.",
    "principals": {
        "tok-reader-01": {"role": "reader", "datasets": ["DS-AGRI-STOCK-001"]},
        "tok-reader-02": {"role": "reader", "datasets": []},
        "tok-writer-01": {"role": "registrar", "datasets": ["DS-AGRI-STOCK-001"]},
    },
    "permissions": {"reader": ["retrieve"], "registrar": ["register", "retrieve"]}})

dump("fx_access_requests.json", {
    "_label": "SIMULATED requests with planted expected results.",
    "requests": [
        {"id": "REQ-01", "token": "tok-reader-01", "action": "retrieve", "dataset_id": "DS-AGRI-STOCK-001",
         "dataset_version": "1.0.0", "expected": "ALLOW (records carry warnings/unresolved flags)"},
        {"id": "REQ-02", "token": None, "action": "retrieve", "dataset_id": "DS-AGRI-STOCK-001",
         "dataset_version": "1.0.0", "expected": "DENY_UNAUTHENTICATED"},
        {"id": "REQ-03", "token": "tok-unknown-77", "action": "retrieve", "dataset_id": "DS-AGRI-STOCK-001",
         "dataset_version": "1.0.0", "expected": "DENY_UNKNOWN_PRINCIPAL"},
        {"id": "REQ-04", "token": "tok-reader-01", "action": "register", "dataset_id": "DS-AGRI-STOCK-001",
         "dataset_version": "1.0.0", "expected": "DENY_ROLE_NOT_PERMITTED"},
        {"id": "REQ-05", "token": "tok-reader-02", "action": "retrieve", "dataset_id": "DS-AGRI-STOCK-001",
         "dataset_version": "1.0.0", "expected": "DENY_DATASET_NOT_GRANTED"},
        {"id": "REQ-06", "token": "tok-writer-01", "action": "register", "dataset_id": "DS-AGRI-STOCK-001",
         "dataset_version": "1.1.0", "expected": "ALLOW"},
    ]}, FX)

# ---------------- Expected counts + README ----------------
c1 = Counter(s for s, _ in labels.values())
c2 = Counter(s for s, _ in labels2.values())
dump("expected_counts.json", {
    "_label": "Planted ground truth. Use only to check YOUR validator, never to generate its answers.",
    "v1_rows": len(rows), "v1_status": dict(c1), "v2_rows": len(rows2), "v2_status": dict(c2),
    "v1_rule_row_counts": {k: len(set(v)) for k, v in sorted(rule_rows.items())}})

readme = f"""# Task 3 practice data: DS-AGRI-STOCK-001 (synthetic grain-warehouse stock)

100% synthetic. Generated by `generate_data.py` (seed 20261015, reproducible).
Reference date for freshness: {REF}. Stale if last_verified older than {STALE_DAYS} days.

NOTE: Task 3 says the reviewer supplies the scenario. Treat this as a PRACTICE dataset
unless your reviewer approves it. State this in AI_USE_LOG.md.

## Three identifiers (keep separate)
- Dataset identity: DS-AGRI-STOCK-001
- Dataset versions: 1.0.0 (62 rows) and 1.1.0 (24 rows)
- Schema versions: S1 (13 columns) and S2 (13 columns, renamed/added/removed fields; breaking)

## Files
- warehouse_stock_v1.csv / warehouse_stock_v2.csv : inputs
- expected_outcomes_v1.csv / _v2.csv : planted ground truth per row
- expected_counts.json : totals per status
- dataset_catalog.json, source_registry.json, access_policy.json : SIMULATED reference data
- fixtures/ : per-rule mini files, envelopes (registration cases), access requests, fx_all_invalid_s1.csv

## Outcomes
ACCEPTED, WARNING, REJECTED, UNRESOLVED. Precedence: REJECTED > UNRESOLVED > WARNING > ACCEPTED.

## Rules planted (IDs are mine; rename or redesign them in your own design note)
| Rule | Detects | Outcome |
|---|---|---|
| GV-01 | missing required field | REJECTED |
| GV-02 | wrong type/format (non-numeric weight, tz-less timestamp in S2) | REJECTED |
| GV-03 | invalid value/domain (negative moisture, unknown commodity, tare > gross, bad grade) | REJECTED |
| GV-04 | net != gross - tare (tolerance 0.5 kg; <=5 kg WARNING; >5 kg REJECTED) | WARNING/REJECTED |
| GV-05 | duplicate record_id (later copy) | REJECTED |
| GV-06 | same warehouse+batch+received_date, different record_id | UNRESOLVED (both rows) |
| GV-07 | missing provenance (source_system or source_ref) | REJECTED |
| GV-08 | source not in registry / deprecated source | UNRESOLVED / WARNING |
| GV-09 | stale last_verified | WARNING |
| GV-10 | freshness unconfirmed (last_verified empty) | UNRESOLVED |
| GV-11 | impossible dates (future received, verified before received) | REJECTED |
| GV-12 | moisture above 14% storage threshold | WARNING |
| GV-13 | file columns do not match declared schema version | REJECT file |
| GV-14 | unknown dataset id / missing or unknown version / unknown schema / count mismatch | REJECT request |

## Expected totals
- v1 ({len(rows)} rows): {dict(c1)}
- v2 ({len(rows2)} rows): {dict(c2)}

Remember: expected files are for CHECKING your validator. Build the validator yourself.
"""
with open(os.path.join(OUT, "README_DATA.md"), "w") as fh:
    fh.write(readme)

print("v1", len(rows), dict(c1))
print("v2", len(rows2), dict(c2))
