#!/usr/bin/env bash
# Mutation check: inject two deliberate bugs into a SCRATCH COPY and confirm the tests fail.
# The real source tree is never modified.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
cp -r "$ROOT/src" "$ROOT/tests" "$ROOT/data" "$ROOT/schemas" "$TMP"/
mkdir -p "$TMP/evidence" "$TMP/reports"
${PY:-python3} - "$TMP/src/gv_validator.py" <<'EOF'
import sys
p = sys.argv[1]
s = open(p).read()
a = "NET_REJECT_KG = 5.0 "
b = 'if v["provenance_ref"] == "":'
assert a in s and b in s, "mutation targets not found"
s = s.replace(a, "NET_REJECT_KG = 500.0 ").replace(b, "if False:")
open(p, "w").write(s)
EOF
echo "MUTATION CHECK (scratch copy; deliberate bugs: NET_REJECT_KG 5 -> 500, GV-07 source-reference check disabled)"
${PY:-python3} "$TMP/tests/run_tests.py" 2>&1 | grep -E "^T[0-9]+ (PASS|FAIL)|passed"
rm -rf "$TMP"
