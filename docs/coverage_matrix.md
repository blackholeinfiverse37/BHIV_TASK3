# Test coverage matrix

Rule or requirement against the fixture that triggers it and the test that checks it. Results are in `evidence/test_results.json` (written by `tests/run_tests.py`).

## Row rules

| Rule | Fixture | Planted rows in main data | Test |
|---|---|---|---|
| GV-01 | `fx_GV-01.csv` | v1 rows 6, 7 | T02, T13 |
| GV-02 | `fx_GV-02.csv` | v1 row 8; v2 row 16 (no UTC offset) | T03, T13, T14 |
| GV-03 | `fx_GV-03.csv` | v1 rows 9, 10, 11; v2 row 4 (grade Z) | T03, T13, T14 |
| GV-04 | `fx_GV-04-large.csv`, `fx_GV-04-small.csv` | v1 rows 12 (reject), 13 (warning) | T13, T14 |
| GV-05 | `fx_GV-05.csv` | v1 row 61 (copy of row 4) | T04, T13 |
| GV-06 | `fx_GV-06.csv` | v1 rows 15 and 62 | T04, T13 |
| GV-07 | `fx_GV-07.csv` | v1 rows 16, 17; v2 row 8 | T05, T13 |
| GV-08 | `fx_GV-08-unknown.csv`, `fx_GV-08-deprecated.csv` | v1 rows 18, 19 (unknown), 20 to 22 (deprecated); v2 row 20 | T13, T14 |
| GV-09 | `fx_GV-09.csv` | v1 rows 23 to 26; v2 row 12 | T06, T13 |
| GV-10 | `fx_GV-10.csv` | v1 rows 27, 28 | T06, T13 |
| GV-11 | `fx_GV-11-future.csv`, `fx_GV-11-order.csv` | v1 rows 29, 30 | T13, T14 |
| GV-12 | `fx_GV-12.csv` | v1 rows 31, 32 | T13, T14 |

## File and request rules

| Rule / outcome | Fixture or envelope | Test |
|---|---|---|
| GV-13 schema mismatch (S1 file declared S2, S2 file declared S1) | `fx_GV-13_s1_columns.csv`, `fx_GV-13_s2_columns.csv`, ENV-07, ENV-08 | T09 |
| GV-14 unknown dataset id | ENV-03; retrieval of `DS-AGRI-NOPE` | T07 |
| GV-14 missing version | ENV-04; retrieval without version | T08 |
| GV-14 unknown dataset version | ENV-05 | T08 |
| GV-14 unknown schema | ENV-06 | T08 |
| GV-14 schema not bound to version | ENV-01 edited in test to declare S2 | T08 |
| GV-14 count mismatch at registration | ENV-09; declared 61 | T12 |
| GV-14 no usable records | `fx_all_invalid_s1.csv` | T12 |

## The 12 mandatory tests

| # | Mandatory item | Test |
|---|---|---|
| 1 | Valid input | T01 |
| 2 | Missing required field | T02 |
| 3 | Invalid field type or value | T03 |
| 4 | Duplicate record | T04 |
| 5 | Missing provenance | T05 |
| 6 | Stale or unconfirmed freshness | T06 |
| 7 | Unknown dataset identity | T07 |
| 8 | Missing or incompatible version | T08 |
| 9 | Schema compatibility or breaking change | T09 |
| 10 | Unauthorized retrieval | T10 |
| 11 | Partial retrieval or records carrying warnings | T11 |
| 12 | Incorrect registration or retrieval count | T12 |

Extra tests: T13 (rule coverage), T14 (independent implementation agrees), T15 (provenance preserved), T16 (determinism).

## Independent verification

| Method | File |
|---|---|
| Second implementation of the row rules, no shared code | `tests/independent_verifier.py` |
| Three-way reconciliation (application, verifier, planted expectations) and retrieved record identities | `tests/reconcile.py` and `reports/reconciliation.md` |
| Mutation check: two deliberate bugs injected in a scratch copy, tests must fail | `evidence/mutation_check.txt` |
