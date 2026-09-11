from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from core.config import settings
from part3_doc_agent import document, web
from part3_doc_agent.graph import DocumentAgent
from part3_doc_agent.memory import ConversationMemory
from part3_doc_agent.mock_llm import MockAgentLLM

@pytest.fixture(scope="module")
def kb(embedder):
    return document.build_index(embedder=embedder)

@pytest.fixture
def client(kb, tmp_path, monkeypatch):

    class TempMemory(ConversationMemory):
        def __init__(self, session_id: str = "default", **kwargs):
            kwargs["session_dir"] = tmp_path
            super().__init__(session_id, **kwargs)

    monkeypatch.setattr(web, "ConversationMemory", TempMemory)
    agent = DocumentAgent(llm=MockAgentLLM(), kb=kb)
    monkeypatch.setattr(web, "get_agent", lambda: agent)
    return TestClient(web.app)

def test_health_reports_the_document_and_tools(client):
    body = client.get("/api/health").json()

    assert body["status"] == "ok"
    assert body["document"] == settings.chat_document_path.name
    assert body["tools"] == ["document_search", "calculator"]
    assert body["chunks"] > 0

def test_chat_returns_the_answer_and_which_tools_ran(client):
    body = client.post("/api/chat", json={"message": "What's 15% of 4800?", "session_id": "t1"}).json()

    assert body["tools_used"] == ["calculator"]
    assert "720" in body["answer"]
    assert body["tool_calls"][0]["output"] == "720"
    assert body["routing_reason"]

def test_chat_reports_no_tools_when_none_were_needed(client):
    body = client.post("/api/chat", json={"message": "Hi there!", "session_id": "t2"}).json()

    assert body["tools_used"] == []
    assert body["trace"], "the trace should still show the routing decision"

def test_memory_is_returned_and_persists_across_requests(client):
    client.post("/api/chat", json={"message": "Hi, I'm Rega.", "session_id": "t3"})
    body = client.post("/api/chat", json={"message": "What is my name?", "session_id": "t3"}).json()

    assert body["memory"]["name"] == "Rega"
    assert "Rega" in body["answer"]
    assert body["tools_used"] == [], "recalling a name needs no tool"

def test_sessions_do_not_leak_into_each_other(client):
    client.post("/api/chat", json={"message": "Hi, I'm Rega.", "session_id": "alice"})
    body = client.post("/api/chat", json={"message": "What is my name?", "session_id": "bob"}).json()

    assert body["memory"] == {}
    assert "Rega" not in body["answer"]

def test_a_session_can_be_read_back(client):
    client.post("/api/chat", json={"message": "Hi, I'm Rega.", "session_id": "t4"})
    body = client.get("/api/session/t4").json()

    assert body["memory"]["name"] == "Rega"
    assert [turn["role"] for turn in body["turns"]] == ["user", "agent"]

def test_a_session_can_be_cleared(client):
    client.post("/api/chat", json={"message": "Hi, I'm Rega.", "session_id": "t5"})
    client.delete("/api/session/t5")

    assert client.get("/api/session/t5").json()["memory"] == {}

def test_an_empty_message_is_rejected(client):
    assert client.post("/api/chat", json={"message": "   ", "session_id": "t6"}).status_code == 400

def test_the_page_is_served(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "PointStar Document Agent" in response.text
