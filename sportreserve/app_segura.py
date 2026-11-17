"""Aplicación refactorizada y endurecida de SportReserve Co. (Actividad 4 — Hardening)."""

from __future__ import annotations

import re
import sqlite3
from flask import Flask, Response, abort, jsonify, request
from markupsafe import escape

from sportreserve.init_db import init_reservas_db

EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def get_db_connection(db_path: str) -> sqlite3.Connection:
    """Abre conexión SQLite3 configurada con filas tipo diccionario."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def create_secure_app(db_path: str = "reservas.db") -> Flask:
    """Construye la aplicación segura de SportReserve Co. mitigando SQLi, IDOR y XSS."""
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024
    init_reservas_db(db_path)

    @app.after_request
    def set_security_headers(response: Response) -> Response:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'none'; object-src 'none'; frame-ancestors 'none'"
        )
        return response

    @app.route("/api/reserva", methods=["GET"])
    def obtener_reserva() -> tuple[Response, int]:
        id_reserva = request.args.get("id")
        user_id_session = request.args.get("user_id")  # ID proveniente del token/sesión

        # Validación positiva de entrada (RE-04)
        if (
            not id_reserva
            or not id_reserva.isdigit()
            or not user_id_session
            or not user_id_session.isdigit()
        ):
            return jsonify({"error": "Parámetros inválidos o sesión no provista"}), 400

        conn = get_db_connection(app.config["DB_PATH"])
        try:
            cursor = conn.cursor()
            # 1. Corrección SQLi (RE-02): Consulta parametrizada (Prepared Statement)
            query = "SELECT * FROM reservas WHERE id = ?"
            reserva = cursor.execute(query, (int(id_reserva),)).fetchone()
        finally:
            conn.close()

        if reserva is None:
            return jsonify({"error": "Reserva no encontrada"}), 404

        # 2. Corrección IDOR (RE-01): Validación estricta de propiedad en servidor
        if int(reserva["user_id"]) != int(user_id_session):
            abort(403, description="Acceso denegado: la reserva pertenece a otro usuario.")

        return jsonify({"reserva": dict(reserva)}), 200

    @app.route("/api/usuarios/buscar", methods=["GET"])
    def buscar_usuario_por_correo() -> tuple[Response, int]:
        correo = (request.args.get("correo") or "").strip().lower()
        if not correo or len(correo) > 150 or not EMAIL_PATTERN.match(correo):
            return jsonify({"error": "Formato de correo electrónico inválido"}), 400

        conn = get_db_connection(app.config["DB_PATH"])
        try:
            cursor = conn.cursor()
            # Corrección SQLi (Hallazgo B / RE-02): Sentencia parametrizada
            filas = cursor.execute(
                "SELECT id, nombre, correo FROM usuarios WHERE correo = ?",
                (correo,),
            ).fetchall()
        finally:
            conn.close()

        return jsonify({"resultados": [dict(f) for f in filas]}), 200

    @app.route("/comentarios", methods=["GET", "POST"])
    def gestionar_comentarios() -> tuple[str, int]:
        conn = get_db_connection(app.config["DB_PATH"])
        try:
            cursor = conn.cursor()
            if request.method == "POST":
                autor = (request.form.get("nombre") or "").strip()
                contenido = (request.form.get("comentario") or "").strip()
                if not 2 <= len(autor) <= 80 or not 1 <= len(contenido) <= 500:
                    return jsonify({"error": "Nombre o comentario fuera de rango"}), 400
                cursor.execute(
                    "INSERT INTO comentarios (user_id, autor, contenido) VALUES (1, ?, ?)",
                    (autor, contenido),
                )
                conn.commit()

            comentarios = cursor.execute(
                "SELECT autor, contenido FROM comentarios ORDER BY id DESC"
            ).fetchall()
        finally:
            conn.close()

        # 3. Corrección XSS (Hallazgo C / RE-03): Escapado contextual con markupsafe.escape()
        nombre_seguro = escape((request.args.get("nombre") or "Invitado").strip()[:80])
        items_html = "".join(
            f"<li><strong>{escape(c['autor'])}:</strong> {escape(c['contenido'])}</li>"
            for c in comentarios
        )
        html = (
            "<!DOCTYPE html><html lang='es'><head><meta charset='utf-8'></head><body>"
            f"<h1>Portal SportReserve - Hola {nombre_seguro}</h1><ul>{items_html}</ul>"
            "</body></html>"
        )
        return html, 200

    @app.errorhandler(403)
    def handle_forbidden(error) -> tuple[Response, int]:
        return jsonify({"error": str(error.description)}), 403

    return app


if __name__ == "__main__":
    secure_app = create_secure_app()
    secure_app.run(host="127.0.0.1", port=5002, debug=False)
