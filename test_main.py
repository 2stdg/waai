import os
from pathlib import Path

ROOT = Path(__file__).parent
os.environ["DB_PATH"] = str(ROOT / "test_bot.db")

import sys
sys.path.insert(0, str(ROOT / "agent"))

import memory

if memory.DB_PATH.exists():
    memory.DB_PATH.unlink()

os.environ.setdefault("WHATSAPP_TOKEN", "x")
os.environ.setdefault("WHATSAPP_PHONE_NUMBER_ID", "x")
os.environ.setdefault("WHATSAPP_VERIFY_TOKEN", "secret")
os.environ.setdefault("WHATSAPP_APP_SECRET", "x")
os.environ.setdefault("NOTIFY_NUMBER", "5210000000000")
os.environ.setdefault("ANTHROPIC_API_KEY", "x")
os.environ.setdefault("LLM_PROVIDER", "anthropic")

from fastapi.testclient import TestClient

import main
from main import app

client = TestClient(app)


def test_verify_webhook_success():
    r = client.get("/webhook", params={"hub.verify_token": "secret", "hub.challenge": "123"})
    assert r.text == "123"


def test_verify_webhook_wrong_token():
    r = client.get("/webhook", params={"hub.verify_token": "wrong", "hub.challenge": "123"})
    assert r.status_code == 403


def test_memory_round_trip():
    phone = "test_phone_123"
    memory.save_message(phone, "user", "hola")
    memory.save_message(phone, "assistant", "hola, en que te ayudo?")
    history = memory.get_history(phone, limit=10)
    assert history == [
        {"role": "user", "content": "hola"},
        {"role": "assistant", "content": "hola, en que te ayudo?"},
    ]


def test_escalation_flow():
    calls = {"n": 0}

    class FakeBlock:
        def __init__(self, type_, **kw):
            self.type = type_
            for k, v in kw.items():
                setattr(self, k, v)

    class FakeResponse:
        def __init__(self, stop_reason, content):
            self.stop_reason = stop_reason
            self.content = content

    def fake_create(**kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return FakeResponse(
                "tool_use",
                [FakeBlock("tool_use", id="t1", name="escalar_a_humano", input={"motivo": "pregunta fuera de alcance"})],
            )
        return FakeResponse("end_turn", [FakeBlock("text", text="Ya avise a alguien del equipo.")])

    original_create = main.claude.messages.create
    original_notify = main._notify_team
    main.claude.messages.create = fake_create
    main._notify_team = lambda phone, motivo: None
    try:
        phone = "test_phone_escalate"
        reply = main.run_agent(phone, "quiero hablar con una persona")
        assert reply == "Ya avise a alguien del equipo."
        assert calls["n"] == 2
        assert memory.is_escalated(phone) is True

        calls["n"] = 0
        reply2 = main.run_agent(phone, "hola de nuevo")
        assert reply2 == main.ESCALATED_REPLY
        assert calls["n"] == 0
    finally:
        main.claude.messages.create = original_create
        main._notify_team = original_notify


if __name__ == "__main__":
    test_verify_webhook_success()
    test_verify_webhook_wrong_token()
    test_memory_round_trip()
    test_escalation_flow()
    print("ok")
