"""Demostración HTTP end-to-end de los controles de seguridad de sesión (Ejercicio 1.2)."""

from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from task_api.app import create_app
from task_api.security import SecurityConfig


class DemoClock:
    """Reloj controlable para demostrar expiración y bloqueo progresivo."""

    def __init__(self, start: int = 1_700_000_000) -> None:
        self.now = start

    def __call__(self) -> int:
        return self.now

    def advance(self, seconds: int) -> None:
        """Avanza el reloj en segundos."""
        self.now += seconds


def main() -> None:
    """Ejecuta secuencia real de peticiones HTTP y guarda la traza en evidencias."""
    out_file = ROOT / "evidencias" / "http_demo_output.txt"
    lines: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        db_path = str(Path(tmp) / "demo_auth.db")
        clock = DemoClock()
        mailbox: list[tuple[str, str]] = []
        app = create_app(
            db_path=db_path,
            security_config=SecurityConfig(
                session_ttl_seconds=300,
                reset_ttl_seconds=120,
                max_failed_attempts=3,
                base_lockout_seconds=30,
            ),
            time_provider=clock,
            mail_sender=lambda email, tok: mailbox.append((email, tok)),
        )
        client = app.test_client()

        def log_req(title: str, resp) -> None:
            lines.append(f"[{title}] -> HTTP {resp.status_code}")
            body = resp.get_json()
            # Ocultar parcialmente token de sesión en impresión para evidencia segura
            if isinstance(body, dict) and "access_token" in body:
                tok = body["access_token"]
                body = {**body, "access_token": f"{tok[:10]}...{tok[-6:]}"}
            lines.append(f"  Respuesta: {json.dumps(body, ensure_ascii=False)}")
            if "Retry-After" in resp.headers:
                lines.append(f"  Header Retry-After: {resp.headers['Retry-After']}s")

        # 1. Registro seguro e intento de escalación de privilegios
        r_esc = client.post(
            "/auth/register",
            json={
                "email": "yeferson@unsaac.edu.pe",
                "full_name": "Yeferson Supa",
                "password": "ClaveSegura123",
                "role": "admin",
            },
        )
        log_req("1. POST /auth/register (rechaza role=admin)", r_esc)

        r_reg = client.post(
            "/auth/register",
            json={
                "email": "yeferson@unsaac.edu.pe",
                "full_name": "Yeferson Supa",
                "password": "ClaveSegura123",
            },
        )
        log_req("2. POST /auth/register (válido Argon2id)", r_reg)

        # 2. Credenciales inválidas sin enumeración y fuerza bruta progresiva
        for idx in range(1, 4):
            r_fail = client.post(
                "/auth/login",
                json={"email": "yeferson@unsaac.edu.pe", "password": f"MalaClave{idx}"},
                environ_base={"REMOTE_ADDR": "190.12.40.10"},
            )
            log_req(f"3.{idx} POST /auth/login (intento fallido #{idx})", r_fail)

        # 3. Avance tras bloqueo y login válido con regeneración de sesión
        clock.advance(31)
        r_ok1 = client.post(
            "/auth/login",
            json={"email": "yeferson@unsaac.edu.pe", "password": "ClaveSegura123"},
            environ_base={"REMOTE_ADDR": "190.12.40.10"},
        )
        tok1 = r_ok1.get_json()["access_token"]
        log_req("4. POST /auth/login (exitoso post-bloqueo)", r_ok1)

        r_ok2 = client.post(
            "/auth/login",
            json={"email": "yeferson@unsaac.edu.pe", "password": "ClaveSegura123"},
            headers={"Authorization": f"Bearer {tok1}"},
            environ_base={"REMOTE_ADDR": "190.12.40.10"},
        )
        tok2 = r_ok2.get_json()["access_token"]
        log_req("5. POST /auth/login (regenera session_id e invalida previo)", r_ok2)

        r_old = client.get("/auth/me", headers={"Authorization": f"Bearer {tok1}"})
        log_req("6. GET /auth/me (token previo invalidado)", r_old)

        # 4. Recuperación con token único + rechazo de reutilización + verificación de audit_logs
        r_fg = client.post("/auth/forgot-password", json={"email": "yeferson@unsaac.edu.pe"})
        log_req("7. POST /auth/forgot-password (emite token corto)", r_fg)
        reset_tok = mailbox[-1][1]

        r_rs1 = client.post(
            "/auth/reset-password",
            json={"token": reset_tok, "new_password": "NuevaClaveSegura99"},
        )
        log_req("8. POST /auth/reset-password (1er uso + revoca sesiones)", r_rs1)

        r_rs2 = client.post(
            "/auth/reset-password",
            json={"token": reset_tok, "new_password": "OtraClave99"},
        )
        log_req("9. POST /auth/reset-password (rechaza reutilización)", r_rs2)

        r_revoked = client.get("/auth/me", headers={"Authorization": f"Bearer {tok2}"})
        log_req("10. GET /auth/me (sesión revocada tras reset)", r_revoked)

        conn = sqlite3.connect(db_path)
        logs = conn.execute(
            "SELECT event_type, actor_email_masked, detail FROM audit_logs ORDER BY id DESC LIMIT 4"
        ).fetchall()
        conn.close()
        lines.append("\n[Bitácora audit_logs (últimos 4 eventos sin tokens expuestos)]")
        for ev, em, det in logs:
            lines.append(f"  - {ev} | {em} | {det}")

    output_text = "\n".join(lines) + "\n"
    out_file.write_text(output_text, encoding="utf-8")
    print(output_text)


if __name__ == "__main__":
    main()

