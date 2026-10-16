# Review packet: Task 3

Candidate: Shivam Verma
Scenario: DS-AGRI-STOCK-001 (synthetic, AI-generated practice scenario). Reviewer approval of this scenario: NOT YET RECORDED.

## Status of this packet
- run by the candidate on the candidate's own machine on 2026-10-15 (log timestamp 2026-10-15T05:48:00Z).
- Task 2 formal approval: reported as approved by the candidate on 2026-10-15. 
- **No Task 3 reviewer decision recorded. Not self-approved.**

## Code revision
Not a git repository. Combined SHA-256 of 42 files (src, tests, tools, schemas, data), from the candidate's Windows run:
`b8ebb6745ef30c5ad44200c8fbed95c18234dfa7c1c9e4c05c1e111437b4cbb8`
Per-file hashes: `evidence/code_manifest.json`.


## Environment (of the recorded run)
Python 3.12.0, Windows 10 (Git Bash, MINGW64_NT-10.0-26300), standard library only, interpreter `python`. Details: `evidence/clean_run_log.txt`.

## Commands
```
bash reproduce.sh
```
Individual steps are listed in README.md.

## What was implemented
- Profiling of two files, 13 row/file rules (GV-01 to GV-13) plus request-level checks (GV-14), four outcome statuses, machine-readable results and exceptions.
- Simulated registry: registration with identity, version and schema checks, count check, controlled retrieval with warnings, simulated access control, simulated Bucket hash chain and InsightFlow events.
- Independent second implementation, reconciliation script, mutation check.

## What was actually tested and the results (from `evidence/test_results.json`)
| Test | Mandatory item | Result |
|---|---|---|
| T01 | 1 Valid input | PASS |
| T02 | 2 Missing required field | PASS |
| T03 | 3 Invalid type or value | PASS |
| T04 | 4 Duplicate record | PASS |
| T05 | 5 Missing provenance | PASS |
| T06 | 6 Stale or unconfirmed freshness | PASS |
| T07 | 7 Unknown dataset identity | PASS |
| T08 | 8 Missing or incompatible version | PASS |
| T09 | 9 Schema compatibility or breaking change | PASS |
| T10 | 10 Unauthorized retrieval | PASS |
| T11 | 11 Partial retrieval / warnings | PASS |
| T12 | 12 Incorrect registration or retrieval count | PASS |
| T13 | Rule coverage | PASS |
| T14 | Independent implementation agrees | PASS |
| T15 | Provenance preserved | PASS |
| T16 | Determinism | PASS |

16 of 16 passed, 0 blocked, on both the AI sandbox run and the candidate's Windows run. Each test's expected and actual values are in the JSON file.

## Totals and reconciliation
| Dataset | Rows | ACCEPTED | WARNING | UNRESOLVED | REJECTED |
|---|---|---|---|---|---|
| 1.0.0 (S1) | 62 | 34 | 10 | 6 | 12 |
| 1.1.0 (S2) | 24 | 19 | 1 | 1 | 3 |

Application, independent verifier and planted expectations agree on every row and every count (`reports/reconciliation.md`, "ALL CHECKS MATCH" in the Windows run). Retrieval: v1 returned 50 and withheld 12; v2 returned 21 and withheld 3; retrieved row identities equal the independent non-rejected rows. Exceptions: 28 (v1), 5 (v2).

## Independently verified
- Row statuses and rule sets by a second implementation and by planted expectations.
- Retrieved record identities and withheld counts against the independent view.
- Tests are able to fail: mutation check, 5 of 16 tests failed with two injected bugs (`evidence/mutation_check.txt`).
- Data regeneration: byte-identical in the Linux sandbox run (data digests matched). In the Windows run the "before" folder was empty, so that digest comparison is not evidence; the row counts and statuses are identical across both machines.

## Simulated (not real)
Registry, catalog, access tokens and policy, Bucket chain, InsightFlow events, all outcome codes such as `REGISTER_OK_WITH_WARNINGS`. None is an official MASTERDB, TANTRA, Bucket or InsightFlow contract. No live integration is claimed.

## Failed, blocked or unknown
- Failed tests: none in the recorded runs. Blocked tests: none.
- An earlier Windows attempt failed because Python was not on PATH; that log was not kept. It was an environment problem, not a test failure.
- Unknown: behaviour on the reviewer's own scenario and on the untested conditions in `docs/limitations.md`.
- Known defects: (1) the first version of `reproduce.sh` removed `data/` before checking that Python worked. Found when it was run without Python on PATH; fixed (Python is now checked first and old data is kept until regeneration succeeds). (2) The independent verifier shares the written rule table with the application, so a flaw in the rule design would not be caught by it. No other defects identified.

## Reviewer-selected failure scenarios (Day 3)
To be filled during the defence: scenario, predicted result, actual result, root cause, handling.

| # | Scenario chosen by reviewer | Prediction | Actual | Root cause and handling |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |

## Evidence paths
`evidence/clean_run_log.txt`, `evidence/test_results.json`, `evidence/mutation_check.txt`, `evidence/registration_scenario.json`, `evidence/access_scenario.json`, `evidence/retrieval_scenario.json`, `evidence/simulated_bucket_chain.json`, `evidence/simulated_insightflow_events.json`, `evidence/code_manifest.json`, `reports/reconciliation.md`, `reports/profiling_v1.md`, `reports/profiling_v2.md`, `reports/validation_results_v1.json`, `reports/validation_results_v2.json`, `reports/exceptions_v1.csv`, `reports/exceptions_v2.csv`.



## Reviewer decision (to be recorded by the designated reviewer only)
- Score: ____ / 100
- Outcome: PASS / PASS WITH FIXES / REVISION REQUIRED / NOT READY
- Failed or blocked tests: ____
- Critical findings: ____
- Reason: ____
- Evidence references: ____