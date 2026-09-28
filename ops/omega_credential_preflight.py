from __future__ import annotations

import os
import sys
from urllib.parse import urlparse


def check() -> dict[str, object]:
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    issues: list[str] = []
    if not url:
        issues.append("SUPABASE_URL_MISSING")
    else:
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc:
            issues.append("SUPABASE_URL_INVALID")
    if not key:
        issues.append("SUPABASE_SERVICE_ROLE_KEY_MISSING")
    elif len(key) < 40:
        issues.append("SUPABASE_SERVICE_ROLE_KEY_TOO_SHORT")
    return {"status": "READY" if not issues else "BLOCKED", "issues": issues}


if __name__ == "__main__":
    result = check()
    print(f"OMEGA_CREDENTIAL_PREFLIGHT={result['status']}")
    for issue in result["issues"]:
        print(f"OMEGA_CREDENTIAL_ISSUE={issue}")
    raise SystemExit(0 if result["status"] == "READY" else 3)
