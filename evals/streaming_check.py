import contextlib
import io
import uuid

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver

import app
from agents import graph as graph_module

REPLY = "Restart the router then retry the VPN login"


def fake_model(text: str, tags=None):
    return GenericFakeChatModel(messages=iter([AIMessage(content=text)]), tags=tags)


def fake_supervisor(state):
    return {"intent": "rag"}


def streaming_rag(state):
    fake_model("INTERNAL GRADER JSON").invoke([HumanMessage(content="grade this")])
    answer = fake_model(REPLY, tags=["answer"]).invoke([HumanMessage(content="answer")])
    return {"messages": [AIMessage(content=str(answer.content))], "retrieved_docs": [{"a": 1}]}


def silent_rag(state):
    return {"messages": [AIMessage(content="Not found in the knowledge base.")], "retrieved_docs": []}


def run(rag_node):
    graph_module.supervisor_node = fake_supervisor
    graph_module.rag_agent_node = rag_node
    graph = graph_module.build_graph(MemorySaver())
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        streamed = app.stream_graph(graph, {"messages": [HumanMessage(content="vpn?")]}, config)
    return streamed, buffer.getvalue()


def case_answer_is_streamed():
    streamed, output = run(streaming_rag)
    return streamed and REPLY in output


def case_internal_calls_are_hidden():
    _, output = run(streaming_rag)
    return "INTERNAL" not in output


def case_steps_are_still_printed():
    _, output = run(streaming_rag)
    return "[supervisor] intent = rag" in output and "[rag_agent]" in output


def case_non_llm_reply_is_not_streamed():
    streamed, output = run(silent_rag)
    return not streamed and "Not found" not in output


CASES = [
    ("Answer tokens are streamed", case_answer_is_streamed),
    ("Internal model calls (grader, planner) stay hidden", case_internal_calls_are_hidden),
    ("Step lines are still printed", case_steps_are_still_printed),
    ("Replies not written by the model are not streamed", case_non_llm_reply_is_not_streamed),
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