from langgraph.graph import END, START, StateGraph

from agents.action_planner import action_planner_node
from agents.direct_responder import direct_responder_node
from agents.rag_agent import rag_agent_node
from agents.state import AgentChatState
from agents.supervisor import supervisor_node


def route_by_intent(state: AgentChatState) -> str:
    return state.get("intent", "rag")


def build_graph(checkpointer=None):
    builder = StateGraph(AgentChatState)

    builder.add_node("supervisor", supervisor_node)
    builder.add_node("direct_responder", direct_responder_node)
    builder.add_node("rag_agent", rag_agent_node)
    builder.add_node("action_planner", action_planner_node)

    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges(
        "supervisor",
        route_by_intent,
        {
            "general": "direct_responder",
            "rag": "rag_agent",
            "action": "action_planner",
        },
    )
    builder.add_edge("direct_responder", END)
    builder.add_edge("rag_agent", END)
    builder.add_edge("action_planner", END)

    return builder.compile(checkpointer=checkpointer)