"""Utilidades criptográficas, control de fuerza bruta y auditoría segura (OWASP)."""

from __future__ import annotations

import hashlib
import re
import secrets
import sqlite3
from dataclasses import dataclass
from typing import Optional

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
_PASSWORD_HASHER = PasswordHasher()


@dataclass(frozen=True)
class SecurityConfig:
    """Parámetros de seguridad configurables para sesiones, bloqueos y recuperación."""

    session_ttl_seconds: int = 3600
    reset_ttl_seconds: int = 900
    max_failed_attempts: int = 3
    base_lockout_seconds: int = 30
    max_lockout_seconds: int = 900


def hash_password(plain_password: str) -> str:
    """Genera un hash lento Argon2id con sal criptográfica automática."""
    return _PASSWORD_HASHER.hash(plain_password)


def verify_password(stored_hash: str, plain_password: str) -> bool:
    """Verifica una contraseña en texto plano contra un hash Argon2id almacenado."""
    try:
        return _PASSWORD_HASHER.verify(stored_hash, plain_password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def validate_password_strength(password: str) -> Optional[str]:
    """Valida requisitos mínimos de complejidad de contraseña; retorna mensaje si falla."""
    if not isinstance(password, str) or len(password) < 8 or len(password) > 128:
        return "La contraseña debe tener entre 8 y 128 caracteres."
    if not any(ch.isupper() for ch in password):
        return "La contraseña debe incluir al menos una letra mayúscula."
    if not any(ch.islower() for ch in password):
        return "La contraseña debe incluir al menos una letra minúscula."
    if not any(ch.isdigit() for ch in password):
        return "La contraseña debe incluir al menos un dígito."
    return None


def normalize_email(raw_email: object) -> Optional[str]:
    """Normaliza y valida sintácticamente un correo electrónico."""
    if not isinstance(raw_email, str):
        return None
    cleaned = raw_email.strip().lower()
    if not cleaned or len(cleaned) > 150 or not EMAIL_REGEX.match(cleaned):
        return None
    return cleaned


def generate_secure_token() -> str:
    """Genera un token aleatorio criptográficamente seguro (256 bits de entropía)."""
    return secrets.token_urlsafe(32)


def hash_token(raw_token: str) -> str:
    """Calcula el digest SHA-256 de un token de alta entropía para almacenamiento seguro."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def mask_email(email: str) -> str:
    """Enmascara un correo para bitácoras de auditoría sin exponer datos personales."""
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    prefix = local[0] if local else "*"
    return f"{prefix}***@{domain}"


def log_security_event(
    conn: sqlite3.Connection,
    event_type: str,
    actor_email: str,
    ip_address: str,
    detail: str,
    now: int,
) -> None:
    """Registra un evento de seguridad auditable sin almacenar secretos ni tokens."""
    conn.execute(
        """
        INSERT INTO audit_logs (event_type, actor_email_masked, ip_address, detail, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (event_type, mask_email(actor_email), ip_address, detail, now),
    )


def get_lockout_remaining(
    conn: sqlite3.Connection,
    email: str,
    ip_address: str,
    now: int,
) -> int:
    """Retorna los segundos restantes de bloqueo activo por cuenta o por IP (0 si libre)."""
    scopes = (f"acct:{email}", f"ip:{ip_address}")
    rows = conn.execute(
        "SELECT locked_until FROM login_attempts WHERE scope_key IN (?, ?)",
        scopes,
    ).fetchall()
    remaining = [max(0, int(row["locked_until"]) - now) for row in rows]
    return max(remaining, default=0)


def _record_scope_failure(
    conn: sqlite3.Connection,
    scope_key: str,
    config: SecurityConfig,
    now: int,
) -> int:
    """Incrementa fallos para un scope (cuenta o IP) y aplica bloqueo progresivo."""
    row = conn.execute(
        """
        SELECT failed_count, lockout_level, locked_until
        FROM login_attempts
        WHERE scope_key = ?
        """,
        (scope_key,),
    ).fetchone()

    failed_count = (int(row["failed_count"]) if row else 0) + 1
    lockout_level = int(row["lockout_level"]) if row else 0
    locked_until = int(row["locked_until"]) if row else 0

    if failed_count >= config.max_failed_attempts:
        lockout_level += 1
        duration = min(
            config.base_lockout_seconds * (2 ** (lockout_level - 1)),
            config.max_lockout_seconds,
        )
        locked_until = now + duration
    else:
        duration = 0

    conn.execute(
        """
        INSERT INTO login_attempts (
            scope_key, failed_count, lockout_level, locked_until, last_attempt_at
        )
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(scope_key) DO UPDATE SET
            failed_count = excluded.failed_count,
            lockout_level = excluded.lockout_level,
            locked_until = excluded.locked_until,
            last_attempt_at = excluded.last_attempt_at
        """,
        (scope_key, failed_count, lockout_level, locked_until, now),
    )
    return duration


def record_failed_login(
    conn: sqlite3.Connection,
    email: str,
    ip_address: str,
    config: SecurityConfig,
    now: int,
) -> int:
    """Registra un intento fallido por cuenta e IP y retorna duración de bloqueo si aplica."""
    acct_lock = _record_scope_failure(conn, f"acct:{email}", config, now)
    ip_lock = _record_scope_failure(conn, f"ip:{ip_address}", config, now)
    return max(acct_lock, ip_lock)


def clear_login_attempts(conn: sqlite3.Connection, email: str, ip_address: str) -> None:
    """Reinicia los contadores de intentos fallidos tras un inicio de sesión exitoso."""
    conn.execute(
        "DELETE FROM login_attempts WHERE scope_key IN (?, ?)",
        (f"acct:{email}", f"ip:{ip_address}"),
    )
