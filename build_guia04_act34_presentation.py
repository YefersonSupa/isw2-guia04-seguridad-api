"""Genera la presentación institucional UNSAAC de la Guía 04 (Actividades 3 y 4)."""

from __future__ import annotations

from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt

from build_guia04_presentation import (
    COLOR_BLUE,
    COLOR_DARK,
    COLOR_GREEN,
    COLOR_MAROON,
    COLOR_MUTED,
    COLOR_ORANGE,
    COLOR_RED,
    _add_card,
    _add_picture_fit,
    _set_header,
    _style_table,
)


def build_guia04_act34_presentation() -> None:
    """Construye la presentación oficial del Equipo 05 para Actividades 3 y 4."""
    script_dir = Path(__file__).resolve().parent
    base_pptx = script_dir.parent / "Plantilla" / "Unsaac_Plantilla 2026_GB.pptx"
    out_pptx = script_dir / "Guia4_Act3y4_Seguridad_ISW_Equipo05.pptx"
    capturas = script_dir / "capturas"

    prs = Presentation(str(base_pptx))
    while len(prs.slides) < 12:
        prs.slides.add_slide(prs.slide_layouts[2])

    # =========================================================================
    # SLIDE 1: PORTADA OFICIAL UNSAAC (EQUIPO 05 — ACTIVIDADES 3 Y 4)
    # =========================================================================
    s1 = prs.slides[0]
    s1.shapes[4].text_frame.text = (
        "FACULTAD DE INGENIERÍA ELÉCTRICA, ELECTRÓNICA, INFORMÁTICA Y MECÁNICA"
    )
    for p in s1.shapes[4].text_frame.paragraphs:
        p.font.name = "Arial"
        p.font.size = Pt(13.5)
        p.font.bold = True
        p.font.color.rgb = COLOR_MAROON

    s1.shapes[5].text_frame.text = (
        "ESCUELA PROFESIONAL DE INGENIERÍA INFORMÁTICA Y DE SISTEMAS"
    )
    for p in s1.shapes[5].text_frame.paragraphs:
        p.font.name = "Arial"
        p.font.size = Pt(11.5)
        p.font.bold = True
        p.font.color.rgb = COLOR_DARK

    s1.shapes[6].text_frame.text = "INGENIERÍA DE SOFTWARE II"
    for p in s1.shapes[6].text_frame.paragraphs:
        p.font.name = "Arial"
        p.font.size = Pt(22)
        p.font.bold = True
        p.font.color.rgb = COLOR_MAROON

    s1.shapes[7].text_frame.text = (
        "GUÍA DE PRÁCTICA 04 (ACTIVIDADES 3 Y 4): Ingeniería de Software Seguro — "
        "Diagnóstico SAST, Validación en Servidor, Hardening (SQLi, IDOR, XSS) y "
        "Verificación Automatizada"
    )
    for p in s1.shapes[7].text_frame.paragraphs:
        p.font.name = "Arial"
        p.font.size = Pt(13.5)
        p.font.bold = True
        p.font.color.rgb = COLOR_DARK

    s1.shapes[9].left = Inches(4.16)
    s1.shapes[9].top = Inches(3.55)
    s1.shapes[9].width = Inches(8.6)
    s1.shapes[9].height = Inches(0.85)
    s1.shapes[9].text_frame.text = (
        "EQUIPO: Equipo 05 (Mismo Grupo)  |  "
        "DOCENTE: Ing. Edwin Alvarez Mamani"
    )
    for p in s1.shapes[9].text_frame.paragraphs:
        p.font.name = "Arial"
        p.font.size = Pt(12.5)
        p.font.bold = True
        p.font.color.rgb = COLOR_MAROON

    s1.shapes[8].left = Inches(4.16)
    s1.shapes[8].top = Inches(4.25)
    s1.shapes[8].width = Inches(8.6)
    s1.shapes[8].height = Inches(2.6)
    s1.shapes[8].text_frame.text = (
        "INTEGRANTES / EQUIPO 05:\n"
        "• SUPA CUSIPAUCAR, Yeferson – 220553\n"
        "• VILLAVICENCIO SEGUIL, Edu Piero – 220555\n"
        "• MAMANI ZANABRIA, Jefersson – 170438\n"
        "• QUISPE LOCUMBER, Aldo – 220610\n"
        "• NIÑO DE GUZMÁN CONDE, Wendel Yovan – 192426"
    )
    for idx, p in enumerate(s1.shapes[8].text_frame.paragraphs):
        p.font.name = "Arial"
        p.font.size = Pt(12.0 if idx > 0 else 12.5)
        p.font.bold = True
        p.font.color.rgb = COLOR_MAROON if idx == 0 else COLOR_DARK
        p.space_after = Pt(2)

    # =========================================================================
    # SLIDE 2: ÍNDICE DE CONTENIDOS — ACTIVIDADES 3 Y 4
    # =========================================================================
    s2 = prs.slides[1]
    tf2 = s2.shapes[1].text_frame
    tf2.text = "Índice de Evidencias — Guía Práctica 04 (Actividades 3 y 4)"
    p0 = tf2.paragraphs[0]
    p0.font.name = "Arial"
    p0.font.size = Pt(18)
    p0.font.bold = True
    p0.font.color.rgb = COLOR_MAROON

    index_items = [
        (
            "Actividad 03: Despliegue y Diagnóstico SAST (app_vulnerable.py)",
            "Identificación exacta de líneas vulnerables (SQLi, IDOR, XSS) con Bandit y Pylint.",
        ),
        (
            "Ejercicio Propuesto 3.1: Validación Robusta en Servidor (POST /tasks)",
            "Contraste Antes vs. Después, límites de payload (413), bloqueo role=admin y logs OWASP.",
        ),
        (
            "Actividad 04: Refactorización y Hardening (app_segura.py)",
            "Prepared Statements, autorización HTTP 403, markupsafe.escape() y política CSP estricta.",
        ),
        (
            "Ejercicio Propuesto 4.1: Eliminación de SQL por Concatenación",
            "Búsquedas parametrizadas (LIKE ? ESCAPE), 5 escenarios borde y guardia anti-concatenación.",
        ),
        (
            "Verificación Integral, Reto RBAC y Análisis Metacognitivo",
            "14/14 pruebas pytest, Bandit 0 issues, Pylint 10/10, CI GitHub Actions y bitácora Drive.",
        ),
    ]
    for title, desc in index_items:
        p_t = tf2.add_paragraph()
        p_t.text = title
        p_t.font.name = "Arial"
        p_t.font.size = Pt(12.5)
        p_t.font.bold = True
        p_t.font.color.rgb = COLOR_DARK
        p_t.space_before = Pt(7)

        p_d = tf2.add_paragraph()
        p_d.text = desc
        p_d.font.name = "Arial"
        p_d.font.size = Pt(10)
        p_d.font.color.rgb = COLOR_MUTED

    # =========================================================================
    # SLIDE 3: ACTIVIDAD 3 - LÍNEAS VULNERABLES DETECTADAS
    # =========================================================================
    _set_header(
        prs.slides[2],
        "ACTIVIDAD 03: Diagnóstico de Líneas Vulnerables (app_vulnerable.py)",
        "Mapeo preciso de las brechas en el código base defectuoso (SportReserve Co. y ejemplos inseguros de la API de tareas):",
    )
    _style_table(
        prs.slides[2],
        [
            "Hallazgo",
            "Archivo y Línea Exacta",
            "Patrón Defectuoso Detectado",
            "CWE / Tipo",
            "Herramienta / Diagnóstico",
        ],
        [
            [
                "Hallazgo A\n(SQLi)",
                "sportreserve/app_vulnerable.py\nLínea 31",
                "query = f\"SELECT * FROM reservas WHERE id = {id_reserva}\"",
                "CWE-89\nCrítico",
                "Bandit B608 (Medium): f-string SQL permite id=999 OR 1=1.",
            ],
            [
                "Hallazgo A\n(IDOR)",
                "sportreserve/app_vulnerable.py\nLínea 39",
                "Retorna dict(reserva) sin comparar reserva['user_id'] con sesión",
                "CWE-639\nCrítico",
                "DAST / pytest: User_A lee reserva 105 de User_B (HTTP 200).",
            ],
            [
                "Hallazgo B\n(SQLi)",
                "sportreserve/app_vulnerable.py\nLínea 52",
                "\"SELECT ... WHERE correo = '\" + correo + \"'\"",
                "CWE-89\nCrítico",
                "Bandit B608 (Medium): ' OR '1'='1 filtra todos los usuarios.",
            ],
            [
                "Hallazgo C\n(XSS)",
                "sportreserve/app_vulnerable.py\nLíneas 78–79",
                "render_template_string(f\"... {nombre_saludo} ... {contenido}\")",
                "CWE-79\nAlto",
                "DAST / pytest: inyecta <script>alert(1)</script> sin escape.",
            ],
            [
                "Ej. 4.1\n(SQLi)",
                "task_api/vulnerable_examples.py\nLínea 61",
                "\"SELECT * FROM tasks WHERE title LIKE '%\" + search + \"%'\"",
                "CWE-89\nCrítico",
                "Bandit B608 (Medium): %' OR 1=1 -- expone tareas ajenas.",
            ],
        ],
        [1.35, 2.55, 3.65, 1.2, 3.35],
        top=1.60,
        height=5.2,
        cell_size=8.2,
        center_cols={3},
        badge_col=3,
    )

    # =========================================================================
    # SLIDE 4: ACTIVIDAD 3 - EVIDENCIA REAL SAST EN CÓDIGO VULNERABLE
    # =========================================================================
    _set_header(
        prs.slides[3],
        "ACTIVIDAD 03: Evidencia SAST en Código Vulnerable (Bandit + Pylint)",
        "Salida real en terminal ejecutando análisis estático sobre sportreserve/app_vulnerable.py y task_api/vulnerable_examples.py:",
    )
    _add_picture_fit(
        prs.slides[3],
        capturas / "captura_sast_vulnerable.png",
        0.55,
        1.55,
        8.25,
        5.35,
    )
    _add_card(
        prs.slides[3],
        8.95,
        1.55,
        3.85,
        5.35,
        "HALLAZGOS SAST (ANTES)",
        [
            "Bandit SAST (3 Alertas B608):",
            "Detecta con precisión los 3 puntos de inyección SQL (CWE-89) en líneas 31, 52 y 61.",
            "Limitación Clave de SAST:",
            "Pylint obtuvo 9.20/10 (solo docstrings) y Bandit no alerta sobre IDOR ni XSS semántico.",
            "Conclusión Técnica:",
            "El análisis estático debe complementarse obligatoriamente con pruebas negativas dinámicas (pytest/HTTP).",
        ],
        COLOR_RED,
        body_size=8.5,
    )

    # =========================================================================
    # SLIDE 5: EJERCICIO 3.1 - VALIDACIÓN EN SERVIDOR (POST /tasks)
    # =========================================================================
    _set_header(
        prs.slides[4],
        "EJERCICIO 3.1: Validación Robusta en Servidor (POST /tasks)",
        "Prevención de datos malformados, abuso de campos (Mass Assignment) y Log Injection conforme a recomendaciones OWASP:",
    )
    _style_table(
        prs.slides[4],
        [
            "Caso de Prueba (Ej. 3.1)",
            "Versión Insegura (Antes)",
            "Versión Segura (task_api/tasks_service.py)",
            "Código HTTP",
            "Registro de Auditoría (OWASP)",
        ],
        [
            ["1. Campo vacío / < 3 chars", "Acepta title=\"\" (HTTP 201)", "Rechaza título fuera de 3..120 caracteres", "400 Bad Request", "Registra param=title (sin payload)"],
            ["2. Campo largo / >16 KiB", "Guarda sin límite de tamaño", "title>120 / desc>1000 -> 400; body>16KiB -> 413", "400 / 413", "Registra regla de longitud"],
            ["3. Estado inválido", "Acepta status=\"hacked\"", "Lista blanca: pendiente, en_progreso, completada", "400 Bad Request", "Registra param=status"],
            ["4. Campo extra inyectado", "Acepta role=\"admin\" / owner_id", "Rechaza toda clave fuera de {title, description, status}", "400 Bad Request", "Registra extra_field:role sin contenido"],
            ["5. Unicode y espacios", "Guarda sin normalizar", "Normaliza .strip() preservando Unicode (Ñ, tildes)", "201 Created", "Aceptado y sanitizado en DOM"],
            ["6. Sin token de sesión", "Permite crear sin usuario real", "Exige Bearer token vigente en tabla sessions", "401 Unauthorized", "Acceso bloqueado en servidor"],
        ],
        [2.2, 2.25, 3.65, 1.4, 2.6],
        top=1.60,
        height=5.2,
        cell_size=8.1,
        center_cols={3},
    )

    # =========================================================================
    # SLIDE 6: ACTIVIDAD 4 - REFACTORIZACIÓN Y HARDENING (app_segura.py)
    # =========================================================================
    _set_header(
        prs.slides[5],
        "ACTIVIDAD 04: Refactorización y Hardening en sportreserve/app_segura.py",
        "Aplicación de defensas en profundidad sobre el código defectuoso para erradicar SQLi, IDOR y XSS en servidor:",
    )
    _add_card(
        prs.slides[5],
        0.55,
        1.60,
        3.95,
        5.1,
        "1. PREPARED STATEMENTS (SQLi)",
        [
            "Antes (Vulnerable):",
            "query = f\"SELECT * FROM reservas WHERE id = {id_reserva}\"",
            "Después (app_segura.py):",
            "query = \"SELECT * FROM reservas WHERE id = ?\"",
            "cursor.execute(query, (int(id_reserva),)).fetchone()",
            "Validación Complementaria:",
            "Verifica id_reserva.isdigit() y EMAIL_PATTERN devolviendo HTTP 400 ante datos inválidos.",
        ],
        COLOR_MAROON,
        body_size=8.4,
    )
    _add_card(
        prs.slides[5],
        4.70,
        1.60,
        3.95,
        5.1,
        "2. CONTROL DE PROPIEDAD (IDOR)",
        [
            "Antes (Vulnerable):",
            "Devolvía la reserva sin comprobar el dueño (User_A accedía a reserva 105 de User_B).",
            "Después (app_segura.py):",
            "if int(reserva['user_id']) != int(user_id_session):",
            "    abort(403, description='Acceso denegado...')",
            "Principio Aplicado:",
            "Autorización obligatoria en servidor por cada objeto solicitado sin filtrar campos privados.",
        ],
        COLOR_BLUE,
        body_size=8.4,
    )
    _add_card(
        prs.slides[5],
        8.85,
        1.60,
        3.95,
        5.1,
        "3. ESCAPE CONTEXTUAL + CSP (XSS)",
        [
            "Antes (Vulnerable):",
            "render_template_string() imprimía <script>alert(1)</script> ejecutable en el navegador.",
            "Después (app_segura.py):",
            "Uso estricto de markupsafe.escape() sobre autor, saludo y contenido de comentarios.",
            "Cabeceras HTTP de Hardening:",
            "CSP: default-src 'self'; script-src 'none'; object-src 'none'",
            "X-Content-Type-Options: nosniff | X-Frame-Options: DENY.",
        ],
        COLOR_GREEN,
        body_size=8.4,
    )

    # =========================================================================
    # SLIDE 7: ACTIVIDAD 4 - SAST POST-HARDENING Y GRÁFICO ANTES VS DESPUÉS
    # =========================================================================
    _set_header(
        prs.slides[6],
        "ACTIVIDAD 04: Verificación SAST Post-Hardening (Antes vs. Después)",
        "Cero vulnerabilidades en Bandit (1251 líneas) y calificación perfecta 10.00/10 en Pylint sobre el código refactorizado:",
    )
    _add_picture_fit(
        prs.slides[6],
        capturas / "captura_sast_segura.png",
        0.55,
        1.55,
        6.15,
        5.30,
    )
    _add_picture_fit(
        prs.slides[6],
        capturas / "grafico_sast_antes_despues.png",
        6.85,
        1.55,
        5.95,
        3.60,
    )
    _add_card(
        prs.slides[6],
        6.85,
        5.25,
        5.95,
        1.60,
        "RESULTADO DE HARDENING VERIFICADO",
        [
            "Reducción del 100 % de brechas: SQLi (3→0), IDOR (2→0), XSS (2→0), Mass Assignment (2→0).",
            "Pylint: 9.20/10 (base defectuosa) → 10.00/10 (código seguro sin supresiones #nosec).",
        ],
        COLOR_GREEN,
        title_size=10.2,
        body_size=8.4,
    )

    # =========================================================================
    # SLIDE 8: EJERCICIO 4.1 - BÚSQUEDAS PARAMETRIZADAS SIN CONCATENACIÓN
    # =========================================================================
    _set_header(
        prs.slides[7],
        "EJERCICIO 4.1: Eliminación de Consultas SQL por Concatenación",
        "Refactorización de búsqueda de tareas con placeholders parametrizados, escape de comodines LIKE y pruebas de borde:",
    )
    _add_card(
        prs.slides[7],
        0.55,
        1.58,
        5.95,
        2.55,
        "CÓDIGO INSEGURO ('ANTES' — vulnerable_examples.py)",
        [
            "query = \"SELECT * FROM tasks WHERE title LIKE '%\" + search + \"%'\"",
            "Peligro: El payload %' OR 1=1 -- cierra la cadena y altera el árbol SQL, filtrando tareas privadas de todos los usuarios.",
            "Resultado en prueba negativa: HTTP 200 devolviendo todas las filas de la tabla.",
        ],
        COLOR_RED,
        title_size=10.2,
        body_size=8.4,
    )
    _add_card(
        prs.slides[7],
        6.75,
        1.58,
        6.05,
        2.55,
        "CÓDIGO SEGURO ('DESPUÉS' — task_api/tasks_service.py)",
        [
            "cursor.execute(\"SELECT ... WHERE owner_id = ? AND title LIKE ? ESCAPE '\\\\'\", (user_id, f\"%{escaped}%\"))",
            "Nota: En SQLite3 el placeholder es '?' (equivalente a '%s' en PostgreSQL/MySQL).",
            "Defensa en profundidad: validación positiva de longitud (<=100) y caracteres + test guardia anti-concatenación.",
        ],
        COLOR_GREEN,
        title_size=10.2,
        body_size=8.4,
    )
    _style_table(
        prs.slides[7],
        ["Escenario (Ej. 4.1)", "Entrada Probada", "Comportamiento Esperado", "Resultado"],
        [
            ["1. Entrada normal", "search=Seguridad", "Retorna solo tareas propias coincidentes (HTTP 200)", "PASA"],
            ["2. Cadena larga", "search='a' * 101", "Rechaza por longitud > 100 (HTTP 400)", "PASA"],
            ["3. Comillas / SQLi", "search=' OR '1'='1", "Rechaza sin alterar estructura SQL (HTTP 400)", "PASA"],
            ["4. Caracteres hostiles", "<script>, ; DROP TABLE", "Rechaza por lista blanca de caracteres (HTTP 400)", "PASA"],
            ["5. Nulos / vacíos", "None, \"\", \"   \"", "Lista tareas propias sin error 500 (HTTP 200)", "PASA"],
        ],
        [2.3, 2.5, 5.8, 1.5],
        top=4.30,
        height=2.55,
        header_size=8.8,
        cell_size=8.0,
        center_cols={3},
        badge_col=3,
    )

    # =========================================================================
    # SLIDE 9: CONTRASTE HTTP REAL (ANTES vs DESPUÉS)
    # =========================================================================
    _set_header(
        prs.slides[8],
        "VERIFICACIÓN DINÁMICA: Pruebas HTTP Antes vs. Después",
        "Ejecución real de peticiones HTTP contra app_vulnerable.py, app_segura.py y /tasks demostrando el bloqueo efectivo:",
    )
    _add_picture_fit(
        prs.slides[8],
        capturas / "captura_http_sportreserve_diff.png",
        0.55,
        1.55,
        8.25,
        5.35,
    )
    _add_card(
        prs.slides[8],
        8.95,
        1.55,
        3.85,
        5.35,
        "IMPACTO COMPROBADO",
        [
            "Hallazgo A (IDOR):",
            "Pasó de HTTP 200 (fuga de reserva de User_B) a HTTP 403 Forbidden sin datos.",
            "Hallazgo B (SQLi Correo):",
            "Pasó de filtrar 3 usuarios completos a HTTP 400 Bad Request.",
            "Hallazgo C (XSS):",
            "Pasó de inyectar <script> crudo a salida escapada + CSP script-src 'none'.",
            "API Tareas (Ej. 3.1 y 4.1):",
            "Bloquea role='admin' y SQLi %' OR 1=1 -- con HTTP 400 y auditoría limpia.",
        ],
        COLOR_BLUE,
        body_size=8.4,
    )

    # =========================================================================
    # SLIDE 10: SUITE AUTOMATIZADA PYTEST (14/14 PASSED)
    # =========================================================================
    _set_header(
        prs.slides[9],
        "AUTOMATIZACIÓN DE PRUEBAS: Suite pytest (14/14 Aprobadas) y CI",
        "Ejecución reproducible en .venv y validación continua en GitHub Actions cubriendo toda la Guía Práctica 04:",
    )
    _add_picture_fit(
        prs.slides[9],
        capturas / "captura_pytest_act34.png",
        0.55,
        1.55,
        8.25,
        5.35,
    )
    _add_card(
        prs.slides[9],
        8.95,
        1.55,
        3.85,
        5.35,
        "COBERTURA AUTOMATIZADA",
        [
            "test_auth_security.py (7 pruebas):",
            "Argon2id, fuerza bruta 429, regeneración/expiración, token 1-uso y frontend CSP.",
            "test_sportreserve_security.py (2):",
            "Reproducción controlada en app_vulnerable.py y bloqueo total en app_segura.py.",
            "test_tasks_security.py (5 pruebas):",
            "Validación 400/413, SQLi, IDOR 403, Reto RBAC y guardia estática SQL.",
            "GitHub Actions CI:",
            "Ejecuta pytest + bandit + pylint automáticamente en cada push a main.",
        ],
        COLOR_GREEN,
        body_size=8.3,
    )

    # =========================================================================
    # SLIDE 11: TABLA OFICIAL DE RESULTADOS CONSOLIDADA
    # =========================================================================
    _set_header(
        prs.slides[10],
        "TABLA CONSOLIDADA DE RESULTADOS Y VERIFICACIÓN (PT-01 a PT-12)",
        "Registro formal de aserciones positivas, negativas y controles de seguridad validados en entorno reproducible:",
    )
    _style_table(
        prs.slides[10],
        ["ID", "Escenario / Requisito Evaluado", "Herramienta", "Esperado", "Obtenido", "Estado"],
        [
            ["PT-01", "Registro Argon2id + bloqueo role='admin'", "pytest / SQLite", "$argon2id$ / 400", "Verificado", "PASA"],
            ["PT-02", "Fuerza bruta por cuenta e IP", "pytest / HTTP", "HTTP 429 progresivo", "30s → 60s", "PASA"],
            ["PT-03", "Regeneración, expiración y reset 1-uso", "pytest / HTTP", "401 / 400 + 0 tokens", "Verificado", "PASA"],
            ["PT-04", "Frontend HTML + CSP sin unsafe-inline", "pytest / Flask", "HTTP 200 + CSP 'self'", "Verificado", "PASA"],
            ["PT-05", "Diagnóstico SAST en app_vulnerable.py", "Bandit / Pylint", "Detecta SQLi B608", "3 B608 + 9.20/10", "PASA"],
            ["PT-06", "SportReserve IDOR (User_A -> id=105)", "pytest / app_segura", "HTTP 403 sin datos", "HTTP 403", "PASA"],
            ["PT-07", "SportReserve SQLi (id y correo)", "pytest / app_segura", "HTTP 400 / 0 fugas", "HTTP 400", "PASA"],
            ["PT-08", "SportReserve XSS (<script>alert(1))", "pytest / app_segura", "Escapado + CSP", "&lt;script&gt;", "PASA"],
            ["PT-09", "POST /tasks validación + payload >16KiB", "pytest / tasks_api", "HTTP 400 / 413 + log", "7 logs OWASP", "PASA"],
            ["PT-10", "GET /tasks búsqueda SQLi y casos borde", "pytest / tasks_api", "400 SQLi / 200 nulo", "Verificado", "PASA"],
            ["PT-11", "Reto RBAC (estudiante/docente/admin)", "pytest / tasks_api", "Docente lee, 403 edit", "Verificado", "PASA"],
            ["PT-12", "SAST final + Guardia anti-SQL concat.", "Bandit / Pylint", "0 issues / 10.00", "0 / 10.00/10", "PASA"],
        ],
        [0.85, 3.85, 1.95, 2.35, 2.05, 1.05],
        top=1.55,
        height=5.35,
        header_size=8.6,
        cell_size=7.5,
        center_cols={0, 2, 5},
        badge_col=5,
    )

    # =========================================================================
    # SLIDE 12: METACOGNICIÓN, RETO RBAC, GITHUB Y DRIVE
    # =========================================================================
    _set_header(
        prs.slides[11],
        "ANÁLISIS METACOGNITIVO, RETO RBAC Y REPOSITORIOS OFICIALES",
        "Reflexión sobre causas raíz, extensión arquitectónica RBAC y enlaces verificables de entrega del Equipo 05:",
    )
    _add_card(
        prs.slides[11],
        0.55,
        1.60,
        3.95,
        5.1,
        "1. ANÁLISIS METACOGNITIVO",
        [
            "SAST vs. Pruebas Negativas:",
            "Bandit detectó los 3 SQLi (B608), pero no IDOR ni XSS semántico; se requiere SAST + DAST/pytest.",
            "Parametrización vs. Validación:",
            "Las consultas parametrizadas separan código y datos en el motor SQL; la validación es defensa complementaria.",
            "Prevención de Log Injection:",
            "Registrar solo la regla violada (extra_field:role) y correo enmascarado evita falsificar bitácoras.",
        ],
        COLOR_MAROON,
        body_size=8.3,
    )
    _add_card(
        prs.slides[11],
        4.70,
        1.60,
        3.95,
        5.1,
        "2. RETO COMPLEJO DE EXTENSIÓN",
        [
            "Control RBAC Multi-Rol Implementado:",
            "Rol estudiante: aislamiento total por owner_id (HTTP 403 en tareas ajenas).",
            "Rol docente: supervisión de lectura (GET /tasks), bloqueado con HTTP 403 al editar o borrar tareas ajenas.",
            "Rol administrador: gestión integral con registro auditable en audit_logs.",
            "Guardia Estática en CI:",
            "Test automatizado impide introducir f-strings o concatenación SQL en futuras versiones.",
        ],
        COLOR_ORANGE,
        body_size=8.3,
    )
    _add_card(
        prs.slides[11],
        8.85,
        1.60,
        3.95,
        5.1,
        "3. REPOSITORIO GITHUB Y BITÁCORA",
        [
            "Repositorio GitHub (CI en Verde):",
            "https://github.com/YefersonSupa/isw2-guia04-seguridad-api",
            "Bitácora Google Drive (Equipo 05):",
            "https://drive.google.com/drive/folders/1S-F9LnMze7nOk9m7HgX4QdU20abIEQLo?usp=sharing",
            "Cierre de Guía Práctica 04:",
            "Actividades 1, 2, 3 y 4 completadas al 100 % con código fuente, frontend web, pruebas (14/14) e informe LaTeX.",
        ],
        COLOR_GREEN,
        body_size=8.3,
    )

    prs.save(str(out_pptx))
    print(f"Presentación Actividades 3 y 4 guardada en: {out_pptx}")


if __name__ == "__main__":
    build_guia04_act34_presentation()
