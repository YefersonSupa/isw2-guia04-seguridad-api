"""Aplicación vulnerable base de SportReserve Co. para diagnóstico SAST (Actividad 3).

ADVERTENCIA: Este módulo contiene vulnerabilidades intencionales (SQLi, IDOR y XSS)
exclusivamente para fines académicos de auditoría SAST y demostración controlada.
"""

import sqlite3
from flask import Flask, request, jsonify, render_template_string

from sportreserve.init_db import init_reservas_db

app = Flask(__name__)
DB_PATH = "reservas.db"


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# VULNERABILIDAD 1 (Hallazgo A): Inyección SQL + IDOR
@app.route('/api/reserva', methods=['GET'])
def obtener_reserva():
    id_reserva = request.args.get('id')
    user_id_session = request.args.get('user_id')  # Simulación de usuario en sesión

    conn = get_db_connection()
    cursor = conn.cursor()
    # Inseguro: Concatenación directa de entradas en la consulta SQL (SQLi)
    query = f"SELECT * FROM reservas WHERE id = {id_reserva}"
    reserva = cursor.execute(query).fetchone()
    conn.close()

    if not reserva:
        return jsonify({"error": "Reserva no encontrada"}), 404

    # Inseguro (IDOR): No verifica si reserva['user_id'] pertenece a user_id_session
    return jsonify({
        "session_user_id": user_id_session,
        "reserva": dict(reserva),
    }), 200


# VULNERABILIDAD 2 (Hallazgo B): Inyección SQL en búsqueda de usuarios por correo
@app.route('/api/usuarios/buscar', methods=['GET'])
def buscar_usuario_por_correo():
    correo = request.args.get('correo', '')
    conn = get_db_connection()
    cursor = conn.cursor()
    # Inseguro: Concatenación directa sin parametrización
    query = "SELECT id, nombre, correo, telefono FROM usuarios WHERE correo = '" + correo + "'"
    filas = cursor.execute(query).fetchall()
    conn.close()
    return jsonify({"resultados": [dict(f) for f in filas]}), 200


# VULNERABILIDAD 3 (Hallazgo C): XSS Reflejado y Almacenado sin filtro ni escape HTML
@app.route('/comentarios', methods=['GET', 'POST'])
def gestionar_comentarios():
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        autor = request.form.get('nombre', 'Anonimo')
        contenido = request.form.get('comentario', '')
        cursor.execute(
            "INSERT INTO comentarios (user_id, autor, contenido) VALUES (1, ?, ?)",
            (autor, contenido),
        )
        conn.commit()

    nombre_saludo = request.args.get('nombre', 'Invitado')
    comentarios = cursor.execute("SELECT autor, contenido FROM comentarios").fetchall()
    conn.close()

    # Inseguro (XSS): Renderización directa en render_template_string sin escape
    items_html = "".join(
        f"<li><strong>{c['autor']}:</strong> {c['contenido']}</li>" for c in comentarios
    )
    html = f"<h1>Portal SportReserve - Hola {nombre_saludo}</h1><ul>{items_html}</ul>"
    return render_template_string(html)


def create_vulnerable_app(db_path: str = "reservas.db") -> Flask:
    """Configura la ruta de BD e inicializa tablas para pruebas controladas."""
    global DB_PATH  # pylint: disable=global-statement
    DB_PATH = db_path
    init_reservas_db(db_path)
    return app


if __name__ == '__main__':
    init_reservas_db(DB_PATH)
    app.run(host='127.0.0.1', port=5001, debug=False)
