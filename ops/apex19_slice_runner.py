from pathlib import Path
import json, os, re, subprocess, sys, time
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/"data"/"apex_parallel"; DATA.mkdir(parents=True,exist_ok=True)
files=sorted((ROOT/"tests").glob("test_*.py")); batch_size=5
start_batch=int(sys.argv[1]) if len(sys.argv)>1 else 1
end_batch=int(sys.argv[2]) if len(sys.argv)>2 else (len(files)+batch_size-1)//batch_size
manifest_path=DATA/"apex19_resilient_manifest.json"; manifest=json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else []
done={int(x["batch"]) for x in manifest if x.get("status")=="passed"}
for batch_no in range(start_batch,end_batch+1):
    if batch_no in done: continue
    i=(batch_no-1)*batch_size; batch=files[i:i+batch_size]
    out=DATA/f"apex19_resilient_{batch_no:03d}.out"; err=DATA/f"apex19_resilient_{batch_no:03d}.err"
    cmd=[sys.executable,"-m","pytest",*[str(x) for x in batch],"-q","--tb=short","--maxfail=1","--basetemp",str(ROOT/".apex_tmp"/f"apex19_resilient_{batch_no:03d}")]
    env=os.environ.copy()
    for k in ("HUBSPOT_ACCESS_TOKEN","MAKE_API_TOKEN","MAKE_WEBHOOK_URL"): env[k]=""
    start=time.time()
    with out.open("w",encoding="utf-8") as fo, err.open("w",encoding="utf-8") as fe:
        p=subprocess.Popen(cmd,cwd=ROOT,stdout=fo,stderr=fe,env=env); deadline=time.time()+45; summary=None
        while time.time()<deadline:
            time.sleep(.5); txt=out.read_text(encoding="utf-8",errors="replace")
            m=re.findall(r"(\d+) passed(?:, (\d+) failed)?(?:, (\d+) skipped)?(?:, \d+ warning[s]?)? in ([0-9.]+)s",txt)
            if m: summary=m[-1]; break
            if p.poll() is not None: break
        if summary and p.poll() is None:
            p.terminate()
            try: p.wait(timeout=2)
            except subprocess.TimeoutExpired: p.kill()
        elif p.poll() is None: p.kill(); p.wait()
    txt=out.read_text(encoding="utf-8",errors="replace"); m=re.findall(r"(\d+) passed(?:, (\d+) failed)?(?:, (\d+) skipped)?(?:, \d+ warning[s]?)? in ([0-9.]+)s",txt); summary=m[-1] if m else None
    status="passed" if summary and not (summary[1] or summary[2]) else "failed"
    row={"batch":batch_no,"files":[str(x.relative_to(ROOT)) for x in batch],"status":status,"tests_passed":int(summary[0]) if summary else 0,"tests_failed":int(summary[1] or 0) if summary else 0,"tests_skipped":int(summary[2] or 0) if summary else 0,"finalization_interrupted":bool(summary and p.returncode not in (0,None)),"seconds":round(time.time()-start,2),"out":str(out),"err":str(err)}
    manifest.append(row); manifest_path.write_text(json.dumps(manifest,indent=2),encoding="utf-8"); print(json.dumps(row),flush=True)
    if status!="passed": break
