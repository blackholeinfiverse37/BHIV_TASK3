#!/usr/bin/env bash
# Clean reproduction: rebuilds data, reports and evidence, runs every step, saves the log.
# Usage:  bash reproduce.sh          (needs Python 3.9+, standard library only)
# Safety: finds a working Python FIRST and changes nothing if there is none.
#         Existing data/ is moved aside and restored if regeneration fails.
set -u
cd "$(dirname "$0")"

PY=""
for cand in python3 python "py -3"; do
  if $cand -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >/dev/null 2>&1; then
    PY="$cand"; break
  fi
done
if [ -z "$PY" ]; then
  echo "ERROR: no working Python 3.9+ found (tried: python3, python, py -3). Nothing was changed."
  echo "Windows: install Python from python.org, tick 'Add python.exe to PATH', open a NEW terminal, retry."
  exit 2
fi
export PY

LOG="$(mktemp)"
digest() { find data -type f 2>/dev/null | sort | xargs sha256sum 2>/dev/null | sha256sum | cut -d' ' -f1; }
{
echo "== clean run: $(date -u +%Y-%m-%dT%H:%M:%SZ) =="
$PY --version
uname -sr
echo "interpreter used: $PY"
BEFORE="$(digest)"
echo "== step 0: clear reports and evidence, move existing data aside"
rm -rf reports evidence data_prev
mkdir reports evidence
[ -d data ] && mv data data_prev
echo "== step 1: regenerate synthetic data"
$PY tools/generate_data.py
if [ ! -f data/warehouse_stock_v1.csv ]; then
  echo "ERROR: data generation failed. Restoring previous data and stopping."
  rm -rf data; [ -d data_prev ] && mv data_prev data
  exit 3
fi
AFTER="$(digest)"
rm -rf data_prev
echo "data digest before: $BEFORE"
echo "data digest after regeneration: $AFTER"
[ "$BEFORE" = "$AFTER" ] && echo "DATA REPRODUCED IDENTICALLY" || echo "DATA DIFFERS FROM PREVIOUS COPY (expected if the previous copy came from another OS or did not exist)"
echo "== step 2: profile, validate, simulated registration and retrieval"
$PY src/run_all.py
echo "== step 3: independent verifier"
$PY -I tests/independent_verifier.py
echo "== step 4: reconciliation"
$PY -I tests/reconcile.py; echo "reconcile exit code: $?"
echo "== step 5: automated tests"
$PY tests/run_tests.py; echo "test exit code: $?"
echo "== step 6: mutation check"
bash tools/mutation_check.sh | tee evidence/mutation_check.txt
echo "== step 7: code manifest"
$PY tools/make_manifest.py
echo "== end of clean run =="
} 2>&1 | tee "$LOG"
cp "$LOG" evidence/clean_run_log.txt 2>/dev/null
rm -f "$LOG"
