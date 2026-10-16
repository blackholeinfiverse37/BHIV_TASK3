# Data dictionary: DS-AGRI-STOCK-001

Synthetic grain-warehouse stock records. Machine-readable versions: `schema_S1.json`, `schema_S2.json`.

## Identity, dataset version, schema version (kept separate)

| Concept | Meaning | Values here |
|---|---|---|
| Dataset identity | What the dataset is | `DS-AGRI-STOCK-001` |
| Dataset version | Which release of the content | `1.0.0` (62 rows), `1.1.0` (24 rows) |
| Schema version | Which column layout the content uses | `S1`, `S2` |

A dataset version is bound to exactly one schema version in the catalog (1.0.0 = S1, 1.1.0 = S2), but they are different keys. A request can get either wrong independently.

## Fields, schema S1 (13 columns)

| Field | Type | Meaning | Constraint |
|---|---|---|---|
| record_id | string | Unique record id | required, unique |
| warehouse_id | string | Warehouse code | required |
| commodity | string | Grain type | required, WHEAT/RICE/MAIZE/SOYBEAN/CHICKPEA |
| batch_id | string | Batch within warehouse | required |
| gross_kg | decimal | Gross weight | required, > 0 |
| tare_kg | decimal | Tare weight | required, >= 0, < gross |
| net_kg | decimal | Net weight | required, >= 0, = gross - tare within 0.5 kg |
| moisture_pct | decimal | Moisture % | required, 0..40, > 14 warns |
| received_date | date | Receipt date | required, ISO date, not in future |
| last_verified_date | date | Last verification | empty = unconfirmed; >= received; > 90 days old = stale |
| source_system | string | Producing system | provenance, must be present |
| source_ref | string | Source entry reference | provenance, must be present |
| unit | string | Always kg | informational |

## Differences in schema S2 (13 columns)

| S1 | S2 | Change |
|---|---|---|
| net_kg | net_weight_kg | renamed |
| moisture_pct | moisture_percent | renamed |
| source_ref | provenance_ref | renamed |
| received_date (date) | received_at (datetime + offset) | renamed and retyped |
| last_verified_date (date) | last_verified_at (datetime + offset) | renamed and retyped |
| unit | (removed) | removed |
| (none) | quality_grade A/B/C, required | added |

An S1 file declared as S2 (or the reverse) fails at column level (rule GV-13) before any row is looked at.

## Natural key

`(warehouse_id, batch_id, date part of received)`. Two rows with the same natural key but different `record_id` are a conflict (GV-06).

## Reference date

All freshness and future-date checks use the fixed reference date 2026-10-15 from `data/dataset_catalog.json`, so results are reproducible on any day.
