"""Genera la presentación institucional UNSAAC de la Guía 04 (Actividades 1 y 2)."""

from __future__ import annotations

import os
from pathlib import Path
from PIL import Image as PILImage
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt


COLOR_MAROON = RGBColor(140, 29, 34)
COLOR_DARK = RGBColor(33, 37, 41)
COLOR_MUTED = RGBColor(92, 102, 112)
COLOR_RED = RGBColor(220, 53, 69)
COLOR_GREEN = RGBColor(25, 135, 84)
COLOR_ORANGE = RGBColor(217, 119, 6)
COLOR_BLUE = RGBColor(29, 78, 216)
COLOR_BG_CARD = RGBColor(248, 249, 252)
COLOR_ALT_ROW = RGBColor(245, 246, 250)
COLOR_BORDER = RGBColor(222, 226, 230)
COLOR_WHITE = RGBColor(255, 255, 255)


def _set_header(slide, title_text: str, subtitle_text: str) -> None:
    """Configura título institucional, limpia placeholders previos y agrega subtítulo."""
    title_shape = slide.shapes[0]
    title_shape.left = Inches(2.2)
    title_shape.top = Inches(0.20)
    title_shape.width = Inches(10.2)
    title_shape.height = Inches(0.88)
    title_shape.text_frame.text = title_text
    for p in title_shape.text_frame.paragraphs:
        p.font.name = "Arial"
        p.font.size = Pt(18.5)
        p.font.bold = True
        p.font.color.rgb = COLOR_DARK

    for shape in list(slide.shapes)[1:]:
        el = shape._element
        el.getparent().remove(el)

    sub = slide.shapes.add_textbox(Inches(0.6), Inches(1.15), Inches(12.1), Inches(0.35))
    sub.text_frame.word_wrap = True
    sub.text_frame.text = subtitle_text
    p_sub = sub.text_frame.paragraphs[0]
    p_sub.font.name = "Arial"
    p_sub.font.size = Pt(10.5)
    p_sub.font.color.rgb = COLOR_MUTED


def _style_table(
    slide,
    headers: list[str],
    rows: list[list[str]],
    col_widths: list[float],
    top: float = 1.55,
    height: float = 5.3,
    header_size: float = 9.5,
    cell_size: float = 8.2,
    center_cols: set[int] | None = None,
    badge_col: int | None = None,
) -> None:
    """Inserta y formatea una tabla con paleta institucional UNSAAC."""
    total_w = sum(col_widths)
    left = (13.333 - total_w) / 2
    t_shape = slide.shapes.add_table(
        len(rows) + 1,
        len(headers),
        Inches(left),
        Inches(top),
        Inches(total_w),
        Inches(height),
    )
    tbl = t_shape.table
    for idx, w in enumerate(col_widths):
        tbl.columns[idx].width = Inches(w)

    center_set = center_cols or set()

    for c_i, h_text in enumerate(headers):
        cell = tbl.cell(0, c_i)
        cell.text = h_text
        cell.fill.solid()
        cell.fill.fore_color.rgb = COLOR_MAROON
        p = cell.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        p.font.name = "Arial"
        p.font.size = Pt(header_size)
        p.font.bold = True
        p.font.color.rgb = COLOR_WHITE

    for r_i, row in enumerate(rows):
        for c_i, val in enumerate(row):
            cell = tbl.cell(r_i + 1, c_i)
            cell.text = val
            cell.fill.solid()
            cell.fill.fore_color.rgb = COLOR_ALT_ROW if r_i % 2 == 0 else COLOR_WHITE
            p = cell.text_frame.paragraphs[0]
            p.font.name = "Arial"
            p.font.size = Pt(cell_size)
            p.alignment = PP_ALIGN.CENTER if c_i in center_set else PP_ALIGN.LEFT

            if c_i == 0:
                p.font.bold = True
                p.font.color.rgb = COLOR_MAROON
            elif badge_col is not None and c_i == badge_col:
                p.font.bold = True
                upper = val.upper()
                if "CRÍTIC" in upper or "OBLIGATORI" in upper:
                    p.font.color.rgb = COLOR_RED
                elif "ALTO" in upper or "ALTA" in upper or "IMPORTANTE" in upper:
                    p.font.color.rgb = COLOR_ORANGE
                else:
                    p.font.color.rgb = COLOR_GREEN
            else:
                p.font.color.rgb = COLOR_DARK


def _add_card(
    slide,
    left: float,
    top: float,
    width: float,
    height: float,
    title: str,
    lines: list[str],
    accent: RGBColor,
    title_size: float = 11.0,
    body_size: float = 8.8,
) -> None:
    """Agrega una tarjeta de contenido con borde y jerarquía tipográfica."""
    card = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height)
    )
    card.fill.solid()
    card.fill.fore_color.rgb = COLOR_BG_CARD
    card.line.color.rgb = accent
    card.line.width = Pt(1.5)

    tf = card.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.16)
    tf.margin_right = Inches(0.16)
    tf.margin_top = Inches(0.14)
    tf.margin_bottom = Inches(0.14)

    p0 = tf.paragraphs[0]
    p0.text = title
    p0.font.name = "Arial"
    p0.font.size = Pt(title_size)
    p0.font.bold = True
    p0.font.color.rgb = accent
    p0.space_after = Pt(6)

    for item in lines:
        p = tf.add_paragraph()
        if item.endswith(":"):
            p.text = f"▸ {item}"
            p.font.name = "Arial"
            p.font.size = Pt(body_size + 0.5)
            p.font.bold = True
            p.font.color.rgb = COLOR_DARK
            p.space_before = Pt(4)
        elif item.startswith("http"):
            p.text = item
            p.font.name = "Arial"
            p.font.size = Pt(body_size - 0.3)
            p.font.bold = True
            p.font.color.rgb = COLOR_MAROON
            p.space_after = Pt(3)
        else:
            p.text = f"▪ {item}"
            p.font.name = "Arial"
            p.font.size = Pt(body_size)
            p.font.color.rgb = COLOR_DARK
            p.space_after = Pt(3)


def _add_picture_fit(
    slide, img_path: Path, left: float, top: float, max_w: float, max_h: float
) -> None:
    """Inserta una imagen preservando exactamente su relación de aspecto dentro del recuadro."""
    with PILImage.open(img_path) as im:
        iw, ih = im.size
    ratio = min(max_w / iw, max_h / ih)
    w = iw * ratio
    h = ih * ratio
    x = left + (max_w - w) / 2
    y = top + (max_h - h) / 2
    slide.shapes.add_picture(str(img_path), Inches(x), Inches(y), Inches(w), Inches(h))


def build_guia04_presentation() -> None:
    """Construye la presentación completa de las Actividades 1 y 2 de la Guía 04."""
    script_dir = Path(__file__).resolve().parent
    base_pptx = script_dir.parent / "Plantilla" / "Unsaac_Plantilla 2026_GB.pptx"
    out_pptx = script_dir / "Guia4_Act1y2_Seguridad_ISW_Equipo05.pptx"
    capturas = script_dir / "capturas"

    prs = Presentation(str(base_pptx))
    while len(prs.slides) < 13:
        prs.slides.add_slide(prs.slide_layouts[2])

    # =========================================================================
    # SLIDE 1: PORTADA OFICIAL UNSAAC (EQUIPO 05 - 5 INTEGRANTES)
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
        "GUÍA DE PRÁCTICA 04 (ACTIVIDADES 1 Y 2): Ingeniería de Software Seguro — "
        "Modelado STRIDE, Matrices de Riesgo P×I, Autenticación Resistente y "
        "Requisitos Verificables"
    )
    for p in s1.shapes[7].text_frame.paragraphs:
        p.font.name = "Arial"
        p.font.size = Pt(13.5)
        p.font.bold = True
        p.font.color.rgb = COLOR_DARK

    # Reordenar posiciones verticales de Equipo/Docente (shape 9) e Integrantes (shape 8)
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
    # SLIDE 2: ÍNDICE DE CONTENIDOS
    # =========================================================================
    s2 = prs.slides[1]
    tf2 = s2.shapes[1].text_frame
    tf2.text = "Índice de Evidencias — Guía Práctica 04 (Actividades 1 y 2)"
    p0 = tf2.paragraphs[0]
    p0.font.name = "Arial"
    p0.font.size = Pt(18)
    p0.font.bold = True
    p0.font.color.rgb = COLOR_MAROON

    index_items = [
        (
            "Actividad 01: Modelado de Amenazas STRIDE y Matriz P×I (SportReserve Co.)",
            "Evaluación cuantitativa de Hallazgos A (IDOR), B (SQLi) y C (XSS) bajo impacto C-I-D.",
        ),
        (
            "Ejercicio Propuesto 1.1: Arquitectura, Límites de Confianza y Top 5 Riesgos",
            "Diagrama de componentes de la API de Tareas, matriz STRIDE completa y plan priorizado.",
        ),
        (
            "Ejercicio Propuesto 1.2: Autenticación Resistente a Ataques Comunes",
            "Implementación real en Flask + Argon2id, bloqueo progresivo, tokens únicos, pytest y SAST.",
        ),
        (
            "Actividad 02: Requisitos de Seguridad Verificables (RE-01 a RE-04)",
            "Criterios de aceptación negativos con códigos HTTP 403 Forbidden y 400 Bad Request.",
        ),
        (
            "Ejercicio Propuesto 2.1: Requisitos RF/RS y Matriz de Trazabilidad",
            "10 Requisitos Funcionales, mapeo de activos, 10 Requisitos de Seguridad y trazabilidad completa.",
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
    # SLIDE 3: ACTIVIDAD 1 - MATRIZ P×I SPORTRESERVE CO.
    # =========================================================================
    _set_header(
        prs.slides[2],
        "ACTIVIDAD 01: Modelado STRIDE y Matriz de Riesgos P×I (SportReserve Co.)",
        "Evaluación del Caso Práctico 01 según taxonomía STRIDE, impacto C-I-D y escala 1–4 Bajo | 5–9 Medio | 10–16 Alto | 17–25 Crítico:",
    )
    _style_table(
        prs.slides[2],
        [
            "Hallazgo",
            "Categoría STRIDE",
            "Actor | Vulnerabilidad",
            "P",
            "I",
            "Riesgo (P×I)",
            "Controles Prioritarios",
        ],
        [
            [
                "Hallazgo A:\nAlteración ID en\n/reservas?id=104\na 105 expone datos",
                "Elevation of Privilege /\nInformation Disclosure",
                "Usuario autenticado malicioso |\nIDOR: ausencia de verificación\nde propiedad en servidor",
                "4",
                "5",
                "20 (Crítico)",
                "Validar reserva.user_id == session.user_id;\nresponder HTTP 403 Forbidden sin fuga de datos.",
            ],
            [
                "Hallazgo B:\nBúsqueda por correo\nsin parametrización\nen BD",
                "Tampering /\nInformation Disclosure",
                "Atacante externo o cliente |\nSQL Injection por concatenación\ndirecta en consulta SQL",
                "5",
                "5",
                "25 (Crítico)",
                "Consultas parametrizadas (Prepared Statements)\n+ validación positiva de formato de correo.",
            ],
            [
                "Hallazgo C:\nComentarios o nombres\nsin filtro de salida",
                "Tampering /\nInformation Disclosure",
                "Usuario externo / atacante |\nXSS Reflejado y Almacenado\nal imprimir HTML sin escapar",
                "4",
                "4",
                "16 (Alto)",
                "Escapado contextual en servidor (markupsafe.escape)\n+ política Content-Security-Policy (CSP).",
            ],
        ],
        [2.2, 1.9, 2.5, 0.55, 0.55, 1.35, 3.15],
        top=1.65,
        height=5.0,
        cell_size=8.6,
        center_cols={3, 4, 5},
        badge_col=5,
    )

    # =========================================================================
    # SLIDE 4: EJERCICIO 1.1 - ARQUITECTURA Y LÍMITES DE CONFIANZA
    # =========================================================================
    _set_header(
        prs.slides[3],
        "EJERCICIO 1.1: Diagrama de Componentes y Límites de Confianza",
        "Identificación previa de actores, activos, componentes y fronteras de confianza para la API web de gestión de tareas:",
    )
    _add_picture_fit(
        prs.slides[3],
        capturas / "diagrama_arquitectura_stride.png",
        0.55,
        1.55,
        8.15,
        5.25,
    )
    _add_card(
        prs.slides[3],
        8.8,
        1.60,
        4.0,
        4.85,
        "COMPONENTES Y FRONTERAS",
        [
            "Límite 1 (Internet — No Confiable):",
            "Navegador/cliente envía credenciales, tokens y JSON de tareas vía HTTPS.",
            "Límite 2 (Red Interna — API Flask):",
            "Valida entradas, ejecuta Argon2id, bloqueos progresivos, RBAC y auditoría.",
            "Límite 3 (Base de Datos SQLite3):",
            "Almacena usuarios, sesiones hasheadas, tokens de reset y tareas con SQL parametrizado.",
            "Límite 4 (Correo y Archivos):",
            "SMTP envía tokens de 1 solo uso; almacenamiento guarda adjuntos aislados del código.",
        ],
        COLOR_MAROON,
        body_size=8.5,
    )

    # =========================================================================
    # SLIDE 5: EJERCICIO 1.1 - MATRIZ STRIDE Y TOP 5 AMENAZAS
    # =========================================================================
    _set_header(
        prs.slides[4],
        "EJERCICIO 1.1: Matriz STRIDE Completa y Plan de Mitigación (Top 5)",
        "Aplicación sistemática de las 6 amenazas STRIDE sobre los flujos de la API y priorización de las cinco amenazas más críticas:",
    )
    _style_table(
        prs.slides[4],
        [
            "Prioridad / Amenaza",
            "Categoría STRIDE",
            "Activo Afectado",
            "Escenario en la API de Tareas",
            "P",
            "I",
            "Nivel",
            "Mitigación Priorizada",
        ],
        [
            [
                "#1: Escalar rol",
                "Elevation of Privilege",
                "Cuentas y roles RBAC",
                "Enviar role='admin' en POST /register",
                "4",
                "5",
                "20 (Crítico)",
                "Lista blanca de campos; rol fijo 'estudiante' en servidor.",
            ],
            [
                "#2: Fijación / robo token",
                "Spoofing",
                "Tokens de sesión",
                "Reutilizar o falsificar sesión tras login",
                "4",
                "4",
                "16 (Alto)",
                "Tokens 256-bit, SHA-256 en BD y regeneración en login.",
            ],
            [
                "#3: Fuga tareas ajenas",
                "Information Disclosure",
                "Tareas y datos personales",
                "Listar o consultar tareas de otro owner_id",
                "4",
                "4",
                "16 (Alto)",
                "Control de propiedad (owner_id == user_id) y HTTP 403.",
            ],
            [
                "#4: Fuerza bruta / flood",
                "Denial of Service",
                "Endpoint /auth/login",
                "Miles de intentos contra cuentas o registro",
                "5",
                "3",
                "15 (Alto)",
                "Límite por cuenta/IP + bloqueo progresivo HTTP 429.",
            ],
            [
                "#5: Modificar/borrar sin rastro",
                "Tampering / Repudio",
                "Tareas y bitácora",
                "Alterar owner_id o borrar sin registro auditable",
                "3",
                "4",
                "12 (Alto)",
                "Auditoría inmutable en audit_logs + rechazo de owner_id.",
            ],
        ],
        [1.45, 1.5, 1.45, 2.35, 0.45, 0.45, 1.15, 3.3],
        top=1.60,
        height=5.2,
        cell_size=8.1,
        center_cols={4, 5, 6},
        badge_col=6,
    )

    # =========================================================================
    # SLIDE 6: MAPA DE CALOR P×I CONSOLIDADO
    # =========================================================================
    _set_header(
        prs.slides[5],
        "ACTIVIDAD 01 + EJ. 1.1: Mapa de Calor de Riesgos P×I Consolidado",
        "Visualización unificada de riesgos críticos y altos para SportReserve Co. (H-A..H-C) y API de Tareas (T1..T5):",
    )
    _add_picture_fit(
        prs.slides[5],
        capturas / "matriz_riesgos_pxi.png",
        0.55,
        1.55,
        8.20,
        5.25,
    )
    _add_card(
        prs.slides[5],
        8.9,
        1.58,
        3.9,
        5.05,
        "CRITERIOS DE PRIORIZACIÓN",
        [
            "Zona Crítica (17–25):",
            "H-B SQLi (25), H-A IDOR (20) y T1 Elevación de rol (20). Bloquean salida a producción.",
            "Zona Alta (10–16):",
            "H-C XSS (16), T2 Spoofing (16), T3 Fuga tareas (16), T4 Fuerza bruta (15), T5 Repudio (12).",
            "Decisión Arquitectónica:",
            "Implementar controles preventivos desde el diseño (Shift-Left Security) en Ejercicio 1.2.",
        ],
        COLOR_RED,
        body_size=8.6,
    )

    # =========================================================================
    # SLIDE 7: EJERCICIO 1.2 - FLUJO DE AUTENTICACIÓN RESISTENTE
    # =========================================================================
    _set_header(
        prs.slides[6],
        "EJERCICIO 1.2: Arquitectura y Flujo de Autenticación Resistente",
        "Diseño de autenticación y ciclo de vida de sesiones contra fuerza bruta, fijación de sesión, enumeración y reuso de tokens:",
    )
    _add_picture_fit(
        prs.slides[6],
        capturas / "diagrama_flujo_autenticacion.png",
        0.55,
        1.55,
        8.25,
        5.25,
    )
    _add_card(
        prs.slides[6],
        8.95,
        1.58,
        3.85,
        4.95,
        "CONTROLES IMPLEMENTADOS",
        [
            "Hash Lento Moderno:",
            "Argon2id con sal automática (sin MD5, SHA-1 ni SHA-256 para claves).",
            "Anti Fuerza Bruta y Enumeración:",
            "Bloqueo temporal progresivo (30s→60s→...) por cuenta e IP y error HTTP 401 genérico.",
            "Ciclo de Vida de Sesión:",
            "Regeneración obligatoria de session_id al loguear y revocación total al cambiar clave.",
            "Recuperación Segura:",
            "Token de 1 solo uso con TTL corto, invalidación previa y log sin exponer el token.",
        ],
        COLOR_GREEN,
        body_size=8.4,
    )

    # =========================================================================
    # SLIDE 8: EJERCICIO 1.2 - EVIDENCIA DE CÓDIGO Y SAST (BANDIT/PYLINT)
    # =========================================================================
    _set_header(
        prs.slides[7],
        "EJERCICIO 1.2: Evidencia Real de Código Seguro y Auditoría SAST",
        "Fragmento fuente de task_api/ (Argon2id, bloqueo progresivo y recuperación) auditado con Bandit y Pylint en entorno .venv:",
    )
    _add_picture_fit(
        prs.slides[7],
        capturas / "captura_codigo_auth.png",
        0.55,
        1.55,
        6.20,
        5.35,
    )
    _add_picture_fit(
        prs.slides[7],
        capturas / "captura_sast_bandit_pylint.png",
        6.95,
        1.55,
        5.85,
        3.75,
    )
    _add_card(
        prs.slides[7],
        6.95,
        5.42,
        5.85,
        1.48,
        "DICTAMEN SAST (task_api/)",
        [
            "Bandit: 0 vulnerabilidades en 777 líneas analizadas (High/Med/Low = 0).",
            "Pylint: Calificación 10.00 / 10; 100 % consultas SQL parametrizadas.",
        ],
        COLOR_GREEN,
        title_size=10.5,
        body_size=8.5,
    )

    # =========================================================================
    # SLIDE 9: EJERCICIO 1.2 - EVIDENCIAS PYTEST Y SIMULACIÓN HTTP
    # =========================================================================
    _set_header(
        prs.slides[8],
        "EJERCICIO 1.2: Evidencias Reales de Pruebas de Seguridad (pytest + HTTP)",
        "Validación automatizada de credenciales inválidas, fuerza bruta simulada, expiración, revocación y reutilización de token:",
    )
    _add_picture_fit(
        prs.slides[8],
        capturas / "captura_pytest_auth.png",
        0.55,
        1.55,
        6.05,
        3.55,
    )
    _add_card(
        prs.slides[8],
        0.55,
        5.22,
        6.05,
        1.68,
        "COBERTURA DE PRUEBAS NEGATIVAS (6/6 PASSED)",
        [
            "test_register_uses_argon2id_and_blocks_privilege_escalation: PASSED",
            "test_brute_force_progressive_lockout_by_account_and_ip: PASSED",
            "test_session_regeneration_expiration_and_logout: PASSED",
            "test_password_reset_single_use_invalidation_expiration_and_safe_logs: PASSED",
        ],
        COLOR_BLUE,
        title_size=10.0,
        body_size=8.0,
    )
    _add_picture_fit(
        prs.slides[8],
        capturas / "captura_http_pruebas_negativas.png",
        6.78,
        1.55,
        6.00,
        5.35,
    )

    # =========================================================================
    # SLIDE 10: ACTIVIDAD 2 - REQUISITOS VERIFICABLES (RE-01..RE-04)
    # =========================================================================
    _set_header(
        prs.slides[9],
        "ACTIVIDAD 02: Especificación de Requisitos de Seguridad Verificables",
        "Formalización de requisitos verificables y criterios de aceptación negativos con códigos HTTP seguros para SportReserve Co.:",
    )
    _style_table(
        prs.slides[9],
        [
            "ID Req.",
            "Requisito de Seguridad Verificada",
            "Amenaza Asociada",
            "Criterio de Aceptación / Validación Negativa",
            "Prioridad",
        ],
        [
            [
                "RE-01",
                "El sistema verificará la propiedad de las reservas en el servidor antes de entregar los datos.",
                "IDOR / Fuga de Privacidad",
                "Se simula petición de User_A solicitando reserva de User_B.\nResultado Esperado: HTTP 403 Forbidden sin datos expuestos.",
                "Crítica",
            ],
            [
                "RE-02",
                "Toda consulta a base de datos ejecutará sentencias parametrizadas (Prepared Statements) sin concatenación.",
                "Inyección SQL (SQLi)",
                "Se envía correo='x@y.com' OR '1'='1' en el endpoint de búsqueda.\nResultado Esperado: HTTP 400 Bad Request o cero registros filtrados.",
                "Crítica",
            ],
            [
                "RE-03",
                "Toda entrada de usuario renderizada en vistas HTML será escapada contextualmente en el servidor.",
                "XSS Reflejado / Almacenado",
                "Se registra comentario con <script>alert(1)</script>.\nResultado Esperado: Salida escapada (&lt;script&gt;) y cabecera CSP activa.",
                "Alta",
            ],
            [
                "RE-04",
                "Los endpoints rechazarán parámetros malformados, tipos inválidos o campos fuera de esquema.",
                "Abuso de Parámetros / Tampering",
                "Se envía id=abc o sin sesión en /api/reserva.\nResultado Esperado: HTTP 400 Bad Request sin stacktrace interno.",
                "Alta",
            ],
        ],
        [0.95, 3.25, 1.9, 4.8, 1.15],
        top=1.62,
        height=5.1,
        cell_size=8.6,
        center_cols={0, 4},
        badge_col=4,
    )

    # =========================================================================
    # SLIDE 11: EJERCICIO 2.1 - REQUISITOS DE SEGURIDAD (RS-01..RS-10)
    # =========================================================================
    _set_header(
        prs.slides[10],
        "EJERCICIO 2.1: Activos y Requisitos de Seguridad (RS-01 a RS-10)",
        "Conversión de los 10 requisitos funcionales en requisitos de seguridad medibles clasificados por criticidad:",
    )
    _style_table(
        prs.slides[10],
        [
            "ID",
            "Requisito de Seguridad",
            "Activo Protegido",
            "Control Esperado",
            "Criterio de Aceptación Medible",
            "Nivel",
        ],
        [
            ["RS-01", "Hash lento en contraseñas", "Credenciales", "Argon2id con sal", "BD guarda prefijo $argon2id$; 0 texto plano.", "Obligatorio"],
            ["RS-02", "Control de propiedad en tareas", "Tareas", "Autorización owner_id", "Usuario no dueño recibe HTTP 403 al editar/borrar.", "Obligatorio"],
            ["RS-03", "Registro seguro de fallos de login", "Registros / Logs", "Log sin secretos", "audit_logs registra evento sin clave ni token.", "Obligatorio"],
            ["RS-04", "Bloqueo por fuerza bruta", "Credenciales", "Límite cuenta e IP", "Al 3er fallo consecutivo retorna HTTP 429 + Retry-After.", "Obligatorio"],
            ["RS-05", "Regeneración y expiración de sesión", "Tokens sesión", "Token 256-bit + TTL", "Nuevo login invalida token previo; TTL vencido -> 401.", "Obligatorio"],
            ["RS-06", "Recuperación con token único", "Credenciales", "Token 1-uso + revocación", "Reuso o token vencido retorna HTTP 400; revoca sesión.", "Obligatorio"],
            ["RS-07", "Control de esquema y sin mass assignment", "Tareas / Roles", "Lista blanca estricta", "Enviar role='admin' o campo extra retorna HTTP 400.", "Obligatorio"],
            ["RS-08", "Consultas SQL parametrizadas", "Base de datos", "Placeholders ?", "Payload ' OR '1'='1' nunca altera estructura SQL.", "Obligatorio"],
            ["RS-09", "Validación positiva en adjuntos/archivos", "Archivos", "MIME/extensión y tamaño", "Archivo no permitido o > límite retorna HTTP 400/413.", "Importante"],
            ["RS-10", "Privacidad y minimización de respuestas", "Datos personales", "Mensajes genéricos", "Login/reset fallido no revela si el correo existe.", "Importante"],
        ],
        [0.75, 2.35, 1.5, 2.05, 4.15, 1.3],
        top=1.55,
        height=5.35,
        header_size=8.8,
        cell_size=7.6,
        center_cols={0, 5},
        badge_col=5,
    )

    # =========================================================================
    # SLIDE 12: EJERCICIO 2.1 - MATRIZ DE TRAZABILIDAD (RF <-> RS <-> PRUEBA)
    # =========================================================================
    _set_header(
        prs.slides[11],
        "EJERCICIO 2.1: Matriz de Trazabilidad Completa (RF ↔ RS ↔ Control ↔ Prueba)",
        "Trazabilidad bidireccional entre los 10 Requisitos Funcionales del sistema de gestión de tareas y su verificación automatizada:",
    )
    _style_table(
        prs.slides[11],
        [
            "ID RF",
            "Requisito Funcional (Sistema de Tareas)",
            "Activo",
            "ID RS",
            "Control Técnico Aplicado",
            "Método / Caso de Prueba Verificable",
        ],
        [
            ["RF-01", "Registro de nuevo usuario", "Credenciales / Datos", "RS-01, RS-07", "Hash Argon2id + rol fijo estudiante", "test_register_uses_argon2id_and_blocks_privilege_escalation"],
            ["RF-02", "Inicio de sesión de usuario", "Credenciales / Sesión", "RS-04, RS-05, RS-10", "Bloqueo progresivo + error genérico", "test_brute_force_progressive_lockout_by_account_and_ip"],
            ["RF-03", "Cierre de sesión (Logout)", "Tokens de sesión", "RS-05", "Revocación inmediata en tabla sessions", "test_session_regeneration_expiration_and_logout"],
            ["RF-04", "Cambio y recuperación de clave", "Credenciales / Tokens", "RS-06, RS-03", "Token 1-uso TTL corto + revoca sesiones", "test_password_reset_single_use_invalidation_expiration_and_safe_logs"],
            ["RF-05", "Crear nueva tarea", "Tareas", "RS-07, RS-08", "Validación positiva + SQL parametrizado", "POST /tasks con campo extra o título < 3 chars -> HTTP 400"],
            ["RF-06", "Listar y buscar tareas", "Tareas / Datos", "RS-02, RS-08", "Filtro por owner_id + LIKE parametrizado", "GET /tasks?search=' OR 1=1 -> solo tareas propias"],
            ["RF-07", "Editar tarea existente", "Tareas", "RS-02, RS-07", "Verificación de propiedad en servidor", "Usuario B edita tarea de Usuario A -> HTTP 403 Forbidden"],
            ["RF-08", "Eliminar tarea", "Tareas / Registros", "RS-02, RS-03", "Verificación rol/dueño + registro en log", "Usuario B elimina tarea ajena -> HTTP 403; éxito auditado"],
            ["RF-09", "Adjuntar archivo a tarea", "Archivos", "RS-09, RS-02", "Validación tipo/tamaño y ruta aislada", "Subir .exe o archivo > 2MB -> HTTP 400 / 413"],
            ["RF-10", "Auditar eventos y gestión de roles", "Registros / Roles", "RS-03, RS-07", "Bitácora sin tokens ni datos sensibles", "Inspección de audit_logs tras eventos de seguridad"],
        ],
        [0.75, 2.30, 1.45, 1.35, 2.70, 3.55],
        top=1.55,
        height=5.35,
        header_size=8.8,
        cell_size=7.6,
        center_cols={0, 3},
    )

    # =========================================================================
    # SLIDE 13: ANÁLISIS METACOGNITIVO, BITÁCORA DRIVE Y CONCLUSIONES
    # =========================================================================
    _set_header(
        prs.slides[12],
        "ANÁLISIS METACOGNITIVO, BITÁCORA EN DRIVE Y CONCLUSIONES",
        "Reflexión sobre causas raíz de vulnerabilidades, trazabilidad del entregable en Google Drive y preparación para Actividades 3 y 4:",
    )
    _add_card(
        prs.slides[12],
        0.55,
        1.60,
        3.95,
        5.1,
        "1. ANÁLISIS METACOGNITIVO",
        [
            "Causa Raíz de SQLi y XSS:",
            "Mezclar plano de control (código) con plano de datos (entrada no confiable); se erradica con separación estricta (parametrización y escape).",
            "Causa Raíz de IDOR y Escalamiento:",
            "Confundir autenticación ('quién eres') con autorización ('qué objeto posees'). Todo acceso debe validar propiedad en el servidor.",
            "Valor de Pruebas Negativas:",
            "Las pruebas unitarias tradicionales solo verifican el camino feliz; las pruebas negativas demuestran que el sistema falla de forma segura (400/401/403/429).",
        ],
        COLOR_MAROON,
        body_size=8.3,
    )
    _add_card(
        prs.slides[12],
        4.70,
        1.60,
        4.05,
        5.1,
        "2. EVIDENCIAS EN BITÁCORA DRIVE",
        [
            "Repositorio / Carpeta Institucional:",
            "Google Drive Oficial del Equipo 05 (Modo Lector):",
            "https://drive.google.com/drive/folders/1S-F9LnMze7nOk9m7HgX4QdU20abIEQLo?usp=sharing",
            "Artefactos Verificados Incluidos:",
            "Código fuente modular en task_api/ (Pylint 10.00/10, Bandit 0 alertas).",
            "Suite automatizada pytest (6/6 pruebas de sesión y recuperación aprobadas).",
            "Informe técnico LaTeX (informe/main.tex) y presentación PDF oficial.",
        ],
        COLOR_BLUE,
        body_size=8.3,
    )
    _add_card(
        prs.slides[12],
        8.95,
        1.60,
        3.85,
        5.1,
        "3. CONCLUSIONES Y SIGUIENTE PASO",
        [
            "Shift-Left Security Validado:",
            "El modelado STRIDE y las matrices P×I permitieron detectar riesgos críticos (25 y 20) antes de codificar módulos de negocio.",
            "Autenticación Robusta en Producción:",
            "Argon2id, bloqueo progresivo y tokens de 1 solo uso neutralizan fuerza bruta, fijación de sesión y enumeración.",
            "Continuidad (Actividades 3 y 4):",
            "Queda definida la línea base de requisitos y pruebas para desplegar SAST sobre app_vulnerable.py y refactorizar app_segura.py.",
        ],
        COLOR_GREEN,
        body_size=8.3,
    )

    prs.save(str(out_pptx))
    print(f"Presentación guardada exitosamente en: {out_pptx}")


if __name__ == "__main__":
    build_guia04_presentation()
