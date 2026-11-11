"""Pruebas unitarias y negativas para gestión segura de tareas (/tasks)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from task_api.app import create_app
from task_api.security import SecurityConfig


def _register_and_login(client, email: str, full_name: str, password: str = "ClaveSegura123") -> str:
    reg = client.post(
        "/auth/register",
        json={"email": email, "full_name": full_name, "password": password},
    )
    assert reg.status_code == 201
    login = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    return login.get_json()["access_token"]


def test_create_task_validation_extra_fields_and_safe_logs(tmp_path: Path) -> None:
    """Valida autenticación, longitudes, estados, rechazo de campos extra y logs OWASP."""
    db_file = str(tmp_path / "tasks.db")
    app = create_app(db_path=db_file, security_config=SecurityConfig())
    client = app.test_client()

    # Sin token -> HTTP 401
    no_auth = client.post("/tasks", json={"title": "Tarea sin sesión"})
    assert no_auth.status_code == 401

    token = _register_and_login(client, "usera@unsaac.edu.pe", "Usuario A")
    headers = {"Authorization": f"Bearer {token}"}

    # Título vacío / demasiado corto o largo -> HTTP 400
    assert client.post("/tasks", json={"title": "ab"}, headers=headers).status_code == 400
    assert (
        client.post("/tasks", json={"title": "x" * 121}, headers=headers).status_code == 400
    )

    # Estado inválido -> HTTP 400
    assert (
        client.post(
            "/tasks",
            json={"title": "Tarea válida", "status": "archivada"},
            headers=headers,
        ).status_code
        == 400
    )

    # Campo inyectado no esperado (owner_id / role) -> HTTP 400 y log sin payload completo
    malicious_title = "INJECTION_MARKER_DO_NOT_LOG"
    r_extra = client.post(
        "/tasks",
        json={"title": malicious_title, "owner_id": 999},
        headers=headers,
    )
    assert r_extra.status_code == 400

    conn = sqlite3.connect(db_file)
    logs = conn.execute(
        "SELECT event_type, detail FROM audit_logs WHERE event_type = 'TASK_VALIDATION_FAILED'"
    ).fetchall()
    conn.close()
    assert len(logs) == 4
    assert "extra_field:owner_id" in logs[-1][1]
    assert malicious_title not in " ".join(row[1] for row in logs)

    # Creación válida con Unicode y espacios
    r_ok = client.post(
        "/tasks",
        json={
            "title": "  Revisión STRIDE — Sesión 04  ",
            "description": "Validar límites de confianza en Cusco",
            "status": "en_progreso",
        },
        headers=headers,
    )
    assert r_ok.status_code == 201
    created = r_ok.get_json()["task"]
    assert created["title"] == "Revisión STRIDE — Sesión 04"
    assert created["status"] == "en_progreso"


def test_tasks_idor_protection_and_parameterized_search(tmp_path: Path) -> None:
    """Verifica bloqueo IDOR (HTTP 403) y búsqueda resistente a inyección SQL."""
    db_file = str(tmp_path / "tasks_idor.db")
    app = create_app(db_path=db_file, security_config=SecurityConfig())
    client = app.test_client()

    tok_a = _register_and_login(client, "dueno@unsaac.edu.pe", "Dueño A")
    tok_b = _register_and_login(client, "otro@unsaac.edu.pe", "Usuario B")

    h_a = {"Authorization": f"Bearer {tok_a}"}
    h_b = {"Authorization": f"Bearer {tok_b}"}

    created = client.post(
        "/tasks",
        json={"title": "Informe de Seguridad 100%", "description": "Privado"},
        headers=h_a,
    ).get_json()["task"]
    task_id = created["id"]

    # Usuario B no ve tareas de Usuario A y no puede editar ni eliminar (HTTP 403)
    assert client.get("/tasks", headers=h_b).get_json()["tasks"] == []
    assert (
        client.put(f"/tasks/{task_id}", json={"status": "completada"}, headers=h_b).status_code
        == 403
    )
    assert client.delete(f"/tasks/{task_id}", headers=h_b).status_code == 403

    # Búsqueda con intento SQLi -> rechazado con HTTP 400 por caracteres inválidos
    sqli_resp = client.get("/tasks?search=' OR '1'='1", headers=h_a)
    assert sqli_resp.status_code == 400

    # Búsqueda válida con comodín '%' escapado y búsqueda normal
    pct_resp = client.get("/tasks?search=100", headers=h_a)
    assert pct_resp.status_code == 200
    assert len(pct_resp.get_json()["tasks"]) == 1

    # Dueño actualiza y luego elimina con éxito
    assert (
        client.put(f"/tasks/{task_id}", json={"status": "completada"}, headers=h_a).status_code
        == 200
    )
    assert client.delete(f"/tasks/{task_id}", headers=h_a).status_code == 200
