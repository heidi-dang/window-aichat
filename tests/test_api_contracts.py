import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("WINDOW_AICHAT_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    from window_aichat.api.server import app

    return TestClient(app)


def test_fs_write_and_read_roundtrip(client: TestClient):
    write_res = client.post("/api/fs/write", json={"path": "hello.txt", "content": "hi"})
    assert write_res.status_code == 200
    write_body = write_res.json()
    assert write_body["status"] == "success"
    assert "hello.txt" in write_body["path"]

    read_res = client.post("/api/fs/read", json={"path": "hello.txt"})
    assert read_res.status_code == 200
    assert read_res.json()["content"] == "hi"


def test_fs_path_traversal_blocked(client: TestClient):
    res = client.post("/api/fs/read", json={"path": "../secrets.txt"})
    assert res.status_code == 403
    body = res.json()
    assert body["error"]["code"] in {"http_error", "validation_error"}


def test_chat_returns_error_envelope_when_no_models_available(client: TestClient):
    res = client.post(
        "/api/chat",
        json={"message": "hi", "history": [], "model": "gemini"},
    )
    assert res.status_code in {400, 503}
    body = res.json()
    assert "error" in body
    assert "code" in body["error"]
    assert "message" in body["error"]

