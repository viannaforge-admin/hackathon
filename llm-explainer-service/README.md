# LLM Explainer Service

Standalone service that converts structured misdelivery metadata into concise explanation text using OpenAI.

## Endpoints

- `GET /v1/health`
- `POST /v1/explain`
- `POST /v1/keywords/extract`

## Environment

- `OPENAI_API_KEY` (required)
- `OPENAI_MODEL` (default `gpt-4o-mini`)
- `OPENAI_TEMPERATURE` (default `0`)
- `OPENAI_TIMEOUT_SECONDS` (default `1.5`)

## Run

```bash
cd llm-explainer-service
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8030
```

## Keyword Extraction Request

```json
{
  "messages": [
    "please review payroll file and invoice note",
    "customer list export for qbr prep"
  ]
}
```

## Keyword Extraction Response

```json
{
  "topics": {
    "finance": {
      "keywords": {
        "invoice": 1
      },
      "phrases": {
        "purchase order": 1
      }
    }
  }
}
```
