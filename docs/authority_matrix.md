# Authority matrix

Who owns what, and how this local exercise touches each component. Responsibilities are copied from the task statement; the "In this exercise" column states what was actually built.

| Component | Canonical responsibility (from the task) | In this exercise | Not done / not claimed |
|---|---|---|---|
| MASTERDB | Governed dataset registration, versions, controlled retrieval, data-quality status | `src/gv_registry_sim.py` imitates registration, version binding, retrieval and quality status, in memory, labelled SIMULATED | No connection to real MASTERDB. No API contract invented as official. No persistence layer, auth service or registry rebuilt (Kavy's area) |
| MDU | Semantic definitions, schemas, ontology, lineage semantics | `schemas/schema_S1.json`, `schema_S2.json` and the data dictionary are local practice definitions that the validator reads | Not MDU artefacts. No ontology or lineage modelling |
| TANTRA | Runtime discovery, authorized capability invocation, orchestration | `authorize()` in the simulation: principal, role, dataset grant. Fake tokens in `data/access_policy.json` | Not TANTRA. Not production security and not a security certification |
| Bucket | Canonical execution and artifact evidence chain | `evidence/simulated_bucket_chain.json`: a hash chain of registration and retrieval events | Not Bucket. The real evidence chain is untouched |
| InsightFlow | Telemetry and observability | `evidence/simulated_insightflow_events.json`: a list of event records | Not InsightFlow. No metrics, dashboards or alerting |

## Decision rights inside the simulation

| Decision | Made by (simulated component) | Why not elsewhere |
|---|---|---|
| Is this dataset id/version known and bound to this schema? | MASTERDB(sim) via the catalog | Registration and versions are MASTERDB's role |
| What does a field mean and which columns does a schema have? | MDU(sim) via `schemas/` | Semantics and schemas are MDU's role |
| May this caller register or retrieve? | TANTRA(sim) via `authorize()` | Authorized invocation is TANTRA's role |
| Is there proof of what happened? | Bucket(sim) hash chain | Evidence chain is Bucket's role |
| What happened and how often? | InsightFlow(sim) events | Telemetry is InsightFlow's role |

## Boundary rules followed
- No repository, API, credential or data outside this folder was used or changed.
- Nothing here duplicates Hariom's data-quality workstream or Kavy's platform work; the scenario, rules, code and evidence are new.
- Every simulated response and file carries a SIMULATED label.
