"""Generador de diagramas técnicos, mapa de calor PxI y capturas de evidencia reales."""

from __future__ import annotations

from pathlib import Path
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
CAPTURAS_DIR = ROOT / "capturas"
EVIDENCIAS_DIR = ROOT / "evidencias"

MAROON = "#8C1D22"
DARK = "#212529"
MUTED = "#5C6670"
GREEN = "#198754"
ORANGE = "#D97706"
RED = "#DC3545"
BLUE = "#1D4ED8"
BG_LIGHT = "#F8F9FC"


def _load_font(candidates: list[str], size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in candidates:
        p = Path(path)
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def _mono_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    return _load_font(
        [
            r"C:\Windows\Fonts\consola.ttf",
            r"C:\Windows\Fonts\lucon.ttf",
            r"C:\Windows\Fonts\cour.ttf",
        ],
        size,
    )


def _sans_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if bold:
        return _load_font(
            [
                r"C:\Windows\Fonts\arialbd.ttf",
                r"C:\Windows\Fonts\seguisb.ttf",
                r"C:\Windows\Fonts\calibrib.ttf",
            ],
            size,
        )
    return _load_font(
        [
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\segoeui.ttf",
            r"C:\Windows\Fonts\calibri.ttf",
        ],
        size,
    )


def build_architecture_stride_diagram() -> None:
    """Genera diagrama de componentes con 4 límites de confianza y flujos STRIDE (Ej. 1.1)."""
    fig, ax = plt.subplots(figsize=(13.5, 7.2), dpi=200)
    ax.set_xlim(0, 13.5)
    ax.set_ylim(0, 7.2)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    # Título
    ax.text(
        6.75,
        6.85,
        "Arquitectura de Componentes, Límites de Confianza y Superficie STRIDE (API Gestión de Tareas)",
        ha="center",
        va="center",
        fontsize=13,
        fontweight="bold",
        color=MAROON,
    )

    # 4 Límites de confianza (zonas punteadas)
    zones = [
        (0.3, 0.95, 2.7, 5.5, "#FEF2F2", RED, "LÍMITE 1: INTERNET\n(Zona No Confiable)"),
        (3.5, 0.95, 4.3, 5.5, "#EFF6FF", BLUE, "LÍMITE 2: RED INTERNA\n(Servidor API RESTful)"),
        (8.4, 4.25, 4.7, 2.2, "#ECFDF5", GREEN, "LÍMITE 3: BASE DE DATOS\n(Almacén Relacional)"),
        (8.4, 0.95, 4.7, 3.05, "#FFFBEB", ORANGE, "LÍMITE 4: SISTEMA ARCHIVOS\nY SERVICIOS EXTERNOS"),
    ]
    for zx, zy, zw, zh, fc, ec, label in zones:
        box = FancyBboxPatch(
            (zx, zy),
            zw,
            zh,
            boxstyle="round,pad=0.06,rounding_size=0.15",
            facecolor=fc,
            edgecolor=ec,
            linestyle="--",
            linewidth=1.8,
        )
        ax.add_patch(box)
        ax.text(
            zx + zw / 2,
            zy + zh - 0.14,
            label,
            ha="center",
            va="top",
            fontsize=8.8,
            fontweight="bold",
            color=ec,
        )

    def draw_node(x: float, y: float, w: float, h: float, title: str, sub: str, border: str) -> None:
        node = FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.04,rounding_size=0.12",
            facecolor="white",
            edgecolor=border,
            linewidth=2.0,
        )
        ax.add_patch(node)
        ax.text(
            x + w / 2,
            y + h * 0.63,
            title,
            ha="center",
            va="center",
            fontsize=10,
            fontweight="bold",
            color=DARK,
        )
        ax.text(
            x + w / 2,
            y + h * 0.28,
            sub,
            ha="center",
            va="center",
            fontsize=8,
            color=MUTED,
        )

    # 5 Componentes requeridos por la guía (pág. 4)
    draw_node(
        0.55,
        3.15,
        2.2,
        1.45,
        "Navegador / Cliente",
        "Estudiante, Docente,\nAdministrador (HTTPS)",
        RED,
    )
    draw_node(
        4.15,
        3.0,
        3.0,
        1.75,
        "API RESTful (Flask)",
        "Auth Argon2id, Rate-Limit,\nValidación, RBAC y Logs",
        BLUE,
    )
    draw_node(
        8.95,
        4.45,
        3.6,
        1.12,
        "Base de Datos (SQLite3)",
        "users, sessions, tasks,\npassword_resets, audit_logs",
        GREEN,
    )
    draw_node(
        8.95,
        2.28,
        3.6,
        0.82,
        "Servicio de Correo (SMTP)",
        "Envío de token 1-uso (TTL corto)",
        ORANGE,
    )
    draw_node(
        8.95,
        1.15,
        3.6,
        0.82,
        "Almacenamiento de Archivos",
        "Adjuntos de tareas y bitácoras",
        ORANGE,
    )

    def draw_flow(x1: float, y1: float, x2: float, y2: float, lbl: str, ly: float) -> None:
        ax.annotate(
            "",
            xy=(x2, y2),
            xytext=(x1, y1),
            arrowprops=dict(arrowstyle="<->", color=DARK, lw=1.7),
        )
        ax.text(
            (x1 + x2) / 2,
            ly,
            lbl,
            ha="center",
            va="center",
            fontsize=7.6,
            fontweight="bold",
            color=MAROON,
            bbox=dict(boxstyle="round,pad=0.22", facecolor="white", edgecolor="#CBD5E1", lw=0.9),
        )

    # Flujos y amenazas STRIDE mapeadas en las fronteras
    draw_flow(2.78, 3.88, 4.12, 3.88, "F1: Peticiones REST\n[S, T, I, D, E]", 4.55)
    draw_flow(7.18, 4.35, 8.92, 5.0, "F2: SQL Parametrizado\n[T, R, I]", 5.25)
    draw_flow(7.18, 3.60, 8.92, 2.68, "F3: Envío Reset Token\n[S, I, D]", 3.38)
    draw_flow(7.18, 3.12, 8.92, 1.56, "F4: Lectura/Escritura\n[T, R, I, E]", 1.62)

    # Leyenda inferior
    ax.text(
        6.75,
        0.42,
        "Taxonomía STRIDE:  [S] Spoofing   [T] Tampering   [R] Repudiation   "
        "[I] Information Disclosure   [D] Denial of Service   [E] Elevation of Privilege",
        ha="center",
        va="center",
        fontsize=8.5,
        fontweight="bold",
        color=DARK,
        bbox=dict(boxstyle="round,pad=0.35", facecolor=BG_LIGHT, edgecolor="#CBD5E1"),
    )

    plt.tight_layout(pad=0.3)
    plt.savefig(CAPTURAS_DIR / "diagrama_arquitectura_stride.png", dpi=200)
    plt.close(fig)


def build_auth_flow_diagram() -> None:
    """Genera el diagrama de flujo de autenticación segura (Ejercicio Propuesto 1.2)."""
    fig, ax = plt.subplots(figsize=(13.5, 7.2), dpi=200)
    ax.set_xlim(0, 13.5)
    ax.set_ylim(0, 7.2)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    ax.text(
        6.75,
        6.85,
        "Flujo de Autenticación Resistente, Gestión de Sesiones y Recuperación (Ejercicio 1.2)",
        ha="center",
        va="center",
        fontsize=13,
        fontweight="bold",
        color=MAROON,
    )

    def box(x: float, y: float, w: float, h: float, title: str, body: str, col: str, bg: str = "white") -> None:
        p = FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.05,rounding_size=0.12",
            facecolor=bg,
            edgecolor=col,
            linewidth=1.8,
        )
        ax.add_patch(p)
        ax.text(x + w / 2, y + h - 0.25, title, ha="center", va="top", fontsize=8.8, fontweight="bold", color=col)
        ax.text(x + w / 2, y + h * 0.36, body, ha="center", va="center", fontsize=7.6, color=DARK)

    def arrow(x1: float, y1: float, x2: float, y2: float, label: str = "", col: str = DARK) -> None:
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="->", color=col, lw=1.6))
        if label:
            ax.text(
                (x1 + x2) / 2,
                (y1 + y2) / 2 + 0.14,
                label,
                ha="center",
                va="center",
                fontsize=7.3,
                fontweight="bold",
                color=col,
                bbox=dict(boxstyle="round,pad=0.14", facecolor="white", edgecolor="none"),
            )

    # Carril 1: Registro y Login
    box(0.4, 5.15, 2.7, 1.2, "1. POST /auth/register", "Valida email, fuerza clave y\nrechaza campos extra (role=admin).\nHash Argon2id + rol estudiante.", BLUE, "#EFF6FF")
    box(3.7, 5.15, 3.0, 1.2, "2. POST /auth/login", "Verifica bloqueo activo por\ncuenta (acct:*) y por IP (ip:*).", MAROON, "#FEF2F2")
    box(7.35, 5.15, 2.6, 1.2, "3. ¿Cuenta/IP bloqueada\no credencial inválida?", "Si falla >= 3 veces:\nBloqueo progresivo 30s -> 60s.", RED, "#FFF1F2")
    box(10.55, 5.15, 2.55, 1.2, "4. Regeneración Sesión", "Invalida token previo,\ncrea nuevo session_id + TTL\n(SHA-256 del token en BD).", GREEN, "#ECFDF5")

    arrow(3.12, 5.75, 3.68, 5.75)
    arrow(6.72, 5.75, 7.33, 5.75)
    arrow(9.97, 5.75, 10.53, 5.75, "Válido", GREEN)

    # Salidas de rechazo de Login
    box(7.35, 3.35, 2.6, 1.15, "Respuesta Segura", "HTTP 401 'Credenciales inválidas'\n(sin enumerar) o HTTP 429\n+ Header Retry-After.", RED)
    arrow(8.65, 5.13, 8.65, 4.52, "Falla", RED)

    # Carril 2: Uso de Sesión y Cambio de Clave
    box(10.55, 3.35, 2.55, 1.15, "5. GET /auth/me & Logout", "Valida revoked=0 y\nexpires_at > now.\nLogout marca revoked=1.", BLUE)
    arrow(11.82, 5.13, 11.82, 4.52, "Token", GREEN)

    box(3.7, 3.35, 3.0, 1.15, "6. POST /auth/change-password", "Valida clave actual (Argon2id).\nActualiza hash y REVOCA todas\nlas sesiones activas del usuario.", ORANGE, "#FFFBEB")
    arrow(5.2, 5.13, 5.2, 4.52, "Autenticado", BLUE)

    # Carril 3: Recuperación de Contraseña
    box(0.4, 1.25, 3.5, 1.4, "7. POST /auth/forgot-password", "Respuesta HTTP 200 genérica.\nSi existe: invalida tokens previos,\nemite token aleatorio (256 bits)\ncon TTL corto y envío por correo.", BLUE, "#EFF6FF")
    box(4.6, 1.25, 4.0, 1.4, "8. POST /auth/reset-password", "Valida hash del token, used=0 y\nexpires_at > now. Marca used=1\n(1 solo uso), cambia hash Argon2id\ny revoca todas las sesiones.", GREEN, "#ECFDF5")
    box(9.3, 1.25, 3.8, 1.4, "9. Bitácora audit_logs (OWASP)", "Registra LOGIN_*, LOGOUT,\nPASSWORD_CHANGED y RESET_*\ncon correo enmascarado y SIN\nexponer tokens ni contraseñas.", DARK, BG_LIGHT)

    arrow(3.92, 1.95, 4.58, 1.95, "Token 1-uso")
    arrow(8.62, 1.95, 9.28, 1.95, "Audita")
    arrow(5.2, 3.33, 5.2, 2.67, "Revoca", ORANGE)
    arrow(11.82, 3.33, 11.82, 2.67, "Audita", DARK)

    ax.text(
        6.75,
        0.42,
        "Controles verificados con pruebas automatizadas (pytest): fuerza bruta, fijación/regeneración, expiración, revocación y reutilización de token.",
        ha="center",
        va="center",
        fontsize=8.5,
        fontweight="bold",
        color=MAROON,
    )

    plt.tight_layout(pad=0.3)
    plt.savefig(CAPTURAS_DIR / "diagrama_flujo_autenticacion.png", dpi=200)
    plt.close(fig)


def build_risk_heatmap() -> None:
    """Genera matriz visual PxI 5x5 con hallazgos de SportReserve y Top 5 del Proyecto Base."""
    fig, ax = plt.subplots(figsize=(10.5, 6.4), dpi=200)
    fig.patch.set_facecolor("white")

    # Construir grilla 5x5 (P en Y=1..5, I en X=1..5)
    for p in range(1, 6):
        for i in range(1, 6):
            score = p * i
            if score >= 17:
                color = "#FCA5A5"  # Crítico
                txt_col = "#7F1D1D"
            elif score >= 10:
                color = "#FDBA74"  # Alto
                txt_col = "#7C2D12"
            elif score >= 5:
                color = "#FDE68A"  # Medio
                txt_col = "#78350F"
            else:
                color = "#A7F3D0"  # Bajo
                txt_col = "#064E3B"
            rect = plt.Rectangle((i - 0.5, p - 0.5), 1, 1, facecolor=color, edgecolor="white", lw=2)
            ax.add_patch(rect)
            ax.text(i + 0.36, p - 0.36, str(score), fontsize=8, color=txt_col, fontweight="bold", ha="right", va="bottom")

    # Puntos exactos de amenazas
    points = [
        (5, 5, "H-B: SQLi Correo (25)", MAROON, (0, 0.14)),
        (5, 4, "H-A: IDOR Reservas (20)\nT1: Elevación role=admin (20)", MAROON, (0, 0.0)),
        (4, 4, "H-C: XSS Sin Escape (16)\nT2: Spoofing Sesión (16)\nT3: Fuga Tareas (16)", BLUE, (0, 0.0)),
        (3, 5, "T4: Fuerza Bruta / DoS (15)", BLUE, (0, 0.0)),
        (4, 3, "T5: Borrado sin Log (12)", BLUE, (0, 0.0)),
    ]
    for imp, prob, label, col, offset in points:
        ax.scatter(imp, prob, s=90, color=col, zorder=5, edgecolors="white", linewidth=1.2)
        ax.text(
            imp + offset[0],
            prob + offset[1] + 0.02,
            label,
            ha="center",
            va="center",
            fontsize=7.6,
            fontweight="bold",
            color=DARK,
            bbox=dict(boxstyle="round,pad=0.22", facecolor="white", edgecolor=col, alpha=0.95),
            zorder=6,
        )

    ax.set_xlim(0.5, 5.5)
    ax.set_ylim(0.5, 5.5)
    ax.set_xticks([1, 2, 3, 4, 5])
    ax.set_yticks([1, 2, 3, 4, 5])
    ax.set_xticklabels(["1\nInsignificante", "2\nMenor", "3\nModerado", "4\nMayor", "5\nCatastrófico"], fontsize=9, fontweight="bold")
    ax.set_yticklabels(["1\nMuy Baja", "2\nBaja", "3\nMedia", "4\nAlta", "5\nMuy Alta"], fontsize=9, fontweight="bold")
    ax.set_xlabel("Impacto (I) — Confidencialidad, Integridad, Disponibilidad", fontsize=10, fontweight="bold", color=DARK)
    ax.set_ylabel("Probabilidad (P)", fontsize=10, fontweight="bold", color=DARK)
    ax.set_title(
        "Matriz de Riesgos P × I: Hallazgos SportReserve Co. (H-A..H-C) y Top 5 API Tareas (T1..T5)",
        fontsize=11.5,
        fontweight="bold",
        color=MAROON,
        pad=12,
    )

    plt.tight_layout()
    plt.savefig(CAPTURAS_DIR / "matriz_riesgos_pxi.png", dpi=200)
    plt.close(fig)


def render_terminal_screenshot(
    title: str,
    command: str,
    body_text: str,
    out_name: str,
    highlight_rules: list[tuple[str, tuple[int, int, int]]] | None = None,
) -> None:
    """Renderiza una captura realista de terminal oscura con salidas reales verificadas."""
    font_title = _sans_font(17, bold=True)
    font_mono = _mono_font(15)
    rules = highlight_rules or []

    wrapped_lines: list[str] = [f"PS C:\\...\\Guia04> {command}", ""]
    for raw in body_text.replace("\t", "    ").splitlines():
        if len(raw) <= 102:
            wrapped_lines.append(raw)
        else:
            wrapped_lines.extend(textwrap.wrap(raw, width=102, subsequent_indent="    "))

    line_h = 22
    pad_x = 28
    header_h = 46
    width = 1180
    height = max(420, header_h + 24 + len(wrapped_lines) * line_h + 24)

    img = Image.new("RGB", (width, height), (20, 24, 32))
    draw = ImageDraw.Draw(img)

    # Barra de título estilo Windows Terminal
    draw.rectangle([(0, 0), (width, header_h)], fill=(34, 39, 50))
    for idx, c in enumerate([(239, 68, 68), (245, 158, 11), (34, 197, 94)]):
        cx = 22 + idx * 24
        draw.ellipse([(cx - 7, 16), (cx + 7, 30)], fill=c)
    draw.text((100, 13), title, font=font_title, fill=(226, 232, 240))

    y = header_h + 18
    for idx, line in enumerate(wrapped_lines):
        color = (226, 232, 240)
        if idx == 0:
            color = (103, 232, 249)
        else:
            for token, tok_color in rules:
                if token in line:
                    color = tok_color
                    break
        draw.text((pad_x, y), line, font=font_mono, fill=color)
        y += line_h

    img.save(CAPTURAS_DIR / out_name)


def _extract_func_block(lines: list[str], func_prefix: str, max_lines: int) -> list[str]:
    for idx, line in enumerate(lines):
        if line.startswith(func_prefix):
            end = min(len(lines), idx + max_lines)
            return [f"{n + 1:03d} | {lines[n]}" for n in range(idx, end)]
    return []


def render_code_screenshot() -> None:
    """Genera captura legible estilo editor VS Code con el código crítico de seguridad."""
    sec_lines = (ROOT / "task_api" / "security.py").read_text(encoding="utf-8").splitlines()
    auth_lines = (ROOT / "task_api" / "auth_service.py").read_text(encoding="utf-8").splitlines()

    snippet = (
        ["# --- task_api/security.py: Hashing lento Argon2id ---"]
        + _extract_func_block(sec_lines, "def hash_password", 12)
        + ["", "# --- task_api/security.py: Bloqueo temporal progresivo ---"]
        + _extract_func_block(sec_lines, "def _record_scope_failure", 19)
        + ["", "# --- task_api/auth_service.py: Invalidación previa y token 1-uso ---"]
        + _extract_func_block(auth_lines, "def request_password_reset", 24)
    )

    render_terminal_screenshot(
        "VS Code — task_api/security.py & task_api/auth_service.py (Ejercicio 1.2)",
        "Select-String -Path task_api\\*.py -Pattern 'hash_password|_record_scope_failure|request_password_reset'",
        "\n".join(snippet),
        "captura_codigo_auth.png",
        highlight_rules=[
            ("# ---", (250, 204, 21)),
            ("def ", (125, 211, 252)),
            ("_PASSWORD_HASHER", (134, 239, 172)),
            ("UPDATE password_resets", (253, 186, 116)),
            ("generate_secure_token", (134, 239, 172)),
        ],
    )


def _read_log(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    return raw.decode("utf-8", errors="replace")


def main() -> None:
    """Genera todos los diagramas y capturas reales de la Guía 04."""
    CAPTURAS_DIR.mkdir(parents=True, exist_ok=True)
    build_architecture_stride_diagram()
    build_auth_flow_diagram()
    build_risk_heatmap()

    pytest_txt = _read_log(EVIDENCIAS_DIR / "pytest_output.txt")
    render_terminal_screenshot(
        "Windows PowerShell — Ejecución Suite de Pruebas de Seguridad (pytest -v)",
        r"..\..\.venv\Scripts\pytest.exe -v",
        pytest_txt,
        "captura_pytest_auth.png",
        highlight_rules=[
            ("PASSED", (74, 222, 128)),
            ("passed", (74, 222, 128)),
            ("collected", (147, 197, 253)),
        ],
    )

    bandit_txt = _read_log(EVIDENCIAS_DIR / "bandit_output.txt")
    pylint_txt = _read_log(EVIDENCIAS_DIR / "pylint_output.txt")
    sast_combined = f"=== BANDIT (SAST Seguridad) ===\n{bandit_txt}\n=== PYLINT (Análisis Estático) ===\n{pylint_txt}"
    render_terminal_screenshot(
        "Windows PowerShell — Auditoría Estática SAST (Bandit + Pylint)",
        r"..\..\.venv\Scripts\bandit.exe -r task_api; ..\..\.venv\Scripts\pylint.exe task_api",
        sast_combined,
        "captura_sast_bandit_pylint.png",
        highlight_rules=[
            ("No issues identified", (74, 222, 128)),
            ("10.00/10", (74, 222, 128)),
            ("===", (250, 204, 21)),
        ],
    )

    http_txt = _read_log(EVIDENCIAS_DIR / "http_demo_output.txt")
    render_terminal_screenshot(
        "Simulación HTTP RESTful — Pruebas Negativas y Sesión (Ejercicio 1.2)",
        r"..\..\.venv\Scripts\python.exe scripts\run_http_demo.py",
        http_txt,
        "captura_http_pruebas_negativas.png",
        highlight_rules=[
            ("HTTP 201", (74, 222, 128)),
            ("HTTP 200", (74, 222, 128)),
            ("HTTP 400", (253, 186, 116)),
            ("HTTP 401", (248, 113, 113)),
            ("HTTP 429", (248, 113, 113)),
            ("Header Retry-After", (250, 204, 21)),
            ("audit_logs", (147, 197, 253)),
        ],
    )

    render_code_screenshot()
    print("Assets generados en:", CAPTURAS_DIR)


if __name__ == "__main__":
    main()
