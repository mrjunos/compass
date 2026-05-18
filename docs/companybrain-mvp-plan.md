# CompanyBrain — Plan MVP

> **Objetivo:** Evolucionar Compass en CompanyBrain, el cerebro operativo AI-first para PyMEs LATAM.
> Generado: 2026-05-18

---

## Resumen ejecutivo

Compass ya es una base sólida: Q&A sobre documentos con PageIndex, persistencia SQLite, un monolito FastAPI limpio y un frontend React 19 parcialmente construido. Este plan lo evoluciona sistemáticamente sin romper el comportamiento existente. Cada fase produce un incremento que el fundador puede usar en su propia empresa — esa es la puerta de validación antes de escalar.

**Deuda técnica reconocida (no se planifica alrededor de ella):**
- I/O bloqueante en handlers async (`upload`, `index_document`) — solución eventual: `asyncio.to_thread`
- Tabla `messages` crece sin límite — necesita política de retención antes de Fase 3
- `mark_indexed()` en `database.py` es código muerto — eliminar en Fase 1
- Sin cobertura de tests ni linting — agregar `ruff` + `pytest-cov` a CI en Fase 1

---

## Nuevo esquema de base de datos

Todas las tablas coexisten en `data/compass.db`. `init_db()` crece con `CREATE TABLE IF NOT EXISTS`. Cambios de columnas en tablas existentes requieren `ALTER TABLE` explícito.

```sql
-- EXISTENTE (sin cambios)
CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL,
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
    indexed     BOOLEAN DEFAULT FALSE
);

-- FASE 1: Entidades de memoria estructurada

CREATE TABLE IF NOT EXISTS people (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    role        TEXT,
    email       TEXT,
    phone       TEXT,
    notes       TEXT,
    source_doc  TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_people_name ON people(name);

CREATE TABLE IF NOT EXISTS clients (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    contact_person  TEXT,
    email           TEXT,
    phone           TEXT,
    status          TEXT DEFAULT 'active',  -- 'active' | 'inactive' | 'prospect'
    last_contact_at DATETIME,
    notes           TEXT,
    source_doc      TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_clients_status ON clients(status);
CREATE INDEX IF NOT EXISTS idx_clients_last_contact ON clients(last_contact_at);

CREATE TABLE IF NOT EXISTS projects (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    client_id       INTEGER REFERENCES clients(id),
    status          TEXT DEFAULT 'active',  -- 'active' | 'completed' | 'paused' | 'cancelled'
    description     TEXT,
    started_at      DATETIME,
    deadline_at     DATETIME,
    last_update_at  DATETIME,
    source_doc      TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
CREATE INDEX IF NOT EXISTS idx_projects_client_id ON projects(client_id);
CREATE INDEX IF NOT EXISTS idx_projects_last_update ON projects(last_update_at);

CREATE TABLE IF NOT EXISTS decisions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    context     TEXT,
    outcome     TEXT NOT NULL,
    made_by     TEXT,
    made_at     DATETIME,
    impact      TEXT,               -- 'high' | 'medium' | 'low'
    source_doc  TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_decisions_made_at ON decisions(made_at);

-- FASE 2: Sistema de conectores

CREATE TABLE IF NOT EXISTS connectors (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    type            TEXT NOT NULL,  -- 'whatsapp' | 'gmail' | 'gcal' | 'slack'
    name            TEXT NOT NULL,
    config          TEXT NOT NULL,  -- JSON (campos sensibles documentados como pendientes de cifrado)
    enabled         BOOLEAN DEFAULT TRUE,
    last_synced_at  DATETIME,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS connector_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    connector_id    INTEGER NOT NULL REFERENCES connectors(id),
    external_id     TEXT,           -- ID del proveedor para deduplicación
    event_type      TEXT NOT NULL,  -- 'message_in' | 'message_out' | 'event_created' | etc.
    payload         TEXT NOT NULL,  -- JSON completo del proveedor
    processed       BOOLEAN DEFAULT FALSE,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_connector_events_connector_id ON connector_events(connector_id);
CREATE INDEX IF NOT EXISTS idx_connector_events_external_id ON connector_events(external_id);
CREATE INDEX IF NOT EXISTS idx_connector_events_processed ON connector_events(processed);

-- FASE 3: Sistema de acciones agénticas

CREATE TABLE IF NOT EXISTS actions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    type            TEXT NOT NULL,  -- 'draft_email' | 'create_calendar_event' | 'create_task'
    payload         TEXT NOT NULL,  -- JSON: parámetros completos de la acción
    status          TEXT DEFAULT 'pending',  -- 'pending' | 'approved' | 'rejected' | 'executed' | 'failed'
    proposed_by     TEXT DEFAULT 'companybrain',
    approved_by     TEXT,
    session_id      TEXT,
    connector_id    INTEGER REFERENCES connectors(id),
    result          TEXT,           -- JSON: resultado de ejecución o error
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_actions_status ON actions(status);
CREATE INDEX IF NOT EXISTS idx_actions_session_id ON actions(session_id);

-- FASE 4: Sistema de alertas y resúmenes

CREATE TABLE IF NOT EXISTS alert_rules (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    rule_type       TEXT NOT NULL,  -- 'client_no_contact' | 'project_no_update' | 'contract_expiry'
    threshold_days  INTEGER NOT NULL,
    enabled         BOOLEAN DEFAULT TRUE,
    delivery        TEXT DEFAULT 'web',  -- 'web' | 'whatsapp' | 'both'
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alert_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id         INTEGER NOT NULL REFERENCES alert_rules(id),
    entity_type     TEXT NOT NULL,  -- 'client' | 'project'
    entity_id       INTEGER NOT NULL,
    message         TEXT NOT NULL,
    delivered       BOOLEAN DEFAULT FALSE,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_alert_events_delivered ON alert_events(delivered);
CREATE INDEX IF NOT EXISTS idx_alert_events_rule_id ON alert_events(rule_id);
```

---

## Nuevos endpoints de API

Todos los routes nuevos siguen el patrón existente: `@limiter.limit(RATE_LIMIT)`, dependencia de auth, tests en `test_*.py`.

### Fase 1 — API de Entidades

```
GET    /entities/people                    → listar personas
POST   /entities/people                    → crear persona manualmente
GET    /entities/people/{id}               → detalle de persona
PATCH  /entities/people/{id}               → actualizar persona

GET    /entities/clients                   → listar clientes (?status=active)
POST   /entities/clients                   → crear cliente manualmente
GET    /entities/clients/{id}              → detalle de cliente
PATCH  /entities/clients/{id}              → actualizar cliente

GET    /entities/projects                  → listar proyectos (?status=active&client_id=)
POST   /entities/projects                  → crear proyecto manualmente
GET    /entities/projects/{id}             → detalle de proyecto
PATCH  /entities/projects/{id}             → actualizar proyecto

GET    /entities/decisions                 → listar decisiones (?limit=20&offset=0)
POST   /entities/decisions                 → crear decisión manualmente

POST   /documents/{doc_id}/extract         → disparar extracción de entidades de un doc
GET    /documents/{doc_id}/entities        → listar entidades extraídas de un doc
```

### Fase 2 — API de Conectores

```
GET    /connectors                         → listar conectores
POST   /connectors                         → registrar conector (tipo + config)
DELETE /connectors/{id}                    → eliminar conector
PATCH  /connectors/{id}/toggle             → habilitar/deshabilitar

POST   /webhooks/whatsapp                  → webhook entrante de WhatsApp (auth propio)
GET    /webhooks/whatsapp                  → verificación de webhook (GET challenge)
POST   /connectors/{id}/sync               → disparar sync manual (Gmail/GCal)
GET    /connectors/{id}/events             → listar eventos crudos del conector
```

### Fase 3 — API de Acciones

```
GET    /actions                            → listar acciones (?status=pending)
GET    /actions/{id}                       → detalle de acción
POST   /actions/{id}/approve               → aprobar y ejecutar acción
POST   /actions/{id}/reject                → rechazar acción
```

### Fase 4 — API de Alertas

```
GET    /alerts/rules                       → listar reglas de alerta
POST   /alerts/rules                       → crear regla
PATCH  /alerts/rules/{id}                  → actualizar regla
DELETE /alerts/rules/{id}                  → eliminar regla

GET    /alerts/events                      → listar alertas disparadas (?delivered=false)
POST   /alerts/events/{id}/dismiss         → marcar como entregada

GET    /digest/preview                     → previsualizar resumen (sin enviar)
POST   /digest/send                        → generar y entregar resumen
```

---

## Fase 1 — Base Completa

**Complejidad: Media.** Sin dependencias externas nuevas. Mayor riesgo: calidad del prompt de extracción de entidades.

### 1.1 Migraciones de base de datos

Extender `backend/database.py`:
- Agregar tablas Fase 1 en `init_db()`
- Agregar funciones CRUD por entidad
- Eliminar `mark_indexed()` (código muerto)
- Agregar `prune_messages(session_id, keep_last=100)`

Firmas a implementar:

```python
def create_person(name, role, email, phone, notes, source_doc) -> int
def list_people(limit=50) -> list[dict]
def get_person(person_id) -> dict | None
def update_person(person_id, **fields) -> bool

def create_client(name, contact_person, email, phone, status, notes, source_doc) -> int
def list_clients(status=None, limit=50) -> list[dict]
def get_client(client_id) -> dict | None
def update_client(client_id, **fields) -> bool

def create_project(name, client_id, status, description, started_at, deadline_at, source_doc) -> int
def list_projects(status=None, client_id=None, limit=50) -> list[dict]
def get_project(project_id) -> dict | None
def update_project(project_id, **fields) -> bool

def create_decision(title, context, outcome, made_by, made_at, impact, source_doc) -> int
def list_decisions(limit=20, offset=0) -> list[dict]
```

### 1.2 Pipeline de extracción de entidades

Crear `backend/extractor.py`:

```python
EXTRACTION_PROMPT = """Eres un asistente que extrae entidades estructuradas de documentos empresariales.

Dado el siguiente contenido, extrae las entidades en formato JSON:

{
  "people": [{"name":"...","role":"...","email":"...","phone":"...","notes":"..."}],
  "clients": [{"name":"...","contact_person":"...","email":"...","notes":"..."}],
  "projects": [{"name":"...","client":"...","status":"...","description":"...","deadline":"..."}],
  "decisions": [{"title":"...","context":"...","outcome":"...","made_by":"...","made_at":"YYYY-MM-DD","impact":"high|medium|low"}]
}

Solo incluye entidades claramente mencionadas. Responde SOLO con el JSON.

DOCUMENTO ({doc_name}):
{content}"""

async def extract_entities_from_doc(doc_id, doc_name, indexer, model) -> dict
async def extract_all_documents(indexer, model) -> dict
```

**Nota importante:** `_extract_summaries()` de `chat.py` debe moverse a `backend/utils.py` y ser importado por ambos `chat.py` y `extractor.py`. Hacer esto primero.

**Fallback de extracción:** Si el LLM no produce JSON válido, reintentar con prompt más estricto ("responde ÚNICAMENTE con JSON válido, sin texto adicional"). Si falla dos veces, loguear y omitir ese documento sin fallar el request.

### 1.3 Routers de entidades

Crear `backend/routers/__init__.py` y `backend/routers/entities.py`:

```python
# backend/routers/entities.py
router = APIRouter(prefix="/entities", tags=["entities"])

class PersonCreate(BaseModel):
    name: str
    role: str | None = None
    email: str | None = None
    phone: str | None = None
    notes: str | None = None

# Incluir en main.py:
# from .routers.entities import router as entities_router
# app.include_router(entities_router)
```

### 1.4 Completar frontend

**Nuevas páginas:**
- `frontend/src/pages/Entities.tsx` — dashboard de Personas, Clientes, Proyectos y Decisiones en tabs. Solo lectura para MVP, con botón "Agregar" por tipo.
- `frontend/src/pages/EntityDetail.tsx` — detalle de un cliente o proyecto con decisiones relacionadas.

**Nuevos componentes:**
- `frontend/src/components/EntityCard.tsx` — tarjeta reutilizable siguiendo el sistema de diseño Nocturnal Architect existente.
- `frontend/src/components/EntityBadge.tsx` — pill de estado (active/inactive/pending) usando tokens de color existentes.

**Archivos a actualizar:**
- `frontend/src/lib/api.ts` — agregar funciones: `getPeople()`, `getClients()`, `getProjects()`, `getDecisions()`, `createPerson()`, `updateClient()`, etc.
- `frontend/src/components/Sidebar.tsx` — agregar nav item `/entities` con icono `Users` de lucide.
- `frontend/src/App.tsx` — agregar rutas `/entities` y `/entities/:type/:id`.
- `frontend/src/pages/Chat.tsx` — traducir sugerencias hardcodeadas al español.

### 1.5 Rebrand a CompanyBrain

Cambios de string (no reestructuración):
- `frontend/src/components/Sidebar.tsx` — `"Compass"` → `"CompanyBrain"`, tagline → `"Tu cerebro empresarial"`
- `backend/chat.py` — primera línea del SYSTEM_PROMPT: `"Eres CompanyBrain, el cerebro operativo de la empresa."`
- `backend/main.py` — `title="CompanyBrain"`, `version="0.3.0"`
- `frontend/index.html` — `<title>CompanyBrain</title>`

### Archivos nuevos en Fase 1

```
backend/extractor.py
backend/utils.py                        (mover _extract_summaries desde chat.py)
backend/routers/__init__.py
backend/routers/entities.py
frontend/src/pages/Entities.tsx
frontend/src/pages/EntityDetail.tsx
frontend/src/components/EntityCard.tsx
frontend/src/components/EntityBadge.tsx
tests/test_extractor.py
tests/test_entities_api.py
```

---

## Fase 2 — Integraciones en Vivo

**Complejidad: Alta.** APIs externas, flujos OAuth, ingesta de webhooks, procesamiento async.

### Arquitectura de conectores

Crear paquete `backend/connectors/`:

```
backend/connectors/
├── __init__.py
├── base.py          ← clase abstracta BaseConnector
├── registry.py      ← CONNECTOR_CLASSES dict + get_connector()
├── whatsapp.py      ← Meta Cloud API
├── gmail.py         ← Google Gmail API (service account)
└── gcal.py          ← Google Calendar API (service account)
```

**`backend/connectors/base.py`:**

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class ConnectorConfig:
    connector_id: int
    connector_type: str
    name: str
    config: dict

@dataclass
class InboundEvent:
    external_id: str
    event_type: str        # 'message_in' | 'email_received' | 'calendar_event'
    sender: str | None
    content: str
    raw_payload: dict

class BaseConnector(ABC):
    def __init__(self, cfg: ConnectorConfig): self.cfg = cfg

    @abstractmethod
    async def verify_webhook(self, headers: dict, body: bytes) -> bool: ...

    @abstractmethod
    async def parse_inbound(self, payload: dict) -> list[InboundEvent]: ...

    @abstractmethod
    async def send_message(self, recipient: str, text: str) -> dict: ...

    @abstractmethod
    async def health_check(self) -> bool: ...

    # Opcionales — no todos los conectores implementan estos
    async def create_draft_email(self, to, subject, body) -> dict:
        raise NotImplementedError

    async def create_calendar_event(self, title, start, end, description, attendees) -> dict:
        raise NotImplementedError

    async def list_recent_emails(self, max_results=10) -> list[dict]:
        raise NotImplementedError

    async def list_upcoming_events(self, days_ahead=7) -> list[dict]:
        raise NotImplementedError
```

### WhatsApp — Meta Cloud API

Usar Meta Cloud API directa (no Twilio — más barato, mejores rate limits para LATAM).

Config requerida en `connectors.config` (JSON):
```json
{
  "phone_number_id": "...",
  "access_token": "...",
  "webhook_verify_token": "...",
  "app_secret": "..."
}
```

**Routing de mensajes WhatsApp al pipeline de chat:**

`session_id = "wa_" + normalized_phone` (ej: `wa_573001234567`). Esto reutiliza la tabla `messages` y `get_session_messages()` sin cambios. Cada contacto de WhatsApp tiene su historial de conversación continuo.

### Google Workspace — Service Account

Usar Service Account con delegación de dominio (no OAuth de 3 patas). Requiere solo configuración del admin de Google Workspace una vez. Asume que el usuario tiene Google Workspace (no Gmail personal) — esto aplica para la agencia target.

Config requerida:
```json
{
  "service_account_file": "./config/service-account.json",
  "delegated_email": "owner@empresa.com",
  "calendar_id": "primary"
}
```

**Nuevas dependencias pip para Fase 2:**
```
google-auth==2.29.0
google-api-python-client==2.126.0
```

### Servicio de sync — `backend/sync.py`

Polling en background para conectores que no hacen push (Gmail, GCal). Corre como tareas asyncio iniciadas en el lifespan de FastAPI.

```python
# Variable de entorno: COMPANYBRAIN_SYNC_INTERVAL_MINUTES=5 (default)
async def start_sync_loop(app: FastAPI) -> None: ...
async def sync_connector(connector_cfg, app: FastAPI) -> None: ...
```

### Archivos nuevos en Fase 2

```
backend/connectors/__init__.py
backend/connectors/base.py
backend/connectors/registry.py
backend/connectors/whatsapp.py
backend/connectors/gmail.py
backend/connectors/gcal.py
backend/routers/webhooks.py
backend/routers/connectors.py
backend/sync.py
frontend/src/pages/Connectors.tsx
tests/test_connectors.py
tests/test_webhooks.py
```

---

## Fase 3 — Acciones Agénticas

**Complejidad: Media.** El desafío mayor es el UX de confianza, no la implementación.

### Definiciones de tools — `backend/tools.py`

```python
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "draft_email",
            "description": "Redactar un borrador de email para revisión humana antes de enviar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                    "context": {"type": "string"}
                },
                "required": ["to", "subject", "body"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_calendar_event",
            "description": "Crear un evento en Google Calendar, requiere aprobación humana.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "start_datetime": {"type": "string", "description": "ISO 8601"},
                    "end_datetime": {"type": "string", "description": "ISO 8601"},
                    "attendees": {"type": "array", "items": {"type": "string"}},
                    "description": {"type": "string"},
                    "context": {"type": "string"}
                },
                "required": ["title", "start_datetime", "end_datetime"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": "Registrar una tarea o acción de seguimiento.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "assigned_to": {"type": "string"},
                    "due_date": {"type": "string", "description": "ISO 8601 date"},
                    "related_client": {"type": "string"},
                    "related_project": {"type": "string"},
                    "context": {"type": "string"}
                },
                "required": ["title"]
            }
        }
    }
]
```

### Pipeline de chat modificado

Cuando la pregunta implica una acción, el LLM puede devolver `tool_calls`. El pipeline:
1. Detecta `tool_calls` en la respuesta del LLM
2. Guarda una `action` pendiente en DB (NO ejecuta)
3. Devuelve la propuesta junto con la respuesta

**Nuevo shape de respuesta de `POST /chat`:**
```json
{
  "answer": "Puedo preparar ese email. Lo he propuesto para tu revisión.",
  "sources": [...],
  "suggestion": null,
  "session_id": "...",
  "proposed_actions": [
    {
      "action_id": 42,
      "type": "draft_email",
      "summary": "Email a camila@empresa.co sobre ClienteX",
      "status": "pending"
    }
  ]
}
```

**Fallback para modelos sin function calling:** Si el modelo no soporta `tool_calls`, parsear la respuesta buscando un marcador `🔧 ACCIÓN:` similar al patrón existente de `💡 SUGERENCIA:`.

### UX de aprobación en el chat

El mensaje del asistente renderiza un `ActionCard` inline — widget compacto con tipo, resumen, y dos botones: "Aprobar" (primary) y "Rechazar" (ghost). Aprobar llama a `POST /actions/{id}/approve`. Todo ocurre sin salir del chat.

### Archivos nuevos en Fase 3

```
backend/tools.py
backend/executor.py
backend/routers/actions.py
frontend/src/components/ActionCard.tsx
frontend/src/pages/Actions.tsx
tests/test_actions.py
```

---

## Fase 4 — Inteligencia Proactiva

**Complejidad: Baja-Media.** Scheduling es sencillo; la calidad de alertas depende del tuning de prompts.

### Scheduler — `backend/scheduler.py`

Tareas asyncio con sleep loops, iniciadas en el lifespan de FastAPI. Sin Celery ni APScheduler (overkill para MVP single-user, añade complejidad operacional).

```
Jobs:
  check_alerts()     → cada 1 hora
  generate_digest()  → diario a las 8:00 AM hora local
```

### Reglas de alerta — `backend/alerts.py`

```python
async def check_client_no_contact(threshold_days, conn) -> list[dict]:
    # SELECT * FROM clients WHERE status='active'
    # AND (last_contact_at < datetime('now', '-N days') OR last_contact_at IS NULL)

async def check_project_no_update(threshold_days, conn) -> list[dict]:
    # SELECT * FROM projects WHERE status='active'
    # AND last_update_at < datetime('now', '-N days')

async def check_contract_expiry(threshold_days, conn) -> list[dict]:
    # SELECT * FROM projects WHERE deadline_at BETWEEN datetime('now')
    # AND datetime('now', '+N days')

RULE_HANDLERS = {
    "client_no_contact": check_client_no_contact,
    "project_no_update": check_project_no_update,
    "contract_expiry": check_contract_expiry,
}
```

### Digest diario

El resumen usa el pipeline LLM existente con un prompt en español. El contexto viene de las tablas de entidades (estado real-time), no de documentos indexados.

### Entrega

- **Web:** `GET /alerts/events?delivered=false` — el frontend hace polling cada 60s y muestra badge de notificaciones en sidebar.
- **WhatsApp:** Si hay conector registrado, `connector.send_message()` al teléfono del dueño configurado en `COMPANYBRAIN_OWNER_PHONE`.

### Variables de entorno nuevas para Fase 4

```env
COMPANYBRAIN_DIGEST_HOUR=8              # hora (0-23) para digest diario
COMPANYBRAIN_ALERT_CHECK_INTERVAL=60   # minutos entre checks de alertas
COMPANYBRAIN_OWNER_PHONE=               # número WhatsApp para digest
```

### Archivos nuevos en Fase 4

```
backend/scheduler.py
backend/alerts.py
backend/routers/alerts.py
frontend/src/pages/Alerts.tsx
tests/test_alerts.py
tests/test_scheduler.py
```

---

## Resumen de archivos por fase

### Qué no cambia
- `backend/indexer.py` — sin cambios
- `backend/watcher.py` — sin cambios en Fases 1-3
- `frontend/src/index.css` — tokens de diseño intactos
- `frontend/src/components/Toast.tsx`, `TopBar.tsx`
- `vite.config.ts`
- `pageindex/` — submodulo intocable

### Qué se modifica (cambios aditivos)
- `backend/database.py` — tablas nuevas, funciones CRUD, eliminar `mark_indexed()`
- `backend/main.py` — incluir routers, hooks en lifespan, metadata
- `backend/chat.py` — manejo de tool_calls (Fase 3), extraer `_extract_summaries` a `utils.py`
- `frontend/src/App.tsx` — rutas nuevas
- `frontend/src/components/Sidebar.tsx` — nav items nuevos
- `frontend/src/lib/api.ts` — funciones API nuevas
- `requirements.txt` — deps por fase
- `.env.example` — variables nuevas con comentarios

---

## Decisiones arquitectónicas clave

| Decisión | Razonamiento | Trade-off |
|---|---|---|
| SQLite sin framework de migraciones | Cero complejidad ops para fundador solo | Requiere disciplina estricta con `ALTER TABLE` |
| Meta Cloud API sobre Twilio para WhatsApp | Gratis (solo pago por conversación), mejores rate limits LATAM | Proceso de aprobación de Meta (1-2 días) |
| Service Account Google sobre OAuth 3-patas | Setup único por admin, sin pantalla de consentimiento | Requiere Google Workspace (no Gmail personal) |
| asyncio scheduler sobre Celery | Cero infraestructura extra, deployment simple | Riesgo de muerte silente (igual que el watcher actual) |
| Extracción de entidades en post-index | Queries rápidas, UI de entidades sin preguntar al LLM | Calidad congelada al momento de indexar; re-extracción manual disponible |
| Aprobación de acciones en el chat | UX de menor fricción, sin cambio de contexto | Acciones pendientes de sesiones anteriores requieren ir a `/actions` |
| session_id WhatsApp = teléfono | Reutiliza tabla `messages` y funciones existentes sin cambios | Historial mezclado si dos personas usan el mismo teléfono |

---

## Riesgos principales

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Modelo Ollama no produce JSON válido para extracción | Alta | Fallback con prompt más estricto + retry; usar `gemma4:e4b` o `llama3.2` según capacidad |
| Modelo Ollama no soporta function calling | Media | Fallback con marcador `🔧 ACCIÓN:` en el response, igual que `💡 SUGERENCIA:` |
| Aprobación de WhatsApp Business API Meta tarda | Media | Documentar en setup; arrancar con web UI primero, agregar WA después |
| Calidad de alertas (demasiados falsos positivos) | Media | Empezar con threshold_days alto (30+ días); hacer configurable desde UI |
| Scheduler asyncio muere silenciosamente | Baja | Agregar heartbeat log; supervisión similar a la del watcher |

---

## Variables de entorno completas (todas las fases)

```env
# Existentes
OLLAMA_API_BASE=http://localhost:11434
COMPASS_MODEL=ollama/gemma4:e4b
COMPASS_DOCS_PATH=./data/docs
COMPASS_WORKSPACE=./data/index
COMPASS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
COMPASS_API_KEY=
COMPASS_RATE_LIMIT=60/minute

# Fase 2 — Sync
COMPANYBRAIN_SYNC_INTERVAL_MINUTES=5    # intervalo de polling para Gmail/GCal

# Fase 4 — Alertas y digest
COMPANYBRAIN_DIGEST_HOUR=8              # hora para digest diario (0-23)
COMPANYBRAIN_ALERT_CHECK_INTERVAL=60   # minutos entre evaluaciones de alertas
COMPANYBRAIN_OWNER_PHONE=               # ej: +573001234567 (WhatsApp del dueño para digest)
```
