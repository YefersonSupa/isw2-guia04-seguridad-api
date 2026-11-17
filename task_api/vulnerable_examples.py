"""Ejemplos deliberadamente inseguros ('Antes') para contraste en Ejercicios 3.1 y 4.1.

ADVERTENCIA: No desplegar en producción. Sirve únicamente para evidenciar el riesgo
antes de aplicar validación positiva (Ej. 3.1) y consultas parametrizadas (Ej. 4.1).
"""

from __future__ import annotations

import sqlite3
from flask import Flask, jsonify, request

from task_api.db import init_db


def create_vulnerable_tasks_app(db_path: str) -> Flask:
    """Crea una instancia Flask con endpoints deliberadamente vulnerables para contraste."""
    app = Flask(__name__)
    init_db(db_path)

    @app.route("/vulnerable/tasks", methods=["POST"])
    def vulnerable_create_task():
        """Ejercicio 3.1 (Paso 2): Acepta cualquier dato sin validar longitud, estado ni campos."""
        data = request.get_json(silent=True) or {}
        title = str(data.get("title", ""))
        description = str(data.get("description", ""))
        status = str(data.get("status", "pendiente"))
        owner_id = int(data.get("owner_id", 1))
        role_injected = data.get("role")  # Mass assignment aceptado sin rechazo

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = OFF;")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tasks (title, description, status, owner_id, created_at) "
            "VALUES (?, ?, ?, ?, 0)",
            (title, description, "pendiente" if status not in {
                "pendiente", "en_progreso", "completada"
            } else status, owner_id),
        )
        conn.commit()
        task_id = cursor.lastrowid
        conn.close()
        return jsonify({
            "id": task_id,
            "title": title,
            "description": description,
            "status_recibido": status,
            "owner_id": owner_id,
            "role_inyectado": role_injected,
        }), 201

    @app.route("/vulnerable/tasks/search", methods=["GET"])
    def vulnerable_search_tasks():
        """Ejercicio 4.1 (Paso 1): Búsqueda vulnerable por concatenación directa de cadenas."""
        search = request.args.get("search", "")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # Código inseguro literal de la Guía 04 (pág. 11)
        query = "SELECT * FROM tasks WHERE title LIKE '%" + search + "%'"
        rows = cursor.execute(query).fetchall()
        conn.close()
        return jsonify({"tasks": [dict(r) for r in rows]}), 200

    return app
