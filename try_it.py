
import sys

sys.path.insert(0, "src")
import gv_registry_sim as R   # noqa: E402
import gv_validator as V      # noqa: E402

if len(sys.argv) < 2:
    sys.exit(__doc__)

path = sys.argv[1]
reg = R.SimulatedRegistry("data", "schemas")
columns, _ = V.read_csv(path)
schema = sys.argv[2] if len(sys.argv) > 2 else ("S2" if "net_weight_kg" in columns else "S1")

report, _ = V.validate_file(path, reg.schemas[schema], reg.sources, reg.ref_date, reg.stale_days)
print(f"File: {path}   schema used: {schema}   rows: {report['total_rows']}")
if not report["column_check"]["ok"]:
    print("FILE REJECTED (GV-13): columns do not match the schema")
    print("  missing:   ", report["column_check"]["missing"])
    print("  unexpected:", report["column_check"]["unexpected"])
    sys.exit(0)
for r in report["records"]:
    print(f"row {r['row_number']:>3}  {r['record_id']:<9} {r['status']:<10} {', '.join(r['rules']) or '-'}")
    for f in r["findings"]:
        print(f"          {f['rule']}: {f['message']}")
print("counts:", report["counts"])