# Design note: validation, outcomes, identity and versions

Scenario: DS-AGRI-STOCK-001, synthetic grain-warehouse stock records (practice dataset, see README caveat).

## 1. Problem and acceptance conditions

**Problem.** Decide, record by record, whether stock data is trustworthy enough to be registered and retrieved, and say why when it is not.

**Expected outputs.** Machine-readable validation results, an exceptions list, a profiling report, a simulated registration/retrieval run, and a reconciliation of counts.

**Acceptance conditions.**
1. Every row gets exactly one status: ACCEPTED, WARNING, UNRESOLVED or REJECTED.
2. Every non-ACCEPTED row names the rule(s) and a human-readable reason.
3. Source references survive from input to retrieval.
4. Dataset identity, dataset version and schema version are checked separately.
5. Counts reconcile three ways: application, independent verifier, planted expectations.
6. Re-running gives byte-identical outputs (fixed reference date, no clock).

## 2. Outcome definitions

| Status | Meaning | Retrieval behaviour (simulated) |
|---|---|---|
| ACCEPTED | No rule fired | returned |
| WARNING | Usable, but something should be visible to the consumer | returned, with warning flags |
| UNRESOLVED | Cannot be judged from the data alone (unknown source, conflicting duplicate, no verification date) | returned, flagged, never treated as clean |
| REJECTED | Violates a hard rule | withheld, counted |

Precedence when several rules fire: REJECTED > UNRESOLVED > WARNING > ACCEPTED. Every firing rule is still listed.

## 3. Identity, dataset version, schema version

| Key | Question it answers | Wrong value gives |
|---|---|---|
| Dataset identity (`DS-AGRI-STOCK-001`) | Which dataset? | `REJECT_UNKNOWN_DATASET_ID` |
| Dataset version (`1.0.0`, `1.1.0`) | Which release of the content? | `REJECT_MISSING_VERSION`, `REJECT_UNKNOWN_DATASET_VERSION` |
| Schema version (`S1`, `S2`) | Which column layout? | `REJECT_UNKNOWN_SCHEMA_VERSION`, `REJECT_SCHEMA_VERSION_INCOMPATIBLE`, `REJECT_SCHEMA_MISMATCH` |

Retrieval never guesses a "latest" version: a missing version is an error, because silently serving a different release is a data-integrity risk.

## 4. Rules: why, what, and what happens on failure

| Rule | Why it exists | Detects | On failure |
|---|---|---|---|
| GV-01 | A record without core fields cannot be used or audited | empty required field | REJECTED |
| GV-02 | Downstream arithmetic and date logic need real numbers and dates | non-numeric weight or moisture, wrong date format, S2 timestamp without UTC offset | REJECTED |
| GV-03 | Physically or logically impossible values | unknown commodity, moisture outside 0..40, gross <= 0, tare < 0, tare >= gross, net < 0, unknown grade | REJECTED |
| GV-04 | Three weights must agree | \|net - (gross - tare)\| > 0.5 kg. Up to 5 kg: WARNING (rounding, scale drift). Above 5 kg: REJECTED | WARNING or REJECTED |
| GV-05 | A record id must identify one record | later occurrence of a record_id in the file (first stays) | REJECTED |
| GV-06 | Two different ids for the same batch and day is a contradiction nobody can settle from the file | same warehouse + batch + receipt date, different record_id | UNRESOLVED (all rows in the group) |
| GV-07 | Data without provenance cannot be traced | empty source_system or source reference | REJECTED |
| GV-08 | Provenance must point to a known source | source not in registry: UNRESOLVED. Source marked DEPRECATED: WARNING | UNRESOLVED or WARNING |
| GV-09 | Old data may be out of date | last verification more than 90 days before the reference date | WARNING |
| GV-10 | "Never verified" differs from "verified long ago" | empty verification date | UNRESOLVED |
| GV-11 | Time cannot run backwards | received after the reference date, or verified before received | REJECTED |
| GV-12 | Storage risk, not a data error | moisture above 14% (and within 0..40) | WARNING |
| GV-13 | A file can claim a schema its columns do not follow | header differs from the declared schema (missing, extra, or reordered columns) | whole file REJECTED at registration |
| GV-14 | Requests can name things that do not exist | unknown dataset id, missing or unknown version, unknown or unbound schema, declared count differs from actual rows, no usable record | request REJECTED |

### Judgement calls (defend these in the review)
- **GV-06 marks both rows UNRESOLVED, not one REJECTED.** Nothing in the file says which is right. It applies only when record ids differ, otherwise it would double-penalise exact duplicates already handled by GV-05.
- **GV-04 has a grey band.** Small differences are common in real weighing; a hard reject would discard good data. The 0.5 kg and 5 kg limits are assumptions (see limitations).
- **Stale is a WARNING, unconfirmed is UNRESOLVED.** Stale data was checked once and is old; unconfirmed data has no evidence of ever being checked.
- **Reference date is fixed (2026-10-15)** so results do not drift with the real date. A real system would take it as an input.
- **Registration refuses a file with zero usable records** (`REJECT_NO_VALID_RECORDS`), rather than registering an empty shell.

## 5. Schema versions with observable differences

S1 and S2 differ in real files (`data/warehouse_stock_v1.csv` vs `_v2.csv`): three renamed fields, two retyped timestamps, one removed column, one added required field. See `schemas/DATA_DICTIONARY.md`. Test T09 proves the difference by computing the column sets and by rejecting S1 files declared as S2 and the reverse.

## 6. Simulation boundaries

`src/gv_registry_sim.py` is a local, in-memory simulation. Its response shapes (`REGISTER_OK_WITH_WARNINGS`, `OK_WITH_WARNINGS`, and so on) are invented for this exercise, are labelled simulated in the code and in every evidence file, and are not an official MASTERDB, TANTRA, Bucket or InsightFlow contract.
