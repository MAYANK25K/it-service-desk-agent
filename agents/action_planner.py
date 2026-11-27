from langchain_core.messages import AIMessage

from agents.state import AgentChatState


def action_planner_node(state: AgentChatState) -> dict:
    return {
        "messages": [
            AIMessage(
                content="Actions such as opening tickets or restarting servers are not enabled yet."
            )
        ]
    }