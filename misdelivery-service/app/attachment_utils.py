from __future__ import annotations

from typing import Any


def detect_attachment_kind(attachments: list[dict[str, Any]]) -> str:
    if not attachments:
        return "none"

    if any(_is_link(item) for item in attachments):
        return "link"
    if any(_is_zip(item) for item in attachments):
        return "zip"
    if any(_is_xlsx(item) for item in attachments):
        return "xlsx"
    if any(_is_pdf(item) for item in attachments):
        return "pdf"
    return "other"


def _is_link(item: dict[str, Any]) -> bool:
    content_type = str(item.get("contentType", "")).lower()
    return bool(item.get("isLink")) or content_type == "text/uri-list"


def _is_zip(item: dict[str, Any]) -> bool:
    name = str(item.get("name", "")).lower()
    content_type = str(item.get("contentType", "")).lower()
    return name.endswith((".zip", ".7z", ".rar")) or "zip" in content_type


def _is_xlsx(item: dict[str, Any]) -> bool:
    name = str(item.get("name", "")).lower()
    content_type = str(item.get("contentType", "")).lower()
    return name.endswith((".xlsx", ".xls")) or "spreadsheet" in content_type


def _is_pdf(item: dict[str, Any]) -> bool:
    name = str(item.get("name", "")).lower()
    content_type = str(item.get("contentType", "")).lower()
    return name.endswith(".pdf") or "pdf" in content_type
