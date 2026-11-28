from langchain_core.messages import AIMessage

from agents.state import AgentChatState
from agents.tools import TOOLS, validate_action


def run_action(action: dict) -> str:
    name = action["tool_name"]
    try:
        args = validate_action(name, action["args"])
        return TOOLS[name].invoke(args)
    except Exception as exc:
        return f"The action failed and nothing was changed: {exc}"


def tool_executor_node(state: AgentChatState) -> dict:
    action = state.get("pending_action")
    status = state.get("approval_status")

    if not action:
        text = "There is no pending action to run."
    elif status == "rejected":
        text = f"Okay, I cancelled the {action['tool_name']} request. Nothing was changed."
    elif status in ("approved", "edited"):
        text = f"Done. {run_action(action)}"
    else:
        text = "I did not run the action because it was not approved."

    return {
        "messages": [AIMessage(content=text)],
        "pending_action": None,
        "approval_status": None,
    }