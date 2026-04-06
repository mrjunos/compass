# Compass - AI Code Audit, Static Analysis & Technical Due Diligence

**Fecha:** 2026-04-06
**Repo:** mrjunos/compass
**Version:** 0.2.0

---

## Resumen Ejecutivo

Compass es un sistema RAG (Retrieval-Augmented Generation) local y autocontenido para PyMEs (1-10 personas). Indexa documentos de la empresa y responde preguntas en lenguaje natural con citas a las fuentes, manteniendo memoria conversacional local. No usa APIs externas, ni bases de datos vectoriales, y ningún dato sale de la máquina.

**Innovación clave:** Usa PageIndex (indexación jerárquica con resúmenes) en vez de embeddings vectoriales tradicionales, lo que los desarrolladores argumentan es más preciso para documentos estructurados como SOPs y logs de decisiones.

| Categoría | Calificación | Prioridad de mejora |
|---|---|---|
| Arquitectura | **B** | Media |
| Calidad de Código | **B+** | Media |
| Testing | **B** | Media |
| Seguridad | **C+** | **ALTA** |
| Escalabilidad | **C** | **ALTA** |
| DevOps / CI/CD | **B-** | Media |
| Documentación | **B** | Baja |

**Calificación General: B-**

---

## 1. Arquitectura y Stack Tecnologico

### Stack

| Componente | Tecnologia |
|---|---|
| Lenguaje | Python 3.11+ |
| Framework | FastAPI 0.128.8 |
| LLM | Ollama (local) via LiteLLM 1.82.0 |
| Base de datos | SQLite (archivo local) |
| Indexacion | PageIndex (submodulo Git) |
| File watching | watchdog 6.0.0 |
| PDF parsing | PyMuPDF 1.26.4 + PyPDF2 3.0.1 |
| Server | Uvicorn 0.39.0 |

### Estructura del Proyecto

```
compass/
├── backend/
│   ├── main.py          # FastAPI app, rutas, lifecycle
│   ├── chat.py          # Pipeline de Q&A + parseo de respuestas LLM
│   ├── indexer.py       # Wrapper de PageIndex con deduplicacion
│   ├── database.py      # Capa de persistencia SQLite
│   └── watcher.py       # Monitor de filesystem (watchdog)
├── tests/
│   ├── test_api.py      # 26 tests de integracion
│   └── conftest.py      # Fixtures y mocking
├── demo/techflow/       # Dataset de ejemplo (5 docs)
├── .github/workflows/ci.yml
├── requirements.txt
└── README.md
```

### Patron Arquitectonico

**Monolito con separacion de responsabilidades.** Cada archivo backend maneja un dominio claro:

```
HTTP (FastAPI) → main.py
                  ├→ chat.py      (logica de Q&A)
                  ├→ indexer.py   (indexacion de documentos)
                  ├→ database.py  (persistencia)
                  └→ watcher.py   (monitoreo de archivos)
                        ↓
                  Ollama + PageIndex + SQLite
```

**Decisiones de diseno notables:**
- Sin base de datos vectorial - PageIndex provee estructura jerarquica
- Local-first - todos los datos y la inferencia LLM se quedan en la maquina
- Prompts en espanol - orientado a LATAM
- Todo el contexto de documentos se pasa al LLM en cada query (sin filtrado semantico)

---

## 2. Analisis de API

### Endpoints

| Metodo | Ruta | Descripcion |
|---|---|---|
| `GET` | `/health` | Health check (status, modelo, docs indexados) |
| `POST` | `/chat` | Q&A principal (pregunta + session_id) |
| `POST` | `/upload` | Ingesta de documentos (multipart) |
| `GET` | `/documents` | Lista documentos indexados |

### Flujo del Chat

```
1. Guardar mensaje del usuario en SQLite
2. Extraer estructuras de TODOS los documentos indexados
3. Construir contexto con resúmenes recursivos
4. Obtener historial de sesion (ultimos 6 mensajes)
5. Llamar LLM: [system_prompt + contexto, ...historial, pregunta]
6. Parsear respuesta: separar answer de "💡 SUGERENCIA:"
7. Guardar respuesta del asistente
8. Retornar {answer, sources, suggestion, session_id}
```

---

## 3. Analisis de Seguridad

### Hallazgos Criticos

#### 3.1 CORS Abierto de Par en Par
**Severidad: CRITICA**
```python
# backend/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # Permite CUALQUIER origen
    allow_methods=["*"],      # Permite CUALQUIER metodo
    allow_headers=["*"],      # Permite CUALQUIER header
)
```
**Riesgo:** Vulnerable a ataques cross-origin y CSRF.
**Recomendacion:** Restringir a origenes especificos (`http://localhost:3000` para desarrollo).

#### 3.2 Upload de Archivos sin Sanitizacion de Nombre
**Severidad: ALTA**
```python
# backend/main.py
ext = Path(file.filename).suffix.lower()
dest = Path(docs_path) / file.filename  # Path traversal posible!
```
**Riesgos:**
- Sin sanitizacion de nombre de archivo (path traversal: `../../etc/passwd`)
- Sin limite de tamano de archivo
- Sin validacion de contenido (magic bytes)
- Solo valida extension, no contenido real

**Recomendacion:** Usar `Path(file.filename).name`, agregar limite de tamano, validar magic bytes.

#### 3.3 Sin Autenticacion ni Autorizacion
**Severidad: ALTA**
- Ningun endpoint requiere autenticacion
- Sin rate limiting (vulnerable a brute force/DoS)
- Session IDs no validados (pueden ser arbitrarios)

### Hallazgos Positivos

- **SQL Injection: SEGURO** - Usa queries parametrizadas con `?` placeholders en todos los casos
- **Secrets: SEGURO** - Sin credenciales hardcodeadas, `.env` en `.gitignore`
- **Dependencias: OK** - Todas pinneadas a versiones exactas, sin vulnerabilidades conocidas detectadas

### Hallazgos Menores

| Hallazgo | Severidad | Detalle |
|---|---|---|
| Sin validacion de env vars al inicio | Media | App arranca sin `OLLAMA_API_BASE` |
| Error messages exponen info interna | Baja | Stack traces podrian filtrar paths |
| Ollama sin auth dentro de la app | Baja | Accesible solo localmente |

---

## 4. Calidad de Codigo

### 4.1 Dependencias

```
fastapi==0.128.8        pymupdf==1.26.4
uvicorn==0.39.0         watchdog==6.0.0
python-multipart==0.0.20  PyPDF2==3.0.1
python-dotenv==1.1.0    pyyaml==6.0.2
litellm==1.82.0         pytest==8.3.5
pytest-asyncio==0.24.0  httpx==0.27.2
```

- Todas pinneadas a versiones exactas
- Sin lock file (no `poetry.lock` ni `pip-compile` output)
- 12 dependencias totales (10 runtime + 2 testing) - razonable

### 4.2 Linting y Formateo

**No existe configuracion de linting.**

Archivos faltantes:
- `.pylintrc` / `ruff.toml` / `.flake8`
- `mypy.ini` / `pyproject.toml`
- `.pre-commit-config.yaml`

**Recomendacion:** Agregar `ruff` para linting + `mypy` para type checking.

### 4.3 Type Safety

| Archivo | Funciones con return types | Cobertura |
|---|---|---|
| chat.py | 3/4 | 75% |
| indexer.py | 5/7 | 71% |
| database.py | 2/5 | 40% |
| watcher.py | 1/3 | 33% |
| main.py | 1/6 | **16%** |

**Problema principal:** `main.py` (el archivo mas expuesto) tiene la peor cobertura de tipos.

### 4.4 Duplicacion de Codigo

**Extensiones de archivo hardcodeadas en 4 lugares:**

```python
# indexer.py
SUPPORTED_EXTENSIONS = {".pdf", ".md", ".markdown", ".txt"}

# watcher.py
SUPPORTED_EXTENSIONS = {".pdf", ".md", ".markdown", ".txt"}

# main.py (linea 44-45)
if f.suffix.lower() in {".pdf", ".md", ".markdown", ".txt"}:

# main.py (linea 105)
if ext not in {".pdf", ".md", ".markdown", ".txt"}:
```

**Riesgo:** Si se agrega soporte para `.docx`, hay que actualizar 4 lugares.

### 4.5 Error Handling

**Problemas encontrados:**

```python
# chat.py - except silencioso sin logging
except Exception:
    return ""  # Falla silenciosa

# main.py - file I/O sin try-catch
with open(dest, "wb") as f:
    shutil.copyfileobj(file.file, f)  # Sin manejo de disco lleno/permisos

# watcher thread sin supervision
# Si el thread muere, nadie lo reinicia
```

### 4.6 Codigo Muerto

```python
# database.py - funcion nunca llamada en el codebase
def mark_indexed(message_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE messages SET indexed = TRUE WHERE id = ?", (message_id,))
```

### 4.7 TODO/FIXME/HACK

No se encontraron comentarios de deuda tecnica. El codigo esta limpio en ese aspecto.

---

## 5. Testing

### Cobertura

- **26 tests** en `tests/test_api.py`
- **Framework:** pytest + pytest-asyncio + httpx
- **Estrategia:** Integracion con todas las dependencias mockeadas

| Endpoint | Tests | Cobertura |
|---|---|---|
| `GET /health` | 4 | Happy path + campos de respuesta |
| `POST /chat` | 7 | Errores + formato + sesiones |
| `POST /upload` | 5 | Validacion + extensiones + formato |
| `GET /documents` | 4 | Estado vacio + lista + campos |

### Lo Bueno

- Sin llamadas reales a Ollama en tests
- Sin I/O a disco en tests
- Sin archivo SQLite real en tests
- Mocking comprehensivo con `unittest.mock`
- CI/CD ejecuta todos los tests en cada push/PR

### Gaps de Testing

| Gap | Riesgo |
|---|---|
| Sin tests de operaciones de base de datos reales | Medio |
| Sin tests de concurrencia | Medio |
| Sin tests de archivos grandes | Bajo |
| Sin tests de JSON malformado | Bajo |
| Sin medicion de coverage (`pytest-cov`) | Medio |
| Sin tests de error de PageIndex | Alto |
| Sin tests de integridad de datos | Medio |

---

## 6. Escalabilidad

### Problemas Criticos

#### 6.1 Carga de Contexto O(n) por Request
```python
# chat.py - Itera TODOS los documentos en cada pregunta
for doc_id, doc in indexer.documents.items():
    structure_json = indexer.get_structure(doc_id)  # I/O repetido
    summaries = _extract_summaries(structure_json)
```
Con 50+ documentos, esto genera overhead significativo. **Sin caching.**

#### 6.2 Contexto LLM Ilimitado
Todos los resumenes de todos los documentos se incluyen en cada prompt. El uso de tokens escala linealmente con la cantidad de documentos.

#### 6.3 Sin Indice en Base de Datos
```sql
-- Tabla messages sin indice en session_id
-- Cada query hace full table scan
SELECT role, content FROM messages WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?
```

#### 6.4 Reversa de Historial en Python
```python
return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
# Deberia usar ORDER BY timestamp ASC en SQL
```

#### 6.5 I/O Bloqueante en Contexto Async
```python
# main.py - operaciones bloqueantes en handlers async
with open(dest, "wb") as f:
    shutil.copyfileobj(file.file, f)  # BLOQUEANTE
doc_id = indexer.index_document(str(dest))  # BLOQUEANTE
```

#### 6.6 Otros Issues
- Sin rate limiting
- Sin timeout en llamadas al LLM
- Sin paginacion en `/documents`
- Sin connection pooling (menor para SQLite)
- Crecimiento ilimitado de la base de datos (sin politica de retencion)

---

## 7. DevOps y CI/CD

### Pipeline Actual (GitHub Actions)

```yaml
# .github/workflows/ci.yml
- Trigger: push a main, PR a main
- Runner: Ubuntu latest
- Steps: checkout con submodulos → Python 3.11 → pip install → pytest
```

### Lo que Falta

| Item | Estado | Impacto |
|---|---|---|
| Docker / docker-compose | No existe | Despliegue manual |
| Pre-commit hooks | No existe | Sin validacion local |
| Linting en CI | No existe | Quality drift |
| Type checking en CI | No existe | Bugs de tipos |
| Coverage en CI | No existe | Sin metricas |
| Deployment pipeline | No existe | Sin CD |
| Health monitoring | No existe | Sin observabilidad |
| Logging estructurado | Basico | Dificil troubleshooting en prod |

### Git Health

- Commits con mensajes claros y descriptivos
- Branch strategy simple (main + feature branches)
- Sin PR templates ni issue templates en `.github/`

---

## 8. Documentacion

### Lo Bueno

- **README.md excelente** (219 lineas): problema claro, stack justificado, quickstart completo, API documentada con ejemplos cURL, roadmap incluido
- **`.env.example`** con todas las variables necesarias
- **Demo dataset** incluido para pruebas rapidas

### Lo que Falta

- Sin especificacion OpenAPI/Swagger formal
- Sin guia de contribucion (CONTRIBUTING.md)
- Sin docstrings en la mayoria de funciones publicas
- Sin guia de deployment a produccion
- Sin documentacion de arquitectura (diagramas de secuencia)
- Sin ADRs (Architecture Decision Records)

---

## 9. Potencial del Proyecto

### Fortalezas

1. **Propuesta de valor clara** - RAG local para PyMEs, sin dependencias cloud
2. **Innovacion tecnica** - PageIndex vs embeddings vectoriales es diferenciador real
3. **Privacy-first** - Ningun dato sale de la maquina
4. **Stack simple** - Pocas dependencias, facil de entender y mantener
5. **Demo incluido** - Reduce friccion para nuevos usuarios
6. **Testing solido** - 26 tests con buena cobertura de happy paths

### Oportunidades

1. **UI web** (en roadmap) - Ampliaria adoption masivamente
2. **Soporte multi-tenant** - Escalaria a equipos mas grandes
3. **Mas formatos** (.docx, .xlsx) - Cubre mas casos de uso
4. **Plugin ecosystem** - Integraciones con Slack, Notion, etc.
5. **Retrieval selectivo** - No enviar TODO el contexto al LLM, mejoraria costo y velocidad

### Riesgos

1. **PageIndex como submodulo externo** - Dependencia critica en proyecto de terceros
2. **Sin auth** - Inutilizable en redes compartidas sin modificacion
3. **Escalabilidad limitada** - Diseno actual no soporta >100 documentos eficientemente
4. **Single point of failure** - Ollama down = app inutil, sin fallback

---

## 10. Plan de Accion Recomendado

### Critico (Hacer ya)

1. Restringir CORS a origenes especificos
2. Sanitizar nombres de archivo en uploads (`Path(filename).name`)
3. Agregar limite de tamano a uploads
4. Agregar indice en `messages(session_id)` en SQLite
5. Agregar timeout a llamadas LLM

### Prioridad Alta

6. Implementar cache en memoria para estructuras de documentos
7. Agregar autenticacion basica (API key al menos)
8. Reemplazar `except Exception` con excepciones especificas + logging
9. Agregar rate limiting
10. Centralizar `SUPPORTED_EXTENSIONS` en un solo lugar

### Prioridad Media

11. Agregar `ruff` + `mypy` al CI
12. Agregar `pytest-cov` para medir cobertura
13. Agregar Dockerfile + docker-compose
14. Agregar type hints completos a `main.py`
15. Eliminar codigo muerto (`mark_indexed`)

### Prioridad Baja

16. Agregar pre-commit hooks
17. Crear CONTRIBUTING.md
18. Implementar retrieval selectivo (no enviar todo el contexto)
19. Agregar paginacion a `/documents`
20. Considerar `aiosqlite` para operaciones de DB no bloqueantes

---

*Reporte generado por AI Code Audit - Claude*
*Este reporte refleja el estado del repositorio al momento del analisis y debe ser revisado periodicamente.*
