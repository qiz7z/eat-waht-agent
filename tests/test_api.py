"""FastAPI 接口测试"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    """创建测试客户端（每次测试独立）"""
    from api import app, _sessions
    _sessions.clear()
    return TestClient(app)


class TestHealthEndpoint:
    """健康检查接口"""

    def test_health_returns_ok(self, client: TestClient):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "active_sessions" in data

    def test_health_default_zero_sessions(self, client: TestClient):
        resp = client.get("/health")
        assert resp.json()["active_sessions"] == 0


class TestChatEndpoint:
    """聊天接口"""

    def test_chat_creates_session(self, client: TestClient):
        resp = client.post("/chat", json={"message": "你好"})
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert data["session_id"] != ""
        assert "response" in data
        assert "history" in data
        assert "is_ready" in data

    def test_chat_reuses_session(self, client: TestClient):
        resp1 = client.post("/chat", json={"message": "你好"})
        sid = resp1.json()["session_id"]

        resp2 = client.post("/chat", json={"message": "想吃辣的", "session_id": sid})
        assert resp2.status_code == 200
        assert resp2.json()["session_id"] == sid

    def test_chat_with_explicit_session_id(self, client: TestClient):
        resp = client.post("/chat", json={"message": "你好", "session_id": "my-session"})
        assert resp.status_code == 200
        assert resp.json()["session_id"] == "my-session"

    def test_chat_empty_message_rejected(self, client: TestClient):
        resp = client.post("/chat", json={"message": ""})
        assert resp.status_code == 422  # Pydantic validation: min_length=1

    def test_chat_response_contains_history(self, client: TestClient):
        resp = client.post("/chat", json={"message": "你好"})
        data = resp.json()
        assert isinstance(data["history"], list)
        assert "response" in data
        assert len(data["response"]) > 0


class TestResetEndpoint:
    """重置接口"""

    def test_reset_existing_session(self, client: TestClient):
        resp1 = client.post("/chat", json={"message": "你好"})
        sid = resp1.json()["session_id"]

        resp2 = client.post("/reset", json={"session_id": sid})
        assert resp2.status_code == 200
        assert resp2.json()["session_id"] == sid
        assert resp2.json()["history"] == []

    def test_reset_nonexistent_session(self, client: TestClient):
        resp = client.post("/reset", json={"session_id": "does-not-exist"})
        assert resp.status_code == 404


class TestDeleteSessionEndpoint:
    """删除会话接口"""

    def test_delete_existing_session(self, client: TestClient):
        resp1 = client.post("/chat", json={"message": "你好"})
        sid = resp1.json()["session_id"]

        resp2 = client.delete(f"/sessions/{sid}")
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "deleted"

    def test_delete_nonexistent_session(self, client: TestClient):
        resp = client.delete("/sessions/does-not-exist")
        assert resp.status_code == 404

    def test_delete_then_chat_creates_new(self, client: TestClient):
        resp1 = client.post("/chat", json={"message": "你好"})
        sid = resp1.json()["session_id"]
        client.delete(f"/sessions/{sid}")

        resp2 = client.post("/chat", json={"message": "再来"})
        assert resp2.json()["session_id"] != sid
