from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class DataStore:
    users: list[dict]
    chats: list[dict]
    messages: list[dict]
    users_by_id: dict[str, dict]
    chats_by_id: dict[str, dict]
    chats_by_user: dict[str, list[dict]]
    messages_by_chat: dict[str, list[dict]]

    @classmethod
    def load(cls, data_dir: Path) -> "DataStore":
        users = json.loads((data_dir / "users.json").read_text(encoding="utf-8"))
        chats = json.loads((data_dir / "chats.json").read_text(encoding="utf-8"))
        messages = json.loads((data_dir / "messages.json").read_text(encoding="utf-8"))

        users_by_id = {user["id"]: user for user in users}
        chats_by_id = {chat["id"]: chat for chat in chats}

        chats_by_user: dict[str, list[dict]] = {user_id: [] for user_id in users_by_id}
        for chat in chats:
            for member in chat["members"]:
                uid = member["userId"]
                chats_by_user.setdefault(uid, []).append(chat)

        messages_by_chat: dict[str, list[dict]] = {}
        for message in messages:
            cid = str(message["chatId"])
            messages_by_chat.setdefault(cid, []).append(message)

        for cid, items in messages_by_chat.items():
            items.sort(key=lambda m: _parse_datetime(str(m["lastModifiedDateTime"])))
            messages_by_chat[cid] = [
                {
                    "id": item["id"],
                    "createdDateTime": item["createdDateTime"],
                    "lastModifiedDateTime": item["lastModifiedDateTime"],
                    "from": item["from"],
                    "body": item["body"],
                    "importance": item["importance"],
                    "attachments": item["attachments"],
                }
                for item in items
            ]

        return cls(
            users=users,
            chats=chats,
            messages=messages,
            users_by_id=users_by_id,
            chats_by_id=chats_by_id,
            chats_by_user=chats_by_user,
            messages_by_chat=messages_by_chat,
        )


def _parse_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)
