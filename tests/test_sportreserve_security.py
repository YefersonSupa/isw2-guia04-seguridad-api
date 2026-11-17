"""Pruebas de contraste SportReserve Co.: app_vulnerable.py (Act. 3) vs app_segura.py (Act. 4)."""

from __future__ import annotations

from pathlib import Path

from sportreserve.app_segura import create_secure_app
from sportreserve.app_vulnerable import create_vulnerable_app


def test_app_vulnerable_exposes_idor_sqli_and_xss(tmp_path: Path) -> None:
    """Confirma reproducción controlada de los Hallazgos A, B y C en app_vulnerable.py."""
    db_file = str(tmp_path / "reservas_vuln.db")
    client = create_vulnerable_app(db_file).test_client()

    # Hallazgo A (IDOR): User_A (user_id=1) lee reserva privada 105 de User_B
    idor_resp = client.get("/api/reserva?id=105&user_id=1")
    assert idor_resp.status_code == 200
    assert idor_resp.get_json()["reserva"]["user_id"] == 2

    # Hallazgo A (SQLi): inyección booleana en parámetro id
    sqli_id_resp = client.get("/api/reserva?id=999%20OR%201=1&user_id=1")
    assert sqli_id_resp.status_code == 200
    assert sqli_id_resp.get_json()["reserva"]["id"] == 104

    # Hallazgo B (SQLi correo): bypass que filtra todos los usuarios
    sqli_email_resp = client.get("/api/usuarios/buscar?correo='%20OR%20'1'='1")
    assert sqli_email_resp.status_code == 200
    assert len(sqli_email_resp.get_json()["resultados"]) >= 3

    # Hallazgo C (XSS reflejado): etiqueta <script> se imprime sin escapar
    xss_resp = client.get("/comentarios?nombre=<script>alert(1)</script>")
    assert xss_resp.status_code == 200
    assert "<script>alert(1)</script>" in xss_resp.get_data(as_text=True)


def test_app_segura_mitigates_idor_sqli_xss_and_invalid_inputs(tmp_path: Path) -> None:
    """Verifica mitigación completa (HTTP 403/400, parametrización y escape XSS) en app_segura.py."""
    db_file = str(tmp_path / "reservas_safe.db")
    client = create_secure_app(db_file).test_client()

    # Acceso legítimo: User_A consulta su propia reserva 104 -> HTTP 200
    ok_resp = client.get("/api/reserva?id=104&user_id=1")
    assert ok_resp.status_code == 200
    assert ok_resp.get_json()["reserva"]["id"] == 104

    # RE-01 (IDOR mitigado): User_A intenta ver reserva 105 de User_B -> HTTP 403 sin datos
    idor_blocked = client.get("/api/reserva?id=105&user_id=1")
    assert idor_blocked.status_code == 403
    assert "reserva" not in idor_blocked.get_json()

    # RE-02 y RE-04 (SQLi y parámetros malformados mitigados): -> HTTP 400
    assert client.get("/api/reserva?id=999%20OR%201=1&user_id=1").status_code == 400
    assert client.get("/api/reserva?id=abc&user_id=1").status_code == 400
    assert client.get("/api/reserva?id=104").status_code == 400

    # Hallazgo B mitigado: payload SQLi en correo -> HTTP 400; correo válido -> 1 fila
    assert client.get("/api/usuarios/buscar?correo='%20OR%20'1'='1").status_code == 400
    valid_user = client.get("/api/usuarios/buscar?correo=user_a@sportreserve.pe")
    assert valid_user.status_code == 200
    assert len(valid_user.get_json()["resultados"]) == 1

    # RE-03 (XSS reflejado y almacenado mitigado con markupsafe.escape + CSP)
    post_xss = client.post(
        "/comentarios",
        data={"nombre": "<b>Eva</b>", "comentario": "<script>alert('xss')</script>"},
    )
    assert post_xss.status_code == 200
    body_post = post_xss.get_data(as_text=True)
    assert "<script>alert('xss')</script>" not in body_post
    assert "&lt;script&gt;alert(&#39;xss&#39;)&lt;/script&gt;" in body_post

    get_xss = client.get("/comentarios?nombre=<script>alert(1)</script>")
    assert get_xss.status_code == 200
    body_get = get_xss.get_data(as_text=True)
    assert "<script>alert(1)</script>" not in body_get
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in body_get
    assert "script-src 'none'" in get_xss.headers["Content-Security-Policy"]
    assert get_xss.headers["X-Content-Type-Options"] == "nosniff"
    assert get_xss.headers["X-Frame-Options"] == "DENY"
