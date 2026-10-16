# Limitations, assumptions and untested conditions

## Assumptions
1. The reference date is fixed at 2026-10-15 and is read from `data/dataset_catalog.json`.
2. Thresholds are my own choices: stale after 90 days, net-weight tolerance 0.5 kg, reject above 5 kg, moisture warning above 14%, hard limit 40%. A reviewer may want different values.
3. Allowed commodities and grades are fixed lists defined for this exercise.
4. The source registry (four sources, one deprecated) is invented.
5. The natural key is warehouse + batch + receipt date.
6. A dataset version is bound to exactly one schema version in the catalog.
7. Input is CSV with a header row, UTF-8, comma separated.

## Limitations
- The registry is an in-memory simulation. Nothing persists between runs; registering the same version twice overwrites the first copy silently (not tested).
- Access control is a three-token lookup. It does not model token expiry, revocation, auditing of denied attempts, or any real attack. It is not security certification.
- Column check requires the exact header (set and order). A reordered header is rejected; a real system might tolerate reordering.
- Duplicate detection is within one file only, not across dataset versions.
- GV-06 uses only the date part of a timestamp; two receipts on the same day with a different time are treated as the same natural key.
- Freshness uses date granularity; the time of day and the UTC offset are ignored after parsing.
- Numbers are parsed as binary floats; comparisons use a 1e-9 allowance. Very large or very precise values were not tested.
- The independent verifier follows the same written rule table as the application. It catches coding mistakes, not a wrong rule design. If the design note is wrong, both implementations would agree on the wrong answer.
- Expected outcomes in `data/expected_outcomes_*.csv` were produced by the same generator that planted the defects, so they are ground truth for the planted cases only. Unplanted defect types are not covered.

## Untested conditions
- Empty file, header-only file, file without a header, non-UTF-8 bytes, very large files.
- Rows with more or fewer cells than the header.
- Two defects in the same cell producing the same rule twice (handled in code, not specifically tested).
- Concurrent registration or retrieval.
- Behaviour with a different reference date than the one in the catalog.
- Any interaction with real MASTERDB, MDU, TANTRA, Bucket or InsightFlow.

## Known defects
None identified at the time of writing. See `review_packets/REVIEW_PACKET.md` for the final statement after the clean run.

## Gap disclosure for the "every rule exercised" requirement
All rules GV-01 to GV-12 have per-rule fixtures (test T13). GV-13 and GV-14 are exercised through registration envelopes (tests T07 to T09 and T12). No rule is left unexercised. A retrieval-time "no valid records" failure does not exist because registration already refuses such files (`REJECT_NO_VALID_RECORDS`, test T12).
