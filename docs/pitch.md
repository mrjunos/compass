# CompanyBrain — Pitch

---

## Una línea

**CompanyBrain es el cerebro operativo de tu empresa: sabe todo, recuerda todo, actúa cuando lo necesitas.**

---

## El problema

Cada empresa pierde inteligencia todos los días.

Una decisión tomada en una reunión que no quedó documentada. Un cliente cuyo historial vive en el email de alguien que ya se fue. Un patrón de ventas que nadie analizó porque toma tres días armar el Excel. Una contratación que repite el mismo error de hace dos años porque nadie recuerda qué pasó.

El conocimiento operativo de una empresa — sus decisiones, sus clientes, sus procesos, sus patrones — está fragmentado en 12 herramientas distintas, en la cabeza de su gente, y en archivos que nadie encuentra.

El resultado: los dueños de empresa toman decisiones con información incompleta, todos los días.

---

## La oportunidad

Las empresas que van a ganar en la próxima década no son las que adoptaron IA — son las que nacieron con IA como capa operativa desde el primer día.

Hoy existe una ventana: la mayoría de las PyMEs de LATAM no tienen un sistema de gestión del conocimiento. No tienen CRM integrado. No tienen análisis de datos. Tienen WhatsApp, Google Drive y la memoria de su equipo.

Eso no es una debilidad — es la oportunidad. Podemos llegar antes que Salesforce, antes que Microsoft, antes que cualquier solución enterprise que cuesta $50k al año y tarda seis meses en implementar.

---

## La solución

**CompanyBrain** es el primer sistema AI-first diseñado desde cero para PyMEs de LATAM.

No es un chatbot. No es un dashboard. Es un cerebro.

Conecta todos los documentos, conversaciones, métricas y decisiones de la empresa en un único punto de inteligencia. Cualquier persona del equipo puede preguntarle cualquier cosa en lenguaje natural — por WhatsApp, desde el teléfono, sin aprender ninguna herramienta nueva — y recibe una respuesta precisa con la fuente exacta de donde viene la información.

Pero más importante: **actúa**. Cuando detecta que un cliente no ha tenido contacto en 30 días, lo dice. Cuando ve que un proyecto va a incumplir un deadline, lo avisa. Cuando el dueño dice "redactá un email de seguimiento para ese cliente", lo propone — y el dueño aprueba con un clic.

---

## Cómo funciona (la diferencia técnica)

La mayoría de los sistemas RAG usan búsqueda vectorial: fragmentan documentos en pedazos y buscan los más parecidos a la pregunta. Funciona para búsqueda, no para razonamiento.

CompanyBrain usa **árboles de conocimiento jerárquicos**: cada documento se indexa como un árbol de resúmenes estructurados. El sistema construye un árbol maestro de toda la empresa — dominios, subdominios, períodos de tiempo. El agente navega ese árbol como lo haría un analista experto: empieza en lo general, baja a lo específico, consulta los datos exactos cuando los necesita.

El resultado: puede responder *"¿debemos lanzar un nuevo servicio premium en Q4?"* analizando en paralelo tres años de historial de ventas, el crecimiento por segmento, el patrón estacional, y las decisiones históricas relacionadas — en menos de 15 segundos, con cada afirmación citada en su fuente.

Todo corre local. Los datos de la empresa nunca salen de la empresa.

---

## El MVP

**Lo que existe hoy (Compass):**
- Indexación de documentos con árboles jerárquicos de resúmenes
- Q&A en lenguaje natural con citas de fuente
- Detección proactiva de gaps de conocimiento
- Historial de conversaciones por sesión
- API completa con auth y rate limiting
- 58 tests, arquitectura limpia

**Lo que estamos construyendo (CompanyBrain):**
- Memoria estructurada: clientes, proyectos, personas y decisiones como entidades reales (no solo texto)
- Extracción automática de entidades al indexar documentos
- Conector WhatsApp — preguntale a tu empresa desde el teléfono, sin instalar nada
- Gmail + Google Calendar — lee, redacta, agenda
- Acciones agénticas con aprobación humana en el chat
- Alertas proactivas y resumen diario
- Capa de métricas para razonamiento sobre datos numéricos

---

## El modelo de negocio

**Dos motores, un flywheel:**

**Motor 1 — SaaS:** $200–500/mes por empresa. La empresa conecta sus herramientas, CompanyBrain aprende su operación. Sin implementación costosa, sin equipo de IT.

**Motor 2 — Transformación:** Entramos a una empresa que no es AI-first y la transformamos. Auditamos sus procesos, instalamos CompanyBrain, integramos sus herramientas, capacitamos al equipo. $5k–20k por proyecto + retainer mensual.

El motor 2 financia el motor 1 en etapa temprana. Cada empresa transformada es un caso de estudio, una referencia, y un cliente SaaS recurrente. La consultoría crea el mercado que el producto captura.

---

## El mercado

**8 millones de PyMEs en Colombia.** Solo en el segmento de 5-50 empleados con herramientas digitales básicas: más de 400,000 empresas. Multiplica por LATAM.

Ninguna solución actual las atiende bien:
- **Notion AI / Confluence:** orientado a documentación, no a operación, no a acción
- **Microsoft Copilot:** requiere M365, demasiado caro, demasiado genérico
- **ChatGPT Enterprise:** sin memoria de empresa, sin integraciones, sin acciones
- **Soluciones verticales (Harvey, Ironclad):** un caso de uso por industria

CompanyBrain es horizontal, operativo, en español, y diseñado para el contexto LATAM desde el primer día.

---

## La visión

En cinco años, toda empresa nueva nace AI-first. Tiene un cerebro operativo desde el día uno.

Hoy, el camino más corto para llegar ahí pasa por las PyMEs de LATAM: mercado subatendido, adopción de WhatsApp del 95%, dueños que toman todas las decisiones y no tienen tiempo de buscar información.

CompanyBrain no es una herramienta más en el stack. Es el sistema operativo de la empresa inteligente.

---

*Construido sobre Compass — base de conocimiento local-first con PageIndex, FastAPI y React.*
*Repositorio: github.com/mrjunos/compass*
