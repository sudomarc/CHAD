from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import urlparse

from chad.app import ChadApp
from chad.auth.engine import AuthEngine
from chad.auth.lifecycle import AccountLifecycleManager
from chad.auth.models import (
    AccessDeniedError,
    AuthError,
    QuotaExceededError,
    User,
    UserRole,
    UserTier,
)
from chad.auth.ownership import DataOwnershipManager
from chad.auth.quotas import QuotaManager
from chad.auth.sessions import SessionManager
from chad.core.conversation import ConversationStatus
from chad.tools.builtin import register_builtin_tools
from chad.tools.registry import ToolRegistry


class WebApiHandler(BaseHTTPRequestHandler):
    app: ChadApp | None = None
    auth_engine: AuthEngine | None = None
    session_manager: SessionManager | None = None
    quota_manager: QuotaManager | None = None
    ownership_manager: DataOwnershipManager | None = None
    lifecycle_manager: AccountLifecycleManager | None = None

    def _send_json(self, data: Any, status: int = HTTPStatus.OK) -> None:
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        self.wfile.write(payload)

    def _read_json(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        body = self.rfile.read(content_length)
        return json.loads(body.decode("utf-8"))

    def _get_current_user(self) -> User | None:
        auth_header = self.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        token = auth_header.split(" ", 1)[1].strip()

        # Try session token
        if self.session_manager is not None and self.auth_engine is not None:
            try:
                session = self.session_manager.authenticate_session(token)
                return self.auth_engine.get_user(session.user_id)
            except Exception:
                pass

        # Try API key
        if self.auth_engine is not None:
            try:
                user, _ = self.auth_engine.authenticate_api_key(token)
                return user
            except Exception:
                pass

        return None

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
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

        current_user = self._get_current_user()

        if path == "/api/auth/me":
            if current_user is None:
                self._send_json({"error": "Unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            self._send_json({"user": current_user.to_dict()})
            return

        if path == "/api/auth/quota":
            if current_user is None:
                self._send_json({"error": "Unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            if self.quota_manager is None:
                self._send_json({"error": "Quota manager not configured"}, HTTPStatus.NOT_IMPLEMENTED)
                return
            usage = self.quota_manager.get_quota_usage(current_user)
            self._send_json({"quota": usage.to_dict()})
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

        if path == "/api/tools":
            registry = ToolRegistry()
            register_builtin_tools(registry)
            tools = [tool.to_dict() for tool in registry.list_tools()]
            self._send_json({"tools": tools})
            return

        if path == "/api/conversations":
            if current_user is not None and current_user.role != UserRole.ADMIN:
                conversations = [
                    conv.to_dict() for conv in self.app.store.list(user_id=current_user.id)
                ]
            else:
                conversations = [conv.to_dict() for conv in self.app.history()]
            self._send_json({"conversations": conversations})
            return

        if path.startswith("/api/conversations/"):
            conv_id = path.split("/")[-1]
            try:
                conv = self.app.load_conversation(conv_id)
                if conv.status == ConversationStatus.DELETED:
                    raise KeyError(conv_id)

                if current_user is not None and self.ownership_manager is not None:
                    self.ownership_manager.assert_access(current_user, conv.owner_id, action="read")
                elif current_user is not None and conv.owner_id is not None:
                    if conv.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
                        raise AccessDeniedError("Access to this conversation is denied")

                self._send_json({"conversation": conv.to_dict()})
            except AccessDeniedError as err:
                self._send_json({"error": str(err)}, HTTPStatus.FORBIDDEN)
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
        current_user = self._get_current_user()

        if path == "/api/auth/register":
            if self.auth_engine is None:
                self._send_json({"error": "Auth not configured"}, HTTPStatus.NOT_IMPLEMENTED)
                return
            username = body.get("username")
            email = body.get("email")
            password = body.get("password")
            role_str = body.get("role", "member")
            tier_str = body.get("tier", "free")
            if not username or not email or not password:
                self._send_json({"error": "Missing required fields (username, email, password)"}, HTTPStatus.BAD_REQUEST)
                return
            try:
                role = UserRole(role_str)
                tier = UserTier(tier_str)
                user = self.auth_engine.register_user(
                    username=username,
                    email=email,
                    password=password,
                    role=role,
                    tier=tier,
                )
                self._send_json({"user": user.to_dict()}, HTTPStatus.CREATED)
            except AuthError as err:
                self._send_json({"error": str(err)}, HTTPStatus.CONFLICT)
            except Exception as err:  # noqa: BLE001
                self._send_json({"error": str(err)}, HTTPStatus.BAD_REQUEST)
            return

        if path == "/api/auth/login":
            if self.auth_engine is None or self.session_manager is None:
                self._send_json({"error": "Auth not configured"}, HTTPStatus.NOT_IMPLEMENTED)
                return
            identifier = body.get("username") or body.get("email") or body.get("identifier")
            password = body.get("password")
            if not identifier or not password:
                self._send_json({"error": "Missing identifier or password"}, HTTPStatus.BAD_REQUEST)
                return
            try:
                user = self.auth_engine.authenticate_password(identifier, password)
                session, raw_token = self.session_manager.create_session(user.id)
                self._send_json(
                    {
                        "token": raw_token,
                        "session_id": session.session_id,
                        "user": user.to_dict(),
                    }
                )
            except AuthError as err:
                self._send_json({"error": str(err)}, HTTPStatus.UNAUTHORIZED)
            return

        if path == "/api/conversations":
            conv = self.app.new_conversation()
            if current_user is not None:
                conv.owner_id = current_user.id
                if self.ownership_manager is not None:
                    self.ownership_manager.register_resource("conversation", conv.id, current_user.id)
            self.app.store.save(conv)
            self._send_json({"conversation": conv.to_dict()}, HTTPStatus.CREATED)
            return

        if path == "/api/chat":
            text = body.get("text") or body.get("message")
            if not text:
                self._send_json({"error": "Missing 'text' in request body"}, HTTPStatus.BAD_REQUEST)
                return

            if current_user is not None and self.quota_manager is not None:
                try:
                    self.quota_manager.check_request_quota(current_user)
                    self.quota_manager.record_request(current_user)
                except QuotaExceededError as err:
                    self._send_json({"error": str(err)}, HTTPStatus.TOO_MANY_REQUESTS)
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

    def do_DELETE(self) -> None:
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        if self.app is None:
            self._send_json({"error": "App instance not bound"}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        current_user = self._get_current_user()

        if path == "/api/auth/account":
            if current_user is None:
                self._send_json({"error": "Unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            if self.lifecycle_manager is None:
                self._send_json({"error": "Account lifecycle manager not configured"}, HTTPStatus.NOT_IMPLEMENTED)
                return
            report = self.lifecycle_manager.delete_account(current_user.id, cascade=True)
            self._send_json({"status": "deleted", "report": report})
            return

        if path.startswith("/api/conversations/"):
            conv_id = path.split("/")[-1]
            try:
                conv = self.app.load_conversation(conv_id)
                if current_user is not None and self.ownership_manager is not None:
                    self.ownership_manager.assert_access(current_user, conv.owner_id, action="delete")
                elif current_user is not None and conv.owner_id is not None:
                    if conv.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
                        raise AccessDeniedError("Access to delete this conversation is denied")

                self.app.store.delete(conv_id)
                if self.ownership_manager is not None:
                    self.ownership_manager.unregister_resource("conversation", conv_id)
                self._send_json({"status": "deleted", "id": conv_id})
            except AccessDeniedError as err:
                self._send_json({"error": str(err)}, HTTPStatus.FORBIDDEN)
            except Exception as err:  # noqa: BLE001
                self._send_json({"error": str(err)}, HTTPStatus.NOT_FOUND)
            return

        self._send_json({"error": "Not Found"}, HTTPStatus.NOT_FOUND)


def create_web_server(
    app: ChadApp,
    host: str = "127.0.0.1",
    port: int = 8000,
    auth_engine: AuthEngine | None = None,
    session_manager: SessionManager | None = None,
    quota_manager: QuotaManager | None = None,
    ownership_manager: DataOwnershipManager | None = None,
    lifecycle_manager: AccountLifecycleManager | None = None,
) -> HTTPServer:
    class Handler(WebApiHandler):
        pass

    Handler.app = app
    Handler.auth_engine = auth_engine
    Handler.session_manager = session_manager
    Handler.quota_manager = quota_manager
    Handler.ownership_manager = ownership_manager
    Handler.lifecycle_manager = lifecycle_manager
    return HTTPServer((host, port), Handler)


def run_web(
    app: ChadApp,
    host: str = "127.0.0.1",
    port: int = 8000,
    auth_engine: AuthEngine | None = None,
    session_manager: SessionManager | None = None,
    quota_manager: QuotaManager | None = None,
    ownership_manager: DataOwnershipManager | None = None,
    lifecycle_manager: AccountLifecycleManager | None = None,
) -> None:
    server = create_web_server(
        app,
        host=host,
        port=port,
        auth_engine=auth_engine,
        session_manager=session_manager,
        quota_manager=quota_manager,
        ownership_manager=ownership_manager,
        lifecycle_manager=lifecycle_manager,
    )
    print(f"CHAD Web API server running at http://{host}:{port}")
    try:
        server.serve_forever()
    finally:
        server.server_close()
