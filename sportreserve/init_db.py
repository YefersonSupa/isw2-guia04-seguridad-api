"""Inicializador de base de datos SQLite3 (reservas.db) para SportReserve Co."""

from __future__ import annotations

import sqlite3

RESERVAS_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    correo TEXT NOT NULL UNIQUE,
    telefono TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reservas (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    cancha TEXT NOT NULL,
    fecha TEXT NOT NULL,
    horario TEXT NOT NULL,
    monto REAL NOT NULL,
    estado TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES usuarios (id)
);

CREATE TABLE IF NOT EXISTS comentarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    autor TEXT NOT NULL,
    contenido TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES usuarios (id)
);
"""


def init_reservas_db(db_path: str = "reservas.db") -> None:
    """Crea el esquema y carga datos semilla consistentes con /reservas?id=104 y 105."""
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(RESERVAS_SCHEMA_SQL)
        existing = conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
        if existing == 0:
            conn.executemany(
                "INSERT INTO usuarios (id, nombre, correo, telefono) VALUES (?, ?, ?, ?)",
                [
                    (1, "User_A (Yeferson Supa)", "user_a@sportreserve.pe", "984100201"),
                    (2, "User_B (Piero Villavicencio)", "user_b@sportreserve.pe", "984100202"),
                    (3, "Admin SportReserve", "admin@sportreserve.pe", "984000000"),
                ],
            )
            conn.executemany(
                """
                INSERT INTO reservas (id, user_id, cancha, fecha, horario, monto, estado)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        104, 1, "Cancha Sintética A",
                        "2026-11-20", "18:00-19:00", 120.0, "confirmada",
                    ),
                    (
                        105, 2, "Cancha VIP B (Privada)",
                        "2026-11-20", "19:00-20:00", 180.0, "pagada",
                    ),
                ],
            )
            conn.execute(
                "INSERT INTO comentarios (user_id, autor, contenido) VALUES (?, ?, ?)",
                (1, "User_A", "Excelente iluminación en la cancha principal."),
            )
            conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init_reservas_db()
    print("Base de datos reservas.db inicializada correctamente.")
