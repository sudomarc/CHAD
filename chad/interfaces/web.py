from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import urlparse

from chad.app import ChadApp


class WebApiHandler(BaseHTTPRequestHandler):
    app: ChadApp | None = None

    def _send_json(self, data: Any, status: int = HTTPStatus.OK) -> None:
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(payload)

    def _read_json(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        body = self.rfile.read(content_length)
        return json.loads(body.decode("utf-8"))

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        if path == "/api/health":
            self._send_json({"status": "ok", "app": "CHAD"})
            return

        if self.app is None:
            self._send_json({"error": "App instance not bound"}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if path == "/api/models":
            models = [
                {
                    "id": m.id,
                    "backend": m.backend,
                    "display_name": m.display_name,
                }
                for m in self.app.gateway.list_models()
            ]
            self._send_json({"models": models})
            return

        if path == "/api/conversations":
            conversations = [conv.to_dict() for conv in self.app.history()]
            self._send_json({"conversations": conversations})
            return

        if path.startswith("/api/conversations/"):
            conv_id = path.split("/")[-1]
            try:
                conv = self.app.load_conversation(conv_id)
                self._send_json({"conversation": conv.to_dict()})
            except Exception as err:  # noqa: BLE001
                self._send_json({"error": str(err)}, HTTPStatus.NOT_FOUND)
            return

        self._send_json({"error": "Not Found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        if self.app is None:
            self._send_json({"error": "App instance not bound"}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        body = self._read_json()

        if path == "/api/conversations":
            conv = self.app.new_conversation()
            self.app.store.save(conv)
            self._send_json({"conversation": conv.to_dict()}, HTTPStatus.CREATED)
            return

        if path == "/api/chat":
            text = body.get("text") or body.get("message")
            if not text:
                self._send_json({"error": "Missing 'text' in request body"}, HTTPStatus.BAD_REQUEST)
                return
            try:
                response = self.app.send(text)
                self._send_json(
                    {
                        "response": response,
                        "conversation": self.app.conversation.to_dict(),
                    }
                )
            except Exception as err:  # noqa: BLE001
                self._send_json({"error": str(err)}, HTTPStatus.BAD_REQUEST)
            return

        self._send_json({"error": "Not Found"}, HTTPStatus.NOT_FOUND)


def create_web_server(app: ChadApp, host: str = "127.0.0.1", port: int = 8000) -> HTTPServer:
    class Handler(WebApiHandler):
        pass

    Handler.app = app
    return HTTPServer((host, port), Handler)


def run_web(app: ChadApp, host: str = "127.0.0.1", port: int = 8000) -> None:
    server = create_web_server(app, host, port)
    print(f"CHAD Web API server running at http://{host}:{port}")
    try:
        server.serve_forever()
    finally:
        server.server_close()
