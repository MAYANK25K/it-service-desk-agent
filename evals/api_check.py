import tempfile
import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage

from agents import graph as graph_module
from agents.persistence import open_checkpointer
from api.main import create_app

PROPOSAL = {
    "tool_name": "create_ticket",
    "args": {"title": "VPN outage", "description": "Users cannot connect to the VPN", "priority": "P2"},
    "risk": "low",
    "impact_summary": "Creates a ticket.",
}


def fake_supervisor(state):
    return {"intent": "action" if "ticket" in state["messages"][-1].content else "general"}


def fake_responder(state):
    return {"messages": [AIMessage(content="Hi there")]}


def fake_planner(state):
    return {"messages": [AIMessage(content="prepared")], "pending_action": PROPOSAL, "approval_status": None}


def make_client():
    graph_module.supervisor_node = fake_supervisor
    graph_module.direct_responder_node = fake_responder
    graph_module.action_planner_node = fake_planner
    checkpointer = open_checkpointer(Path(tempfile.mkdtemp()) / "api_check.sqlite")
    graph = graph_module.build_graph(checkpointer)
    return TestClient(create_app(checkpointer, graph)), graph


def chat(graph, thread_id, text):
    graph.invoke({"messages": [HumanMessage(content=text)]}, {"configurable": {"thread_id": thread_id}})


def case_health():
    client, _ = make_client()
    with client:
        body = client.get("/api/health").json()
    return body["status"] == "ok" and bool(body["model"])


def case_cors():
    client, _ = make_client()
    with client:
        allowed = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
        blocked = client.get("/api/health", headers={"Origin": "http://evil.example"})
    return (
        allowed.headers.get("access-control-allow-origin") == "http://localhost:5173"
        and "access-control-allow-origin" not in blocked.headers
    )


def case_new_thread_and_empty_list():
    client, _ = make_client()
    with client:
        created = client.post("/api/threads")
        listed = client.get("/api/threads").json()
    uuid.UUID(created.json()["thread_id"])
    return created.status_code == 201 and listed == {"threads": []}


def case_unknown_thread_is_404():
    client, _ = make_client()
    with client:
        return client.get(f"/api/threads/{uuid.uuid4()}/messages").status_code == 404


def case_history_and_listing():
    client, graph = make_client()
    thread = str(uuid.uuid4())
    chat(graph, thread, "hello")
    with client:
        listed = client.get("/api/threads").json()["threads"]
        history = client.get(f"/api/threads/{thread}/messages").json()
    entry = listed[0]
    return (
        entry["thread_id"] == thread
        and entry["title"] == "hello"
        and entry["messages"] == 2
        and bool(entry["updated_at"])
        and history["messages"] == [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        and history["awaiting_approval"] is False
        and history["pending_action"] is None
    )


def case_pending_action_is_exposed():
    client, graph = make_client()
    thread = str(uuid.uuid4())
    chat(graph, thread, "open a ticket")
    with client:
        history = client.get(f"/api/threads/{thread}/messages").json()
    return history["awaiting_approval"] is True and history["pending_action"] == PROPOSAL


CASES = [
    ("Health endpoint reports status and model", case_health),
    ("CORS allows the React dev server only", case_cors),
    ("New thread gets an id; list starts empty", case_new_thread_and_empty_list),
    ("Unknown thread returns 404", case_unknown_thread_is_404),
    ("Thread list and history show real conversation", case_history_and_listing),
    ("A waiting approval is exposed with its action", case_pending_action_is_exposed),
]


def main() -> None:
    passed = 0
    for name, case in CASES:
        ok = case()
        passed += ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    print(f"\nPassed {passed}/{len(CASES)}")


if __name__ == "__main__":
    main()