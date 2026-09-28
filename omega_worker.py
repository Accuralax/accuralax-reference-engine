import os
import time
from pathlib import Path


def load_local_env() -> None:
    """Load local .env values without ever printing secret values."""
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or key in os.environ:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ[key] = value


load_local_env()
from src.core.canonical_worker import CanonicalOmegaWorker
from src.core.agent_scheduler import AgentScheduler
from src.core.omega_runtime_adapter import OmegaRuntimeAdapter


def main():
    interval = int(os.getenv("OMEGA_WORKER_INTERVAL_SECONDS", "30"))
    worker = CanonicalOmegaWorker(OmegaRuntimeAdapter())
    scheduler = AgentScheduler(worker, db_path=os.path.join("data", "omega_scheduler.sqlite3"), interval_seconds=interval)
    scheduler.register("ACCURALAX", "CORE", enabled=True)
    print(scheduler.start(), flush=True)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print(scheduler.stop(), flush=True)


if __name__ == "__main__":
    main()
