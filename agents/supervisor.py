from typing import Literal

from langchain_core.messages import AnyMessage, HumanMessage
from pydantic import BaseModel, Field

from agents.llm import get_llm
from agents.state import AgentChatState

HISTORY_WINDOW = 6


class RouteDecision(BaseModel):
    intent: Literal["general", "rag", "action"] = Field(
        description="general = chat, rag = knowledge base question, action = state-changing request."
    )
    reason: str = Field(description="One short sentence explaining the choice.")


SUPERVISOR_PROMPT = """You are the router of an IT Service Desk assistant. Classify the user's LATEST message into exactly one intent.

- general: greetings, thanks, small talk, and questions about the conversation itself (for example "what did I just ask?" or "can you repeat that?").
- rag: questions that need facts from IT documentation: incident procedures, SLA targets, escalation contacts, VPN problems, server restart rules, passwords and access policies. Questions about HOW to do something are rag, even when the topic is an action.
- action: the user asks you to DO something that changes state: open or create a ticket, escalate an incident, restart a server. Follow-ups such as "go ahead and open a ticket for that" are action; use the conversation to understand what "that" refers to.

Examples:
"Hi there" -> general
"Thanks, that helps" -> general
"What did I ask you earlier?" -> general
"What is the P1 response time?" -> rag
"How do I restart a production server?" -> rag
"Open a high-priority ticket for the VPN outage" -> action
"Please restart server APP-02" -> action
"Go ahead and open a ticket for that" -> action

Reply with the intent and a one-sentence reason."""


def format_transcript(messages: list[AnyMessage]) -> str:
    lines = []
    for message in messages[-HISTORY_WINDOW:]:
        role = "User" if isinstance(message, HumanMessage) else "Assistant"
        text = str(message.content).replace("\n", " ")
        lines.append(f"{role}: {text[:300]}")
    return "\n".join(lines)


def classify_intent(messages: list[AnyMessage]) -> RouteDecision:
    latest = str(messages[-1].content)
    transcript = format_transcript(messages[:-1]) or "(none)"
    user_message = (
        f"Conversation so far:\n{transcript}\n\nLatest user message: {latest}"
    )
    router = get_llm().with_structured_output(RouteDecision)
    try:
        decision = router.invoke(
            [("system", SUPERVISOR_PROMPT), ("human", user_message)]
        )
    except Exception as exc:
        return RouteDecision(
            intent="rag",
            reason=f"Router error ({type(exc).__name__}); defaulting to knowledge-base lookup.",
        )
    if isinstance(decision, RouteDecision):
        return decision
    return RouteDecision(
        intent="rag", reason="Router returned no verdict; defaulting to lookup."
    )


def supervisor_node(state: AgentChatState) -> dict:
    decision = classify_intent(state["messages"])
    return {"intent": decision.intent}