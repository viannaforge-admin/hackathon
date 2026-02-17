# Keyword Review Frontend

Basic UI for reviewing LLM-extracted keywords/phrases per topic.

- Topic dropdown
- Suggestions table with columns: type, term, score, add, ignore
- Submit to apply actions

The UI hides ignored terms because backend excludes `ignored=true` rows.

## Run

```bash
cd keyword-review-frontend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8040
```
