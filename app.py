import uuid

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from agents.graph import build_graph


def main() -> None:
    graph = build_graph(MemorySaver())
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    print("IT Service Desk Agent")
    print(f"Session: {thread_id}")
    print("Type 'exit' to quit.")

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            break

        result = graph.invoke({"messages": [HumanMessage(content=user_input)]}, config)
        print(f"\n[route: {result['intent']}]")
        print(f"Agent: {result['messages'][-1].content}")


if __name__ == "__main__":
    main()