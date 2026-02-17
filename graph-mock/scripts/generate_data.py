from __future__ import annotations

import json
import random
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

NOW_UTC = datetime(2026, 2, 15, 0, 0, 0, tzinfo=UTC)
WINDOW_DAYS = 35
SEED = 20260215
TZ = ZoneInfo("Asia/Kolkata")


def iso_z(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_users() -> list[dict]:
    users: list[dict] = [
        {
            "id": "u001",
            "displayName": "Rahul Sharma",
            "userPrincipalName": "rahul.sharma@company.com",
            "mail": "rahul.sharma@company.com",
            "userType": "Member",
            "department": "Engineering",
            "jobTitle": "Senior Backend Engineer",
            "persona": "engineer",
        },
        {
            "id": "u002",
            "displayName": "Rahul Verma",
            "userPrincipalName": "rahul.verma@company.com",
            "mail": "rahul.verma@company.com",
            "userType": "Member",
            "department": "Engineering",
            "jobTitle": "Platform Engineer",
            "persona": "engineer",
        },
        {
            "id": "u003",
            "displayName": "Amit Singh",
            "userPrincipalName": "amit.singh@company.com",
            "mail": "amit.singh@company.com",
            "userType": "Member",
            "department": "Engineering",
            "jobTitle": "SRE Engineer",
            "persona": "engineer",
        },
        {
            "id": "u004",
            "displayName": "Amit Sinha",
            "userPrincipalName": "amit.sinha@company.com",
            "mail": "amit.sinha@company.com",
            "userType": "Member",
            "department": "Engineering",
            "jobTitle": "Engineering Manager",
            "persona": "engineer",
        },
        {
            "id": "u005",
            "displayName": "Neha Gupta",
            "userPrincipalName": "neha.gupta@company.com",
            "mail": "neha.gupta@company.com",
            "userType": "Member",
            "department": "Engineering",
            "jobTitle": "Frontend Engineer",
            "persona": "engineer",
        },
        {
            "id": "u006",
            "displayName": "Neha Goyal",
            "userPrincipalName": "neha.goyal@company.com",
            "mail": "neha.goyal@company.com",
            "userType": "Member",
            "department": "Engineering",
            "jobTitle": "QA Engineer",
            "persona": "engineer",
        },
        {
            "id": "u007",
            "displayName": "Priya Menon",
            "userPrincipalName": "priya.menon@company.com",
            "mail": "priya.menon@company.com",
            "userType": "Member",
            "department": "Sales",
            "jobTitle": "Account Executive",
            "persona": "sales",
        },
        {
            "id": "u008",
            "displayName": "Karan Mehta",
            "userPrincipalName": "karan.mehta@company.com",
            "mail": "karan.mehta@company.com",
            "userType": "Member",
            "department": "Customer Success",
            "jobTitle": "Customer Success Manager",
            "persona": "sales",
        },
        {
            "id": "u009",
            "displayName": "Sana Khan",
            "userPrincipalName": "sana.khan@company.com",
            "mail": "sana.khan@company.com",
            "userType": "Member",
            "department": "Sales",
            "jobTitle": "Solutions Consultant",
            "persona": "sales",
        },
        {
            "id": "u010",
            "displayName": "Arjun Batra",
            "userPrincipalName": "arjun.batra@company.com",
            "mail": "arjun.batra@company.com",
            "userType": "Member",
            "department": "Customer Success",
            "jobTitle": "Implementation Specialist",
            "persona": "sales",
        },
        {
            "id": "u011",
            "displayName": "Isha Kapoor",
            "userPrincipalName": "isha.kapoor@company.com",
            "mail": "isha.kapoor@company.com",
            "userType": "Member",
            "department": "HR",
            "jobTitle": "HR Business Partner",
            "persona": "hrfinance",
        },
        {
            "id": "u012",
            "displayName": "Vivek Jain",
            "userPrincipalName": "vivek.jain@company.com",
            "mail": "vivek.jain@company.com",
            "userType": "Member",
            "department": "Finance",
            "jobTitle": "Finance Operations Lead",
            "persona": "hrfinance",
        },
        {
            "id": "u013",
            "displayName": "Rahul",
            "userPrincipalName": "rahul@vendor.com",
            "mail": "rahul@vendor.com",
            "userType": "Guest",
            "department": "Vendor",
            "jobTitle": "Integration Consultant",
            "persona": "external",
        },
        {
            "id": "u014",
            "displayName": "Emily Clark",
            "userPrincipalName": "emily.clark@partner.org",
            "mail": "emily.clark@partner.org",
            "userType": "Guest",
            "department": "Partner",
            "jobTitle": "Partner Manager",
            "persona": "external",
        },
        {
            "id": "u015",
            "displayName": "David Lee",
            "userPrincipalName": "david.lee@partner.org",
            "mail": "david.lee@partner.org",
            "userType": "Guest",
            "department": "Client",
            "jobTitle": "IT Director",
            "persona": "external",
        },
        {
            "id": "u016",
            "displayName": "Meera Iyer",
            "userPrincipalName": "meera@vendor.com",
            "mail": "meera@vendor.com",
            "userType": "Guest",
            "department": "Vendor",
            "jobTitle": "Delivery Lead",
            "persona": "external",
        },
        {
            "id": "u017",
            "displayName": "Tom Wilson",
            "userPrincipalName": "tom.wilson@gmail.com",
            "mail": "tom.wilson@gmail.com",
            "userType": "Guest",
            "department": "Client",
            "jobTitle": "Founder",
            "persona": "external",
        },
        {
            "id": "u018",
            "displayName": "Alicia Gomez",
            "userPrincipalName": "alicia.gomez@partner.org",
            "mail": "alicia.gomez@partner.org",
            "userType": "Guest",
            "department": "Partner",
            "jobTitle": "Procurement Lead",
            "persona": "external",
        },
    ]
    return users


def build_chats(users_by_id: dict[str, dict]) -> list[dict]:
    one_on_one_pairs = [
        ("c001", "u001", "u002"),
        ("c002", "u003", "u004"),
        ("c003", "u005", "u006"),
        ("c004", "u001", "u003"),
        ("c005", "u002", "u004"),
        ("c006", "u001", "u005"),
        ("c007", "u007", "u013"),
        ("c008", "u008", "u014"),
        ("c009", "u009", "u015"),
        ("c010", "u010", "u016"),
        ("c011", "u007", "u008"),
        ("c012", "u009", "u010"),
        ("c013", "u011", "u012"),
        ("c014", "u007", "u017"),
    ]

    groups: list[tuple[str, str, list[str]]] = [
        ("c015", "All-Hands", ["u001", "u002", "u003", "u004", "u005", "u006", "u007", "u008", "u009", "u010"]),
        ("c016", "Finance Ops", ["u011", "u012", "u007", "u008", "u009", "u010", "u003", "u004"]),
        ("c017", "Eng Platform", ["u001", "u002", "u003", "u004", "u005", "u006", "u011", "u012"]),
        ("c018", "Customer XYZ", ["u007", "u008", "u009", "u010", "u013", "u014", "u015"]),
        ("c019", "Oncall", ["u001", "u002", "u003", "u004", "u005"]),
        ("c020", "Release", ["u001", "u003", "u004", "u005", "u006"]),
        ("c021", "Pipeline", ["u007", "u008", "u009", "u010", "u012"]),
        ("c022", "QBR Prep", ["u007", "u008", "u009", "u010", "u014"]),
        ("c023", "HR Team", ["u011", "u012", "u007"]),
        ("c024", "Payroll Ops", ["u011", "u012", "u004", "u003"]),
        ("c025", "Customer ABC", ["u007", "u009", "u013", "u016"]),
        ("c026", "Incident Review", ["u001", "u002", "u003", "u004", "u005", "u006"]),
        ("c027", "Hiring Panel", ["u011", "u003", "u005", "u008"]),
        ("c028", "Onboarding Buddy", ["u006", "u011", "u010"]),
    ]

    chats: list[dict] = []
    for chat_id, a, b in one_on_one_pairs:
        chats.append(
            {
                "id": chat_id,
                "chatType": "oneOnOne",
                "members": [
                    {"userId": a, "displayName": users_by_id[a]["displayName"]},
                    {"userId": b, "displayName": users_by_id[b]["displayName"]},
                ],
            }
        )

    for chat_id, topic, members in groups:
        chats.append(
            {
                "id": chat_id,
                "topic": topic,
                "chatType": "group",
                "members": [{"userId": m, "displayName": users_by_id[m]["displayName"]} for m in members],
            }
        )

    return chats


def persona_weights(topic: str, persona: str) -> float:
    topic_l = topic.lower()
    if any(key in topic_l for key in ["eng", "oncall", "release", "incident"]):
        return {"engineer": 1.35, "sales": 0.65, "hrfinance": 0.55, "external": 0.40}[persona]
    if any(key in topic_l for key in ["customer", "pipeline", "qbr"]):
        return {"engineer": 0.65, "sales": 1.35, "hrfinance": 0.60, "external": 0.95}[persona]
    if any(key in topic_l for key in ["hr", "payroll", "finance"]):
        return {"engineer": 0.70, "sales": 0.75, "hrfinance": 1.40, "external": 0.30}[persona]
    return {"engineer": 1.0, "sales": 1.0, "hrfinance": 0.9, "external": 0.6}[persona]


def persona_hours(persona_mix: str, rng: random.Random) -> int:
    if persona_mix == "engineer":
        return rng.randint(9, 19)
    if persona_mix == "sales":
        return rng.randint(10, 23) if rng.random() < 0.18 else rng.randint(10, 20)
    if persona_mix == "hrfinance":
        return rng.randint(10, 18)
    return rng.randint(9, 20)


def infer_chat_focus(chat: dict, personas: dict[str, str]) -> str:
    topic = chat.get("topic", "").lower()
    if any(key in topic for key in ["eng", "oncall", "release", "incident"]):
        return "engineer"
    if any(key in topic for key in ["customer", "pipeline", "qbr"]):
        return "sales"
    if any(key in topic for key in ["hr", "payroll", "finance"]):
        return "hrfinance"

    counts = {"engineer": 0, "sales": 0, "hrfinance": 0, "external": 0}
    for member in chat["members"]:
        counts[personas[member["userId"]]] += 1
    return max(counts.items(), key=lambda item: item[1])[0]


def choose_base_time(chat: dict, focus: str, rng: random.Random) -> datetime:
    now_local = NOW_UTC.astimezone(TZ)
    start_local = (NOW_UTC - timedelta(days=WINDOW_DAYS)).astimezone(TZ)
    day_count = (now_local.date() - start_local.date()).days
    day_offsets = list(range(day_count + 1))

    weights: list[float] = []
    for offset in day_offsets:
        day = start_local.date() + timedelta(days=offset)
        weekday = day.weekday()
        weight = 1.0 if weekday < 5 else 0.3
        if chat["chatType"] == "group" and weekday == 0:
            weight *= 1.6
        weights.append(weight)

    day_offset = rng.choices(day_offsets, weights=weights, k=1)[0]
    chosen_day = start_local.date() + timedelta(days=day_offset)
    hour = persona_hours(focus, rng)
    minute = rng.randint(0, 59)
    second = rng.randint(0, 59)
    local_dt = datetime(
        year=chosen_day.year,
        month=chosen_day.month,
        day=chosen_day.day,
        hour=hour,
        minute=minute,
        second=second,
        tzinfo=TZ,
    )
    utc_dt = local_dt.astimezone(UTC)
    if utc_dt > NOW_UTC:
        utc_dt = NOW_UTC - timedelta(minutes=rng.randint(1, 45))
    return utc_dt


def select_sender(chat: dict, personas: dict[str, str], rng: random.Random) -> str:
    member_ids = [member["userId"] for member in chat["members"]]
    topic = chat.get("topic", "")
    weights: list[float] = []
    for idx, user_id in enumerate(member_ids):
        persona = personas[user_id]
        base = persona_weights(topic, persona)
        weights.append(base + max(0.0, 0.08 - idx * 0.01))
    return rng.choices(member_ids, weights=weights, k=1)[0]


def pick_text(persona: str, topic: str, rng: random.Random) -> str:
    engineer_msgs = [
        "Pushed a fix for the retry path. Please review when free.",
        "Can you check pod logs for the 5xx spike in prod?",
        "Merged the PR; deployment is queued for this evening.",
        "I updated the runbook with the latest rollback steps.",
        "Let's close the incident after confirming dashboard latency.",
    ]
    sales_msgs = [
        "Sharing the updated deck before tomorrow's client call.",
        "Can we lock a slot for a follow-up demo this week?",
        "Customer asked for pricing options with annual billing.",
        "I sent meeting notes and next actions to the stakeholder.",
        "Let's align on QBR narrative and renewal timeline.",
    ]
    hrfinance_msgs = [
        "Payroll sheet is ready for sign-off before EOD.",
        "Please validate invoice coding for this vendor batch.",
        "Headcount tracker has been updated for February.",
        "Policy draft is ready; sharing for quick review.",
        "Can we confirm reimbursement approvals by 4 PM?",
    ]

    if any(key in topic.lower() for key in ["incident", "oncall"]):
        return rng.choice(
            [
                "Service recovered. Monitoring for another 20 minutes.",
                "Pager triggered again; checking dependency latency now.",
                "Need one more confirmation on error budget before closure.",
            ]
        )

    if persona == "engineer":
        return rng.choice(engineer_msgs)
    if persona == "sales":
        return rng.choice(sales_msgs)
    if persona == "hrfinance":
        return rng.choice(hrfinance_msgs)
    return rng.choice(
        [
            "Thanks, reviewed this and shared feedback on email.",
            "Confirmed from our side. Please proceed with next step.",
            "Joining the call 10 minutes early to sync on agenda.",
        ]
    )


def build_attachments(persona: str, message_id: str, rng: random.Random) -> list[dict]:
    def attachment(aid: str, name: str, content_type: str, size: int, is_link: bool) -> dict:
        return {
            "id": aid,
            "name": name,
            "contentType": content_type,
            "size": size,
            "isLink": is_link,
        }

    chance = {"engineer": 0.04, "sales": 0.14, "hrfinance": 0.20, "external": 0.05}[persona]
    if rng.random() >= chance:
        return []

    aid = f"a-{message_id}"
    if persona == "engineer":
        ticket = f"JIRA-{rng.randint(1000, 9999)}"
        return [attachment(aid, ticket, "text/uri-list", rng.randint(90, 220), True)]
    if persona == "sales":
        if rng.random() < 0.45:
            return [attachment(aid, "Proposal_Q1.pdf", "application/pdf", rng.randint(25_000, 220_000), False)]
        return [attachment(aid, "Call_Notes_Link", "text/uri-list", rng.randint(90, 220), True)]
    if persona == "hrfinance":
        if rng.random() < 0.55:
            return [attachment(aid, "Payroll_Feb.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", rng.randint(40_000, 180_000), False)]
        return [attachment(aid, "Invoice_1023.pdf", "application/pdf", rng.randint(20_000, 140_000), False)]
    return [attachment(aid, "Meeting_Link", "text/uri-list", rng.randint(90, 220), True)]


def importance_for_chat(topic: str, rng: random.Random) -> str:
    topic_l = topic.lower()
    high_prob = 0.08 if any(key in topic_l for key in ["oncall", "incident"]) else 0.015
    return "high" if rng.random() < high_prob else "normal"


def generate_messages(users: list[dict], chats: list[dict]) -> list[dict]:
    rng = random.Random(SEED)
    personas = {user["id"]: str(user["persona"]) for user in users}

    targets = {
        "oneOnOne": 180,
        "group_small": 320,
        "group_large": 1100,
    }

    messages: list[dict] = []
    message_counter = 1

    for chat in chats:
        size = len(chat["members"])
        if chat["chatType"] == "oneOnOne":
            target = targets["oneOnOne"]
        elif size <= 6:
            target = targets["group_small"]
        else:
            target = targets["group_large"]

        focus = infer_chat_focus(chat, personas)
        topic = chat.get("topic", "")

        produced = 0
        while produced < target:
            burst = rng.randint(3, 8) if chat["chatType"] == "group" else rng.randint(1, 3)
            burst = min(burst, target - produced)
            base_time = choose_base_time(chat, focus, rng)

            for _ in range(burst):
                sender_id = select_sender(chat, personas, rng)
                persona = personas[sender_id]
                created_dt = base_time + timedelta(minutes=rng.randint(0, 14) if chat["chatType"] == "group" else rng.randint(0, 90))
                if created_dt > NOW_UTC:
                    created_dt = NOW_UTC - timedelta(minutes=rng.randint(1, 30))

                modified_dt = created_dt
                if rng.random() < 0.12:
                    modified_dt = created_dt + timedelta(minutes=rng.randint(1, 5))
                    if modified_dt > NOW_UTC:
                        modified_dt = NOW_UTC

                message_id = f"m{message_counter:06d}"
                message_counter += 1

                messages.append(
                    {
                        "id": message_id,
                        "chatId": chat["id"],
                        "createdDateTime": iso_z(created_dt),
                        "lastModifiedDateTime": iso_z(modified_dt),
                        "from": {
                            "user": {
                                "id": sender_id,
                                "displayName": next(user["displayName"] for user in users if user["id"] == sender_id),
                            }
                        },
                        "body": {
                            "contentType": "text",
                            "content": pick_text(persona, topic, rng),
                        },
                        "importance": importance_for_chat(topic, rng),
                        "attachments": build_attachments(persona, message_id, rng),
                    }
                )
                produced += 1

    messages.sort(key=lambda item: (item["chatId"], item["lastModifiedDateTime"], item["id"]))
    return messages


def strip_persona_fields(users: Iterable[dict]) -> list[dict]:
    clean: list[dict] = []
    for user in users:
        item = dict(user)
        item.pop("persona", None)
        clean.append(item)
    return clean


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    users = build_users()
    users_by_id = {user["id"]: user for user in users}
    chats = build_chats(users_by_id)
    messages = generate_messages(users, chats)

    (data_dir / "users.json").write_text(json.dumps(strip_persona_fields(users), indent=2), encoding="utf-8")
    (data_dir / "chats.json").write_text(json.dumps(chats, indent=2), encoding="utf-8")
    (data_dir / "messages.json").write_text(json.dumps(messages, indent=2), encoding="utf-8")

    print(f"Wrote {len(users)} users, {len(chats)} chats, {len(messages)} messages to {data_dir}")


if __name__ == "__main__":
    main()
