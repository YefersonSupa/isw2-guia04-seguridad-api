"""Aplicación Flask principal para la API de Gestión de Tareas (Guía 04 - Equipo 05)."""

from __future__ import annotations

import os
import time
from typing import Callable, Optional

from flask import Flask, Response, jsonify, render_template, request

from task_api.auth_service import (
    MailSender,
    authenticate_session,
    change_password,
    confirm_password_reset,
    login_user,
    logout_user,
    register_user,
    request_password_reset,
)
from task_api.db import db_session, init_db
from task_api.security import SecurityConfig
from task_api.tasks_service import create_task, delete_task, list_tasks, update_task


def _extract_bearer_token() -> Optional[str]:
    """Extrae el token Bearer del encabezado Authorization de forma segura."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:].strip()
    return token or None


def _register_auth_routes(
    app: Flask,
    resolved_db: str,
    cfg: SecurityConfig,
    now_fn: Callable[[], int],
    mail_sender: Optional[MailSender],
) -> None:
    """Registra los endpoints de autenticación y manejo de sesiones en la app Flask."""

    @app.route("/auth/register", methods=["POST"])
    def register_endpoint() -> tuple[Response, int]:
        body = request.get_json(silent=True) or {}
        if not isinstance(body, dict):
            return jsonify({"error": "Cuerpo JSON inválido."}), 400
        allowed = {"email", "full_name", "password"}
        extra = set(body.keys()) - allowed
        with db_session(resolved_db) as conn:
            res = register_user(
                conn,
                body.get("email"),
                body.get("full_name"),
                body.get("password"),
                request.remote_addr or "127.0.0.1",
                now_fn(),
                extra_fields=extra if extra else None,
            )
        return jsonify(res.payload), res.status_code

    @app.route("/auth/login", methods=["POST"])
    def login_endpoint() -> tuple[Response, int]:
        body = request.get_json(silent=True) or {}
        if not isinstance(body, dict):
            return jsonify({"error": "Cuerpo JSON inválido."}), 400
        prev_token = _extract_bearer_token()
        with db_session(resolved_db) as conn:
            res = login_user(
                conn,
                body.get("email"),
                body.get("password"),
                request.remote_addr or "127.0.0.1",
                prev_token,
                cfg,
                now_fn(),
            )
        response = jsonify(res.payload)
        if res.status_code == 429 and "retry_after" in res.payload:
            response.headers["Retry-After"] = str(res.payload["retry_after"])
        return response, res.status_code

    @app.route("/auth/logout", methods=["POST"])
    def logout_endpoint() -> tuple[Response, int]:
        token = _extract_bearer_token()
        with db_session(resolved_db) as conn:
            res = logout_user(conn, token, request.remote_addr or "127.0.0.1", now_fn())
        return jsonify(res.payload), res.status_code

    @app.route("/auth/change-password", methods=["POST"])
    def change_password_endpoint() -> tuple[Response, int]:
        body = request.get_json(silent=True) or {}
        if not isinstance(body, dict):
            return jsonify({"error": "Cuerpo JSON inválido."}), 400
        token = _extract_bearer_token()
        with db_session(resolved_db) as conn:
            res = change_password(
                conn,
                token,
                body.get("current_password"),
                body.get("new_password"),
                request.remote_addr or "127.0.0.1",
                now_fn(),
            )
        return jsonify(res.payload), res.status_code

    @app.route("/auth/forgot-password", methods=["POST"])
    def forgot_password_endpoint() -> tuple[Response, int]:
        body = request.get_json(silent=True) or {}
        if not isinstance(body, dict):
            return jsonify({"error": "Cuerpo JSON inválido."}), 400
        with db_session(resolved_db) as conn:
            res = request_password_reset(
                conn,
                body.get("email"),
                request.remote_addr or "127.0.0.1",
                cfg,
                now_fn(),
                mail_sender=mail_sender,
            )
        return jsonify(res.payload), res.status_code

    @app.route("/auth/reset-password", methods=["POST"])
    def reset_password_endpoint() -> tuple[Response, int]:
        body = request.get_json(silent=True) or {}
        if not isinstance(body, dict):
            return jsonify({"error": "Cuerpo JSON inválido."}), 400
        with db_session(resolved_db) as conn:
            res = confirm_password_reset(
                conn,
                body.get("token"),
                body.get("new_password"),
                request.remote_addr or "127.0.0.1",
                now_fn(),
            )
        return jsonify(res.payload), res.status_code

    @app.route("/auth/me", methods=["GET"])
    def me_endpoint() -> tuple[Response, int]:
        token = _extract_bearer_token()
        with db_session(resolved_db) as conn:
            session = authenticate_session(conn, token, now_fn())
        if not session:
            return jsonify({"error": "Acceso no autorizado. Sesión inválida o expirada."}), 401
        return jsonify(
            {
                "session_id": session["session_id"],
                "user": {
                    "id": session["user_id"],
                    "email": session["email"],
                    "full_name": session["full_name"],
                    "role": session["role"],
                },
            }
        ), 200


def _register_task_routes(
    app: Flask,
    resolved_db: str,
    now_fn: Callable[[], int],
) -> None:
    """Registra los endpoints CRUD seguros de gestión de tareas."""

    @app.route("/tasks", methods=["GET"])
    def list_tasks_endpoint() -> tuple[Response, int]:
        token = _extract_bearer_token()
        search_term = request.args.get("search")
        with db_session(resolved_db) as conn:
            res = list_tasks(conn, token, search_term, now_fn())
        return jsonify(res.payload), res.status_code

    @app.route("/tasks", methods=["POST"])
    def create_task_endpoint() -> tuple[Response, int]:
        body = request.get_json(silent=True)
        token = _extract_bearer_token()
        with db_session(resolved_db) as conn:
            res = create_task(
                conn,
                token,
                body,
                request.remote_addr or "127.0.0.1",
                now_fn(),
            )
        return jsonify(res.payload), res.status_code

    @app.route("/tasks/<int:task_id>", methods=["PUT"])
    def update_task_endpoint(task_id: int) -> tuple[Response, int]:
        body = request.get_json(silent=True)
        token = _extract_bearer_token()
        with db_session(resolved_db) as conn:
            res = update_task(
                conn,
                token,
                task_id,
                body,
                request.remote_addr or "127.0.0.1",
                now_fn(),
            )
        return jsonify(res.payload), res.status_code

    @app.route("/tasks/<int:task_id>", methods=["DELETE"])
    def delete_task_endpoint(task_id: int) -> tuple[Response, int]:
        token = _extract_bearer_token()
        with db_session(resolved_db) as conn:
            res = delete_task(
                conn,
                token,
                task_id,
                request.remote_addr or "127.0.0.1",
                now_fn(),
            )
        return jsonify(res.payload), res.status_code


def create_app(
    db_path: Optional[str] = None,
    security_config: Optional[SecurityConfig] = None,
    time_provider: Optional[Callable[[], int]] = None,
    mail_sender: Optional[MailSender] = None,
) -> Flask:
    """Construye y configura la instancia Flask con controles de seguridad de sesión."""
    app = Flask(__name__)
    resolved_db = db_path or os.environ.get("TASK_API_DB", "task_api.db")
    cfg = security_config or SecurityConfig()
    now_fn = time_provider or (lambda: int(time.time()))

    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024  # 16 KiB máximo por solicitud JSON
    app.config["DB_PATH"] = resolved_db
    init_db(resolved_db)

    @app.after_request
    def apply_security_headers(response: Response) -> Response:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-store"
        if request.path.startswith("/auth/") or request.path.startswith("/tasks"):
            response.headers["Content-Security-Policy"] = "default-src 'none'"
        else:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self'; style-src 'self'; "
                "img-src 'self'; connect-src 'self'; frame-ancestors 'none'; "
                "base-uri 'self'; form-action 'self'"
            )
        return response

    @app.route("/", methods=["GET"])
    def index_page() -> str:
        """Sirve la interfaz web interactiva para probar el módulo de autenticación y tareas."""
        return render_template("index.html")

    _register_auth_routes(app, resolved_db, cfg, now_fn, mail_sender)
    _register_task_routes(app, resolved_db, now_fn)
    return app


def _console_mail_preview(email: str, raw_token: str) -> None:
    """Imprime el correo simulado solo en consola local (nunca en HTTP ni audit_logs)."""
    print(f"[DEV MAILBOX] Destinatario: {email} | Token de recuperación (1 uso): {raw_token}")


if __name__ == "__main__":
    application = create_app(mail_sender=_console_mail_preview)
    application.run(host="127.0.0.1", port=5000, debug=False)
