"""Servicios seguros para gestión de tareas (CRUD, validación positiva y control IDOR)."""

from __future__ import annotations

import logging
import re
import sqlite3
from typing import Optional

from task_api.auth_service import ServiceResult, authenticate_session
from task_api.security import log_security_event

LOGGER = logging.getLogger("task_api.security")
ALLOWED_TASK_STATUSES = {"pendiente", "en_progreso", "completada"}
ALLOWED_TASK_FIELDS = {"title", "description", "status"}
SEARCH_SAFE_REGEX = re.compile(r"^[\w\sáéíóúÁÉÍÓÚñÑ.,\-_@#()]{0,100}$")


def _validate_title(raw_title: object) -> tuple[Optional[str], Optional[ServiceResult]]:
    if not isinstance(raw_title, str) or not 3 <= len(raw_title.strip()) <= 120:
        return None, ServiceResult(
            400,
            {"error": "El título es obligatorio y debe tener entre 3 y 120 caracteres."},
        )
    return raw_title.strip(), None


def _validate_description(raw_desc: object) -> tuple[Optional[str], Optional[ServiceResult]]:
    if raw_desc is None:
        return "", None
    if not isinstance(raw_desc, str) or len(raw_desc.strip()) > 1000:
        return None, ServiceResult(
            400,
            {"error": "La descripción no puede superar los 1000 caracteres."},
        )
    return raw_desc.strip(), None


def _validate_status(raw_status: object) -> tuple[Optional[str], Optional[ServiceResult]]:
    if not isinstance(raw_status, str) or raw_status.strip() not in ALLOWED_TASK_STATUSES:
        return None, ServiceResult(
            400,
            {"error": "Estado inválido. Permitidos: pendiente, en_progreso, completada."},
        )
    return raw_status.strip(), None


_FIELD_VALIDATORS = (
    ("title", _validate_title, None),
    ("description", _validate_description, ""),
    ("status", _validate_status, "pendiente"),
)


def _validate_task_payload(
    body: object,
    require_title: bool,
) -> tuple[Optional[dict[str, str]], Optional[str], Optional[ServiceResult]]:
    """Valida entrada positiva de tareas sin almacenar payloads maliciosos en logs."""
    if not isinstance(body, dict):
        return None, "body", ServiceResult(400, {"error": "Cuerpo JSON inválido."})

    extra_fields = set(body.keys()) - ALLOWED_TASK_FIELDS
    if extra_fields:
        first_extra = sorted(extra_fields)[0]
        return (
            None,
            f"extra_field:{first_extra}",
            ServiceResult(400, {"error": "Campos no permitidos en la solicitud."}),
        )

    cleaned: dict[str, str] = {}
    for field_name, validator, default_val in _FIELD_VALIDATORS:
        if field_name in body or (require_title and default_val is None):
            val, err = validator(body.get(field_name))
            if err or val is None:
                return None, field_name, err
            cleaned[field_name] = val
        elif require_title and default_val is not None:
            cleaned[field_name] = default_val

    if not cleaned:
        return (
            None,
            "empty_update",
            ServiceResult(400, {"error": "Debe indicar al menos un campo válido a actualizar."}),
        )
    return cleaned, None, None


def create_task(
    conn: sqlite3.Connection,
    raw_token: Optional[str],
    body: object,
    ip_address: str,
    now: int,
) -> ServiceResult:
    """Crea una tarea asignando el dueño (owner_id) exclusivamente desde la sesión."""
    session = authenticate_session(conn, raw_token, now)
    if not session:
        return ServiceResult(401, {"error": "Acceso no autorizado. Sesión inválida o expirada."})

    cleaned, failed_param, err = _validate_task_payload(body, require_title=True)
    if err or cleaned is None:
        LOGGER.warning("Validación fallida en POST /tasks [param=%s]", failed_param)
        log_security_event(
            conn,
            "TASK_VALIDATION_FAILED",
            session["email"],
            ip_address,
            f"Regla de validación rechazada en parámetro: {failed_param}",
            now,
        )
        return err  # type: ignore[return-value]

    cursor = conn.execute(
        """
        INSERT INTO tasks (title, description, status, owner_id, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            cleaned["title"],
            cleaned["description"],
            cleaned["status"],
            session["user_id"],
            now,
        ),
    )
    task_id = cursor.lastrowid
    row = conn.execute(
        "SELECT id, title, description, status, owner_id, created_at FROM tasks WHERE id = ?",
        (task_id,),
    ).fetchone()
    return ServiceResult(201, {"message": "Tarea creada correctamente.", "task": dict(row)})


def list_tasks(
    conn: sqlite3.Connection,
    raw_token: Optional[str],
    search_query: Optional[str],
    now: int,
) -> ServiceResult:
    """Lista tareas del usuario autenticado aplicando búsqueda SQL parametrizada."""
    session = authenticate_session(conn, raw_token, now)
    if not session:
        return ServiceResult(401, {"error": "Acceso no autorizado. Sesión inválida o expirada."})

    term = (search_query or "").strip()
    if len(term) > 100 or (term and not SEARCH_SAFE_REGEX.match(term)):
        return ServiceResult(
            400,
            {"error": "El parámetro de búsqueda contiene caracteres o longitud inválidos."},
        )

    escaped_term = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    like_pattern = f"%{escaped_term}%"

    if session["role"] == "administrador":
        rows = conn.execute(
            """
            SELECT id, title, description, status, owner_id, created_at
            FROM tasks
            WHERE title LIKE ? ESCAPE '\\'
            ORDER BY id DESC
            """,
            (like_pattern,),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT id, title, description, status, owner_id, created_at
            FROM tasks
            WHERE owner_id = ? AND title LIKE ? ESCAPE '\\'
            ORDER BY id DESC
            """,
            (session["user_id"], like_pattern),
        ).fetchall()

    return ServiceResult(200, {"tasks": [dict(r) for r in rows]})


def update_task(
    conn: sqlite3.Connection,
    raw_token: Optional[str],
    task_id: int,
    body: object,
    ip_address: str,
    now: int,
) -> ServiceResult:
    """Actualiza una tarea verificando propiedad en servidor (previene IDOR con HTTP 403)."""
    session = authenticate_session(conn, raw_token, now)
    if not session:
        return ServiceResult(401, {"error": "Acceso no autorizado. Sesión inválida o expirada."})

    existing = conn.execute(
        "SELECT id, title, description, status, owner_id, created_at FROM tasks WHERE id = ?",
        (task_id,),
    ).fetchone()
    if not existing:
        return ServiceResult(404, {"error": "Tarea no encontrada."})

    if existing["owner_id"] != session["user_id"] and session["role"] != "administrador":
        log_security_event(
            conn,
            "IDOR_TASK_UPDATE_DENIED",
            session["email"],
            ip_address,
            f"Acceso denegado sobre tarea id={task_id}",
            now,
        )
        return ServiceResult(403, {"error": "Acceso denegado. No es propietario de la tarea."})

    cleaned, failed_param, err = _validate_task_payload(body, require_title=False)
    if err or cleaned is None:
        LOGGER.warning("Validación fallida en PUT /tasks [param=%s]", failed_param)
        return err  # type: ignore[return-value]

    new_title = cleaned.get("title", existing["title"])
    new_desc = cleaned.get("description", existing["description"])
    new_status = cleaned.get("status", existing["status"])

    conn.execute(
        "UPDATE tasks SET title = ?, description = ?, status = ? WHERE id = ?",
        (new_title, new_desc, new_status, task_id),
    )
    updated = conn.execute(
        "SELECT id, title, description, status, owner_id, created_at FROM tasks WHERE id = ?",
        (task_id,),
    ).fetchone()
    return ServiceResult(200, {"message": "Tarea actualizada.", "task": dict(updated)})


def delete_task(
    conn: sqlite3.Connection,
    raw_token: Optional[str],
    task_id: int,
    ip_address: str,
    now: int,
) -> ServiceResult:
    """Elimina una tarea validando propiedad en servidor y registrando auditoría."""
    session = authenticate_session(conn, raw_token, now)
    if not session:
        return ServiceResult(401, {"error": "Acceso no autorizado. Sesión inválida o expirada."})

    existing = conn.execute(
        "SELECT id, owner_id FROM tasks WHERE id = ?",
        (task_id,),
    ).fetchone()
    if not existing:
        return ServiceResult(404, {"error": "Tarea no encontrada."})

    if existing["owner_id"] != session["user_id"] and session["role"] != "administrador":
        log_security_event(
            conn,
            "IDOR_TASK_DELETE_DENIED",
            session["email"],
            ip_address,
            f"Intento de eliminación no autorizado sobre tarea id={task_id}",
            now,
        )
        return ServiceResult(403, {"error": "Acceso denegado. No es propietario de la tarea."})

    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    log_security_event(
        conn,
        "TASK_DELETED",
        session["email"],
        ip_address,
        f"Tarea eliminada id={task_id}",
        now,
    )
    return ServiceResult(200, {"message": "Tarea eliminada correctamente."})
