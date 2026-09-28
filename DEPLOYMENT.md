# Production deployment notes

## Architecture
- Frontend: Vite static build (`ui/dist`)
- API: Python HTTP service (`python -m src.api_server`), default port 8788
- Persistent runtime data: SQLite under `data/`
- Secrets: environment variables only; never commit `.env`

## Required checks
1. `python -m py_compile src/api_server.py`
2. `pytest -q`
3. `cd ui && npm ci && npm run build`
4. Start the API with `python -m src.api_server`
5. Smoke test `GET /health` after startup

## Production security
- Set `API_AUTH_MODE=api_key` or `API_AUTH_MODE=bearer`.
- Set a strong `API_API_KEY` or `API_BEARER_TOKEN`; never commit secrets.
- Set `API_CORS_ORIGIN` to the exact frontend origin; do not use `*` for authenticated production deployments.
- Keep the API bound to `127.0.0.1` behind an HTTPS reverse proxy unless direct exposure is explicitly required.
- Set `CREATIVE_API_PORT` explicitly.
- Keep `.env` outside version control.
- Back up `data/` according to the recovery policy.
- Do not expose SQLite files publicly.
- Require CI to pass before deployment.

## Local development
The default `.env.example` uses disabled authentication and localhost CORS for local-only development. Do not carry those defaults into an internet-facing deployment.
