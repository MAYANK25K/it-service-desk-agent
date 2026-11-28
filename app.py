import uuid

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from pydantic import ValidationError

from agents.graph import build_graph
from agents.tools import ARG_MODELS, assess_impact, validate_action

UPPERCASE_FIELDS = {"priority", "level", "ticket_id"}


def last_reply(graph, config) -> str:
    return graph.get_state(config).values["messages"][-1].content


def show_proposal(action: dict) -> None:
    print("\n  --- Approval needed ---")
    print(f"  Action : {action['tool_name']}")
    for name, value in action["args"].items():
        print(f"  {name:<12}: {value}")
    print(f"  Risk   : {action['risk'].upper()}")
    print(f"  Impact : {action['impact_summary']}")
    print("  -----------------------")


def explain(error: Exception) -> str:
    if isinstance(error, ValidationError):
        return "; ".join(f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in error.errors())
    return str(error)


def edit_action(action: dict):
    name = action["tool_name"]
    new_args = dict(action["args"])
    print("  Press Enter to keep the current value.")
    for field in ARG_MODELS[name].model_fields:
        current = new_args.get(field)
        value = input(f"  {field} [{'' if current is None else current}]: ").strip()
        if value:
            new_args[field] = value.upper() if field in UPPERCASE_FIELDS else value
    try:
        validated = validate_action(name, new_args)
    except ValueError as exc:
        print(f"  That edit is not valid: {explain(exc)}")
        return None
    impact = assess_impact(name, validated)
    return {**action, "args": validated, "risk": impact["risk"], "impact_summary": impact["summary"]}


def review(action: dict):
    status = "approved"
    while True:
        show_proposal(action)
        choice = input("  Approve? [y] yes  [e] edit  [n] no: ").strip().lower()
        if choice in ("y", "yes"):
            return status, action
        if choice in ("n", "no"):
            return "rejected", action
        if choice in ("e", "edit"):
            edited = edit_action(action)
            if edited is not None:
                action = edited
                status = "edited"
        else:
            print("  Please type y, e or n.")


def run_turn(graph, config, text: str) -> None:
    result = graph.invoke({"messages": [HumanMessage(content=text)]}, config)
    print(f"[route: {result.get('intent', '?')}]")
    print(f"\nAgent: {last_reply(graph, config)}")

    snapshot = graph.get_state(config)
    if "tool_executor" in snapshot.next:
        status, action = review(snapshot.values["pending_action"])
        graph.update_state(
            config,
            {"pending_action": action, "approval_status": status},
            as_node="action_planner",
        )
        graph.invoke(None, config)
        print(f"\nAgent: {last_reply(graph, config)}")


def main() -> None:
    graph = build_graph(MemorySaver())
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    print("IT Service Desk Agent. Type 'exit' to quit.")
    while True:
        text = input("\nYou: ").strip()
        if text.lower() in ("exit", "quit"):
            break
        if not text:
            continue
        run_turn(graph, config, text)


if __name__ == "__main__":
    main()