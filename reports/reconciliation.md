# Reconciliation

Three views of the same data: (A) application output, (B) independent verifier, (C) planted expected outcomes from the generator.


## v1

- MATCH: v1 row totals A=B=C (A=62 B=62 C=62)
- MATCH: v1 status counts A=B (A={'ACCEPTED': 34, 'WARNING': 10, 'UNRESOLVED': 6, 'REJECTED': 12} B={'ACCEPTED': 34, 'WARNING': 10, 'UNRESOLVED': 6, 'REJECTED': 12})
- MATCH: v1 status counts A=C (C={'ACCEPTED': 34, 'WARNING': 10, 'UNRESOLVED': 6, 'REJECTED': 12})
- MATCH: v1 per-row status and rule set A=B=C (all rows agree)
- MATCH: v1 exception count = rows not ACCEPTED (exceptions=28)

## v2

- MATCH: v2 row totals A=B=C (A=24 B=24 C=24)
- MATCH: v2 status counts A=B (A={'ACCEPTED': 19, 'WARNING': 1, 'UNRESOLVED': 1, 'REJECTED': 3} B={'ACCEPTED': 19, 'WARNING': 1, 'UNRESOLVED': 1, 'REJECTED': 3})
- MATCH: v2 status counts A=C (C={'ACCEPTED': 19, 'WARNING': 1, 'UNRESOLVED': 1, 'REJECTED': 3})
- MATCH: v2 per-row status and rule set A=B=C (all rows agree)
- MATCH: v2 exception count = rows not ACCEPTED (exceptions=5)

## retrieval

- MATCH: RET-01 retrieved row identities = independent non-rejected rows (50 rows)
- MATCH: RET-01 withheld count = independent rejected count (withheld=12)
- MATCH: RET-02 retrieved row identities = independent non-rejected rows (21 rows)
- MATCH: RET-02 withheld count = independent rejected count (withheld=3)

**Overall: ALL CHECKS MATCH**
