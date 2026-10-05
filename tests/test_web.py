from __future__ import annotations

import json
import threading
import urllib.request
from pathlib import Path
from typing import Any

from chad.app import ChadApp
from chad.core.config import AppConfig
from chad.core.conversation import ChatRequest
from chad.interfaces.web import create_web_server
from chad.llm.client import LapisClient, ModelInfo


class MockLapisClient(LapisClient):
    def generate(self, request: ChatRequest) -> str:
        last_msg = request.messages[-1].content
        return f"Echo: {last_msg}"

    def current_model(self) -> ModelInfo:
        return ModelInfo(id="test-model", display_name="Test Model")


def _make_app(tmp_path: Path) -> ChadApp:
    config = AppConfig(storage_dir=tmp_path / "storage")
    client = MockLapisClient()
    return ChadApp.create(config, client)


def _http_request(url: str, method: str = "GET", data: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
    req = urllib.request.Request(url, method=method)
    if data is not None:
        payload = json.dumps(data).encode("utf-8")
        req.add_header("Content-Type", "application/json")
        req.data = payload

    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            body = json.loads(resp.read().decode("utf-8"))
            return status, body
    except urllib.error.HTTPError as err:
        body = json.loads(err.read().decode("utf-8"))
        return err.code, body


def test_web_health(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    server = create_web_server(app, host="127.0.0.1", port=0)
    host, port = server.server_address

    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    try:
        url = f"http://{host}:{port}/api/health"
        status, body = _http_request(url)
        assert status == 200
        assert body["status"] == "ok"
        assert body["app"] == "CHAD"
    finally:
        server.shutdown()
        server.server_close()


def test_web_models_and_conversations(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    server = create_web_server(app, host="127.0.0.1", port=0)
    host, port = server.server_address

    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    try:
        base_url = f"http://{host}:{port}"

        # GET /api/models
        status, body = _http_request(f"{base_url}/api/models")
        assert status == 200
        assert "models" in body
        assert len(body["models"]) >= 1

        # POST /api/conversations
        status, body = _http_request(f"{base_url}/api/conversations", method="POST")
        assert status == 201
        assert "conversation" in body
        conv_id = body["conversation"]["id"]

        # GET /api/conversations
        status, body = _http_request(f"{base_url}/api/conversations")
        assert status == 200
        assert len(body["conversations"]) >= 1

        # POST /api/chat
        status, body = _http_request(
            f"{base_url}/api/chat", method="POST", data={"text": "Hello world!"}
        )
        assert status == 200
        assert "response" in body
        assert body["response"] == "Echo: Hello world!"

        # GET /api/conversations/<id>
        status, body = _http_request(f"{base_url}/api/conversations/{conv_id}")
        assert status == 200
        assert body["conversation"]["id"] == conv_id

    finally:
        server.shutdown()
        server.server_close()


def test_web_not_found_and_errors(tmp_path: Path) -> None:
    app = _make_app(tmp_path)
    server = create_web_server(app, host="127.0.0.1", port=0)
    host, port = server.server_address

    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    try:
        base_url = f"http://{host}:{port}"

        # GET invalid endpoint
        status, body = _http_request(f"{base_url}/api/invalid")
        assert status == 404

        # POST /api/chat missing text
        status, body = _http_request(f"{base_url}/api/chat", method="POST", data={})
        assert status == 400
        assert "error" in body

    finally:
        server.shutdown()
        server.server_close()
