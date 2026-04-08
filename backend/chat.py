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


async def _route_documents(
    question: str,
    indexer: CompassIndexer,
    model: str,
    history: list,
) -> list[str]:
    """Select which documents are relevant to the question using a lightweight LLM call."""
    doc_manifest = []
    for doc_id, doc in indexer.documents.items():
        doc_name = doc.get("doc_name", doc_id)
        try:
            structure_json = indexer.get_structure(doc_id)
            first_summary = _extract_first_summary(structure_json)
            doc_manifest.append(f"- {doc_name}: {first_summary}")
        except Exception:
            doc_manifest.append(f"- {doc_name}: (no summary available)")

    if not doc_manifest:
        return []

    # Include recent conversation context so the router understands follow-ups
    conv_context = ""
    if history:
        recent = history[-4:]  # last 2 exchanges
        conv_lines = [f"{m['role']}: {m['content'][:200]}" for m in recent]
        conv_context = f"\n\nRecent conversation:\n" + "\n".join(conv_lines)

    routing_prompt = f"""Given these available documents:
{chr(10).join(doc_manifest)}
{conv_context}

Which documents are relevant to answer this question: "{question}"

Reply with ONLY the document names, one per line. Pick 1-3 most relevant documents. If the question is a follow-up to the conversation, pick documents relevant to the ongoing topic."""

    try:
        response = await litellm.acompletion(
            model=model,
            messages=[{"role": "user", "content": routing_prompt}],
            timeout=15,
        )
        raw = response.choices[0].message.content.strip()

        # Match returned names against actual doc names
        all_names = {doc.get("doc_name", did): did for did, doc in indexer.documents.items()}
        selected = []
        for line in raw.splitlines():
            name = line.strip().lstrip("- ").strip()
            if name in all_names:
                selected.append(all_names[name])
            else:
                # Fuzzy: check if any doc name is contained in the line
                for doc_name, did in all_names.items():
                    if doc_name.lower() in line.lower() and did not in selected:
                        selected.append(did)

        if selected:
            logger.info(f"Router selected {len(selected)} docs: {[indexer.documents[d].get('doc_name', d) for d in selected]}")
            return selected
    except Exception as e:
        logger.warning(f"Document routing failed, falling back to all docs: {e}")

    # Fallback: return all
    return list(indexer.documents.keys())


def _extract_first_summary(structure_json: str) -> str:
    """Extract just the first/top-level summary for routing (lightweight)."""
    try:
        tree = json.loads(structure_json)
        nodes = tree if isinstance(tree, list) else [tree]
        if nodes and nodes[0].get("summary"):
            summary = nodes[0]["summary"]
            return summary[:150] + "..." if len(summary) > 150 else summary
    except Exception:
        pass
    return "(no summary)"


async def process_chat(
    question: str,
    session_id: str,
    indexer: CompassIndexer,
    model: str,
) -> dict:
    # 1. Save user message
    save_message(session_id, "user", question)

    # 2. Get recent chat history
    history = get_session_messages(session_id, limit=10)

    # 3. Route: select relevant documents (lightweight LLM call)
    relevant_doc_ids = await _route_documents(question, indexer, model, history[:-1])

    # 4. Build context from only the relevant documents
    sources = []
    context_parts = []

    for doc_id in relevant_doc_ids:
        doc = indexer.documents.get(doc_id)
        if not doc:
            continue
        try:
            doc_name = doc.get("doc_name", doc_id)
            structure_json = indexer.get_structure(doc_id)
            summaries = _extract_summaries(structure_json)
            if summaries:
                sources.append({"doc_name": doc_name, "doc_id": doc_id})
                context_parts.append(f"[{doc_name}]\n{summaries}")
        except Exception as e:
            logger.warning(f"Context build failed for {doc_id}: {e}")

    # 5. Build messages
    context = "\n\n---\n\n".join(context_parts) if context_parts else "No se encontró información relevante en los documentos."

    messages = [
        {"role": "system", "content": f"{SYSTEM_PROMPT}\n\nCONTEXTO:\n{context}"}
    ]
    for msg in history[:-1]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": question})

    # 5. Single LLM call — answer + optional suggestion embedded
    response = await litellm.acompletion(model=model, messages=messages, timeout=60)
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
    except Exception as e:
        logger.warning(f"Failed to extract summaries from structure JSON: {e}")
        return ""
