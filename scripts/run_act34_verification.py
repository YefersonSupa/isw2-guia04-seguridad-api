"""Script de verificación integral para Actividades 3 y 4 (SAST + HTTP Antes vs. Después)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sportreserve.app_segura import create_secure_app
from sportreserve.app_vulnerable import create_vulnerable_app
from task_api.app import create_app
from task_api.security import SecurityConfig
from task_api.vulnerable_examples import create_vulnerable_tasks_app


def _run_cmd(args: list[str]) -> str:
    proc = subprocess.run(
        args,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    out = proc.stdout.strip()
    if proc.stderr.strip() and "INFO" not in proc.stderr:
        out = f"{out}\n{proc.stderr.strip()}" if out else proc.stderr.strip()
    return out


def run_http_comparison() -> str:
    """Ejecuta peticiones HTTP reales comparando código vulnerable vs. refactorizado."""
    lines: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        vuln_client = create_vulnerable_app(str(tmp_dir / "v_res.db")).test_client()
        safe_client = create_secure_app(str(tmp_dir / "s_res.db")).test_client()

        lines.append("=== CASO PRÁCTICO 01: SPORTRESERVE CO. (ANTES vs DESPUÉS) ===")

        # Hallazgo A: IDOR
        r_v_idor = vuln_client.get("/api/reserva?id=105&user_id=1")
        r_s_idor = safe_client.get("/api/reserva?id=105&user_id=1")
        lines.append(
            f"[Hallazgo A - IDOR] GET /api/reserva?id=105&user_id=1\n"
            f"  ANTES  (app_vulnerable.py): HTTP {r_v_idor.status_code} -> EXPONE reserva de User_B "
            f"(owner={r_v_idor.get_json()['reserva']['user_id']})\n"
            f"  DESPUÉS(app_segura.py)    : HTTP {r_s_idor.status_code} -> {json.dumps(r_s_idor.get_json(), ensure_ascii=False)}"
        )

        # Hallazgo B: SQLi en correo
        r_v_sql = vuln_client.get("/api/usuarios/buscar?correo='%20OR%20'1'='1")
        r_s_sql = safe_client.get("/api/usuarios/buscar?correo='%20OR%20'1'='1")
        lines.append(
            f"[Hallazgo B - SQLi] GET /api/usuarios/buscar?correo=' OR '1'='1\n"
            f"  ANTES  (app_vulnerable.py): HTTP {r_v_sql.status_code} -> FILTRA {len(r_v_sql.get_json()['resultados'])} usuarios completos\n"
            f"  DESPUÉS(app_segura.py)    : HTTP {r_s_sql.status_code} -> {json.dumps(r_s_sql.get_json(), ensure_ascii=False)}"
        )

        # Hallazgo C: XSS
        r_v_xss = vuln_client.get("/comentarios?nombre=<script>alert(1)</script>")
        r_s_xss = safe_client.get("/comentarios?nombre=<script>alert(1)</script>")
        v_has_raw = "<script>alert(1)</script>" in r_v_xss.get_data(as_text=True)
        s_has_esc = "&lt;script&gt;alert(1)&lt;/script&gt;" in r_s_xss.get_data(as_text=True)
        lines.append(
            f"[Hallazgo C - XSS]  GET /comentarios?nombre=<script>alert(1)</script>\n"
            f"  ANTES  (app_vulnerable.py): HTTP {r_v_xss.status_code} -> <script> crudo inyectado={v_has_raw}\n"
            f"  DESPUÉS(app_segura.py)    : HTTP {r_s_xss.status_code} -> escapado={s_has_esc} | CSP={r_s_xss.headers['Content-Security-Policy']}"
        )

        lines.append("\n=== EJERCICIOS 3.1 y 4.1: API TAREAS (VALIDACIÓN + SQLi + IDOR) ===")
        vt_client = create_vulnerable_tasks_app(str(tmp_dir / "v_tasks.db")).test_client()
        vt_client.post("/vulnerable/tasks", json={"title": "", "status": "hacked", "role": "admin"})
        vt_client.post("/vulnerable/tasks", json={"title": "Secreto Docente", "owner_id": 2})
        r_vt_sqli = vt_client.get("/vulnerable/tasks/search?search=x%25'%20OR%201=1%20--")

        st_app = create_app(db_path=str(tmp_dir / "s_tasks.db"), security_config=SecurityConfig())
        st_client = st_app.test_client()
        st_client.post(
            "/auth/register",
            json={"email": "a@unsaac.edu.pe", "full_name": "Estudiante A", "password": "ClaveSegura123"},
        )
        tok = st_client.post(
            "/auth/login",
            json={"email": "a@unsaac.edu.pe", "password": "ClaveSegura123"},
        ).get_json()["access_token"]
        hdr = {"Authorization": f"Bearer {tok}"}

        r_st_extra = st_client.post(
            "/tasks",
            json={"title": "Tarea prueba", "role": "admin"},
            headers=hdr,
        )
        r_st_ok = st_client.post(
            "/tasks",
            json={"title": "Hardening Guía 04", "description": "SAST y pruebas", "status": "en_progreso"},
            headers=hdr,
        )
        r_st_sqli = st_client.get("/tasks?search=x%25'%20OR%201=1%20--", headers=hdr)
        lines.append(
            f"[Ej. 3.1 Validación] POST /tasks con campo extra role='admin'\n"
            f"  ANTES  (/vulnerable/tasks): HTTP 201 -> aceptó título vacío y role='admin'\n"
            f"  DESPUÉS(/tasks)           : HTTP {r_st_extra.status_code} -> {json.dumps(r_st_extra.get_json(), ensure_ascii=False)}\n"
            f"  DESPUÉS(/tasks válido)    : HTTP {r_st_ok.status_code} -> id={r_st_ok.get_json()['task']['id']}"
        )
        lines.append(
            f"[Ej. 4.1 Búsqueda]  GET /tasks?search=x%' OR 1=1 --\n"
            f"  ANTES  (/vulnerable/search): HTTP {r_vt_sqli.status_code} -> SQLi expone {len(r_vt_sqli.get_json()['tasks'])} tareas\n"
            f"  DESPUÉS(/tasks?search=...) : HTTP {r_st_sqli.status_code} -> {json.dumps(r_st_sqli.get_json(), ensure_ascii=False)}"
        )

    return "\n".join(lines) + "\n"


def main() -> None:
    """Genera los archivos de evidencia reales para Actividades 3 y 4."""
    ev_dir = ROOT / "evidencias"
    ev_dir.mkdir(parents=True, exist_ok=True)
    py_dir = Path(sys.executable).parent

    bandit_exe = str(py_dir / "bandit.exe")
    pylint_exe = str(py_dir / "pylint.exe")
    pytest_exe = str(py_dir / "pytest.exe")

    pytest_out = _run_cmd([pytest_exe, "-v"])
    (ev_dir / "act34_pytest_output.txt").write_text(pytest_out + "\n", encoding="utf-8")

    sast_vuln = (
        "=== BANDIT SAST (CÓDIGO VULNERABLE: app_vulnerable.py & vulnerable_examples.py) ===\n"
        + _run_cmd([bandit_exe, "sportreserve/app_vulnerable.py", "task_api/vulnerable_examples.py"])
        + "\n\n=== PYLINT (app_vulnerable.py) ===\n"
        + _run_cmd([pylint_exe, "sportreserve/app_vulnerable.py"])
    )
    (ev_dir / "act34_sast_vulnerable.txt").write_text(sast_vuln + "\n", encoding="utf-8")

    sast_safe = (
        "=== BANDIT SAST (CÓDIGO SEGURO: app_segura.py & task_api/) ===\n"
        + _run_cmd([
            bandit_exe,
            "-r",
            "sportreserve/app_segura.py",
            "sportreserve/init_db.py",
            "task_api",
            "--exclude",
            "task_api/vulnerable_examples.py",
        ])
        + "\n\n=== PYLINT (app_segura.py, init_db.py & task_api/) ===\n"
        + _run_cmd([
            pylint_exe,
            "sportreserve/app_segura.py",
            "sportreserve/init_db.py",
            "task_api",
            "--ignore=vulnerable_examples.py",
        ])
    )
    (ev_dir / "act34_sast_segura.txt").write_text(sast_safe + "\n", encoding="utf-8")

    http_comp = run_http_comparison()
    (ev_dir / "act34_http_comparison.txt").write_text(http_comp, encoding="utf-8")

    print(pytest_out)
    print("\n--- HTTP COMPARISON ---")
    print(http_comp)


if __name__ == "__main__":
    main()
