import time


def describe_step(node: str, changes: dict) -> str:
    if node == "supervisor":
        return f"intent = {changes.get('intent', '?')}"
    if node == "rag_agent":
        return f"retrieved {len(changes.get('retrieved_docs') or [])} chunks and answered"
    if node == "direct_responder":
        return "replied"
    if node == "action_planner":
        action = changes.get("pending_action")
        return f"prepared {action['tool_name']}" if action else "needs more details"
    if node == "tool_executor":
        return "finished"
    return "done"


def collect_sources(docs: list[dict]) -> list[dict]:
    seen = set()
    sources = []
    for doc in docs:
        key = (doc.get("source"), doc.get("section_ref"))
        if key in seen:
            continue
        seen.add(key)
        sources.append(
            {
                "source": doc.get("source"),
                "doc_id": doc.get("doc_id"),
                "section_ref": doc.get("section_ref"),
                "section": doc.get("section"),
            }
        )
    return sources


def stream_events(graph, payload, config):
    """Run the graph and yield plain-dict events: step, token, then one done.

    Used by both the terminal chat and the web API."""
    started = time.perf_counter()
    streamed = False
    sources: list[dict] = []

    for mode, data in graph.stream(payload, config, stream_mode=["updates", "messages"]):
        if mode == "messages":
            chunk, metadata = data
            text = str(chunk.content)
            if "answer" in (metadata.get("tags") or []) and text:
                streamed = True
                yield {"type": "token", "text": text}
            continue

        for node, changes in data.items():
            if node.startswith("__") or not isinstance(changes, dict):
                continue
            if node == "rag_agent":
                sources = collect_sources(changes.get("retrieved_docs") or [])
            now = time.perf_counter()
            yield {
                "type": "step",
                "node": node,
                "summary": describe_step(node, changes),
                "seconds": round(now - started, 1),
            }
            started = now

    snapshot = graph.get_state(config)
    messages = snapshot.values.get("messages", [])
    waiting = "tool_executor" in snapshot.next
    yield {
        "type": "done",
        "text": str(messages[-1].content) if messages else "",
        "streamed": streamed,
        "sources": sources,
        "pending_action": snapshot.values.get("pending_action") if waiting else None,
    }