import json
import logging
import litellm

from .database import save_message, get_session_messages
from .indexer import CompassIndexer

logger = logging.getLogger(__name__)

SUGGESTION_MARKER = "💡 SUGERENCIA:"

SYSTEM_PROMPT = f"""Eres Compass, el cerebro operativo de la empresa.
Responde usando exclusivamente el contexto de los documentos de la empresa proporcionados.
Cita siempre el documento y la sección de donde viene la información (ej: [servicios.md — Sección]).
Si no encuentras la respuesta en los documentos, dilo claramente.

Al final de tu respuesta, si identificas un gap de conocimiento — algo que debería estar documentado \
pero no está — agrégalo en esta línea exacta:
{SUGGESTION_MARKER} <una sola oración sobre qué documentar>

Si no hay gap relevante, no incluyas esa línea."""


async def process_chat(
    question: str,
    session_id: str,
    indexer: CompassIndexer,
    model: str,
) -> dict:
    # 1. Save user message
    save_message(session_id, "user", question)

    # 2. Build context from PageIndex summaries
    sources = []
    context_parts = []

    for doc_id, doc in indexer.documents.items():
        try:
            doc_name = doc.get("doc_name", doc_id)
            structure_json = indexer.get_structure(doc_id)
            summaries = _extract_summaries(structure_json)
            if summaries:
                sources.append({"doc_name": doc_name, "doc_id": doc_id})
                context_parts.append(f"[{doc_name}]\n{summaries}")
        except Exception as e:
            logger.warning(f"Context build failed for {doc_id}: {e}")

    # 3. Get recent chat history
    history = get_session_messages(session_id, limit=6)

    # 4. Build messages
    context = "\n\n---\n\n".join(context_parts) if context_parts else "No se encontró información relevante en los documentos."

    messages = [
        {"role": "system", "content": f"{SYSTEM_PROMPT}\n\nCONTEXTO:\n{context}"}
    ]
    for msg in history[:-1]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": question})

    # 5. Single LLM call — answer + optional suggestion embedded
    response = await litellm.acompletion(model=model, messages=messages)
    raw = response.choices[0].message.content

    # 6. Parse answer and suggestion from the same response
    answer, suggestion = _parse_response(raw)

    # 7. Save assistant response (clean answer only)
    save_message(session_id, "assistant", answer)

    return {
        "answer": answer,
        "sources": sources,
        "suggestion": suggestion,
        "session_id": session_id,
    }


def _parse_response(raw: str) -> tuple[str, str | None]:
    """Split the LLM response into answer and optional suggestion."""
    if SUGGESTION_MARKER in raw:
        parts = raw.split(SUGGESTION_MARKER, 1)
        answer = parts[0].strip()
        suggestion = parts[1].strip() if len(parts) > 1 else None
        return answer, suggestion or None
    return raw.strip(), None


def _extract_summaries(structure_json: str) -> str:
    """Recursively extract all node summaries from PageIndex structure JSON."""
    def _collect(nodes: list, parts: list):
        for node in nodes:
            if node.get("summary"):
                parts.append(node["summary"])
            if node.get("nodes"):
                _collect(node["nodes"], parts)

    try:
        tree = json.loads(structure_json)
        parts = []
        _collect(tree if isinstance(tree, list) else [tree], parts)
        return "\n\n".join(parts)
    except Exception:
        return ""
