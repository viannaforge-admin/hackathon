from app.services.filtering import apply_message_filter


def test_apply_message_filter_keeps_ge_threshold() -> None:
    messages = [
        {"id": "1", "lastModifiedDateTime": "2026-01-10T00:00:00Z"},
        {"id": "2", "lastModifiedDateTime": "2026-01-20T10:30:00Z"},
        {"id": "3", "lastModifiedDateTime": "2026-02-10T09:00:00Z"},
    ]

    result = apply_message_filter(messages, "lastModifiedDateTime ge 2026-01-20T00:00:00Z")

    assert [m["id"] for m in result] == ["2", "3"]


def test_apply_message_filter_none_returns_input() -> None:
    messages = [{"id": "1", "lastModifiedDateTime": "2026-01-10T00:00:00Z"}]
    result = apply_message_filter(messages, None)
    assert result == messages


def test_apply_message_filter_rejects_unsupported_expression() -> None:
    messages = [{"id": "1", "lastModifiedDateTime": "2026-01-10T00:00:00Z"}]

    raised = False
    try:
        apply_message_filter(messages, "from/user/id eq 'u001'")
    except ValueError:
        raised = True

    assert raised
