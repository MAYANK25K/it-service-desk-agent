import json
import logging

from agents.events import stream_events

logger = logging.getLogger(__name__)

SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def friendly_error(exc: Exception) -> str:
    if isinstance(exc, ConnectionError) or "connect" in type(exc).__name__.lower():
        return "I can't reach the language model. Make sure Ollama is running."
    return "Something went wrong while preparing the reply."


def event_stream(graph, payload, config):
    """Turn graph events into Server-Sent Events. Always ends with a done event."""
    try:
        for event in stream_events(graph, payload, config):
            kind = event["type"]
            if kind == "step":
                yield sse("step", {k: event[k] for k in ("node", "summary", "seconds")})
            elif kind == "token":
                yield sse("token", {"text": event["text"]})
            elif kind == "done":
                if not event["streamed"] and event["text"]:
                    yield sse("message", {"text": event["text"]})
                if event["sources"]:
                    yield sse("sources", {"sources": event["sources"]})
                if event["pending_action"]:
                    yield sse("interrupt", {"action": event["pending_action"]})
    except Exception as exc:
        logger.exception("Chat stream failed")
        yield sse("error", {"message": friendly_error(exc)})
    yield sse("done", {})