"""Pruebas automatizadas de seguridad de autenticación y sesiones (Ejercicio Propuesto 1.2)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from task_api.app import create_app
from task_api.security import SecurityConfig


class FakeClock:
    """Reloj determinista para probar expiración de sesiones, tokens y desbloqueos."""

    def __init__(self, initial_ts: int = 1_700_000_000) -> None:
        self.now = initial_ts

    def __call__(self) -> int:
        return self.now

    def advance(self, seconds: int) -> None:
        """Avanza el tiempo simulado en segundos."""
        self.now += seconds


def _build_test_context(tmp_path: Path, config: SecurityConfig | None = None):
    db_file = str(tmp_path / "test_auth.db")
    clock = FakeClock()
    sent_mails: list[tuple[str, str]] = []

    def fake_mailer(email: str, token: str) -> None:
        sent_mails.append((email, token))

    cfg = config or SecurityConfig(
        session_ttl_seconds=300,
        reset_ttl_seconds=120,
        max_failed_attempts=3,
        base_lockout_seconds=30,
        max_lockout_seconds=300,
    )
    app = create_app(
        db_path=db_file,
        security_config=cfg,
        time_provider=clock,
        mail_sender=fake_mailer,
    )
    return app.test_client(), db_file, clock, sent_mails


def _register_sample_user(client, email="yeferson@unsaac.edu.pe", password="ClaveSegura123"):
    return client.post(
        "/auth/register",
        json={
            "email": email,
            "full_name": "Yeferson Supa",
            "password": password,
        },
    )


def test_register_uses_argon2id_and_blocks_privilege_escalation(tmp_path: Path) -> None:
    """Verifica hash lento Argon2id y rechazo de asignación masiva de rol."""
    client, db_file, _, _ = _build_test_context(tmp_path)

    esc_resp = client.post(
        "/auth/register",
        json={
            "email": "attacker@unsaac.edu.pe",
            "full_name": "Atacante",
            "password": "PasswordValido1",
            "role": "admin",
        },
    )
    assert esc_resp.status_code == 400

    ok_resp = _register_sample_user(client)
    assert ok_resp.status_code == 201
    assert ok_resp.get_json()["user"]["role"] == "estudiante"

    conn = sqlite3.connect(db_file)
    stored_hash = conn.execute(
        "SELECT password_hash FROM users WHERE email = ?",
        ("yeferson@unsaac.edu.pe",),
    ).fetchone()[0]
    conn.close()

    assert stored_hash.startswith("$argon2id$")
    assert "ClaveSegura123" not in stored_hash


def test_invalid_credentials_return_generic_error_without_enumeration(tmp_path: Path) -> None:
    """Verifica mensaje de error idéntico para cuenta inexistente y clave incorrecta."""
    client, _, _, _ = _build_test_context(tmp_path)
    _register_sample_user(client)

    resp_unknown = client.post(
        "/auth/login",
        json={"email": "noexiste@unsaac.edu.pe", "password": "ClaveIncorrecta1"},
        environ_base={"REMOTE_ADDR": "10.0.0.10"},
    )
    resp_wrong_pwd = client.post(
        "/auth/login",
        json={"email": "yeferson@unsaac.edu.pe", "password": "ClaveIncorrecta1"},
        environ_base={"REMOTE_ADDR": "10.0.0.11"},
    )

    assert resp_unknown.status_code == 401
    assert resp_wrong_pwd.status_code == 401
    assert resp_unknown.get_json() == resp_wrong_pwd.get_json()


def test_brute_force_progressive_lockout_by_account_and_ip(tmp_path: Path) -> None:
    """Simula fuerza bruta y verifica bloqueo temporal progresivo por cuenta y por IP."""
    client, _, clock, _ = _build_test_context(tmp_path)
    _register_sample_user(client)

    # 1) Fuerza bruta distribuida contra la misma cuenta desde distintas IPs
    for idx in range(2):
        r = client.post(
            "/auth/login",
            json={"email": "yeferson@unsaac.edu.pe", "password": "WrongPassword1"},
            environ_base={"REMOTE_ADDR": f"192.168.1.{idx + 10}"},
        )
        assert r.status_code == 401

    r_lock_1 = client.post(
        "/auth/login",
        json={"email": "yeferson@unsaac.edu.pe", "password": "WrongPassword1"},
        environ_base={"REMOTE_ADDR": "192.168.1.99"},
    )
    assert r_lock_1.status_code == 429
    assert int(r_lock_1.headers["Retry-After"]) == 30

    # Incluso con clave correcta durante el bloqueo, la cuenta permanece protegida
    r_during_lock = client.post(
        "/auth/login",
        json={"email": "yeferson@unsaac.edu.pe", "password": "ClaveSegura123"},
        environ_base={"REMOTE_ADDR": "192.168.1.200"},
    )
    assert r_during_lock.status_code == 429

    # Avanza el reloj tras primer bloqueo y falla de nuevo -> bloqueo progresivo (60s)
    clock.advance(31)
    r_lock_2 = client.post(
        "/auth/login",
        json={"email": "yeferson@unsaac.edu.pe", "password": "WrongPassword1"},
        environ_base={"REMOTE_ADDR": "192.168.1.201"},
    )
    assert r_lock_2.status_code == 429
    assert int(r_lock_2.headers["Retry-After"]) == 60

    # 2) Fuerza bruta por IP atacando distintas cuentas inexistentes
    attacker_ip = "203.0.113.55"
    for idx in range(2):
        r_ip = client.post(
            "/auth/login",
            json={"email": f"objetivo{idx}@unsaac.edu.pe", "password": "GuessPassword1"},
            environ_base={"REMOTE_ADDR": attacker_ip},
        )
        assert r_ip.status_code == 401

    r_ip_blocked = client.post(
        "/auth/login",
        json={"email": "otro@unsaac.edu.pe", "password": "GuessPassword1"},
        environ_base={"REMOTE_ADDR": attacker_ip},
    )
    assert r_ip_blocked.status_code == 429


def test_session_regeneration_expiration_and_logout(tmp_path: Path) -> None:
    """Verifica regeneración de ID de sesión, expiración temporal y logout."""
    client, _, clock, _ = _build_test_context(tmp_path)
    _register_sample_user(client)

    login1 = client.post(
        "/auth/login",
        json={"email": "yeferson@unsaac.edu.pe", "password": "ClaveSegura123"},
    )
    assert login1.status_code == 200
    d1 = login1.get_json()

    # Al volver a iniciar sesión enviando el token previo, se regenera e invalida el anterior
    login2 = client.post(
        "/auth/login",
        json={"email": "yeferson@unsaac.edu.pe", "password": "ClaveSegura123"},
        headers={"Authorization": f"Bearer {d1['access_token']}"},
    )
    assert login2.status_code == 200
    d2 = login2.get_json()
    assert d2["session_id"] != d1["session_id"]
    assert d2["access_token"] != d1["access_token"]

    old_me = client.get("/auth/me", headers={"Authorization": f"Bearer {d1['access_token']}"})
    assert old_me.status_code == 401

    valid_me = client.get("/auth/me", headers={"Authorization": f"Bearer {d2['access_token']}"})
    assert valid_me.status_code == 200

    # Avanza el reloj hasta expirar la sesión (TTL=300s)
    clock.advance(301)
    expired_me = client.get("/auth/me", headers={"Authorization": f"Bearer {d2['access_token']}"})
    assert expired_me.status_code == 401

    # Nueva sesión + cierre de sesión explícito
    login3 = client.post(
        "/auth/login",
        json={"email": "yeferson@unsaac.edu.pe", "password": "ClaveSegura123"},
    )
    token3 = login3.get_json()["access_token"]
    logout_resp = client.post("/auth/logout", headers={"Authorization": f"Bearer {token3}"})
    assert logout_resp.status_code == 200
    after_logout = client.get("/auth/me", headers={"Authorization": f"Bearer {token3}"})
    assert after_logout.status_code == 401


def test_change_password_revokes_all_active_sessions(tmp_path: Path) -> None:
    """Verifica revocación inmediata de sesiones activas al cambiar la contraseña."""
    client, _, _, _ = _build_test_context(tmp_path)
    _register_sample_user(client)

    s1 = client.post(
        "/auth/login",
        json={"email": "yeferson@unsaac.edu.pe", "password": "ClaveSegura123"},
    ).get_json()["access_token"]
    s2 = client.post(
        "/auth/login",
        json={"email": "yeferson@unsaac.edu.pe", "password": "ClaveSegura123"},
    ).get_json()["access_token"]

    chg = client.post(
        "/auth/change-password",
        json={"current_password": "ClaveSegura123", "new_password": "NuevaClaveSegura456"},
        headers={"Authorization": f"Bearer {s1}"},
    )
    assert chg.status_code == 200

    assert client.get("/auth/me", headers={"Authorization": f"Bearer {s1}"}).status_code == 401
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {s2}"}).status_code == 401


def test_password_reset_single_use_invalidation_expiration_and_safe_logs(tmp_path: Path) -> None:
    """Verifica token de un solo uso, invalidación previa, expiración y logs sin secretos."""
    client, db_file, clock, sent_mails = _build_test_context(tmp_path)
    _register_sample_user(client)

    active_token = client.post(
        "/auth/login",
        json={"email": "yeferson@unsaac.edu.pe", "password": "ClaveSegura123"},
    ).get_json()["access_token"]

    # Primera solicitud de token
    r1 = client.post("/auth/forgot-password", json={"email": "yeferson@unsaac.edu.pe"})
    assert r1.status_code == 200
    assert len(sent_mails) == 1
    token_first = sent_mails[0][1]

    # Segunda solicitud -> debe invalidar el primer token
    r2 = client.post("/auth/forgot-password", json={"email": "yeferson@unsaac.edu.pe"})
    assert r2.status_code == 200
    assert len(sent_mails) == 2
    token_second = sent_mails[1][1]
    assert token_first != token_second

    # Reutilizar o usar el primer token ya invalidado debe fallar
    bad_reset = client.post(
        "/auth/reset-password",
        json={"token": token_first, "new_password": "OtraClaveValida789"},
    )
    assert bad_reset.status_code == 400

    # El segundo token funciona una sola vez y revoca sesiones previas
    ok_reset = client.post(
        "/auth/reset-password",
        json={"token": token_second, "new_password": "OtraClaveValida789"},
    )
    assert ok_reset.status_code == 200
    assert (
        client.get("/auth/me", headers={"Authorization": f"Bearer {active_token}"}).status_code
        == 401
    )

    # Intentar reutilizar el mismo token de un solo uso debe ser rechazado
    reuse_reset = client.post(
        "/auth/reset-password",
        json={"token": token_second, "new_password": "OtroIntento999"},
    )
    assert reuse_reset.status_code == 400

    # Solicitar un tercer token y dejar que expire (TTL=120s)
    client.post("/auth/forgot-password", json={"email": "yeferson@unsaac.edu.pe"})
    token_third = sent_mails[2][1]
    clock.advance(121)
    expired_reset = client.post(
        "/auth/reset-password",
        json={"token": token_third, "new_password": "ClaveExpirada999"},
    )
    assert expired_reset.status_code == 400

    # Verificar que la bitácora de auditoría registró eventos sin exponer ningún token
    conn = sqlite3.connect(db_file)
    logs = conn.execute("SELECT event_type, detail FROM audit_logs").fetchall()
    conn.close()
    assert any(row[0] == "PASSWORD_RESET_REQUESTED" for row in logs)
    assert any(row[0] == "PASSWORD_RESET_COMPLETED" for row in logs)
    joined_details = " ".join(row[1] for row in logs)
    for tok in (token_first, token_second, token_third):
        assert tok not in joined_details


def test_frontend_index_and_security_headers(tmp_path: Path) -> None:
    """Verifica que el frontend HTML y sus estáticos se sirvan con CSP estricta."""
    client, _, _, _ = _build_test_context(tmp_path)

    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Portal de Autenticación Segura" in html
    assert "script-src 'self'" in resp.headers["Content-Security-Policy"]
    assert "'unsafe-inline'" not in resp.headers["Content-Security-Policy"]
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["X-Content-Type-Options"] == "nosniff"

    css_resp = client.get("/static/style.css")
    js_resp = client.get("/static/app.js")
    assert css_resp.status_code == 200
    assert js_resp.status_code == 200


