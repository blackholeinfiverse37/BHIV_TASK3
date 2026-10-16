"""Automated tests. Each test states EXPECTED (hard-coded literal) and records ACTUAL.

Run:  python3 tests/run_tests.py
Writes evidence/test_results.json. Exit code 1 if any test fails.
Expected values are literals taken from the planted-defect design, not computed by the code under test.
"""
import json
import os
import sys
import traceback
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, HERE)

import gv_registry_sim as R      # noqa: E402
import gv_validator as V         # noqa: E402
import independent_verifier as IV  # noqa: E402

DATA = os.path.join(ROOT, "data")
FX = os.path.join(DATA, "fixtures")
SCHEMAS = os.path.join(ROOT, "schemas")

TESTS = []


def test(tid, title, mandatory=None):
    def deco(fn):
        TESTS.append((tid, title, mandatory, fn))
        return fn
    return deco


def registry():
    return R.SimulatedRegistry(DATA, SCHEMAS)


def run_fixture(name, schema="S1"):
    reg = registry()
    report, _ = V.validate_file(os.path.join(FX, name), reg.schemas[schema], reg.sources,
                                reg.ref_date, reg.stale_days)
    return report


def statuses(report):
    return [r["status"] for r in report["records"]]


def rules_of(report):
    return [r["rules"] for r in report["records"]]


def env(env_id):
    for e in json.load(open(os.path.join(FX, "fx_envelopes.json")))["envelopes"]:
        if e["id"] == env_id:
            return dict(e)
    raise KeyError(env_id)


A, W, U, X = "ACCEPTED", "WARNING", "UNRESOLVED", "REJECTED"
WRITER, READER = "tok-writer-01", "tok-reader-01"


@test("T01", "Valid input", 1)
def t01():
    rep = run_fixture("fx_GV-01.csv")
    return ([A], [statuses(rep)[0]]), None  # control row only


@test("T02", "Missing required field", 2)
def t02():
    rep = run_fixture("fx_GV-01.csv")
    return ({"s": [A, X, X], "r": [[], ["GV-01"], ["GV-01"]]},
            {"s": statuses(rep), "r": rules_of(rep)}), None


@test("T03", "Invalid field type or value", 3)
def t03():
    a, b = run_fixture("fx_GV-02.csv"), run_fixture("fx_GV-03.csv")
    exp = {"type": ([A, X], [[], ["GV-02"]]),
           "value": ([A, X, X, X], [[], ["GV-03"], ["GV-03"], ["GV-03"]])}
    act = {"type": (statuses(a), rules_of(a)), "value": (statuses(b), rules_of(b))}
    return (json.loads(json.dumps(exp)), json.loads(json.dumps(act))), None


@test("T04", "Duplicate record", 4)
def t04():
    dup = run_fixture("fx_GV-05.csv")          # control, original, later copy
    key = run_fixture("fx_GV-06.csv")          # control, two rows with same natural key
    exp = {"dup_status": [A, A, X], "dup_rules": [[], [], ["GV-05"]],
           "key_status": [A, U, U], "key_rules": [[], ["GV-06"], ["GV-06"]]}
    act = {"dup_status": statuses(dup), "dup_rules": rules_of(dup),
           "key_status": statuses(key), "key_rules": rules_of(key)}
    return (exp, act), None


@test("T05", "Missing provenance", 5)
def t05():
    rep = run_fixture("fx_GV-07.csv")
    return ({"s": [A, X, X], "r": [[], ["GV-07"], ["GV-07"]]},
            {"s": statuses(rep), "r": rules_of(rep)}), None


@test("T06", "Stale or unconfirmed freshness", 6)
def t06():
    stale, unconf = run_fixture("fx_GV-09.csv"), run_fixture("fx_GV-10.csv")
    exp = {"stale": [A, W, W, W, W], "unconfirmed": [A, U, U]}
    act = {"stale": statuses(stale), "unconfirmed": statuses(unconf)}
    return (exp, act), None


@test("T07", "Unknown dataset identity", 7)
def t07():
    reg = registry()
    out = {"register": reg.register(WRITER, env("ENV-03"))["outcome"],
           "retrieve": reg.retrieve(READER, "DS-AGRI-NOPE", "1.0.0")["outcome"]}
    return ({"register": "REJECT_UNKNOWN_DATASET_ID", "retrieve": "REJECT_UNKNOWN_DATASET_ID"}, out), None


@test("T08", "Missing or incompatible version", 8)
def t08():
    reg = registry()
    incompat = env("ENV-01")
    incompat["schema_version"] = "S2"             # 1.0.0 is bound to S1 in the catalog
    out = {"missing_version": reg.register(WRITER, env("ENV-04"))["outcome"],
           "unknown_version": reg.register(WRITER, env("ENV-05"))["outcome"],
           "unknown_schema": reg.register(WRITER, env("ENV-06"))["outcome"],
           "schema_not_bound_to_version": reg.register(WRITER, incompat)["outcome"],
           "retrieve_without_version": reg.retrieve(READER, "DS-AGRI-STOCK-001", None)["outcome"]}
    exp = {"missing_version": "REJECT_MISSING_VERSION", "unknown_version": "REJECT_UNKNOWN_DATASET_VERSION",
           "unknown_schema": "REJECT_UNKNOWN_SCHEMA_VERSION",
           "schema_not_bound_to_version": "REJECT_SCHEMA_VERSION_INCOMPATIBLE",
           "retrieve_without_version": "REJECT_MISSING_VERSION"}
    return (exp, out), None


@test("T09", "Schema compatibility or breaking change", 9)
def t09():
    reg = registry()
    s1, s2 = set(reg.schemas["S1"]["columns"]), set(reg.schemas["S2"]["columns"])
    out = {"mismatch_s1_as_s2": reg.register(WRITER, env("ENV-07"))["outcome"],
           "mismatch_s2_as_s1": reg.register(WRITER, env("ENV-08"))["outcome"],
           "removed_in_s2": sorted(s1 - s2), "added_in_s2": sorted(s2 - s1),
           "clean_s1_ok": reg.register(WRITER, env("ENV-01"))["outcome"],
           "clean_s2_ok": reg.register(WRITER, env("ENV-02"))["outcome"]}
    exp = {"mismatch_s1_as_s2": "REJECT_SCHEMA_MISMATCH", "mismatch_s2_as_s1": "REJECT_SCHEMA_MISMATCH",
           "removed_in_s2": sorted(["last_verified_date", "moisture_pct", "net_kg", "received_date",
                                    "source_ref", "unit"]),
           "added_in_s2": sorted(["last_verified_at", "moisture_percent", "net_weight_kg", "provenance_ref",
                                  "quality_grade", "received_at"]),
           "clean_s1_ok": "REGISTER_OK_WITH_WARNINGS", "clean_s2_ok": "REGISTER_OK_WITH_WARNINGS"}
    return (exp, out), None


@test("T10", "Unauthorized retrieval", 10)
def t10():
    reg = registry()
    reg.register(WRITER, env("ENV-01"))
    ds = "DS-AGRI-STOCK-001"
    out = {"no_token": reg.retrieve(None, ds, "1.0.0")["outcome"],
           "unknown_token": reg.retrieve("tok-unknown-77", ds, "1.0.0")["outcome"],
           "reader_without_grant": reg.retrieve("tok-reader-02", ds, "1.0.0")["outcome"],
           "reader_cannot_register": reg.register(READER, env("ENV-01"))["outcome"],
           "authorised_reader": reg.retrieve(READER, ds, "1.0.0")["outcome"]}
    exp = {"no_token": "DENY_UNAUTHENTICATED", "unknown_token": "DENY_UNKNOWN_PRINCIPAL",
           "reader_without_grant": "DENY_DATASET_NOT_GRANTED",
           "reader_cannot_register": "DENY_ROLE_NOT_PERMITTED", "authorised_reader": "OK_WITH_WARNINGS"}
    return (exp, out), None


@test("T11", "Partial retrieval and records carrying warnings", 11)
def t11():
    reg = registry()
    reg.register(WRITER, env("ENV-01"))
    reg.register(WRITER, env("ENV-02"))
    r1 = reg.retrieve(READER, "DS-AGRI-STOCK-001", "1.0.0")
    r2 = reg.retrieve(READER, "DS-AGRI-STOCK-001", "1.1.0")
    out = {"v1": [r1["outcome"], r1["returned_count"], r1["withheld_rejected"],
                  r1["returned_status_counts"], sorted(r1["warnings"])],
           "v2": [r2["outcome"], r2["returned_count"], r2["withheld_rejected"],
                  r2["returned_status_counts"], sorted(r2["warnings"])]}
    exp = {"v1": ["OK_WITH_WARNINGS", 50, 12, {"ACCEPTED": 34, "WARNING": 10, "UNRESOLVED": 6},
                  sorted(["PARTIAL_RETRIEVAL_REJECTED_WITHHELD", "RECORDS_WITH_WARNINGS",
                          "UNRESOLVED_RECORDS_INCLUDED", "STALE_RECORDS_PRESENT",
                          "FRESHNESS_UNCONFIRMED_PRESENT"])],
           "v2": ["OK_WITH_WARNINGS", 21, 3, {"ACCEPTED": 19, "WARNING": 1, "UNRESOLVED": 1},
                  sorted(["PARTIAL_RETRIEVAL_REJECTED_WITHHELD", "RECORDS_WITH_WARNINGS",
                          "UNRESOLVED_RECORDS_INCLUDED", "STALE_RECORDS_PRESENT"])]}
    return (exp, out), None


@test("T12", "Incorrect registration or retrieval count", 12)
def t12():
    reg = registry()
    off_by_one = env("ENV-01")
    off_by_one["declared_record_count"] = 61
    all_invalid = env("ENV-01")
    all_invalid.update(file="fixtures/fx_all_invalid_s1.csv", declared_record_count=3)
    out = {"declared_60_actual_62": reg.register(WRITER, env("ENV-09"))["outcome"],
           "declared_61_actual_62": reg.register(WRITER, off_by_one)["outcome"],
           "all_rows_invalid": reg.register(WRITER, all_invalid)["outcome"]}
    reg.register(WRITER, env("ENV-01"))
    out["retrieve_expecting_62"] = reg.retrieve(READER, "DS-AGRI-STOCK-001", "1.0.0", 62)["outcome"]
    out["retrieve_expecting_50"] = reg.retrieve(READER, "DS-AGRI-STOCK-001", "1.0.0", 50)["outcome"]
    exp = {"declared_60_actual_62": "REJECT_COUNT_MISMATCH", "declared_61_actual_62": "REJECT_COUNT_MISMATCH",
           "all_rows_invalid": "REJECT_NO_VALID_RECORDS", "retrieve_expecting_62": "FAIL_COUNT_MISMATCH",
           "retrieve_expecting_50": "OK_WITH_WARNINGS"}
    return (exp, out), None


@test("T13", "Every row rule has a fixture that triggers it (coverage)")
def t13():
    cover = {"fx_GV-01.csv": "GV-01", "fx_GV-02.csv": "GV-02", "fx_GV-03.csv": "GV-03",
             "fx_GV-04-large.csv": "GV-04", "fx_GV-04-small.csv": "GV-04", "fx_GV-05.csv": "GV-05",
             "fx_GV-06.csv": "GV-06", "fx_GV-07.csv": "GV-07", "fx_GV-08-unknown.csv": "GV-08",
             "fx_GV-08-deprecated.csv": "GV-08", "fx_GV-09.csv": "GV-09", "fx_GV-10.csv": "GV-10",
             "fx_GV-11-future.csv": "GV-11", "fx_GV-11-order.csv": "GV-11", "fx_GV-12.csv": "GV-12"}
    out = {}
    for fname, rule in cover.items():
        rep = run_fixture(fname)
        out[fname] = rule in {x for r in rep["records"][1:] for x in r["rules"]} \
            and not rep["records"][0]["rules"]          # planted rows hit the rule, control row is clean
    return ({k: True for k in cover}, out), None


@test("T14", "Application results equal the independent second implementation")
def t14():
    reg = registry()
    diffs = {}
    for tag, fname, schema in (("v1", "warehouse_stock_v1.csv", "S1"), ("v2", "warehouse_stock_v2.csv", "S2")):
        rep, _ = V.validate_file(os.path.join(DATA, fname), reg.schemas[schema], reg.sources,
                                 reg.ref_date, reg.stale_days)
        ind = IV.classify_file(os.path.join(DATA, fname), schema)
        diffs[tag] = [a["row_number"] for a, b in zip(rep["records"], ind)
                      if (a["status"], a["rules"]) != (b["status"], b["rules"])]
        diffs[tag + "_rows"] = [len(rep["records"]), len(ind)]
    return ({"v1": [], "v1_rows": [62, 62], "v2": [], "v2_rows": [24, 24]}, diffs), None


@test("T15", "Provenance preserved: every retrieved record carries its source reference")
def t15():
    reg = registry()
    reg.register(WRITER, env("ENV-01"))
    res = reg.retrieve(READER, "DS-AGRI-STOCK-001", "1.0.0")
    missing = [r["row_number"] for r in res["records"]
               if not (r["provenance"]["source_system"] and r["provenance"]["source_ref"])]
    return ({"records_without_provenance": []}, {"records_without_provenance": missing}), None


@test("T16", "Determinism: two runs give identical output")
def t16():
    reg = registry()
    outs = []
    for _ in range(2):
        rep, _ = V.validate_file(os.path.join(DATA, "warehouse_stock_v1.csv"), reg.schemas["S1"],
                                 reg.sources, reg.ref_date, reg.stale_days)
        outs.append(json.dumps(rep, sort_keys=True))
    return ({"identical": True}, {"identical": outs[0] == outs[1]}), None


def main():
    results, failed = [], 0
    print(f"Running {len(TESTS)} tests  (python {sys.version.split()[0]})")
    for tid, title, mandatory, fn in TESTS:
        try:
            (exp, act), _ = fn()
            ok = exp == act
            err = None
        except Exception:                                # a crash is a FAIL, never a silent pass
            exp, act, ok, err = None, None, False, traceback.format_exc()
        failed += 0 if ok else 1
        results.append({"id": tid, "title": title, "mandatory_item": mandatory,
                        "expected": exp, "actual": act, "result": "PASS" if ok else "FAIL", "error": err})
        print(f"{tid} {'PASS' if ok else 'FAIL'}  {title}")
        if not ok:
            print("   expected:", json.dumps(exp))
            print("   actual:  ", json.dumps(act))
            if err:
                print(err)
    os.makedirs(os.path.join(ROOT, "evidence"), exist_ok=True)
    with open(os.path.join(ROOT, "evidence", "test_results.json"), "w") as fh:
        json.dump({"total": len(results), "passed": len(results) - failed, "failed": failed,
                   "tests": results}, fh, indent=2)
        fh.write("\n")
    print(f"\n{len(results) - failed}/{len(results)} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
