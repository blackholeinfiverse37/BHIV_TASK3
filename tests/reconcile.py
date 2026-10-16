"""Reconcile three sources: application results, independent verifier, planted expected files.

Usage (after src/run_all.py and tests/independent_verifier.py):  python3 -I tests/reconcile.py
Exit code 0 only if everything matches. Writes reports/reconciliation.md and .json.
"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
R = os.path.join(ROOT, "reports")
E = os.path.join(ROOT, "evidence")
D = os.path.join(ROOT, "data")


def jload(p):
    with open(p) as fh:
        return json.load(fh)


def expected_rows(tag):
    with open(os.path.join(D, f"expected_outcomes_{tag}.csv"), newline="") as fh:
        return [(int(r["row_number"]), r["record_id"], r["expected_status"],
                 sorted(x for x in r["expected_rules"].split("|") if x)) for r in csv.DictReader(fh)]


def main():
    lines = ["# Reconciliation", "",
             "Three views of the same data: (A) application output, (B) independent verifier, "
             "(C) planted expected outcomes from the generator.", ""]
    summary = {"checks": [], "all_match": True}

    def check(name, ok, detail=""):
        summary["checks"].append({"check": name, "ok": ok, "detail": detail})
        summary["all_match"] &= ok
        lines.append(f"- {'MATCH' if ok else 'MISMATCH'}: {name}" + (f" ({detail})" if detail else ""))

    for tag in ("v1", "v2"):
        app = jload(os.path.join(R, f"validation_results_{tag}.json"))
        ind = jload(os.path.join(R, f"independent_results_{tag}.json"))
        exp = expected_rows(tag)
        lines += ["", f"## {tag}", ""]
        check(f"{tag} row totals A=B=C", app["total_rows"] == ind["total_rows"] == len(exp),
              f"A={app['total_rows']} B={ind['total_rows']} C={len(exp)}")
        check(f"{tag} status counts A=B", app["counts"] == ind["counts"],
              f"A={app['counts']} B={ind['counts']}")
        c_counts = {s: sum(1 for e in exp if e[2] == s) for s in app["counts"]}
        check(f"{tag} status counts A=C", app["counts"] == c_counts, f"C={c_counts}")
        bad = []
        for a, b, c in zip(app["records"], ind["records"], exp):
            if not (a["row_number"] == b["row_number"] == c[0]
                    and a["record_id"] == b["record_id"] == c[1]
                    and a["status"] == b["status"] == c[2]
                    and a["rules"] == b["rules"] == c[3]):
                bad.append(a["row_number"])
        check(f"{tag} per-row status and rule set A=B=C", not bad,
              "all rows agree" if not bad else f"differing rows: {bad}")
        exc = jload(os.path.join(R, f"exceptions_{tag}.json"))
        check(f"{tag} exception count = rows not ACCEPTED",
              exc["exception_count"] == app["total_rows"] - app["counts"]["ACCEPTED"],
              f"exceptions={exc['exception_count']}")

    # retrieval identities vs independent view
    ret = {r["case"]: r for r in jload(os.path.join(E, "retrieval_scenario.json"))["results"]}
    lines += ["", "## retrieval", ""]
    for case, tag in (("RET-01", "v1"), ("RET-02", "v2")):
        ind = jload(os.path.join(R, f"independent_results_{tag}.json"))
        want = [r["row_number"] for r in ind["records"] if r["status"] != "REJECTED"]
        got = ret[case]["returned_row_numbers"]
        check(f"{case} retrieved row identities = independent non-rejected rows", want == got,
              f"{len(got)} rows")
        rej = sum(1 for r in ind["records"] if r["status"] == "REJECTED")
        check(f"{case} withheld count = independent rejected count", ret[case]["withheld_rejected"] == rej,
              f"withheld={ret[case]['withheld_rejected']}")

    lines += ["", f"**Overall: {'ALL CHECKS MATCH' if summary['all_match'] else 'MISMATCH FOUND'}**", ""]
    with open(os.path.join(R, "reconciliation.md"), "w") as fh:
        fh.write("\n".join(lines))
    with open(os.path.join(R, "reconciliation.json"), "w") as fh:
        json.dump(summary, fh, indent=2)
        fh.write("\n")
    print("\n".join(lines))
    return 0 if summary["all_match"] else 1


if __name__ == "__main__":
    sys.exit(main())
