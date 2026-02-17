# Microsoft Graph Teams Mock Server

Deterministic local FastAPI mock for a subset of Microsoft Graph Teams APIs.

## Features

- No auth required
- Graph-like endpoints:
  - `GET /v1.0/users`
  - `GET /v1.0/users/{userId}/chats`
  - `GET /v1.0/chats/{chatId}/messages`
- Graph-like list wrapper: `{ "value": [...] }`
- Pagination: `$top` (default `50`) and `$skip` (default `0`)
- `@odata.nextLink` when more records exist
- Message filtering support:
  - `$filter=lastModifiedDateTime ge <ISO8601>`
- Graph-like error shape for 400/404
- Deterministic dataset with fixed `NOW = 2026-02-15T00:00:00Z`

## Dataset Overview

- Window: `NOW-35d .. NOW`
- Users: 18 total
  - 12 internal (`company.com`)
  - 6 guest/external (`vendor.com`, `partner.org`, `gmail.com`)
- Chats: 28 total
  - 14 one-on-one
  - 10 small groups (3-6 members)
  - 4 larger groups (7-10 members)
- Messages: 10,120 total (deterministic)

Includes name-collision contacts for misdelivery testing:
- Rahul Sharma / Rahul Verma / Rahul (`rahul@vendor.com`)
- Amit Singh / Amit Sinha
- Neha Gupta / Neha Goyal

## Local Run (Without Docker)

From this folder (`graph-mock`):

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Regenerate Dataset

```bash
python scripts/generate_data.py
```

Rewrites:
- `data/users.json`
- `data/chats.json`
- `data/messages.json`

## Run With Docker Compose

From workspace root (parent directory):

```bash
docker compose up --build
```

Graph mock URL:
- `http://127.0.0.1:8000`

## Example Calls

```bash
curl 'http://127.0.0.1:8000/v1.0/users'
curl 'http://127.0.0.1:8000/v1.0/users?$top=5&$skip=5'
curl 'http://127.0.0.1:8000/v1.0/users/u001/chats'
curl 'http://127.0.0.1:8000/v1.0/chats/c017/messages?$top=20'
curl 'http://127.0.0.1:8000/v1.0/chats/c017/messages?$filter=lastModifiedDateTime%20ge%202026-02-01T00:00:00Z'
```

## Tests

```bash
pytest -q
```
