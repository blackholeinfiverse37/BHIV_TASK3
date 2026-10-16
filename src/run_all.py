"""Run the whole local pipeline: profile, validate, exceptions, simulated registration/retrieval.

Usage (from the submission root):  python3 src/run_all.py
Outputs go to reports/ and evidence/. Nothing here reads the clock, so reruns are byte-identical.
"""
import csv
import json
import os
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import gv_profile as P          # noqa: E402
import gv_registry_sim as R     # noqa: E402
import gv_validator as V        # noqa: E402

DATA = os.path.join(ROOT, "data")
SCHEMAS = os.path.join(ROOT, "schemas")
REPORTS = os.path.join(ROOT, "reports")
EVIDENCE = os.path.join(ROOT, "evidence")


def dump(path, obj):
    with open(path, "w") as fh:
        json.dump(obj, fh, indent=2, sort_keys=False)
        fh.write("\n")


def main():
    os.makedirs(REPORTS, exist_ok=True)
    os.makedirs(EVIDENCE, exist_ok=True)
    reg = R.SimulatedRegistry(DATA, SCHEMAS)
    ref = reg.ref_date
    print(f"Reference date {ref}  stale after {reg.stale_days} days")

    # ---- profile + validate + exceptions ----
    for ver in reg.catalog["versions"]:
        tag = "v1" if ver["schema_version"] == "S1" else "v2"
        schema = reg.schemas[ver["schema_version"]]
        path = os.path.join(DATA, ver["file"])
        columns, rows = V.read_csv(path)
        prof = P.profile(columns, rows, schema)
        dump(os.path.join(REPORTS, f"profiling_{tag}.json"), prof)
        with open(os.path.join(REPORTS, f"profiling_{tag}.md"), "w") as fh:
            fh.write(P.to_markdown(f"{reg.catalog['dataset_id']} {ver['dataset_version']} ({ver['schema_version']})", prof))

        report, _ = V.validate_file(path, schema, reg.sources, ref, reg.stale_days)
        out = {"dataset_id": reg.catalog["dataset_id"], "dataset_version": ver["dataset_version"],
               "schema_version": ver["schema_version"], "reference_date": ref.isoformat(),
               "total_rows": report["total_rows"], "counts": report["counts"],
               "records": report["records"]}
        dump(os.path.join(REPORTS, f"validation_results_{tag}.json"), out)
        exc = [r for r in report["records"] if r["status"] != "ACCEPTED"]
        dump(os.path.join(REPORTS, f"exceptions_{tag}.json"),
             {"dataset_version": ver["dataset_version"], "exception_count": len(exc), "exceptions": exc})
        with open(os.path.join(REPORTS, f"exceptions_{tag}.csv"), "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["row_number", "record_id", "status", "rules", "first_message"])
            for r in exc:
                w.writerow([r["row_number"], r["record_id"], r["status"], "|".join(r["rules"]),
                            r["findings"][0]["message"] if r["findings"] else ""])
        print(f"{tag} rows={report['total_rows']} counts={report['counts']} exceptions={len(exc)}")

    # ---- simulated registration ----
    envelopes = json.load(open(os.path.join(DATA, "fixtures", "fx_envelopes.json")))["envelopes"]
    reg_results = []
    for env in envelopes:
        res = reg.register("tok-writer-01", env)
        expected = env["expected"].split(" ")[0]
        reg_results.append({"envelope_id": env["id"], "expected": env["expected"],
                            "outcome": res["outcome"], "match": res["outcome"] == expected,
                            "detail": {k: v for k, v in res.items()
                                       if k in ("counts", "total_rows", "declared", "actual", "column_check")}})
        print(f"  {env['id']}: {res['outcome']}  (expected {expected})")
    dump(os.path.join(EVIDENCE, "registration_scenario.json"),
         {"label": "SIMULATED registration. Not MASTERDB.", "results": reg_results})

    # ---- simulated access control ----
    reqs = json.load(open(os.path.join(DATA, "fixtures", "fx_access_requests.json")))["requests"]
    acc = []
    for q in reqs:
        got = reg.authorize(q["token"], q["action"], q["dataset_id"])
        exp = q["expected"].split(" ")[0]
        acc.append({"request_id": q["id"], "action": q["action"], "expected": q["expected"],
                    "outcome": got, "match": got == exp})
        print(f"  {q['id']}: {got}  (expected {exp})")
    dump(os.path.join(EVIDENCE, "access_scenario.json"),
         {"label": "SIMULATED local access model. Not a security certification.", "results": acc})

    # ---- simulated retrieval ----
    cases = [
        ("RET-01", "tok-reader-01", "DS-AGRI-STOCK-001", "1.0.0", None),
        ("RET-02", "tok-reader-01", "DS-AGRI-STOCK-001", "1.1.0", None),
        ("RET-03", "tok-reader-01", "DS-AGRI-STOCK-001", "1.0.0", 62),
        ("RET-04", "tok-reader-01", "DS-AGRI-STOCK-001", None, None),
        ("RET-05", "tok-reader-01", "DS-AGRI-NOPE", "1.0.0", None),
        ("RET-06", None, "DS-AGRI-STOCK-001", "1.0.0", None),
    ]
    ret = []
    for cid, tok, ds, ver, exp_count in cases:
        res = reg.retrieve(tok, ds, ver, exp_count)
        ret.append({"case": cid, "dataset_version": ver, "expected_count": exp_count,
                    "outcome": res["outcome"], "returned_count": res.get("returned_count"),
                    "withheld_rejected": res.get("withheld_rejected"),
                    "warnings": res.get("warnings"),
                    "returned_status_counts": res.get("returned_status_counts"),
                    "returned_row_numbers": [r["row_number"] for r in res.get("records", [])]})
        print(f"  {cid}: {res['outcome']} returned={res.get('returned_count')}")
    dump(os.path.join(EVIDENCE, "retrieval_scenario.json"),
         {"label": "SIMULATED retrieval. Not MASTERDB.", "results": ret})

    dump(os.path.join(EVIDENCE, "simulated_insightflow_events.json"),
         {"label": "SIMULATED telemetry. Not InsightFlow.", "events": reg.events})
    dump(os.path.join(EVIDENCE, "simulated_bucket_chain.json"),
         {"label": "SIMULATED evidence chain. Not Bucket.", "entries": reg.bucket_chain})
    print("Done. See reports/ and evidence/.")


if __name__ == "__main__":
    main()
