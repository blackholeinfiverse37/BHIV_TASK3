"""SIMULATED local registry for registration and retrieval.

This is NOT MASTERDB and NOT an official API contract. It only models, in memory, the
behaviour the assessment asks to demonstrate: governed registration with versions,
controlled retrieval, and quality status. TANTRA, Bucket and InsightFlow are modelled
only as labelled stubs (an authorization check, a hash chain, an event list).
"""
import hashlib
import json
import os

import gv_validator as V

SIM_LABEL = "SIMULATED"


def _load(path):
    with open(path) as fh:
        return json.load(fh)


def _hash(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


class SimulatedRegistry:
    LABEL = "SIMULATED local registry. Not MASTERDB, not an official contract."

    def __init__(self, data_dir, schema_dir):
        self.data_dir = data_dir
        self.catalog = _load(os.path.join(data_dir, "dataset_catalog.json"))
        self.policy = _load(os.path.join(data_dir, "access_policy.json"))
        reg = _load(os.path.join(data_dir, "source_registry.json"))
        self.sources = {s["source_system"]: s["status"] for s in reg["sources"]}
        self.schemas = {}
        for name in ("S1", "S2"):
            self.schemas[name] = _load(os.path.join(schema_dir, f"schema_{name}.json"))
        from datetime import date
        self.ref_date = date.fromisoformat(self.catalog["reference_date"])
        self.stale_days = self.catalog["stale_after_days"]
        self.store = {}              # (dataset_id, version) -> registered content
        self.events = []             # SIMULATED InsightFlow telemetry
        self.bucket_chain = []       # SIMULATED Bucket evidence chain

    # ---------- simulated side components ----------
    def _emit(self, kind, **details):
        self.events.append({"seq": len(self.events) + 1, "simulated": True,
                            "component": "InsightFlow(sim)", "type": kind, **details})

    def _bucket(self, kind, payload):
        prev = self.bucket_chain[-1]["entry_hash"] if self.bucket_chain else "0" * 64
        digest = _hash(payload)
        entry = {"seq": len(self.bucket_chain) + 1, "simulated": True, "component": "Bucket(sim)",
                 "type": kind, "payload_sha256": digest, "prev_hash": prev}
        entry["entry_hash"] = _hash({"prev": prev, "payload": digest, "type": kind})
        self.bucket_chain.append(entry)

    # ---------- access control (stand-in for TANTRA authorization) ----------
    def authorize(self, token, action, dataset_id):
        """Return 'ALLOW' or a DENY_/REJECT_ code. Order: principal, role, dataset exists, grant."""
        if not token:
            return "DENY_UNAUTHENTICATED"
        principal = self.policy["principals"].get(token)
        if principal is None:
            return "DENY_UNKNOWN_PRINCIPAL"
        if action not in self.policy["permissions"].get(principal["role"], []):
            return "DENY_ROLE_NOT_PERMITTED"
        if dataset_id != self.catalog["dataset_id"]:
            return "REJECT_UNKNOWN_DATASET_ID"
        if dataset_id not in principal["datasets"]:
            return "DENY_DATASET_NOT_GRANTED"
        return "ALLOW"

    def _version_entry(self, version):
        for v in self.catalog["versions"]:
            if v["dataset_version"] == version:
                return v
        return None

    # ---------- registration ----------
    def register(self, token, envelope):
        env_id = envelope.get("id")
        base = {"simulated": True, "envelope_id": env_id, "action": "register"}

        def fail(code, **extra):
            self._emit("register_failed", envelope_id=env_id, outcome=code)
            return {**base, "outcome": code, **extra}

        decision = self.authorize(token, "register", envelope.get("dataset_id"))
        if decision != "ALLOW":
            return fail(decision)
        version = envelope.get("dataset_version")
        if not version:
            return fail("REJECT_MISSING_VERSION")
        entry = self._version_entry(version)
        if entry is None:
            return fail("REJECT_UNKNOWN_DATASET_VERSION", dataset_version=version)
        schema_name = envelope.get("schema_version")
        if schema_name not in self.schemas:
            return fail("REJECT_UNKNOWN_SCHEMA_VERSION", schema_version=schema_name)
        if schema_name != entry["schema_version"]:
            return fail("REJECT_SCHEMA_VERSION_INCOMPATIBLE", declared=schema_name,
                        catalog_schema=entry["schema_version"])
        path = os.path.join(self.data_dir, envelope["file"])
        report, rows = V.validate_file(path, self.schemas[schema_name], self.sources,
                                       self.ref_date, self.stale_days)
        if not report["column_check"]["ok"]:
            return fail("REJECT_SCHEMA_MISMATCH", column_check=report["column_check"])
        declared = envelope.get("declared_record_count")
        if declared != report["total_rows"]:
            return fail("REJECT_COUNT_MISMATCH", declared=declared, actual=report["total_rows"])
        counts = report["counts"]
        if counts["ACCEPTED"] + counts["WARNING"] + counts["UNRESOLVED"] == 0:
            return fail("REJECT_NO_VALID_RECORDS", counts=counts)

        key = (envelope["dataset_id"], version)
        self.store[key] = {"schema_version": schema_name, "records": report["records"],
                           "rows": rows, "counts": counts, "total_rows": report["total_rows"]}
        outcome = "REGISTER_OK" if counts["WARNING"] + counts["UNRESOLVED"] + counts["REJECTED"] == 0 \
            else "REGISTER_OK_WITH_WARNINGS"
        self._emit("registered", envelope_id=env_id, dataset_version=version, outcome=outcome)
        self._bucket("registration", {"dataset_id": envelope["dataset_id"], "version": version,
                                      "schema": schema_name, "counts": counts,
                                      "result_digest": _hash(report["records"])})
        return {**base, "outcome": outcome, "dataset_id": envelope["dataset_id"],
                "dataset_version": version, "schema_version": schema_name,
                "total_rows": report["total_rows"], "counts": counts}

    # ---------- retrieval ----------
    def retrieve(self, token, dataset_id, dataset_version=None, expected_count=None):
        base = {"simulated": True, "action": "retrieve", "dataset_id": dataset_id,
                "dataset_version": dataset_version}

        def fail(code, **extra):
            self._emit("retrieve_failed", outcome=code)
            return {**base, "outcome": code, **extra}

        decision = self.authorize(token, "retrieve", dataset_id)
        if decision != "ALLOW":
            return fail(decision)
        if not dataset_version:
            return fail("REJECT_MISSING_VERSION")           # no implicit "latest"
        if self._version_entry(dataset_version) is None:
            return fail("REJECT_UNKNOWN_DATASET_VERSION")
        stored = self.store.get((dataset_id, dataset_version))
        if stored is None:
            return fail("REJECT_NOT_REGISTERED")

        returned, withheld = [], 0
        for rec, raw in zip(stored["records"], stored["rows"]):
            if rec["status"] == "REJECTED":
                withheld += 1
                continue
            returned.append({"row_number": rec["row_number"], "record_id": rec["record_id"],
                             "status": rec["status"], "rules": rec["rules"],
                             "provenance": rec["provenance"], "freshness": rec["freshness"],
                             "data": raw})
        warnings = []
        if withheld:
            warnings.append("PARTIAL_RETRIEVAL_REJECTED_WITHHELD")
        if any(r["status"] == "WARNING" for r in returned):
            warnings.append("RECORDS_WITH_WARNINGS")
        if any(r["status"] == "UNRESOLVED" for r in returned):
            warnings.append("UNRESOLVED_RECORDS_INCLUDED")
        if any(r["freshness"]["stale"] for r in returned):
            warnings.append("STALE_RECORDS_PRESENT")
        if any(r["freshness"]["unconfirmed"] for r in returned):
            warnings.append("FRESHNESS_UNCONFIRMED_PRESENT")

        outcome = "OK_WITH_WARNINGS" if warnings else "OK"
        if expected_count is not None and expected_count != len(returned):
            outcome = "FAIL_COUNT_MISMATCH"
            warnings.append("EXPECTED_COUNT_DIFFERS")
        self._emit("retrieved", dataset_version=dataset_version, outcome=outcome,
                   returned=len(returned))
        self._bucket("retrieval", {"dataset_id": dataset_id, "version": dataset_version,
                                   "returned": [r["row_number"] for r in returned],
                                   "outcome": outcome})
        return {**base, "outcome": outcome, "schema_version": stored["schema_version"],
                "registered_total_rows": stored["total_rows"],
                "returned_count": len(returned), "withheld_rejected": withheld,
                "expected_count": expected_count, "warnings": warnings,
                "returned_status_counts": {s: sum(1 for r in returned if r["status"] == s)
                                           for s in ("ACCEPTED", "WARNING", "UNRESOLVED")},
                "records": returned}
