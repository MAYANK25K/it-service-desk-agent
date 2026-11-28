import sqlite3
import tempfile
import uuid
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from agents import graph as graph_module
from agents import tools

PROPOSAL = {
    "tool_name": "create_ticket",
    "args": {"title": "VPN outage", "description": "Users cannot connect to the VPN", "priority": "P2"},
    "risk": "low",
    "impact_summary": "Creates a ticket.",
}


def fake_supervisor(state):
    return {"intent": "action"}


def fake_planner(state):
    return {
        "messages": [AIMessage(content="prepared")],
        "pending_action": PROPOSAL,
        "approval_status": None,
    }


def priorities() -> list[str]:
    with sqlite3.connect(tools.OPS_DB) as conn:
        return [row[0] for row in conn.execute("SELECT priority FROM tickets ORDER BY id")]


def start():
    graph = graph_module.build_graph(MemorySaver())
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    graph.invoke({"messages": [HumanMessage(content="open a ticket")]}, config)
    return graph, config


def decide(graph, config, status, action=None):
    graph.update_state(
        config,
        {"pending_action": action or PROPOSAL, "approval_status": status},
        as_node="action_planner",
    )
    graph.invoke(None, config)


def fresh_db() -> None:
    tools.OPS_DB = Path(tempfile.mkdtemp()) / "hitl_check.db"
    tools.create_ticket.invoke(
        {"title": "Seed ticket", "description": "Seed ticket for the HITL check", "priority": "P4"}
    )


def case_pauses_before_running():
    graph, config = start()
    return "tool_executor" in graph.get_state(config).next and priorities() == ["P4"]


def case_approve_runs():
    graph, config = start()
    decide(graph, config, "approved")
    return priorities() == ["P4", "P2"] and graph.get_state(config).values["pending_action"] is None


def case_reject_changes_nothing():
    graph, config = start()
    decide(graph, config, "rejected")
    reply = graph.get_state(config).values["messages"][-1].content
    return priorities() == ["P4"] and "cancelled" in reply


def case_edit_runs_edited_values():
    graph, config = start()
    edited = {**PROPOSAL, "args": {**PROPOSAL["args"], "priority": "P1"}}
    decide(graph, config, "edited", edited)
    return priorities() == ["P4", "P1"]


def case_no_decision_runs_nothing():
    graph, config = start()
    graph.invoke(None, config)
    return priorities() == ["P4"]


def case_invalid_args_run_nothing():
    graph, config = start()
    bad = {**PROPOSAL, "args": {**PROPOSAL["args"], "priority": "P9"}}
    decide(graph, config, "approved", bad)
    reply = graph.get_state(config).values["messages"][-1].content
    return priorities() == ["P4"] and "failed" in reply


CASES = [
    ("Graph pauses before the tool and writes nothing", case_pauses_before_running),
    ("Approve runs the tool once", case_approve_runs),
    ("Reject changes nothing", case_reject_changes_nothing),
    ("Edit runs the edited values", case_edit_runs_edited_values),
    ("Resuming with no decision runs nothing", case_no_decision_runs_nothing),
    ("Invalid arguments run nothing", case_invalid_args_run_nothing),
]


def main() -> None:
    graph_module.supervisor_node = fake_supervisor
    graph_module.action_planner_node = fake_planner

    passed = 0
    for name, case in CASES:
        fresh_db()
        ok = case()
        passed += ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    print(f"\nPassed {passed}/{len(CASES)}")


if __name__ == "__main__":
    main()