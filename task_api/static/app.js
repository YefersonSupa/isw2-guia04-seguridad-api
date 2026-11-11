"use strict";

const state = {
    accessToken: null,
    sessionId: null,
    user: null,
};

function updateSessionView() {
    const badge = document.getElementById("session-badge");
    const metaUser = document.getElementById("meta-user");
    const metaRole = document.getElementById("meta-role");
    const metaSid = document.getElementById("meta-session-id");
    const metaTok = document.getElementById("meta-token");

    if (state.accessToken && state.user) {
        badge.textContent = "Sesión activa";
        badge.className = "status-badge status-ok";
        metaUser.textContent = `${state.user.full_name} (${state.user.email})`;
        metaRole.textContent = state.user.role;
        metaSid.textContent = state.sessionId || "—";
        metaTok.textContent = `${state.accessToken.slice(0, 10)}...${state.accessToken.slice(-6)}`;
    } else {
        badge.textContent = "Sin sesión activa";
        badge.className = "status-badge status-idle";
        metaUser.textContent = "—";
        metaRole.textContent = "—";
        metaSid.textContent = "—";
        metaTok.textContent = "—";
    }
}

function showAlert(status, payload, retryAfter) {
    const alertBox = document.getElementById("http-alert");
    alertBox.classList.remove("hidden", "alert-ok", "alert-warn", "alert-err");

    let text = `HTTP ${status}: ${payload.message || payload.error || "Respuesta recibida"}`;
    if (retryAfter) {
        text += ` (Retry-After: ${retryAfter}s)`;
    }
    alertBox.textContent = text;

    if (status >= 200 && status < 300) {
        alertBox.classList.add("alert-ok");
    } else if (status === 429) {
        alertBox.classList.add("alert-warn");
    } else {
        alertBox.classList.add("alert-err");
    }
}

function appendHttpLog(method, path, status, payload, retryAfter) {
    const history = document.getElementById("http-history");
    const empty = history.querySelector(".empty-msg");
    if (empty) {
        empty.remove();
    }

    const entry = document.createElement("div");
    entry.className = "log-entry";

    const head = document.createElement("div");
    head.className = "log-head";

    const routeSpan = document.createElement("span");
    routeSpan.textContent = `${method} ${path}`;

    const codeSpan = document.createElement("span");
    codeSpan.className = `code-chip ${status < 300 ? "code-2xx" : "code-4xx"}`;
    codeSpan.textContent = retryAfter ? `HTTP ${status} (Retry-After: ${retryAfter}s)` : `HTTP ${status}`;

    head.appendChild(routeSpan);
    head.appendChild(codeSpan);

    const sanitizedPayload = { ...payload };
    if (typeof sanitizedPayload.access_token === "string") {
        const tok = sanitizedPayload.access_token;
        sanitizedPayload.access_token = `${tok.slice(0, 10)}...${tok.slice(-6)}`;
    }

    const body = document.createElement("pre");
    body.className = "log-body";
    body.textContent = JSON.stringify(sanitizedPayload, null, 2);

    entry.appendChild(head);
    entry.appendChild(body);
    history.prepend(entry);

    showAlert(status, sanitizedPayload, retryAfter);
}

async function apiRequest(method, path, bodyObj = null) {
    const headers = { "Content-Type": "application/json" };
    if (state.accessToken) {
        headers.Authorization = `Bearer ${state.accessToken}`;
    }
    const opts = { method, headers };
    if (bodyObj !== null) {
        opts.body = JSON.stringify(bodyObj);
    }

    const resp = await fetch(path, opts);
    let data = {};
    try {
        data = await resp.json();
    } catch {
        data = { error: "Respuesta sin JSON válido" };
    }
    const retryAfter = resp.headers.get("Retry-After");
    appendHttpLog(method, path, resp.status, data, retryAfter);
    return { status: resp.status, data };
}

function setupTabs() {
    const buttons = document.querySelectorAll(".tab-btn");
    const panes = document.querySelectorAll(".tab-pane");

    buttons.forEach((btn) => {
        btn.addEventListener("click", () => {
            const target = btn.dataset.tab;
            buttons.forEach((b) => b.classList.remove("active"));
            panes.forEach((p) => p.classList.remove("active"));
            btn.classList.add("active");
            document.getElementById(`tab-${target}`).classList.add("active");
        });
    });
}

function renderTasksList(tasks) {
    const listBox = document.getElementById("tasks-list");
    listBox.textContent = "";

    if (!Array.isArray(tasks) || tasks.length === 0) {
        const empty = document.createElement("p");
        empty.className = "empty-msg";
        empty.textContent = "No hay tareas registradas para este criterio.";
        listBox.appendChild(empty);
        return;
    }

    const nextStatusMap = {
        pendiente: "en_progreso",
        en_progreso: "completada",
        completada: "pendiente",
    };

    tasks.forEach((task) => {
        const item = document.createElement("div");
        item.className = "task-item";

        const info = document.createElement("div");
        info.className = "task-info";

        const titleEl = document.createElement("div");
        titleEl.className = "task-title";
        titleEl.textContent = `#${task.id} · ${task.title} [${task.status}]`;

        const descEl = document.createElement("div");
        descEl.className = "task-desc";
        descEl.textContent = task.description || "Sin descripción";

        info.appendChild(titleEl);
        info.appendChild(descEl);

        const actions = document.createElement("div");
        actions.className = "task-actions";

        const btnAdvance = document.createElement("button");
        btnAdvance.type = "button";
        btnAdvance.className = "btn btn-secondary btn-sm";
        const targetStatus = nextStatusMap[task.status] || "pendiente";
        btnAdvance.textContent = `Pasar a ${targetStatus}`;
        btnAdvance.addEventListener("click", async () => {
            const res = await apiRequest("PUT", `/tasks/${task.id}`, { status: targetStatus });
            if (res.status === 200) {
                await refreshTasks();
            }
        });

        const btnDelete = document.createElement("button");
        btnDelete.type = "button";
        btnDelete.className = "btn btn-danger btn-sm";
        btnDelete.textContent = "Eliminar";
        btnDelete.addEventListener("click", async () => {
            const res = await apiRequest("DELETE", `/tasks/${task.id}`);
            if (res.status === 200) {
                await refreshTasks();
            }
        });

        actions.appendChild(btnAdvance);
        actions.appendChild(btnDelete);
        item.appendChild(info);
        item.appendChild(actions);
        listBox.appendChild(item);
    });
}

async function refreshTasks() {
    const query = document.getElementById("task-search-input").value.trim();
    const qs = query ? `?search=${encodeURIComponent(query)}` : "";
    const { status, data } = await apiRequest("GET", `/tasks${qs}`);
    if (status === 200) {
        renderTasksList(data.tasks);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    setupTabs();
    updateSessionView();

    document.getElementById("form-register").addEventListener("submit", async (ev) => {
        ev.preventDefault();
        const payload = {
            full_name: document.getElementById("reg-name").value,
            email: document.getElementById("reg-email").value,
            password: document.getElementById("reg-password").value,
        };
        if (document.getElementById("reg-simulate-escalation").checked) {
            payload.role = "admin";
        }
        await apiRequest("POST", "/auth/register", payload);
    });

    document.getElementById("form-login").addEventListener("submit", async (ev) => {
        ev.preventDefault();
        const { status, data } = await apiRequest("POST", "/auth/login", {
            email: document.getElementById("login-email").value,
            password: document.getElementById("login-password").value,
        });
        if (status === 200) {
            state.accessToken = data.access_token;
            state.sessionId = data.session_id;
            state.user = data.user;
            updateSessionView();
            await refreshTasks();
        }
    });

    document.getElementById("form-task-create").addEventListener("submit", async (ev) => {
        ev.preventDefault();
        const payload = {
            title: document.getElementById("task-title").value,
            description: document.getElementById("task-desc").value,
            status: document.getElementById("task-status").value,
        };
        if (document.getElementById("task-simulate-extra").checked) {
            payload.owner_id = 999;
        }
        const { status } = await apiRequest("POST", "/tasks", payload);
        if (status === 201) {
            document.getElementById("task-title").value = "";
            document.getElementById("task-desc").value = "";
            await refreshTasks();
        }
    });

    document.getElementById("form-task-search").addEventListener("submit", async (ev) => {
        ev.preventDefault();
        await refreshTasks();
    });

    document.getElementById("btn-bruteforce-demo").addEventListener("click", async () => {
        const email = document.getElementById("login-email").value || "objetivo@unsaac.edu.pe";
        for (let i = 1; i <= 3; i += 1) {
            await apiRequest("POST", "/auth/login", {
                email,
                password: `ClaveFalsa${i}`,
            });
        }
    });

    document.getElementById("btn-check-me").addEventListener("click", async () => {
        const { status, data } = await apiRequest("GET", "/auth/me");
        if (status === 200) {
            state.sessionId = data.session_id;
            state.user = data.user;
        } else if (status === 401) {
            state.accessToken = null;
            state.sessionId = null;
            state.user = null;
        }
        updateSessionView();
    });

    document.getElementById("btn-logout").addEventListener("click", async () => {
        const { status } = await apiRequest("POST", "/auth/logout");
        if (status === 200 || status === 401) {
            state.accessToken = null;
            state.sessionId = null;
            state.user = null;
            updateSessionView();
        }
    });

    document.getElementById("form-change-password").addEventListener("submit", async (ev) => {
        ev.preventDefault();
        const { status } = await apiRequest("POST", "/auth/change-password", {
            current_password: document.getElementById("chg-current").value,
            new_password: document.getElementById("chg-new").value,
        });
        if (status === 200) {
            state.accessToken = null;
            state.sessionId = null;
            state.user = null;
            updateSessionView();
        }
    });

    document.getElementById("form-forgot").addEventListener("submit", async (ev) => {
        ev.preventDefault();
        await apiRequest("POST", "/auth/forgot-password", {
            email: document.getElementById("forgot-email").value,
        });
    });

    document.getElementById("form-reset").addEventListener("submit", async (ev) => {
        ev.preventDefault();
        const { status } = await apiRequest("POST", "/auth/reset-password", {
            token: document.getElementById("reset-token").value,
            new_password: document.getElementById("reset-password").value,
        });
        if (status === 200) {
            state.accessToken = null;
            state.sessionId = null;
            state.user = null;
            updateSessionView();
        }
    });

    document.getElementById("btn-clear-log").addEventListener("click", () => {
        const history = document.getElementById("http-history");
        history.textContent = "";
        const empty = document.createElement("p");
        empty.className = "empty-msg";
        empty.textContent = "Historial limpiado.";
        history.appendChild(empty);
        document.getElementById("http-alert").classList.add("hidden");
    });
});
