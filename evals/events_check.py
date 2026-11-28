import uuid

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from agents import graph as graph_module
from agents.events import mark_cited, stream_events

REPLY = "Restart the router then retry the VPN login"
DOCS = [
    {"source": "vpn_troubleshooting.md", "doc_id": "KB-VPN-014", "section_ref": "3", "section": "3. Error 809"},
    {"source": "vpn_troubleshooting.md", "doc_id": "KB-VPN-014", "section_ref": "3", "section": "3. Error 809"},
    {"source": "sla_policy.md", "doc_id": "POL-SLA-001", "section_ref": "3", "section": "3. Targets"},
]
PROPOSAL = {
    "tool_name": "create_ticket",
    "args": {"title": "VPN outage", "description": "Users cannot connect to the VPN", "priority": "P2"},
    "risk": "low",
    "impact_summary": "Creates a ticket.",
}


def fake_supervisor(state):
    text = state["messages"][-1].content
    return {"intent": "action" if "ticket" in text else "rag"}


def streaming_rag(state):
    model = GenericFakeChatModel(messages=iter([AIMessage(content=REPLY)]), tags=["answer"])
    answer = model.invoke([HumanMessage(content="answer")])
    return {"messages": [AIMessage(content=str(answer.content))], "retrieved_docs": DOCS}


def fake_planner(state):
    return {"messages": [AIMessage(content="prepared")], "pending_action": PROPOSAL, "approval_status": None}


def events_for(text):
    graph_module.supervisor_node = fake_supervisor
    graph_module.rag_agent_node = streaming_rag
    graph_module.action_planner_node = fake_planner
    graph = graph_module.build_graph(MemorySaver())
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    return list(stream_events(graph, {"messages": [HumanMessage(content=text)]}, config))


def case_event_order():
    events = events_for("vpn?")
    kinds = [e["type"] for e in events]
    return kinds[0] == "step" and "token" in kinds and kinds[-1] == "done" and kinds.count("done") == 1


def case_tokens_rebuild_the_answer():
    events = events_for("vpn?")
    joined = "".join(e["text"] for e in events if e["type"] == "token")
    return joined == REPLY and events[-1]["text"] == REPLY and events[-1]["streamed"]


def case_sources_are_unique():
    done = events_for("vpn?")[-1]
    return [(s["source"], s["section_ref"]) for s in done["sources"]] == [
        ("vpn_troubleshooting.md", "3"),
        ("sla_policy.md", "3"),
    ]


def case_pending_action_is_reported():
    done = events_for("open a ticket")[-1]
    return done["pending_action"] == PROPOSAL and done["sources"] == [] and not done["streamed"]


def case_cited_flags():
    sources = [
        {"source": "vpn_troubleshooting.md", "section_ref": "3"},
        {"source": "vpn_troubleshooting.md", "section_ref": "4.2"},
        {"source": "sla_policy.md", "section_ref": "3"},
    ]
    text = "Switch network. [Source: vpn_troubleshooting.md, Section 4.2]. Also see [Source: sla_policy.md, Section 3]."
    flagged = mark_cited(sources, text)
    uncited = mark_cited(sources, "No citations here.")
    return (
        [(s["source"], s["section_ref"], s["cited"]) for s in flagged]
        == [("vpn_troubleshooting.md", "4.2", True), ("sla_policy.md", "3", True), ("vpn_troubleshooting.md", "3", False)]
        and not any(s["cited"] for s in uncited)
    )

CASES = [
    ("Events arrive as step, tokens, then one done", case_event_order),
    ("Tokens rebuild the full answer", case_tokens_rebuild_the_answer),
    ("Sources are de-duplicated", case_sources_are_unique),
    ("A paused action is reported in the done event", case_pending_action_is_reported),
    ("Sources are flagged as cited, cited first", case_cited_flags),
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