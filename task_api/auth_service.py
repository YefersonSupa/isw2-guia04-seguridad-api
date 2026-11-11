"""Servicios de autenticación resistente a ataques comunes (Ejercicio Propuesto 1.2)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Callable, Optional

from task_api.security import (
    SecurityConfig,
    clear_login_attempts,
    generate_secure_token,
    get_lockout_remaining,
    hash_password,
    hash_token,
    log_security_event,
    normalize_email,
    record_failed_login,
    validate_password_strength,
    verify_password,
)

# Hash dummy precomputado para mitigar ataques de temporización cuando el usuario no existe.
_DUMMY_HASH = hash_password("Dummy!Secure#Check99")
MailSender = Callable[[str, str], None]


@dataclass(frozen=True)
class ServiceResult:
    """Resultado estandarizado de operaciones de autenticación."""

    status_code: int
    payload: dict


def _validate_register_input(
    raw_email: object,
    raw_name: object,
    raw_password: object,
    extra_fields: Optional[set[str]],
) -> tuple[Optional[str], Optional[str], Optional[ServiceResult]]:
    """Valida entrada de registro retornando correo, nombre limpio o error."""
    if extra_fields:
        return None, None, ServiceResult(400, {"error": "Campos no permitidos en la solicitud."})

    email = normalize_email(raw_email)
    if not email:
        return None, None, ServiceResult(400, {"error": "Correo electrónico inválido."})

    if not isinstance(raw_name, str) or not 3 <= len(raw_name.strip()) <= 100:
        return (
            None,
            None,
            ServiceResult(400, {"error": "El nombre debe tener entre 3 y 100 caracteres."}),
        )

    if not isinstance(raw_password, str):
        return None, None, ServiceResult(400, {"error": "Contraseña inválida."})

    pwd_error = validate_password_strength(raw_password)
    if pwd_error:
        return None, None, ServiceResult(400, {"error": pwd_error})

    return email, raw_name.strip(), None


def register_user(
    conn: sqlite3.Connection,
    raw_email: object,
    raw_name: object,
    raw_password: object,
    ip_address: str,
    now: int,
    extra_fields: Optional[set[str]] = None,
) -> ServiceResult:
    """Registra un usuario nuevo con rol mínimo ('estudiante') y hash Argon2id."""
    email, clean_name, err = _validate_register_input(
        raw_email, raw_name, raw_password, extra_fields
    )
    if err or not email or not clean_name:
        return err  # type: ignore[return-value]

    existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        log_security_event(
            conn, "REGISTER_DUPLICATE", email, ip_address, "Intento con correo existente", now
        )
        return ServiceResult(400, {"error": "No fue posible completar el registro."})

    pwd_hash = hash_password(str(raw_password))
    cursor = conn.execute(
        """
        INSERT INTO users (email, full_name, password_hash, role, created_at)
        VALUES (?, ?, ?, 'estudiante', ?)
        """,
        (email, clean_name, pwd_hash, now),
    )
    log_security_event(
        conn, "REGISTER_SUCCESS", email, ip_address, "Usuario registrado con rol estudiante", now
    )
    return ServiceResult(
        201,
        {
            "message": "Usuario registrado correctamente.",
            "user": {
                "id": cursor.lastrowid,
                "email": email,
                "full_name": clean_name,
                "role": "estudiante",
            },
        },
    )


def _handle_failed_login(
    conn: sqlite3.Connection,
    email: str,
    ip_address: str,
    config: SecurityConfig,
    now: int,
) -> ServiceResult:
    """Registra fallo de login y devuelve HTTP 429 si se activa bloqueo, o HTTP 401 genérico."""
    lock_secs = record_failed_login(conn, email, ip_address, config, now)
    log_security_event(conn, "LOGIN_FAILED", email, ip_address, "Fallo de autenticación", now)
    if lock_secs > 0:
        return ServiceResult(
            429,
            {
                "error": "Demasiados intentos fallidos. Intente nuevamente más tarde.",
                "retry_after": lock_secs,
            },
        )
    return ServiceResult(401, {"error": "Credenciales inválidas."})


def login_user(
    conn: sqlite3.Connection,
    raw_email: object,
    raw_password: object,
    ip_address: str,
    previous_token: Optional[str],
    config: SecurityConfig,
    now: int,
) -> ServiceResult:
    """Autentica credenciales, aplica bloqueo progresivo y regenera el ID de sesión."""
    email = normalize_email(raw_email) or "unknown@invalid.local"
    remaining_lock = get_lockout_remaining(conn, email, ip_address, now)
    if remaining_lock > 0:
        log_security_event(
            conn,
            "LOGIN_BLOCKED",
            email,
            ip_address,
            f"Bloqueo temporal activo ({remaining_lock}s restantes)",
            now,
        )
        return ServiceResult(
            429,
            {
                "error": "Demasiados intentos fallidos. Intente nuevamente más tarde.",
                "retry_after": remaining_lock,
            },
        )

    if not isinstance(raw_password, str) or email == "unknown@invalid.local":
        return _handle_failed_login(conn, email, ip_address, config, now)

    user = conn.execute(
        "SELECT id, email, full_name, password_hash, role FROM users WHERE email = ?",
        (email,),
    ).fetchone()

    stored_hash = user["password_hash"] if user else _DUMMY_HASH
    password_ok = verify_password(stored_hash, raw_password)
    if not user or not password_ok:
        return _handle_failed_login(conn, email, ip_address, config, now)

    clear_login_attempts(conn, email, ip_address)

    # Regeneración obligatoria de sesión: invalida cualquier token previo para evitar fijación.
    if previous_token:
        conn.execute(
            "UPDATE sessions SET revoked = 1 WHERE token_hash = ?",
            (hash_token(previous_token),),
        )

    session_id = generate_secure_token()
    raw_session_token = generate_secure_token()
    expires_at = now + config.session_ttl_seconds
    conn.execute(
        """
        INSERT INTO sessions (
            session_id, token_hash, user_id, ip_address, created_at, expires_at, revoked
        )
        VALUES (?, ?, ?, ?, ?, ?, 0)
        """,
        (session_id, hash_token(raw_session_token), user["id"], ip_address, now, expires_at),
    )
    log_security_event(
        conn, "LOGIN_SUCCESS", email, ip_address, "Sesión iniciada con nuevo identificador", now
    )
    return ServiceResult(
        200,
        {
            "message": "Inicio de sesión exitoso.",
            "session_id": session_id,
            "access_token": raw_session_token,
            "expires_at": expires_at,
            "user": {
                "id": user["id"],
                "email": user["email"],
                "full_name": user["full_name"],
                "role": user["role"],
            },
        },
    )


def authenticate_session(
    conn: sqlite3.Connection,
    raw_token: Optional[str],
    now: int,
) -> Optional[sqlite3.Row]:
    """Valida un token de sesión verificando que no esté revocado ni expirado."""
    if not raw_token:
        return None
    row = conn.execute(
        """
        SELECT s.session_id, s.expires_at, s.revoked,
               u.id AS user_id, u.email, u.full_name, u.role
        FROM sessions s
        JOIN users u ON u.id = s.user_id
        WHERE s.token_hash = ?
        """,
        (hash_token(raw_token),),
    ).fetchone()
    if not row or int(row["revoked"]) == 1 or int(row["expires_at"]) <= now:
        return None
    return row


def logout_user(
    conn: sqlite3.Connection,
    raw_token: Optional[str],
    ip_address: str,
    now: int,
) -> ServiceResult:
    """Revoca el token de sesión actual del usuario."""
    session = authenticate_session(conn, raw_token, now)
    if not session:
        return ServiceResult(401, {"error": "Sesión inválida o expirada."})
    conn.execute(
        "UPDATE sessions SET revoked = 1 WHERE session_id = ?",
        (session["session_id"],),
    )
    log_security_event(
        conn, "LOGOUT", session["email"], ip_address, "Sesión cerrada por el usuario", now
    )
    return ServiceResult(200, {"message": "Sesión cerrada correctamente."})


def change_password(
    conn: sqlite3.Connection,
    raw_token: Optional[str],
    current_password: object,
    new_password: object,
    ip_address: str,
    now: int,
) -> ServiceResult:
    """Cambia la contraseña actual y revoca todas las sesiones activas del usuario."""
    session = authenticate_session(conn, raw_token, now)
    if not session:
        return ServiceResult(401, {"error": "Sesión inválida o expirada."})

    if not isinstance(current_password, str) or not isinstance(new_password, str):
        return ServiceResult(400, {"error": "Parámetros de contraseña inválidos."})

    user = conn.execute(
        "SELECT id, email, password_hash FROM users WHERE id = ?",
        (session["user_id"],),
    ).fetchone()
    if not user or not verify_password(user["password_hash"], current_password):
        log_security_event(
            conn,
            "PASSWORD_CHANGE_FAILED",
            session["email"],
            ip_address,
            "Contraseña actual incorrecta",
            now,
        )
        return ServiceResult(401, {"error": "Credenciales inválidas."})

    pwd_error = validate_password_strength(new_password)
    if pwd_error:
        return ServiceResult(400, {"error": pwd_error})

    new_hash = hash_password(new_password)
    conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user["id"]))
    conn.execute("UPDATE sessions SET revoked = 1 WHERE user_id = ?", (user["id"],))
    log_security_event(
        conn,
        "PASSWORD_CHANGED",
        user["email"],
        ip_address,
        "Contraseña actualizada y sesiones previas revocadas",
        now,
    )
    return ServiceResult(
        200,
        {"message": "Contraseña actualizada. Todas las sesiones activas fueron revocadas."},
    )


def request_password_reset(
    conn: sqlite3.Connection,
    raw_email: object,
    ip_address: str,
    config: SecurityConfig,
    now: int,
    mail_sender: Optional[MailSender] = None,
) -> ServiceResult:
    """Emite un token de recuperación de un solo uso con expiración corta e invalida previos."""
    generic_msg = (
        "Si el correo se encuentra registrado, recibirá instrucciones de restablecimiento."
    )
    email = normalize_email(raw_email)
    if not email:
        return ServiceResult(400, {"error": "Correo electrónico inválido."})

    user = conn.execute("SELECT id, email FROM users WHERE email = ?", (email,)).fetchone()
    if not user:
        log_security_event(
            conn,
            "PASSWORD_RESET_UNKNOWN_EMAIL",
            email,
            ip_address,
            "Solicitud de recuperación procesada sin exposición de estado",
            now,
        )
        return ServiceResult(200, {"message": generic_msg})

    # Invalida cualquier token previo pendiente para este usuario.
    conn.execute(
        "UPDATE password_resets SET used = 1 WHERE user_id = ? AND used = 0",
        (user["id"],),
    )

    raw_reset_token = generate_secure_token()
    expires_at = now + config.reset_ttl_seconds
    conn.execute(
        """
        INSERT INTO password_resets (user_id, token_hash, created_at, expires_at, used)
        VALUES (?, ?, ?, ?, 0)
        """,
        (user["id"], hash_token(raw_reset_token), now, expires_at),
    )
    log_security_event(
        conn,
        "PASSWORD_RESET_REQUESTED",
        email,
        ip_address,
        "Token de un solo uso emitido con expiración corta (valor oculto en bitácora)",
        now,
    )
    if mail_sender is not None:
        mail_sender(email, raw_reset_token)

    return ServiceResult(200, {"message": generic_msg})


def confirm_password_reset(
    conn: sqlite3.Connection,
    raw_token: object,
    new_password: object,
    ip_address: str,
    now: int,
) -> ServiceResult:
    """Valida token de un solo uso no expirado, actualiza contraseña y revoca sesiones."""
    if not isinstance(raw_token, str) or not raw_token.strip():
        return ServiceResult(400, {"error": "Token de recuperación inválido o expirado."})
    if not isinstance(new_password, str):
        return ServiceResult(400, {"error": "Contraseña inválida."})

    pwd_error = validate_password_strength(new_password)
    if pwd_error:
        return ServiceResult(400, {"error": pwd_error})

    token_digest = hash_token(raw_token.strip())
    reset_row = conn.execute(
        """
        SELECT pr.id, pr.user_id, pr.expires_at, pr.used, u.email
        FROM password_resets pr
        JOIN users u ON u.id = pr.user_id
        WHERE pr.token_hash = ?
        """,
        (token_digest,),
    ).fetchone()

    if not reset_row or int(reset_row["used"]) == 1 or int(reset_row["expires_at"]) <= now:
        actor = reset_row["email"] if reset_row else "unknown@invalid.local"
        log_security_event(
            conn,
            "PASSWORD_RESET_REJECTED",
            actor,
            ip_address,
            "Intento con token inválido, expirado o reutilizado",
            now,
        )
        return ServiceResult(400, {"error": "Token de recuperación inválido o expirado."})

    new_hash = hash_password(new_password)
    conn.execute("UPDATE password_resets SET used = 1 WHERE id = ?", (reset_row["id"],))
    conn.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (new_hash, reset_row["user_id"]),
    )
    conn.execute(
        "UPDATE sessions SET revoked = 1 WHERE user_id = ?",
        (reset_row["user_id"],),
    )
    log_security_event(
        conn,
        "PASSWORD_RESET_COMPLETED",
        reset_row["email"],
        ip_address,
        "Contraseña restablecida con éxito y sesiones anteriores revocadas",
        now,
    )
    return ServiceResult(200, {"message": "Contraseña restablecida correctamente."})
