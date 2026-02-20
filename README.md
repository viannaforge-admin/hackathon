# Teams Mock + Baseline + Misdelivery

This workspace contains five services:

- `keyword-db`: Postgres store for keyword/phrase suggestions on port `5432`
- `graph-mock`: Microsoft Graph (Teams) mock server on port `8000`
- `baseline-service`: topic-aware behavioral baseline builder on port `8010`
- `misdelivery-service`: pre-send misdelivery risk checker on port `8020`
- `llm-explainer-service`: optional explanation generator on port `8030`
- `keyword-review-frontend`: basic UI for topic keyword review on port `8040`

## Services

- Graph mock base URL: `http://127.0.0.1:8000`
- Keyword DB: `postgresql://postgres:postgres@127.0.0.1:5432/keywords`
- Baseline service base URL: `http://127.0.0.1:8010`
- Misdelivery service base URL: `http://127.0.0.1:8020`
- LLM explainer service base URL: `http://127.0.0.1:8030`
- Keyword review frontend URL: `http://127.0.0.1:8040`

## Quick Start (Docker Compose)

From this directory (workspace root):

```bash
docker compose up --build
```

## New Machine Setup

1. Install Docker Desktop or Rancher Desktop (with Docker Compose support).
2. Clone/copy this repository to a local folder.
3. Create env file:

```bash
cp .env.example .env
```

4. Edit `.env`:
- Set `OPENAI_API_KEY` if you want LLM explanations or keyword mining.
- Set `USE_LLM_EXPLAINER=true` to enable WARN/BLOCK explanation generation.
- Set `USE_LLM_KEYWORD_MINER=true` to enable batch keyword extraction during baseline build.

5. Start all services:

```bash
docker compose up --build -d
```

Run in background:

```bash
docker compose up --build -d
```

Stop:

```bash
docker compose down
```

## Build Baseline

Start baseline build (non-blocking):

```bash
curl -X POST "http://127.0.0.1:8010/v1/baseline/build" \
  -H "Content-Type: application/json" \
  -d '{"days": 35}'
```

Check progress:

```bash
curl "http://127.0.0.1:8010/v1/baseline/status"
```

Fetch one user baseline:

```bash
curl "http://127.0.0.1:8010/v1/baseline/u001"
```

With host volume mount, baseline file is written to:

- `baseline-service/baseline.json`
- `baseline-service/keyword_stats.json` (if `USE_LLM_KEYWORD_MINER=true`)

Open review UI:

- `http://127.0.0.1:8040`

## Folder Layout

- `graph-mock/` Graph Teams mock API
- `baseline-service/` Baseline builder API + CLI
- `misdelivery-service/` Misdelivery detection API
- `llm-explainer-service/` Optional GenAI explanation API
- `keyword-review-frontend/` UI to review/add/ignore extracted terms
- `docker-compose.yml` Runs all services together
