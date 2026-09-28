from pathlib import Path
import subprocess, sys, json, time, os

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "apex_parallel"
DATA.mkdir(parents=True, exist_ok=True)
files = sorted((ROOT / "tests").glob("test_*.py"))
batch_size = 5
manifest = []
for i in range(0, len(files), batch_size):
    batch = files[i:i+batch_size]
    batch_no = i // batch_size + 1
    out = DATA / f"apex19_batch_{batch_no:02d}.out"
    err = DATA / f"apex19_batch_{batch_no:02d}.err"
    cmd = [sys.executable, "-m", "pytest", *[str(x) for x in batch], "-q", "--tb=short", "--maxfail=1", "--basetemp", str(ROOT / ".apex_tmp" / f"apex19_batch_{batch_no:02d}")]
    started = time.time()
    env = os.environ.copy()
    env["HUBSPOT_ACCESS_TOKEN"] = ""
    env["MAKE_API_TOKEN"] = ""
    env["MAKE_WEBHOOK_URL"] = ""
    try:
        with out.open("w", encoding="utf-8") as fo, err.open("w", encoding="utf-8") as fe:
            p = subprocess.run(cmd, cwd=ROOT, stdout=fo, stderr=fe, timeout=60, env=env)
        rc = p.returncode
    except subprocess.TimeoutExpired:
        rc = 124
        err.write_text("BATCH_TIMEOUT\n", encoding="utf-8")
    except KeyboardInterrupt:
        rc = 130
        err.write_text("RUNNER_INTERRUPTED\n", encoding="utf-8")
        raise
    manifest.append({"batch": batch_no, "files": [str(x.relative_to(ROOT)) for x in batch], "returncode": rc, "seconds": round(time.time()-started,2), "out": str(out), "err": str(err)})
    (DATA / "apex19_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"BATCH {batch_no}: rc={rc} seconds={manifest[-1]['seconds']}")
    if rc != 0:
        break
print(f"COMPLETED_BATCHES={len(manifest)} TOTAL_FILES={len(files)}")
