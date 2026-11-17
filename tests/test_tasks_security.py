"""Pruebas unitarias y negativas para gestión segura de tareas (/tasks — Ej. 3.1, 4.1 y RBAC)."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from task_api.app import create_app
from task_api.security import SecurityConfig
from task_api.vulnerable_examples import create_vulnerable_tasks_app


def _register_and_login(
    client,
    email: str,
    full_name: str,
    password: str = "ClaveSegura123",
) -> str:
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


def test_vulnerable_tasks_before_hardening(tmp_path: Path) -> None:
    """Contraste 'Antes' (Ej. 3.1 y 4.1): muestra mass assignment y SQLi por concatenación."""
    db_file = str(tmp_path / "vuln_tasks.db")
    client = create_vulnerable_tasks_app(db_file).test_client()

    # Versión insegura acepta campo vacío, estado inválido y role='admin' sin rechazo
    r_bad = client.post(
        "/vulnerable/tasks",
        json={"title": "", "status": "hacked", "role": "admin", "owner_id": 1},
    )
    assert r_bad.status_code == 201
    assert r_bad.get_json()["role_inyectado"] == "admin"

    client.post("/vulnerable/tasks", json={"title": "Secreto Docente", "owner_id": 2})

    # Búsqueda insegura con concatenación SQL vulnerable a %' OR 1=1 --
    r_sqli = client.get("/vulnerable/tasks/search?search=noexiste%25'%20OR%201=1%20--")
    assert r_sqli.status_code == 200
    assert len(r_sqli.get_json()["tasks"]) >= 2


def test_create_task_validation_extra_fields_and_safe_logs(tmp_path: Path) -> None:
    """Ej. 3.1: valida vacío, largo, payload excesivo, estado, role=admin, Unicode y logs OWASP."""
    db_file = str(tmp_path / "tasks.db")
    app = create_app(db_path=db_file, security_config=SecurityConfig())
    client = app.test_client()

    # 1) Solicitud sin token de autenticación -> HTTP 401
    assert client.post("/tasks", json={"title": "Tarea sin sesión"}).status_code == 401

    token = _register_and_login(client, "usera@unsaac.edu.pe", "Usuario A")
    headers = {"Authorization": f"Bearer {token}"}

    # 2) Campo vacío / demasiado corto y demasiado largo -> HTTP 400
    assert client.post("/tasks", json={"title": ""}, headers=headers).status_code == 400
    assert client.post("/tasks", json={"title": "   "}, headers=headers).status_code == 400
    assert client.post("/tasks", json={"title": "x" * 121}, headers=headers).status_code == 400
    assert (
        client.post(
            "/tasks",
            json={"title": "Título válido", "description": "d" * 1001},
            headers=headers,
        ).status_code
        == 400
    )

    # 3) Límite de tamaño global de solicitud (MAX_CONTENT_LENGTH = 16 KiB) -> HTTP 413
    oversized = client.post(
        "/tasks",
        data='{"title":"ok","description":"' + ("A" * 20_000) + '"}',
        content_type="application/json",
        headers=headers,
    )
    assert oversized.status_code == 413

    # 4) Valor de estado inválido -> HTTP 400
    assert (
        client.post(
            "/tasks",
            json={"title": "Tarea válida", "status": "archivada"},
            headers=headers,
        ).status_code
        == 400
    )

    # 5) Campo adicional inyectado (role: 'admin' y owner_id) -> HTTP 400 y log sin payload
    malicious_title = "INJECTION_MARKER_DO_NOT_LOG"
    assert (
        client.post(
            "/tasks",
            json={"title": malicious_title, "role": "admin"},
            headers=headers,
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/tasks",
            json={"title": malicious_title, "owner_id": 999},
            headers=headers,
        ).status_code
        == 400
    )

    conn = sqlite3.connect(db_file)
    logs = conn.execute(
        "SELECT event_type, detail FROM audit_logs WHERE event_type = 'TASK_VALIDATION_FAILED'"
    ).fetchall()
    conn.close()
    assert len(logs) == 7
    joined_details = " ".join(row[1] for row in logs)
    assert "extra_field:role" in joined_details
    assert "extra_field:owner_id" in joined_details
    assert malicious_title not in joined_details

    # 6) Caracteres Unicode y espacios -> HTTP 201 normalizado
    r_ok = client.post(
        "/tasks",
        json={
            "title": "  Revisión STRIDE — Sesión 04 Ñandú  ",
            "description": "Validar límites de confianza en Cusco",
            "status": "en_progreso",
        },
        headers=headers,
    )
    assert r_ok.status_code == 201
    created = r_ok.get_json()["task"]
    assert created["title"] == "Revisión STRIDE — Sesión 04 Ñandú"
    assert created["status"] == "en_progreso"


def test_tasks_idor_protection_and_parameterized_search(tmp_path: Path) -> None:
    """Ej. 4.1: bloquea IDOR (403) y valida búsqueda parametrizada ante todos los casos borde."""
    db_file = str(tmp_path / "tasks_idor.db")
    app = create_app(db_path=db_file, security_config=SecurityConfig())
    client = app.test_client()

    tok_a = _register_and_login(client, "dueno@unsaac.edu.pe", "Dueño A")
    tok_b = _register_and_login(client, "otro@unsaac.edu.pe", "Usuario B")

    h_a = {"Authorization": f"Bearer {tok_a}"}
    h_b = {"Authorization": f"Bearer {tok_b}"}

    created = client.post(
        "/tasks",
        json={"title": "Informe de Seguridad 100", "description": "Privado"},
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

    # Casos de prueba Ej. 4.1:
    # a) Entrada normal
    r_normal = client.get("/tasks?search=Seguridad", headers=h_a)
    assert r_normal.status_code == 200
    assert len(r_normal.get_json()["tasks"]) == 1

    # b) Cadena larga (> 100 chars) -> HTTP 400
    assert client.get(f"/tasks?search={'a' * 101}", headers=h_a).status_code == 400

    # c) Comillas / intento SQLi -> HTTP 400
    assert client.get("/tasks?search='%20OR%20'1'='1", headers=h_a).status_code == 400
    assert client.get('/tasks?search="OR 1=1', headers=h_a).status_code == 400

    # d) Caracteres especiales hostiles (<script>, ; DROP) -> HTTP 400
    assert client.get("/tasks?search=<script>alert(1)</script>", headers=h_a).status_code == 400
    assert client.get("/tasks?search=test;DROP%20TABLE%20tasks", headers=h_a).status_code == 400

    # e) Valores nulos / vacíos -> HTTP 200 devolviendo lista propia sin error
    assert len(client.get("/tasks", headers=h_a).get_json()["tasks"]) == 1
    assert len(client.get("/tasks?search=", headers=h_a).get_json()["tasks"]) == 1
    assert len(client.get("/tasks?search=%20%20", headers=h_a).get_json()["tasks"]) == 1

    # Dueño actualiza y elimina con éxito
    assert (
        client.put(f"/tasks/{task_id}", json={"status": "completada"}, headers=h_a).status_code
        == 200
    )
    assert client.delete(f"/tasks/{task_id}", headers=h_a).status_code == 200


def test_rbac_roles_student_teacher_admin(tmp_path: Path) -> None:
    """Reto de extensión RBAC: verifica separación de privilegios entre estudiante/docente/admin."""
    db_file = str(tmp_path / "rbac.db")
    app = create_app(db_path=db_file, security_config=SecurityConfig())
    client = app.test_client()

    tok_est = _register_and_login(client, "est@unsaac.edu.pe", "Estudiante Uno")
    tok_doc = _register_and_login(client, "doc@unsaac.edu.pe", "Docente Supervisor")
    tok_adm = _register_and_login(client, "adm@unsaac.edu.pe", "Admin Sistema")

    # Promoción controlada en BD simulando aprovisionamiento administrativo
    conn = sqlite3.connect(db_file)
    conn.execute("UPDATE users SET role = 'docente' WHERE email = 'doc@unsaac.edu.pe'")
    conn.execute("UPDATE users SET role = 'administrador' WHERE email = 'adm@unsaac.edu.pe'")
    conn.commit()
    conn.close()

    h_est = {"Authorization": f"Bearer {tok_est}"}
    h_doc = {"Authorization": f"Bearer {tok_doc}"}
    h_adm = {"Authorization": f"Bearer {tok_adm}"}

    task_id = client.post(
        "/tasks",
        json={"title": "Entrega Guía 04", "description": "Actividades 3 y 4"},
        headers=h_est,
    ).get_json()["task"]["id"]

    # Docente puede supervisar en modo lectura, pero recibe HTTP 403 al intentar editar/borrar
    assert len(client.get("/tasks", headers=h_doc).get_json()["tasks"]) == 1
    assert (
        client.put(f"/tasks/{task_id}", json={"status": "completada"}, headers=h_doc).status_code
        == 403
    )
    assert client.delete(f"/tasks/{task_id}", headers=h_doc).status_code == 403

    # Administrador puede gestionar y eliminar con rastro auditable
    assert (
        client.put(f"/tasks/{task_id}", json={"status": "completada"}, headers=h_adm).status_code
        == 200
    )
    assert client.delete(f"/tasks/{task_id}", headers=h_adm).status_code == 200


def test_no_sql_concatenation_in_production_modules() -> None:
    """Ej. 4.1 (Paso 6): asegura ausencia de SQL concatenado o f-strings SQL en código seguro."""
    root = Path(__file__).resolve().parents[1]
    production_files = [
        root / "sportreserve" / "app_segura.py",
        root / "task_api" / "app.py",
        root / "task_api" / "auth_service.py",
        root / "task_api" / "tasks_service.py",
        root / "task_api" / "security.py",
        root / "task_api" / "db.py",
    ]
    bad_sql_pattern = re.compile(
        r'(f["\']\s*(SELECT|INSERT|UPDATE|DELETE)\b)|(SELECT\s+.+\+\s*\w+)',
        re.IGNORECASE,
    )
    for file_path in production_files:
        content = file_path.read_text(encoding="utf-8")
        assert not bad_sql_pattern.search(content), f"SQL inseguro detectado en {file_path.name}"
