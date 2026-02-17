from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from app.routes.chats import router as chats_router
from app.routes.messages import router as messages_router
from app.routes.users import router as users_router
from app.services.data_store import DataStore


app = FastAPI(title="Microsoft Graph Teams Mock", version="1.0.0")
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
app.state.store = DataStore.load(DATA_DIR)

app.include_router(users_router, prefix="/v1.0")
app.include_router(chats_router, prefix="/v1.0")
app.include_router(messages_router, prefix="/v1.0")
