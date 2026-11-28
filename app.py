import argparse
import uuid

from langchain_core.messages import HumanMessage
from pydantic import ValidationError

from agents.graph import build_graph
from agents.persistence import list_threads, open_checkpointer
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


def resume_with_review(graph, config) -> None:
    snapshot = graph.get_state(config)
    status, action = review(snapshot.values["pending_action"])
    graph.update_state(
        config,
        {"pending_action": action, "approval_status": status},
        as_node="action_planner",
    )
    graph.invoke(None, config)
    print(f"\nAgent: {last_reply(graph, config)}")


def is_waiting_for_approval(graph, config) -> bool:
    return "tool_executor" in graph.get_state(config).next


def run_turn(graph, config, text: str) -> None:
    result = graph.invoke({"messages": [HumanMessage(content=text)]}, config)
    print(f"[route: {result.get('intent', '?')}]")
    print(f"\nAgent: {last_reply(graph, config)}")
    if is_waiting_for_approval(graph, config):
        resume_with_review(graph, config)


def print_threads(checkpointer, graph) -> None:
    threads = list_threads(checkpointer, graph)
    if not threads:
        print("No saved conversations yet.")
        return
    print("Saved conversations (most recent first):")
    for t in threads:
        waiting = "  [waiting for approval]" if t["awaiting_approval"] else ""
        print(f"  {t['thread_id']}  {t['messages']:>3} msgs  {t['title']}{waiting}")
    print("\nResume one with: python app.py --thread-id <id>")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="IT Service Desk Agent")
    parser.add_argument("--thread-id", help="resume a saved conversation")
    parser.add_argument("--list-threads", action="store_true", help="list saved conversations and exit")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    checkpointer = open_checkpointer()
    graph = build_graph(checkpointer)

    if args.list_threads:
        print_threads(checkpointer, graph)
        return

    thread_id = args.thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    saved = graph.get_state(config).values.get("messages", [])

    print("IT Service Desk Agent. Type 'exit' to quit.")
    if saved:
        print(f"Resuming conversation {thread_id} ({len(saved)} messages so far).")
    else:
        print(f"New conversation {thread_id}. Resume it later with: python app.py --thread-id {thread_id}")

    if is_waiting_for_approval(graph, config):
        print(f"\nAgent: {last_reply(graph, config)}")
        print("This conversation has an action waiting for your decision.")
        resume_with_review(graph, config)

    while True:
        text = input("\nYou: ").strip()
        if text.lower() in ("exit", "quit"):
            break
        if not text:
            continue
        run_turn(graph, config, text)


if __name__ == "__main__":
    main()