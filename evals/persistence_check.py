import builtins
import contextlib
import io
import sqlite3
import tempfile
import uuid
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage

import app
from agents import graph as graph_module
from agents import tools
from agents.persistence import list_threads, open_checkpointer

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
    return {
        "messages": [AIMessage(content="prepared")],
        "pending_action": PROPOSAL,
        "approval_status": None,
    }


def open_graph(path):
    checkpointer = open_checkpointer(path)
    return checkpointer, graph_module.build_graph(checkpointer)


def config_for(thread_id):
    return {"configurable": {"thread_id": thread_id}}


def ticket_count() -> int:
    with sqlite3.connect(tools.OPS_DB) as conn:
        return conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]


def case_history_survives_restart(path):
    thread = str(uuid.uuid4())
    _, graph = open_graph(path)
    graph.invoke({"messages": [HumanMessage(content="hello")]}, config_for(thread))
    _, reopened = open_graph(path)
    messages = reopened.get_state(config_for(thread)).values["messages"]
    return [m.content for m in messages] == ["hello", "Hi there"]


def case_threads_are_isolated(path):
    a, b = str(uuid.uuid4()), str(uuid.uuid4())
    _, graph = open_graph(path)
    graph.invoke({"messages": [HumanMessage(content="hello")]}, config_for(a))
    graph.invoke({"messages": [HumanMessage(content="hello again")]}, config_for(b))
    return len(graph.get_state(config_for(a)).values["messages"]) == 2


def case_pending_approval_survives_restart(path):
    thread = str(uuid.uuid4())
    _, graph = open_graph(path)
    graph.invoke({"messages": [HumanMessage(content="open a ticket")]}, config_for(thread))
    before = ticket_count()

    _, reopened = open_graph(path)
    config = config_for(thread)
    if not app.is_waiting_for_approval(reopened, config) or ticket_count() != before:
        return False

    answers = iter(["y"])
    builtins.input = lambda prompt="": next(answers)
    with contextlib.redirect_stdout(io.StringIO()):
        app.resume_with_review(reopened, config)
    return ticket_count() == before + 1 and not app.is_waiting_for_approval(reopened, config)


def case_thread_list(path):
    thread = str(uuid.uuid4())
    checkpointer, graph = open_graph(path)
    graph.invoke({"messages": [HumanMessage(content="open a ticket please")]}, config_for(thread))
    found = {t["thread_id"]: t for t in list_threads(checkpointer, graph)}
    entry = found.get(thread)
    return bool(entry) and entry["title"] == "open a ticket please" and entry["awaiting_approval"]


CASES = [
    ("Conversation history survives a restart", case_history_survives_restart),
    ("Threads do not leak into each other", case_threads_are_isolated),
    ("A pending approval survives a restart and can be resolved", case_pending_approval_survives_restart),
    ("Thread list shows title and waiting-for-approval", case_thread_list),
]


def main() -> None:
    graph_module.supervisor_node = fake_supervisor
    graph_module.direct_responder_node = fake_responder
    graph_module.action_planner_node = fake_planner

    work = Path(tempfile.mkdtemp())
    tools.OPS_DB = work / "ops.db"
    tools.create_ticket.invoke(
        {"title": "Seed ticket", "description": "Seed ticket for the persistence check", "priority": "P4"}
    )
    path = work / "checkpoints.sqlite"

    passed = 0
    for name, case in CASES:
        ok = case(path)
        passed += ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    print(f"\nPassed {passed}/{len(CASES)}")


if __name__ == "__main__":
    main()