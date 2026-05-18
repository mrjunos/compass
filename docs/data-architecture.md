# CompanyBrain — Arquitectura de datos a escala

> Diseño de la capa de métricas y el meta-árbol de empresa.
> Complementa `companybrain-mvp-plan.md` con el modelo de datos para razonamiento agéntico a escala.

---

## El problema a resolver

El sistema actual en `chat.py` tiene dos limitaciones que se vuelven críticas con el crecimiento:

**Limitación 1 — O(n) en contexto**

```python
# chat.py — _extract_summaries()
# Carga TODOS los resúmenes de TODOS los nodos de TODOS los documentos seleccionados.
# Con 5 documentos pequeños: ~2k tokens. Con 500 documentos: imposible.
def _extract_summaries(structure_json: str) -> str:
    def _collect(nodes, parts):
        for node in nodes:
            if node.get("summary"):
                parts.append(node["summary"])   # todo entra al contexto
            if node.get("nodes"):
                _collect(node["nodes"], parts)  # recursivo sin límite
```

**Limitación 2 — Solo documentos como fuente de verdad**

Un historial de ventas no es un documento. Un patrón estacional no es un archivo Markdown. Los datos numéricos estructurados requieren consultas precisas, no recuperación semántica. Un agente que intenta "recordar" números que leyó en un documento comete errores. Un agente que consulta una tabla con la query correcta siempre es exacto.

La solución combina dos piezas:
1. **Capa de métricas** — almacenamiento y consulta de datos estructurados temporales.
2. **Meta-árbol de empresa** — árbol jerárquico de resúmenes que cubre toda la empresa, navegable en O(log n).

Estas dos piezas se conectan mediante **herramientas de agente** que saben exactamente a dónde ir según el tipo de dato.

---

## Los tres planos de datos

Antes del diseño detallado, la taxonomía fundamental. Cada tipo de dato tiene un hogar natural:

| Tipo de dato | Ejemplos | Almacenamiento | Acceso del agente |
|---|---|---|---|
| **Estructurado temporal** | ventas, usuarios, sesiones, facturación | Tablas de series de tiempo en SQLite | SQL via herramienta |
| **Conocimiento no estructurado** | documentos, SOPs, decisiones, actas | PageIndex (árbol por documento) | Navegación de meta-árbol |
| **Entidades relacionadas** | clientes, proyectos, personas | SQLite (tablas del MVP plan) | SQL via herramienta |
| **Conversaciones** | chat, WhatsApp, email | SQLite `messages` + resúmenes indexados | Meta-árbol (nodo de conversaciones) |
| **Tendencias externas** | mercado, competidores, búsquedas | Ingestión periódica → PageIndex | Meta-árbol (nodo de tendencias) |

La regla de oro: **el agente nunca adivina un número — lo consulta. Nunca recuerda contexto — lo navega.**

---

## Parte 1 — Capa de métricas

### Schema: tablas de series de tiempo

```sql
-- Eventos crudos — la fuente de verdad, append-only
CREATE TABLE IF NOT EXISTS metric_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    occurred_at     DATETIME NOT NULL,
    metric_type     TEXT NOT NULL,      -- ver tipos abajo
    value           REAL NOT NULL,
    currency        TEXT,               -- 'COP' | 'USD' | 'EUR' (null si no aplica)
    dimension_1     TEXT,               -- primera dimensión de segmentación
    dimension_2     TEXT,               -- segunda dimensión (opcional)
    entity_id       INTEGER,            -- FK lógica: client_id, project_id, user_id
    entity_type     TEXT,               -- 'client' | 'project' | 'user' | 'product'
    source          TEXT,               -- 'manual' | 'alegra' | 'hubspot' | 'stripe' | 'whatsapp'
    external_id     TEXT,               -- ID del sistema fuente (para dedup)
    metadata        TEXT,               -- JSON: datos adicionales sin schema fijo
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Índices para los patrones de query más comunes
CREATE INDEX IF NOT EXISTS idx_metric_events_type_date
    ON metric_events(metric_type, occurred_at);

CREATE INDEX IF NOT EXISTS idx_metric_events_entity
    ON metric_events(entity_type, entity_id, occurred_at);

CREATE INDEX IF NOT EXISTS idx_metric_events_external
    ON metric_events(source, external_id);  -- dedup por fuente


-- Agregaciones diarias precomputadas — evita full scans en queries de dashboard
CREATE TABLE IF NOT EXISTS metric_daily (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            DATE NOT NULL,
    metric_type     TEXT NOT NULL,
    dimension       TEXT,               -- null = total, o valor de segmentación
    total           REAL NOT NULL,
    count           INTEGER NOT NULL,
    min_val         REAL,
    max_val         REAL,
    avg_val         REAL,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_metric_daily_unique
    ON metric_daily(date, metric_type, COALESCE(dimension, ''));


-- Snapshots periódicos de métricas clave — lectura ultrarrápida para el agente
CREATE TABLE IF NOT EXISTS metric_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_date   DATE NOT NULL,
    metric_type     TEXT NOT NULL,
    period          TEXT NOT NULL,      -- 'day' | 'week' | 'month' | 'quarter' | 'year'
    value           REAL NOT NULL,
    change_pct      REAL,               -- % vs período anterior (null en primer snapshot)
    summary_text    TEXT,               -- ej: "Ventas Q4 2024: $610k (+45% vs Q4 2023)"
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_metric_snapshots_unique
    ON metric_snapshots(snapshot_date, metric_type, period);
```

**Tipos de métricas (`metric_type`):**

```
# Revenue
sale_amount         — transacción de venta completada
invoice_issued      — factura emitida
invoice_paid        — pago recibido
invoice_overdue     — factura vencida sin pago

# Usuarios / Clientes
client_acquired     — nuevo cliente
client_churned      — cliente que cancela
client_contact      — interacción con cliente (reunión, email, llamada)
proposal_sent       — propuesta enviada
proposal_won        — propuesta aceptada
proposal_lost       — propuesta rechazada

# Proyectos
project_started     — inicio de proyecto
project_completed   — cierre de proyecto
project_milestone   — hito alcanzado
project_delayed     — retraso detectado

# Equipo (si aplica)
employee_hours      — horas trabajadas por persona/proyecto
```

**Convención de dimensiones:**

`dimension_1` y `dimension_2` llevan los valores de segmentación más importantes:

```
Para sale_amount:
  dimension_1 = segmento ('enterprise' | 'smb' | 'startup')
  dimension_2 = canal ('referral' | 'inbound' | 'outbound' | 'partner')

Para client_contact:
  dimension_1 = tipo ('meeting' | 'email' | 'whatsapp' | 'call')
  dimension_2 = dirección ('inbound' | 'outbound')
```

---

### Herramientas de consulta para el agente

Estas funciones son las "tools" que el agente llama directamente. No son búsquedas semánticas — son queries SQL con parámetros validados.

```python
# backend/metrics.py

def query_metric(
    metric_type: str,
    start_date: str,           # ISO 8601 date
    end_date: str,
    dimension: str | None = None,
    entity_id: int | None = None,
    entity_type: str | None = None,
    granularity: str = "month",   # 'day' | 'week' | 'month' | 'quarter' | 'year'
) -> list[dict]:
    """
    Returns aggregated metric data for the given period.
    Uses metric_daily if granularity allows, otherwise queries metric_events.

    Example return:
    [
      {"period": "2024-Q4", "total": 610000, "count": 47, "change_pct": 45.2},
      {"period": "2024-Q3", "total": 210000, "count": 31, "change_pct": 12.1},
    ]
    """

def detect_seasonal_pattern(
    metric_type: str,
    years_back: int = 3,
    dimension: str | None = None,
) -> dict:
    """
    Computes the seasonal index for each quarter/month by comparing
    each period against the annual average across all years.

    Example return:
    {
      "peak_period": "Q4",
      "peak_multiplier": 2.9,
      "trough_period": "Q1",
      "trough_multiplier": 0.6,
      "by_quarter": {"Q1": 0.6, "Q2": 0.9, "Q3": 1.0, "Q4": 2.9},
      "confidence": "high",     # 'high' si >=3 años, 'low' si <3
      "years_analyzed": 3
    }

def compute_growth(
    metric_type: str,
    current_period: str,    # ej: "2025-Q1"
    vs_period: str,         # ej: "2024-Q1"  (YoY)  o  "2024-Q4"  (QoQ)
    dimension: str | None = None,
) -> dict:
    """
    Example return:
    {
      "current": 195000,
      "previous": 142000,
      "change": 53000,
      "change_pct": 37.3,
      "trend": "accelerating"  # vs the prior comparison period's change_pct
    }

def get_metric_snapshot(
    metric_type: str,
    period: str = "month",
    limit: int = 12,
) -> list[dict]:
    """
    Fast read from metric_snapshots. Used for dashboard and digest generation.
    Returns most recent N snapshots with pre-computed change_pct.
    """

def ingest_metric_event(
    metric_type: str,
    value: float,
    occurred_at: str,
    dimension_1: str | None = None,
    dimension_2: str | None = None,
    entity_id: int | None = None,
    entity_type: str | None = None,
    source: str = "manual",
    external_id: str | None = None,
    metadata: dict | None = None,
) -> int:
    """
    Insert a raw event and queue a metric_daily recompute for that day.
    Returns event id.
    """
```

**Definición de las tools para el agente** (en `backend/tools.py`):

```python
METRIC_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_metric",
            "description": "Consulta datos históricos de una métrica del negocio por período, segmento o entidad.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric_type": {
                        "type": "string",
                        "description": "Tipo de métrica: sale_amount, client_acquired, proposal_won, etc."
                    },
                    "start_date": {"type": "string", "description": "Fecha inicio ISO 8601 (YYYY-MM-DD)"},
                    "end_date":   {"type": "string", "description": "Fecha fin ISO 8601 (YYYY-MM-DD)"},
                    "granularity": {
                        "type": "string",
                        "enum": ["day", "week", "month", "quarter", "year"],
                        "description": "Nivel de agregación"
                    },
                    "dimension": {"type": "string", "description": "Filtro de segmento (enterprise, smb, etc.)"}
                },
                "required": ["metric_type", "start_date", "end_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "detect_seasonal_pattern",
            "description": "Detecta el patrón estacional de una métrica analizando los últimos N años.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric_type": {"type": "string"},
                    "years_back":  {"type": "integer", "default": 3}
                },
                "required": ["metric_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compute_growth",
            "description": "Calcula el crecimiento de una métrica entre dos períodos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric_type":      {"type": "string"},
                    "current_period":   {"type": "string", "description": "Ej: '2025-Q1'"},
                    "vs_period":        {"type": "string", "description": "Ej: '2024-Q1' (YoY) o '2024-Q4' (QoQ)"},
                    "dimension":        {"type": "string"}
                },
                "required": ["metric_type", "current_period", "vs_period"]
            }
        }
    }
]
```

---

### Proceso de ingestión

Los datos llegan desde tres vías:

**Vía 1 — Manual** (siempre disponible)
`POST /metrics/events` — el usuario registra ventas, contactos, hitos directamente desde la UI.

**Vía 2 — Conectores** (Fase 2 del MVP plan)
Cuando Gmail sincroniza una factura pagada, o HubSpot envía un deal cerrado, el conector llama a `ingest_metric_event()` con `source="alegra"` / `source="hubspot"`. El `external_id` previene duplicados.

**Vía 3 — Extracción desde documentos**
Cuando se indexa un documento que contiene cifras históricas (reporte anual, resumen de ventas), el pipeline de extracción de entidades (`extractor.py`) también extrae métricas pasadas y las ingesta con `source="document_extraction"`.

**Recompute de agregaciones** (background job en `scheduler.py`):
- Al insertar un `metric_event`, se marca el día como "dirty" en una tabla `recompute_queue`.
- El scheduler corre cada 5 minutos y procesa la cola: recomputa `metric_daily` para los días marcados.
- `metric_snapshots` se actualiza cada hora para períodos recientes, diariamente para histórico.

---

## Parte 2 — Meta-árbol de empresa

### El insight central

`_route_documents()` en `chat.py` ya hace algo parecido a lo que necesitamos: usa los resúmenes del nivel raíz de cada documento para decidir a cuál ir. El meta-árbol generaliza esta idea a **toda la empresa**, con múltiples niveles de navegación.

En lugar de: *"¿cuál de mis 5 documentos es relevante?"*
El meta-árbol responde: *"¿en qué dominio de la empresa está la respuesta, en qué subdominio, y qué tipo de dato necesito?"*

La diferencia a escala: con 500 documentos, cargar todos sus resúmenes en el routing prompt es inviable. Con el meta-árbol, el agente siempre ve solo ~10-20 nodos a la vez y navega hacia abajo selectivamente.

### Schema

```sql
-- Nodos del árbol de conocimiento de la empresa
CREATE TABLE IF NOT EXISTS knowledge_tree (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_id           INTEGER REFERENCES knowledge_tree(id),
    node_type           TEXT NOT NULL,
    -- 'root' | 'domain' | 'subdomain' | 'document' | 'metric_summary'
    -- | 'entity_summary' | 'conversation_summary'
    name                TEXT NOT NULL,
    description         TEXT,           -- etiqueta humana, sin estructura
    summary             TEXT,           -- resumen generado por LLM (~150 palabras)
    summary_token_count INTEGER,        -- para monitorear crecimiento de contexto
    summary_updated_at  DATETIME,
    is_stale            BOOLEAN DEFAULT FALSE, -- true cuando hijos son más nuevos que summary
    doc_id              TEXT,           -- si node_type='document', doc_id de PageIndex
    metric_type         TEXT,           -- si node_type='metric_summary'
    entity_type         TEXT,           -- si node_type='entity_summary'
    time_range_start    DATE,           -- para nodos temporales (sales/2024, etc.)
    time_range_end      DATE,
    depth               INTEGER NOT NULL DEFAULT 0,  -- 0=root, 1=domain, 2=subdomain...
    sort_order          INTEGER DEFAULT 0,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_knowledge_tree_parent
    ON knowledge_tree(parent_id);

CREATE INDEX IF NOT EXISTS idx_knowledge_tree_type
    ON knowledge_tree(node_type);

CREATE INDEX IF NOT EXISTS idx_knowledge_tree_doc
    ON knowledge_tree(doc_id)
    WHERE doc_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_knowledge_tree_stale
    ON knowledge_tree(is_stale)
    WHERE is_stale = TRUE;
```

### Estructura canónica del árbol

El árbol se inicializa con esta estructura fija al crear la empresa. Los nodos hoja se van poblando automáticamente.

```
[root] TechFlow Agency
│   summary: "Agencia digital 5 personas, $450k ARR, 23 clientes activos,
│             8 proyectos en curso. Q4 es temporada alta (2.9x baseline).
│             Segmento enterprise creciendo, trabajo AI/diseño lidera ingresos."
│
├── [domain] Comercial
│   │   summary: "23 clientes activos, $450k ARR, +38% YoY.
│   │             Top 5 enterprise = 60% revenue. 4 propuestas activas."
│   │
│   ├── [subdomain] Ventas
│   │   │   summary: "Registro histórico en 2024 ($610k Q4). Ciclo
│   │   │             de ventas promedio 18 días. Canal referidos = 70%."
│   │   ├── [metric_summary] Ventas / 2025        ← nodo auto-generado
│   │   ├── [metric_summary] Ventas / 2024
│   │   └── [metric_summary] Ventas / 2023
│   │
│   ├── [subdomain] Clientes
│   │   │   summary: "23 activos, 4 en riesgo de churn (sin contacto >30 días).
│   │   │             LTV promedio $19k. Mejor segmento: enterprise tech."
│   │   └── [entity_summary] Clientes activos     ← regenerado cada 6h
│   │
│   ├── [subdomain] Propuestas
│   │   └── [metric_summary] Propuestas / 2025
│   │
│   └── [subdomain] Tendencias de mercado
│       ├── [document] análisis-mercado-2026.md   ← hoja PageIndex
│       └── [document] trends-Q1-2026.md
│
├── [domain] Proyectos
│   │   summary: "8 activos, 2 con riesgo de deadline.
│   │             Capacidad actual al 85%. Entrega promedio 6 semanas."
│   ├── [subdomain] Activos
│   │   └── [entity_summary] Proyectos activos
│   └── [subdomain] Completados
│       └── [entity_summary] Proyectos 2024
│
├── [domain] Conocimiento operativo
│   │   summary: "Documentados: onboarding, servicios, procesos.
│   │             3 documentos indexados. Último update: hace 2 semanas."
│   ├── [document] servicios.md
│   ├── [document] onboarding-clientes.md
│   ├── [document] onboarding-equipo.md
│   └── [document] proveedores.md
│
├── [domain] Decisiones
│   │   summary: "12 decisiones en 2025. Pricing subió 15% en Q1.
│   │             3 decisiones reversadas. Última: cambio stack React+Vite."
│   ├── [subdomain] Pricing
│   │   └── [document] decisiones.md          ← mismos docs, clasificados por dominio
│   └── [subdomain] Equipo y herramientas
│       └── [document] decisiones.md
│
└── [domain] Métricas recientes
        summary: "Última semana: 2 ventas ($18k), 1 nuevo cliente,
                  3 contactos con clientes, 1 propuesta enviada."
        └── [metric_summary] Actividad / últimos-7-días
```

**Observación clave:** un mismo documento puede aparecer en múltiples nodos del árbol (ej: `decisiones.md` bajo Pricing Y bajo Equipo). El árbol organiza por **dominio de negocio**, no por archivo. El `doc_id` apunta al mismo árbol de PageIndex en ambos casos.

### Mecanismo de actualización incremental

Cuando cambia algo (nuevo documento indexado, nueva métrica ingresada, nueva entidad creada):

```
Evento disparador → actualizar nodo hoja → propagar hacia arriba

1. Ocurre un evento:
   - Se indexa "propuesta-clienteX.pdf"        → nodo tipo 'document' creado bajo Comercial/Propuestas
   - Entra una venta de $25,000               → nodo 'metric_summary' Ventas/2025 marcado stale
   - Se registra contacto con cliente ABC     → nodo 'entity_summary' Clientes marcado stale

2. El nodo afectado se marca is_stale = TRUE

3. El scheduler (cada hora por default, configurable) corre refresh_stale_summaries():
   a. Encuentra todos los nodos stale
   b. Para cada uno, regenera el summary usando LLM:
      - Reúne los summaries de todos sus hijos directos
      - Prompt: "Dado estos resúmenes de subsecciones, genera un resumen de 150 palabras
                 del estado actual de {domain}. Incluye números clave, tendencias y alertas."
      - Guarda el nuevo summary, marca is_stale = FALSE
   c. Marca el padre como is_stale = TRUE (la propagación sube un nivel)
   d. Repite hasta llegar al root

4. El root siempre refleja el estado actual de la empresa
   (con un lag máximo igual al intervalo del scheduler)
```

**Costo del refresh:** un nodo stale = 1 llamada LLM con contexto pequeño (~500 tokens entrada, ~200 salida). Para un árbol de profundidad 4 con factor de ramificación 5, un cambio en hoja = máximo 4 refreshes (uno por nivel). Muy barato.

```python
# backend/knowledge_tree.py

async def refresh_stale_summaries(model: str, max_nodes: int = 20) -> int:
    """
    Procesa hasta max_nodes nodos stale, empezando por los más profundos
    (bottom-up para que el padre ya tenga hijos frescos al ser procesado).
    Retorna el número de nodos actualizados.
    """

async def _regenerate_summary(node_id: int, model: str) -> str:
    """
    Reúne los summaries de los hijos del nodo y llama al LLM para condensar.
    Para nodos tipo 'document': usa la raíz del árbol PageIndex correspondiente.
    Para nodos tipo 'metric_summary': usa get_metric_snapshot() formateado.
    Para nodos tipo 'entity_summary': usa una query SQL sobre las tablas de entidades.
    """

def get_company_map(depth: int = 1) -> dict:
    """
    Retorna el árbol desde la raíz hasta `depth` niveles.
    depth=1: root + dominios (siempre en contexto, ~800 tokens)
    depth=2: root + dominios + subdominios (~2500 tokens)
    Usado por el agente al inicio de cada conversación.
    """

def get_node_children(node_id: int) -> list[dict]:
    """
    Retorna los hijos directos de un nodo con sus summaries.
    El agente llama esto para navegar un nivel hacia abajo.
    """

def mark_subtree_stale(node_id: int) -> None:
    """
    Marca un nodo y todos sus ancestros como stale.
    Llamado por indexer.py al indexar un nuevo documento,
    por metrics.py al ingestar un evento, por database.py al crear/actualizar entidades.
    """
```

---

## Parte 3 — Protocolo de navegación del agente

Esta es la pieza que une las dos partes anteriores. Define cómo el agente usa el meta-árbol y las herramientas de métricas para responder preguntas complejas.

### El contexto siempre cargado

En toda conversación, el `SYSTEM_PROMPT` incluye el company map (profundidad 1):

```python
# chat.py — modificación al SYSTEM_PROMPT

company_map = get_company_map(depth=1)
# ~800 tokens, siempre fresco (máx 1h de lag)

SYSTEM_PROMPT = f"""Eres CompanyBrain, el cerebro operativo de la empresa.

MAPA DE CONOCIMIENTO DE LA EMPRESA:
{format_company_map(company_map)}

Para responder, puedes:
1. Usar el contexto de documentos proporcionado (para preguntas sobre procesos, decisiones, equipo)
2. Llamar herramientas para consultar datos numéricos precisos (ventas, crecimiento, patrones)
3. Navegar el mapa para identificar qué subdominios explorar

Cita siempre la fuente: [documento — sección] para conocimiento, [métrica — período] para datos.
...
"""
```

El mapa de la empresa se ve así en el prompt (texto, no JSON):

```
CONOCIMIENTO DISPONIBLE:
• Comercial (23 clientes, $450k ARR, +38% YoY. 4 propuestas activas.)
• Proyectos (8 activos, 2 en riesgo de deadline. Capacidad al 85%.)
• Conocimiento operativo (servicios, onboarding, proveedores — 4 docs)
• Decisiones (12 en 2025. Pricing +15% Q1. Último: stack React+Vite.)
• Métricas recientes (última semana: 2 ventas $18k, 1 nuevo cliente)
```

Esto son ~150 tokens. El agente sabe qué dominios existen y puede decidir si necesita profundizar.

### Los tres modos de recuperación

**Modo A — Respuesta directa desde contexto**
Para preguntas sobre procesos, políticas, equipo: el flujo actual de `chat.py` es correcto. El router selecciona documentos relevantes, `_extract_summaries()` los carga.

Cambio: en lugar de cargar TODOS los summaries de un árbol, se carga solo hasta un nivel de profundidad configurable. Si el agente necesita más detalle, navega explícitamente.

**Modo B — Consulta de datos estructurados**
Para preguntas sobre números, métricas, tendencias: el agente llama herramientas directamente.

```python
# El agente detecta que necesita datos numéricos y llama:
result = query_metric("sale_amount", "2023-01-01", "2025-12-31", granularity="quarter")
# Recibe datos exactos, no texto aproximado
```

**Modo C — Navegación profunda del árbol**
Para preguntas complejas que cruzan dominios: el agente navega el árbol un nivel a la vez.

```python
# El agente llama la herramienta navigate_tree cuando el mapa indica
# que la respuesta está en un subdominio específico:
children = get_node_children(node_id=domain_comercial_id)
# Recibe summaries de: Ventas, Clientes, Propuestas, Tendencias
# Decide en cuál subdirección profundizar
```

### Herramienta de navegación para el agente

```python
NAVIGATION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "navigate_knowledge_tree",
            "description": "Navega el árbol de conocimiento de la empresa para encontrar información específica en un dominio o subdominio.",
            "parameters": {
                "type": "object",
                "properties": {
                    "node_id": {
                        "type": "integer",
                        "description": "ID del nodo a expandir. Usa el ID del dominio relevante del mapa de empresa."
                    },
                    "expand_documents": {
                        "type": "boolean",
                        "default": False,
                        "description": "Si true, para nodos tipo 'document' también retorna el contexto completo del documento."
                    }
                },
                "required": ["node_id"]
            }
        }
    }
]
```

---

## El workflow completo: decisión basada en 4 fuentes

**Pregunta:** *"¿Debemos lanzar una nueva línea de servicio premium en Q4 de este año?"*

### Paso 1 — Planificación (1 llamada LLM pequeña, ~1s)

El agente recibe la pregunta + el company map. Genera un plan:

```
Necesito:
  [A] Historial de ventas por trimestre, últimos 3 años → query_metric()
  [B] Crecimiento de clientes por segmento → compute_growth()
  [C] Patrón estacional de ingresos → detect_seasonal_pattern()
  [D] Tendencias de mercado → navigate_knowledge_tree(domain=Comercial/Tendencias)
  [E] Decisiones pasadas sobre lanzamientos → navigate_knowledge_tree(domain=Decisiones)
```

### Paso 2 — Recuperación paralela (~2-3s, sin LLM)

Las 5 consultas corren en paralelo (asyncio.gather):

```python
sales_history, client_growth, seasonal, _ , _ = await asyncio.gather(
    query_metric("sale_amount", "2022-01-01", "2025-04-30", granularity="quarter"),
    compute_growth("client_acquired", "2025-Q1", "2024-Q1", dimension="enterprise"),
    detect_seasonal_pattern("sale_amount", years_back=3),
    navigate_knowledge_tree(node_id=tendencias_node_id),
    navigate_knowledge_tree(node_id=decisiones_node_id),
)
```

**Resultados concretos:**

```python
sales_history = [
    {"period": "2022-Q4", "total": 280000, "count": 21},
    {"period": "2023-Q4", "total": 420000, "count": 34, "change_pct": 50},
    {"period": "2024-Q4", "total": 610000, "count": 47, "change_pct": 45.2},
    {"period": "2024-Q1", "total": 180000, ...},
    ...
]

client_growth = {
    "current": 8, "previous": 4,
    "change_pct": 100,   # enterprise duplicó en YoY
    "trend": "accelerating"
}

seasonal = {
    "peak_period": "Q4",
    "peak_multiplier": 2.9,
    "trough_period": "Q1",
    "trough_multiplier": 0.58,
    "confidence": "high",
    "years_analyzed": 3
}

trends_context = """
[análisis-mercado-2026.md — Tendencias]
Categoría AI-tools: búsquedas +65% YoY. Empresas aumentando presupuesto en herramientas
digitales. Segmento enterprise prioriza soluciones integradas sobre puntuales.

[trends-Q1-2026.md — Resumen ejecutivo]
SaaS tradicional -12% en nuevas adquisiciones. Servicios managed/consultivos +28%.
Oportunidad: empresas buscan acompañamiento, no solo software.
"""

decisions_context = """
[decisiones.md — Decisiones de pricing]
Mar-2024: Lanzamos Plan Pro para enterprise. Resultado a 90 días: +22% conversión
enterprise, sin impacto en SMB. Decisión: mantener diferenciación por segmento.
"""
```

### Paso 3 — Ensamblaje de contexto (~50ms)

Los resultados se convierten en un bloque de contexto compacto y estructurado, no en texto libre:

```
DATOS RECUPERADOS PARA ANÁLISIS:

VENTAS HISTÓRICAS (Q4 últimos 3 años):
  Q4 2022: $280k  |  Q4 2023: $420k (+50%)  |  Q4 2024: $610k (+45%)
  Tendencia Q4: crecimiento sostenido, acelerando.

CRECIMIENTO CLIENTES ENTERPRISE (YoY Q1):
  4 → 8 clientes (+100%). Tendencia: acelerando.

PATRÓN ESTACIONAL (3 años de datos):
  Q4 es 2.9x el baseline trimestral. Q1 cae a 0.58x (-42% vs promedio).
  Riesgo: cualquier lanzamiento en Q4 enfrenta cliff fuerte en enero.

TENDENCIAS DE MERCADO:
  + AI-tools: +65% en búsquedas [análisis-mercado-2026.md]
  + Servicios managed/consultivos: +28% [trends-Q1-2026.md]
  - SaaS tradicional: -12% en adquisición nueva

DECISIONES HISTÓRICAS RELEVANTES:
  Plan Pro (Mar-2024): +22% conversión enterprise. SMB no respondió. [decisiones.md]

PREGUNTA: ¿Lanzar línea premium en Q4?
```

Total de tokens en este contexto: ~600. Mucho menos que cargar todos los documentos completos.

### Paso 4 — Razonamiento final (1 llamada LLM principal, ~5-8s)

El LLM razona sobre datos concretos y citables:

```
RECOMENDACIÓN: Lanzar en Q4, orientado exclusivamente a Enterprise.

FUNDAMENTOS:
• El patrón 2.9x de Q4 maximiza la exposición del lanzamiento [métrica estacional, 3 años]
• Enterprise duplicó YoY y respondió bien a Plan Pro en 2024 [decisiones.md + métricas]
• Tendencia managed services +28% valida una propuesta premium de alto acompañamiento
  [análisis-mercado-2026.md]
• SMB nunca respondió a premium — no enfocar recursos ahí [decisiones.md]

RIESGO PRINCIPAL:
El cliff de enero (caída a 0.58x del promedio) golpea duro a nuevos servicios sin
base de clientes recurrentes. Diseñar el producto con contrato mínimo anual
para mitigar abandono post-Q4 es crítico.

ACCIÓN SUGERIDA:
• Lanzar 15 octubre, solo tier Enterprise, contrato mínimo 12 meses
• Precio: escalar desde el Plan Pro existente (+40-60%)
• Canales: referidos (70% del pipeline actual) + outreach directo top 20 prospects
• Métrica de éxito a 90 días: 3 contratos cerrados antes de diciembre
```

**Latencia total estimada:** 8-12 segundos. Comparable a una búsqueda en Google para una pregunta que normalmente requeriría 2 horas de análisis manual.

---

## Implementación: qué construir y en qué orden

Este diseño introduce dos nuevos módulos al codebase:

### `backend/metrics.py` — Capa de métricas

```
Construir:
  ingest_metric_event()   — insert en metric_events + queue recompute
  query_metric()          — select con agregación desde metric_daily
  detect_seasonal_pattern() — análisis estadístico sobre 3+ años
  compute_growth()        — delta entre dos períodos
  get_metric_snapshot()   — read rápido de metric_snapshots
  recompute_daily()       — job que procesa la cola de recomputes

Tests en tests/test_metrics.py:
  - ingestión y dedup por external_id
  - query por período y dimensión
  - detección de patrón estacional (datos mock de 3 años)
  - cómputo de crecimiento YoY y QoQ
```

### `backend/knowledge_tree.py` — Meta-árbol

```
Construir:
  init_tree()                 — crea la estructura canónica de dominios al inicializar la empresa
  get_company_map(depth)      — retorna árbol desde root hasta depth niveles
  get_node_children(node_id)  — retorna hijos directos con summaries
  mark_subtree_stale(node_id) — marca nodo + ancestros como stale
  refresh_stale_summaries()   — regenera summaries de nodos stale (bottom-up)
  _regenerate_summary()       — 1 llamada LLM para condensar summaries de hijos
  add_document_node()         — llamado por indexer.py al indexar un doc nuevo
  add_metric_summary_node()   — llamado al crear un período nuevo de métricas

Tests en tests/test_knowledge_tree.py:
  - estructura inicial correcta
  - propagación de staleness hacia arriba
  - refresh bottom-up en el orden correcto
  - get_company_map retorna el depth correcto
```

### Modificaciones a archivos existentes

**`backend/database.py`:** Agregar tablas `metric_events`, `metric_daily`, `metric_snapshots`, `knowledge_tree` en `init_db()`.

**`backend/indexer.py`:** Al final de `index_document()`, llamar a `knowledge_tree.add_document_node()` y `knowledge_tree.mark_subtree_stale()`.

**`backend/chat.py`:** Modificaciones en `process_chat()`:
1. Al inicio, cargar `get_company_map(depth=1)` e incluirlo en el system prompt.
2. Agregar `METRIC_TOOLS` y `NAVIGATION_TOOLS` a la llamada LiteLLM.
3. Si la respuesta contiene `tool_calls`, ejecutar las herramientas y hacer una segunda llamada con los resultados.

**`backend/scheduler.py`** (Fase 4 del MVP plan): agregar `refresh_stale_summaries()` al ciclo de jobs.

**`backend/main.py`:** Endpoint `POST /metrics/events` para ingestión manual.

### Variables de entorno nuevas

```env
COMPANYBRAIN_TREE_REFRESH_INTERVAL=60   # minutos entre refreshes del meta-árbol
COMPANYBRAIN_METRICS_RECOMPUTE_INTERVAL=5  # minutos entre recomputes de agregaciones
COMPANYBRAIN_MAP_DEPTH=1                # profundidad del company map siempre en contexto
```

---

## Restricciones de diseño importantes

**SQLite es suficiente para el MVP.** Con índices correctos, SQLite maneja cómodamente 10 millones de filas en `metric_events` para una empresa de 50 personas en 5 años. El límite práctico de SQLite (escrituras concurrentes) no es problema para un sistema single-tenant. Si la empresa crece a múltiples usuarios simultáneos escribiendo métricas, migrar `metric_events` a PostgreSQL es quirúrgico — las queries no cambian.

**Los summaries del árbol son aproximados, no autoritativos.** El agente siempre cita la fuente original (el documento PageIndex o la métrica consultada), nunca el summary del árbol. El árbol es para navegación, no para respuestas.

**El refresh del árbol tiene lag intencional.** No necesita ser tiempo real. Un lag de 1 hora en el summary del root es aceptable para un negocio de 5-20 personas. El agente siempre puede usar las herramientas directas (`query_metric`) para datos exactos cuando la pregunta lo requiere.

**La profundidad del árbol no debe superar 5.** Más profundidad aumenta la latencia de refresh y la complejidad de navegación sin beneficio proporcional. Si hay más granularidad, agregar dimensiones al nodo existente en lugar de crear subnodos.
