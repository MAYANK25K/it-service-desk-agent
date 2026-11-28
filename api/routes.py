import uuid

from fastapi import APIRouter, HTTPException, Request

from agents.config import CHAT_MODEL
from agents.persistence import list_threads

router = APIRouter()

ROLES = {"human": "user", "ai": "assistant"}


def thread_config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "model": CHAT_MODEL}


@router.get("/threads")
def get_threads(request: Request) -> dict:
    state = request.app.state
    return {"threads": list_threads(state.checkpointer, state.graph)}


@router.post("/threads", status_code=201)
def create_thread() -> dict:
    return {"thread_id": str(uuid.uuid4())}


@router.get("/threads/{thread_id}/messages")
def get_messages(thread_id: str, request: Request) -> dict:
    snapshot = request.app.state.graph.get_state(thread_config(thread_id))
    messages = snapshot.values.get("messages", [])
    if not messages:
        raise HTTPException(status_code=404, detail="Thread not found")

    waiting = "tool_executor" in snapshot.next
    return {
        "thread_id": thread_id,
        "messages": [
            {"role": ROLES[m.type], "content": str(m.content)}
            for m in messages
            if m.type in ROLES
        ],
        "awaiting_approval": waiting,
        "pending_action": snapshot.values.get("pending_action") if waiting else None,
    }