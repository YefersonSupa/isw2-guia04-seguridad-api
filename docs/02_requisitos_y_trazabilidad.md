# Especificación de Requisitos de Seguridad y Matriz de Trazabilidad

Documentación técnica de la **Actividad 2** y **Ejercicio Propuesto 2.1** de la Guía de Práctica 04 (*Ingeniería de Software II — UNSAAC*).

## 1. Requisitos de Seguridad Verificables — SportReserve Co. (`RE-01`..`RE-04`)

| ID Req. | Requisito de Seguridad Verificada | Amenaza Asociada | Criterio de Aceptación / Validación Negativa | Prioridad |
|---|---|---|---|---|
| **RE-01** | El sistema verificará la propiedad de las reservas en el servidor antes de entregar los datos. | IDOR / Fuga de Privacidad | Petición de `User_A` solicitando recurso de `User_B` $\rightarrow$ **HTTP 403 Forbidden** sin datos expuestos. | Crítica |
| **RE-02** | Toda consulta a BD ejecutará sentencias parametrizadas sin concatenación directa. | Inyección SQL (SQLi) | Envío de `'x@y.com' OR '1'='1'` en búsqueda $\rightarrow$ **HTTP 400 Bad Request** o cero registros filtrados. | Crítica |
| **RE-03** | Toda entrada de usuario renderizada en HTML será escapada contextualmente. | XSS Reflejado / Almacenado | Envío de `<script>alert(1)</script>` $\rightarrow$ salida escapada y CSP activa sin ejecución JS. | Alta |
| **RE-04** | Los endpoints rechazarán parámetros malformados o tipos inválidos. | Abuso de Parámetros / Tampering | Envío de `id=abc` o sin sesión $\rightarrow$ **HTTP 400 Bad Request** sin stacktrace interno. | Alta |

---

## 2. Requisitos de Seguridad del Sistema de Tareas (`RS-01`..`RS-10`)

| ID | Requisito de Seguridad | Activo Protegido | Control Esperado | Clasificación | Criterio de Aceptación Medible |
|---|---|---|---|---|---|
| **RS-01** | Las contraseñas no se almacenan en texto plano | Credenciales | Hash lento Argon2id con sal | Obligatorio | Columna `password_hash` inicia con `$argon2id$`. |
| **RS-02** | Solo el dueño puede editar o eliminar su tarea | Tareas | Autorización `owner_id` en servidor | Obligatorio | Usuario distinto recibe `HTTP 403 Forbidden`. |
| **RS-03** | Registrar fallos de inicio de sesión y seguridad | Registros / Logs | Bitácora `audit_logs` sin secretos | Obligatorio | Evento registrado sin contraseñas, tokens ni payloads maliciosos. |
| **RS-04** | Mitigar fuerza bruta en autenticación | Credenciales | Límite por cuenta e IP + backoff | Obligatorio | Al 3er fallo retorna `HTTP 429` y header `Retry-After`. |
| **RS-05** | Regeneración y expiración estricta de sesión | Tokens de sesión | Token 256-bit + TTL + rotación | Obligatorio | Nuevo login invalida token previo; TTL vencido $\rightarrow$ `HTTP 401`. |
| **RS-06** | Recuperación con token único y corto plazo | Credenciales | Token 1-uso + invalidación previa | Obligatorio | Reuso o token expirado retorna `HTTP 400` y revoca sesiones. |
| **RS-07** | Prevenir asignación masiva (*Mass Assignment*) | Cuentas y Tareas | Lista blanca estricta de campos | Obligatorio | Enviar `role="admin"` u `owner_id` retorna `HTTP 400`. |
| **RS-08** | Consultas SQL parametrizadas al 100 % | Base de datos | Placeholders `?` en SQLite3 | Obligatorio | Payloads `' OR '1'='1` rechazados o tratados como dato literal. |
| **RS-09** | Validación positiva de archivos adjuntos | Archivos | Lista blanca MIME/extensión y tamaño | Importante | Extensión ejecutable o tamaño excesivo $\rightarrow$ `HTTP 400/413`. |
| **RS-10** | Privacidad y mensajes de error genéricos | Datos personales | Respuestas uniformes en login/reset | Importante | Mismo `HTTP 401` si el correo existe o no en el sistema. |

---

## 3. Matriz de Trazabilidad Completa (`RF` ↔ `RS` ↔ `Control` ↔ `Prueba`)

| ID RF | Requisito Funcional | Activo | ID RS | Control Técnico | Prueba Automatizada (`pytest`) |
|---|---|---|---|---|---|
| **RF-01** | Registro de usuario | Credenciales / Datos | RS-01, RS-07 | Argon2id + rol fijo `estudiante` | `test_register_uses_argon2id_and_blocks_privilege_escalation` |
| **RF-02** | Inicio de sesión | Credenciales / Sesión | RS-04, RS-05, RS-10 | Bloqueo progresivo + error genérico | `test_brute_force_progressive_lockout_by_account_and_ip` |
| **RF-03** | Cierre de sesión | Tokens de sesión | RS-05 | Revocación inmediata (`revoked=1`) | `test_session_regeneration_expiration_and_logout` |
| **RF-04** | Cambio y reset de clave | Credenciales / Tokens | RS-06, RS-03 | Token 1-uso + revoca sesiones | `test_password_reset_single_use_invalidation_expiration_and_safe_logs` |
| **RF-05** | Crear nueva tarea | Tareas | RS-07, RS-08 | Validación positiva + SQL `?` | `test_create_task_validation_extra_fields_and_safe_logs` |
| **RF-06** | Listar y buscar tareas | Tareas / Datos | RS-02, RS-08 | Filtro `owner_id` + `LIKE ? ESCAPE` | `test_tasks_idor_protection_and_parameterized_search` |
| **RF-07** | Editar tarea | Tareas | RS-02, RS-07 | Verificación `owner_id` en servidor | `test_tasks_idor_protection_and_parameterized_search` (`HTTP 403`) |
| **RF-08** | Eliminar tarea | Tareas / Registros | RS-02, RS-03 | Propiedad + log `TASK_DELETED` | `test_tasks_idor_protection_and_parameterized_search` (`HTTP 403`) |
| **RF-09** | Adjuntar archivo a tarea | Archivos | RS-09, RS-02 | Validación MIME/tamaño (diseño) | Escenario negativo `HTTP 400 / 413` |
| **RF-10** | Auditar eventos y roles | Registros / Roles | RS-03, RS-07 | `audit_logs` sin tokens ni secretos | Verificado en `tests/test_auth_security.py` y `test_tasks_security.py` |
