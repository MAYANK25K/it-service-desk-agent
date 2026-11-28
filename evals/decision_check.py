import sqlite3
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage

from agents import graph as graph_module
from agents import tools
from agents.persistence import open_checkpointer
from api.main import create_app

PROPOSAL = {
    "tool_name": "create_ticket",
    "args": {"title": "VPN outage", "description": "Users cannot connect to the VPN", "priority": "P2"},
    "risk": "low",
    "impact_summary": "Creates a ticket.",
}


def fake_supervisor(state):
    return {"intent": "action"}


def fake_planner(state):
    return {"messages": [AIMessage(content="prepared")], "pending_action": PROPOSAL, "approval_status": None}


def priorities() -> list[str]:
    with sqlite3.connect(tools.OPS_DB) as conn:
        return [row[0] for row in conn.execute("SELECT priority FROM tickets ORDER BY id")]


def waiting_thread():
    """A fresh API client plus a thread that is paused at an approval."""
    tools.OPS_DB = Path(tempfile.mkdtemp()) / "decision_check.db"
    tools.create_ticket.invoke(
        {"title": "Seed ticket", "description": "Seed ticket for the decision check", "priority": "P4"}
    )
    graph_module.supervisor_node = fake_supervisor
    graph_module.action_planner_node = fake_planner
    checkpointer = open_checkpointer(Path(tempfile.mkdtemp()) / "decision_check.sqlite")
    graph = graph_module.build_graph(checkpointer)
    thread = str(uuid.uuid4())
    graph.invoke({"messages": [HumanMessage(content="open a ticket")]}, {"configurable": {"thread_id": thread}})
    return TestClient(create_app(checkpointer, graph)), thread


def decide(client, thread, decision, args=None):
    body = {"decision": decision}
    if args is not None:
        body["args"] = args
    return client.post(f"/api/threads/{thread}/decision", json=body)


def is_waiting(client, thread) -> bool:
    return client.get(f"/api/threads/{thread}/messages").json()["awaiting_approval"]


def case_approve_runs_the_tool():
    client, thread = waiting_thread()
    with client:
        response = decide(client, thread, "approve")
        waiting = is_waiting(client, thread)
    body = response.json()
    return (
        response.status_code == 200
        and body["status"] == "approved"
        and body["message"].startswith("Done. Ticket INC-")
        and body["steps"][-1]["node"] == "tool_executor"
        and priorities() == ["P4", "P2"]
        and not waiting
    )


def case_reject_changes_nothing():
    client, thread = waiting_thread()
    with client:
        response = decide(client, thread, "reject")
    return "cancelled" in response.json()["message"] and priorities() == ["P4"]


def case_edit_runs_edited_values():
    client, thread = waiting_thread()
    with client:
        response = decide(client, thread, "edit", {"priority": "p1"})
    return response.json()["status"] == "edited" and priorities() == ["P4", "P1"]


def case_invalid_edit_keeps_waiting_then_recovers():
    client, thread = waiting_thread()
    with client:
        bad = decide(client, thread, "edit", {"priority": "P9"})
        still_waiting = is_waiting(client, thread)
        no_change = priorities() == ["P4"]
        good = decide(client, thread, "approve")
    return bad.status_code == 422 and still_waiting and no_change and good.status_code == 200


def case_unknown_field_and_empty_edit_are_rejected():
    client, thread = waiting_thread()
    with client:
        unknown = decide(client, thread, "edit", {"colour": "red"})
        empty = decide(client, thread, "edit", {})
        missing = decide(client, thread, "edit")
    return (
        unknown.status_code == 422
        and "colour" in unknown.json()["detail"]
        and empty.status_code == 422
        and missing.status_code == 422
        and priorities() == ["P4"]
    )


def case_nothing_waiting_is_409():
    client, thread = waiting_thread()
    with client:
        unknown_thread = decide(client, str(uuid.uuid4()), "approve")
        decide(client, thread, "approve")
        second = decide(client, thread, "approve")
    return unknown_thread.status_code == 409 and second.status_code == 409 and priorities() == ["P4", "P2"]


def case_double_click_runs_once():
    client, thread = waiting_thread()
    with client:
        with ThreadPoolExecutor(max_workers=4) as pool:
            responses = list(pool.map(lambda _: decide(client, thread, "approve"), range(4)))
    codes = sorted(r.status_code for r in responses)
    return codes == [200, 409, 409, 409] and priorities() == ["P4", "P2"]


CASES = [
    ("Approve runs the tool and returns its result", case_approve_runs_the_tool),
    ("Reject changes nothing", case_reject_changes_nothing),
    ("Edit runs the edited, normalised values", case_edit_runs_edited_values),
    ("An invalid edit is refused and the action keeps waiting", case_invalid_edit_keeps_waiting_then_recovers),
    ("Unknown fields and empty edits are refused", case_unknown_field_and_empty_edit_are_rejected),
    ("Deciding with nothing waiting returns 409", case_nothing_waiting_is_409),
    ("Four simultaneous approvals run the tool once", case_double_click_runs_once),
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