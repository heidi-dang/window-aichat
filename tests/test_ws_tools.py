import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("WINDOW_AICHAT_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("WINDOW_AICHAT_DB_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.chdir(tmp_path)
    from window_aichat.api.server import app

    return TestClient(app)


def test_ws_tools_emits_tool_frames(client: TestClient):
    with client.websocket_connect("/ws/tools") as ws:
        ws.send_json({"type": "run", "tool": "explain", "code": "print('hi')"})
        first = ws.receive_json()
        assert first["type"] == "tool"
        assert first["stage"] in {"start", "error"}

