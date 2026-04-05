import logging
import litellm

from .database import save_message, get_session_messages
from .indexer import CompassIndexer

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Eres Compass, el cerebro operativo de la empresa.
Responde usando exclusivamente el contexto de los documentos de la empresa proporcionados.
Cita siempre el documento y la sección de donde viene la información (ej: [servicios.md — Paquetes]).
Si no encuentras la respuesta en los documentos, dilo claramente y sugiere qué documento podría tenerla."""

SUGGESTION_PROMPT = """Eres un asistente que ayuda a mejorar la base de conocimiento de una empresa.
Dado el contexto de una pregunta y su respuesta, sugiere en UNA oración qué información adicional
debería documentarse o qué gap de conocimiento existe.
Si no hay una sugerencia útil, responde exactamente: null"""


async def process_chat(
    question: str,
    session_id: str,
    indexer: CompassIndexer,
    model: str,
) -> dict:
    # 1. Save user message
    save_message(session_id, "user", question)

    # 2. Build context from PageIndex summaries (already generated during indexing)
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
    for msg in history[:-1]:  # exclude the message we just saved
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": question})

    # 5. LLM response
    response = await litellm.acompletion(model=model, messages=messages)
    answer = response.choices[0].message.content

    # 6. Save assistant response
    save_message(session_id, "assistant", answer)

    # 7. Proactive suggestion
    suggestion = await _get_suggestion(question, answer, model) if context_parts else None

    return {
        "answer": answer,
        "sources": sources,
        "suggestion": suggestion,
        "session_id": session_id,
    }


def _extract_summaries(structure_json: str) -> str:
    """Recursively extract all node summaries from PageIndex structure JSON."""
    import json

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


async def _get_suggestion(question: str, answer: str, model: str) -> str | None:
    try:
        response = await litellm.acompletion(
            model=model,
            messages=[
                {"role": "system", "content": SUGGESTION_PROMPT},
                {"role": "user", "content": f"Pregunta: {question}\n\nRespuesta: {answer}"},
            ],
            max_tokens=120,
        )
        result = response.choices[0].message.content.strip()
        return None if result.lower() == "null" else result
    except Exception as e:
        logger.warning(f"Suggestion failed: {e}")
        return None
