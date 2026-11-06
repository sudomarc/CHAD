from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, ClassVar
from urllib.parse import urlparse

from chad.app import ChadApp
from chad.auth.lifecycle import AccountLifecycleManager
from chad.auth.models import Permission, User, UserRole
from chad.auth.ownership import AccessDeniedError, DataOwnershipManager
from chad.auth.quotas import QuotaExceededError, QuotaManager
from chad.auth.security import generate_salt, generate_user_id, hash_password, verify_password
from chad.auth.session import SessionManager
from chad.core.conversation import ConversationStatus
from chad.tools.builtin import register_builtin_tools
from chad.tools.registry import ToolRegistry


class WebApiHandler(BaseHTTPRequestHandler):
    app: ChadApp | None = None
    session_manager: SessionManager = SessionManager()
    ownership_manager: DataOwnershipManager = DataOwnershipManager()
    quota_manager: QuotaManager = QuotaManager()
    users: ClassVar[dict[str, User]] = {}  # user_id -> User
    users_by_username: ClassVar[dict[str, User]] = {}  # username -> User
    lifecycle_manager: AccountLifecycleManager = AccountLifecycleManager(
        session_manager, ownership_manager, users
    )

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
        content_length_header = self.headers.get("Content-Length")
        if not content_length_header:
            return {}
        try:
            content_length = int(content_length_header)
        except ValueError:
            return {}
        if content_length <= 0:
            return {}
        body = self.rfile.read(content_length)
        if not body:
            return {}
        try:
            return json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}

    def _get_current_user(self) -> User | None:
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            user_id = self.session_manager.validate_token(token)
            if user_id:
                return self.users.get(user_id)
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

        if path == "/api/auth/me":
            user = self._get_current_user()
            if not user:
                self._send_json({"error": "Unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            self._send_json({"user": user.to_dict()})
            return

        if path == "/api/auth/quota":
            user = self._get_current_user()
            if not user:
                self._send_json({"error": "Unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            self._send_json({"quotas": user.quotas.to_dict()})
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

        if path == "/api/tools":
            registry = ToolRegistry()
            register_builtin_tools(registry)
            tools = [tool.to_dict() for tool in registry.list_tools()]
            self._send_json({"tools": tools})
            return

        if path == "/api/conversations":
            user = self._get_current_user()
            all_convs = self.app.history()
            # If multi-user identity exists (any registered user), unauthenticated access is forbidden to owned resources
            if user:
                if user.role == UserRole.ADMIN:
                    filtered = [conv.to_dict() for conv in all_convs]
                else:
                    filtered = [
                        conv.to_dict()
                        for conv in all_convs
                        if self.ownership_manager.can_access(user, conv.id, "read")
                    ]
            elif self.users:
                # If users are registered, unauthenticated requests can only access unowned/public resources
                filtered = [
                    conv.to_dict()
                    for conv in all_convs
                    if self.ownership_manager.get_owner(conv.id) is None
                ]
            else:
                filtered = [conv.to_dict() for conv in all_convs]
            self._send_json({"conversations": filtered})
            return

        if path.startswith("/api/conversations/"):
            conv_id = path.split("/")[-1]
            user = self._get_current_user()
            owner = self.ownership_manager.get_owner(conv_id)
            if owner is not None:
                if not user:
                    self._send_json({"error": "Unauthorized"}, HTTPStatus.UNAUTHORIZED)
                    return
                try:
                    self.ownership_manager.require_access(user, conv_id, "read")
                except AccessDeniedError as e:
                    self._send_json({"error": str(e)}, HTTPStatus.FORBIDDEN)
                    return
            try:
                conv = self.app.load_conversation(conv_id)
                if conv.status == ConversationStatus.DELETED:
                    raise KeyError(conv_id)
                self._send_json({"conversation": conv.to_dict()})
            except Exception as err:  # noqa: BLE001
                self._send_json({"error": str(err)}, HTTPStatus.NOT_FOUND)
            return

        self._send_json({"error": "Not Found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        body = self._read_json()

        # Auth endpoints (do not require app instance)
        if path == "/api/auth/register":
            username = body.get("username")
            password = body.get("password")
            email = body.get("email")
            role_val = body.get("role", "member")

            if not username or not password:
                self._send_json({"error": "Missing username or password"}, HTTPStatus.BAD_REQUEST)
                return

            if username in self.users_by_username:
                self._send_json({"error": "Username already exists"}, HTTPStatus.CONFLICT)
                return

            try:
                role = UserRole(role_val)
            except ValueError:
                role = UserRole.MEMBER

            salt = generate_salt()
            pwd_hash = hash_password(password, salt)
            user_id = generate_user_id()
            user = User(
                id=user_id,
                username=username,
                password_hash=pwd_hash,
                salt=salt,
                role=role,
                email=email,
            )
            self.users[user_id] = user
            self.users_by_username[username] = user
            session = self.session_manager.create_session(user)
            self._send_json(
                {
                    "user": user.to_dict(),
                    "token": session.token,
                },
                HTTPStatus.CREATED,
            )
            return

        if path == "/api/auth/login":
            username = body.get("username")
            password = body.get("password")
            if not username or not password:
                self._send_json({"error": "Missing username or password"}, HTTPStatus.BAD_REQUEST)
                return

            user = self.users_by_username.get(username)
            if not user or not verify_password(password, user.salt, user.password_hash):
                self._send_json({"error": "Invalid credentials"}, HTTPStatus.UNAUTHORIZED)
                return

            if not user.is_active:
                self._send_json({"error": "Account is inactive"}, HTTPStatus.FORBIDDEN)
                return

            session = self.session_manager.create_session(user)
            self._send_json(
                {
                    "user": user.to_dict(),
                    "token": session.token,
                }
            )
            return

        if self.app is None:
            self._send_json({"error": "App instance not bound"}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        user = self._get_current_user()

        if path == "/api/conversations":
            if user and not user.has_permission(Permission.CONVERSATION_CREATE):
                self._send_json({"error": "Permission denied"}, HTTPStatus.FORBIDDEN)
                return

            conv = self.app.new_conversation()
            self.app.store.save(conv)
            if user:
                self.ownership_manager.assign_owner(conv.id, user.id)
            self._send_json({"conversation": conv.to_dict()}, HTTPStatus.CREATED)
            return

        if path == "/api/chat":
            if user:
                try:
                    self.quota_manager.require_rate_limit(user)
                except QuotaExceededError as qe:
                    self._send_json({"error": str(qe)}, HTTPStatus.TOO_MANY_REQUESTS)
                    return

            text = body.get("text") or body.get("message")
            if not text:
                self._send_json({"error": "Missing 'text' in request body"}, HTTPStatus.BAD_REQUEST)
                return
            try:
                response = self.app.send(text)
                if user:
                    # Estimate tokens (e.g. prompt length // 4 + response length // 4)
                    est_tokens = max(1, (len(text) + len(response)) // 4)
                    self.quota_manager.record_tokens(user, est_tokens)
                self._send_json(
                    {
                        "response": response,
                        "conversation": self.app.conversation.to_dict(),
                    }
                )
            except QuotaExceededError as qe:
                self._send_json({"error": str(qe)}, HTTPStatus.TOO_MANY_REQUESTS)
            except Exception as err:  # noqa: BLE001
                self._send_json({"error": str(err)}, HTTPStatus.BAD_REQUEST)
            return

        self._send_json({"error": "Not Found"}, HTTPStatus.NOT_FOUND)

    def do_DELETE(self) -> None:
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        if path == "/api/auth/account":
            user = self._get_current_user()
            if not user:
                self._send_json({"error": "Unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return
            # Remove username lookup
            self.users_by_username.pop(user.username, None)
            result = self.lifecycle_manager.delete_account(user.id)
            self._send_json({"status": "deleted", "result": result})
            return

        if self.app is None:
            self._send_json({"error": "App instance not bound"}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if path.startswith("/api/conversations/"):
            conv_id = path.split("/")[-1]
            user = self._get_current_user()
            owner = self.ownership_manager.get_owner(conv_id)
            if owner is not None:
                if not user:
                    self._send_json({"error": "Unauthorized"}, HTTPStatus.UNAUTHORIZED)
                    return
                try:
                    self.ownership_manager.require_access(user, conv_id, "delete")
                except AccessDeniedError as e:
                    self._send_json({"error": str(e)}, HTTPStatus.FORBIDDEN)
                    return
            try:
                self.app.store.delete(conv_id)
                self.ownership_manager.remove_resource(conv_id)
                self._send_json({"status": "deleted", "id": conv_id})
            except Exception as err:  # noqa: BLE001
                self._send_json({"error": str(err)}, HTTPStatus.NOT_FOUND)
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
