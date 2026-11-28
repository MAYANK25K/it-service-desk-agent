import json
import logging
import tempfile
import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from agents import graph as graph_module
from agents.persistence import open_checkpointer
from api.main import create_app

REPLY = "Restart the router then retry the VPN login"
DOCS = [
    {"source": "vpn_troubleshooting.md", "doc_id": "KB-VPN-014", "section_ref": "3", "section": "3. Error 809"},
    {"source": "vpn_troubleshooting.md", "doc_id": "KB-VPN-014", "section_ref": "3", "section": "3. Error 809"},
]
PROPOSAL = {
    "tool_name": "create_ticket",
    "args": {"title": "VPN outage", "description": "Users cannot connect to the VPN", "priority": "P2"},
    "risk": "low",
    "impact_summary": "Creates a ticket.",
}


def fake_supervisor(state):
    text = state["messages"][-1].content
    if "ticket" in text:
        return {"intent": "action"}
    if "hello" in text:
        return {"intent": "general"}
    return {"intent": "rag"}


def fake_rag(state):
    if "boom" in state["messages"][-1].content:
        raise ConnectionError("Failed to connect to Ollama")
    model = GenericFakeChatModel(messages=iter([AIMessage(content=REPLY)]), tags=["answer"])
    answer = model.invoke("answer")
    return {"messages": [AIMessage(content=str(answer.content))], "retrieved_docs": DOCS}


def fake_responder(state):
    return {"messages": [AIMessage(content="Hi there")]}


def fake_planner(state):
    return {"messages": [AIMessage(content="prepared")], "pending_action": PROPOSAL, "approval_status": None}


def make_client():
    graph_module.supervisor_node = fake_supervisor
    graph_module.rag_agent_node = fake_rag
    graph_module.direct_responder_node = fake_responder
    graph_module.action_planner_node = fake_planner
    checkpointer = open_checkpointer(Path(tempfile.mkdtemp()) / "sse_check.sqlite")
    graph = graph_module.build_graph(checkpointer)
    return TestClient(create_app(checkpointer, graph))


def parse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.split("\n"))
        events.append((lines["event"], json.loads(lines["data"])))
    return events


def say(client, thread, message):
    return client.post(f"/api/threads/{thread}/chat", json={"message": message})


def case_streamed_answer():
    thread = str(uuid.uuid4())
    with make_client() as client:
        response = say(client, thread, "vpn problem")
    events = parse(response.text)
    kinds = [kind for kind, _ in events]
    tokens = "".join(data["text"] for kind, data in events if kind == "token")
    sources = next(data["sources"] for kind, data in events if kind == "sources")
    return (
        response.headers["content-type"].startswith("text/event-stream")
        and kinds[0] == "step"
        and kinds[-1] == "done"
        and "message" not in kinds
        and tokens == REPLY
        and [(s["source"], s["section_ref"]) for s in sources] == [("vpn_troubleshooting.md", "3")]
    )


def case_plain_reply_uses_message_event():
    with make_client() as client:
        events = parse(say(client, str(uuid.uuid4()), "hello").text)
    kinds = [kind for kind, _ in events]
    message = next(data["text"] for kind, data in events if kind == "message")
    return message == "Hi there" and "token" not in kinds and kinds[-1] == "done"


def case_action_pauses_with_interrupt():
    thread = str(uuid.uuid4())
    with make_client() as client:
        events = parse(say(client, thread, "open a ticket").text)
        history = client.get(f"/api/threads/{thread}/messages").json()
    interrupt = next(data["action"] for kind, data in events if kind == "interrupt")
    return interrupt == PROPOSAL and history["awaiting_approval"] is True


def case_paused_thread_rejects_new_chat():
    thread = str(uuid.uuid4())
    with make_client() as client:
        say(client, thread, "open a ticket")
        blocked = say(client, thread, "hello")
        history = client.get(f"/api/threads/{thread}/messages").json()
    return blocked.status_code == 409 and len(history["messages"]) == 2


def case_empty_message_is_rejected():
    with make_client() as client:
        return say(client, str(uuid.uuid4()), "   ").status_code == 422


def case_model_failure_becomes_error_event():
    with make_client() as client:
        events = parse(say(client, str(uuid.uuid4()), "boom").text)
    kinds = [kind for kind, _ in events]
    message = next(data["message"] for kind, data in events if kind == "error")
    return "error" in kinds and kinds[-1] == "done" and "Ollama" in message


def case_conversation_is_saved():
    thread = str(uuid.uuid4())
    with make_client() as client:
        say(client, thread, "hello")
        history = client.get(f"/api/threads/{thread}/messages").json()
    return [m["role"] for m in history["messages"]] == ["user", "assistant"]


CASES = [
    ("Answer streams as steps, tokens, sources, done", case_streamed_answer),
    ("Non-streamed reply arrives as a message event", case_plain_reply_uses_message_event),
    ("An action turn ends with an interrupt event", case_action_pauses_with_interrupt),
    ("A thread waiting for approval refuses new chat (409)", case_paused_thread_rejects_new_chat),
    ("An empty message is rejected (422)", case_empty_message_is_rejected),
    ("A model failure becomes an error event, then done", case_model_failure_becomes_error_event),
    ("The conversation is saved after the stream", case_conversation_is_saved),
]


def main() -> None:
    logging.getLogger("api.sse").setLevel(logging.CRITICAL)  # the failure case is intentional
    passed = 0
    for name, case in CASES:
        ok = case()
        passed += ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    print(f"\nPassed {passed}/{len(CASES)}")


if __name__ == "__main__":
    main()