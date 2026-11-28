import uuid
from typing import Annotated, Any, Literal, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, StringConstraints

from agents.config import CHAT_MODEL
from agents.decisions import build_edited_action, describe_error
from agents.events import stream_events
from agents.persistence import list_threads
from api.sse import SSE_HEADERS, event_stream

router = APIRouter()


class ChatRequest(BaseModel):
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]


class DecisionRequest(BaseModel):
    decision: Literal["approve", "reject", "edit"]
    args: Optional[dict[str, Any]] = None


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


@router.post("/threads/{thread_id}/chat")
def chat(thread_id: str, body: ChatRequest, request: Request) -> StreamingResponse:
    graph = request.app.state.graph
    config = thread_config(thread_id)
    if "tool_executor" in graph.get_state(config).next:
        raise HTTPException(
            status_code=409,
            detail="This conversation is waiting for an approval decision.",
        )
    payload = {"messages": [HumanMessage(content=body.message)]}
    return StreamingResponse(
        event_stream(graph, payload, config),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@router.post("/threads/{thread_id}/decision")
def decide(thread_id: str, body: DecisionRequest, request: Request) -> dict:
    graph = request.app.state.graph
    config = thread_config(thread_id)

    with request.app.state.decision_lock:
        snapshot = graph.get_state(config)
        if "tool_executor" not in snapshot.next:
            raise HTTPException(
                status_code=409,
                detail="No action is waiting for approval in this conversation.",
            )

        action = snapshot.values["pending_action"]
        if body.decision == "reject":
            status = "rejected"
        elif body.decision == "approve":
            status = "approved"
        else:
            if not body.args:
                raise HTTPException(status_code=422, detail="Provide the fields to change in args.")
            try:
                action = build_edited_action(action, body.args)
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=describe_error(exc))
            status = "edited"

        graph.update_state(
            config,
            {"pending_action": action, "approval_status": status},
            as_node="action_planner",
        )

        steps, final = [], {}
        for event in stream_events(graph, None, config):
            if event["type"] == "step":
                steps.append({k: event[k] for k in ("node", "summary", "seconds")})
            elif event["type"] == "done":
                final = event

    return {"decision": body.decision, "status": status, "message": final["text"], "steps": steps}