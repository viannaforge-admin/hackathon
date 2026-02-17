# Topic-Aware Baseline Builder

Builds `baseline.json` by learning sender communication behavior from the existing Graph mock API.

## Data Source

Only source used:
- `http://127.0.0.1:8000`

## Project Layout

- `app/main.py`
- `app/graph_client.py`
- `app/keyword_miner.py`
- `app/topic_classifier.py`
- `app/config/topic_keywords.json`
- `app/baseline_builder.py`
- `build_baseline.py`
- `tests/test_topic_classifier.py`
- `tests/test_graph_pagination.py`

## Topic Rules (JSON)

Topics and keywords are loaded from:
- `app/config/topic_keywords.json`

Schema:
- `normal_threshold`: integer
- `topics.<topic>.single_keywords`: string[]
- `topics.<topic>.phrases`: string[]

The classifier reloads this file automatically when it changes.

Optional override:
- Set env `TOPIC_RULES_FILE=/absolute/path/to/topic_keywords.json`

## Local Run (Without Docker)

From this folder (`baseline-service`):

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8010
```

## API

### Start build (background)

```bash
curl -X POST "http://127.0.0.1:8010/v1/baseline/build" \
  -H "Content-Type: application/json" \
  -d '{"days": 35}'
```

Immediate response:

```json
{"status":"started"}
```

### Check status

```bash
curl "http://127.0.0.1:8010/v1/baseline/status"
```

### Get one user baseline

```bash
curl "http://127.0.0.1:8010/v1/baseline/u001"
```

### Keyword review APIs

```bash
curl "http://127.0.0.1:8010/v1/keywords/topics"
curl "http://127.0.0.1:8010/v1/keywords/suggestions?topic=finance"
curl -X POST "http://127.0.0.1:8010/v1/keywords/review" -H "Content-Type: application/json" -d '{"items":[{"topic":"finance","term":"invoice aging","termType":"phrase","action":"add"}]}'
```

## CLI Build

```bash
python build_baseline.py --days 35 --base-url http://127.0.0.1:8000
```

Writes:
- `./baseline.json`
- `./keyword_stats.json` (keyword + phrase frequency counts from batched LLM extraction, when enabled)

## Optional Batched LLM Keyword Mining

During baseline build, messages can be batched and sent to LLM service for keyword/phrase extraction.

Environment variables:
- `USE_LLM_KEYWORD_MINER=true|false` (default `false`)
- `KEYWORD_MINER_URL` (default `http://127.0.0.1:8030`)
- `KEYWORD_MINER_BATCH_SIZE` (default `200`)
- `KEYWORD_MINER_TIMEOUT_SECONDS` (default `3.0`)
- `KEYWORD_MINER_MAX_RETRIES` (default `3`)

Each extraction response increments cumulative counts in `keyword_stats.json`.

`keyword_stats.json` stores per-topic terms as:

- `occurrences` (int)
- `ignored` (bool)
- `reasonForIgnore` (`0` not ignored, `1` added, `2` ignored)

Any item with `ignored=true` is excluded from suggestions API and frontend table.

## Tests

```bash
pytest -q
```

## Run With Docker Compose

From workspace root (parent directory):

```bash
docker compose up --build
```

Services:
- Graph mock: `http://127.0.0.1:8000`
- Baseline service: `http://127.0.0.1:8010`

With volume mount enabled in compose, generated baseline is available on host at:
- `baseline-service/baseline.json`
