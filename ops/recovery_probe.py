from __future__ import annotations
import json
import time
from api_watchdog import healthy, start_server

URL="http://127.0.0.1:8789/health"

def main():
    if healthy(URL):
        print("PROBE_ABORT=PORT_ALREADY_HEALTHY")
        return 2
    child=start_server(8789)
    try:
        deadline=time.monotonic()+8
        while time.monotonic()<deadline:
            if healthy(URL):
                print(json.dumps({"probe":"recovered","child_pid":child.pid},sort_keys=True))
                return 0
            if child.poll() is not None:
                print(json.dumps({"probe":"child_exited","child_pid":child.pid,"returncode":child.returncode},sort_keys=True))
                return 1
            time.sleep(.5)
        print(json.dumps({"probe":"startup_timeout","child_pid":child.pid},sort_keys=True))
        return 1
    finally:
        if child.poll() is None:
            child.terminate()
            child.wait(timeout=5)

if __name__=="__main__": raise SystemExit(main())
