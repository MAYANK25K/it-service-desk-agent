import re
from typing import Literal, Optional

from langchain_core.messages import AIMessage, AnyMessage
from pydantic import BaseModel, Field, ValidationError

from agents.llm import get_llm
from agents.state import AgentChatState
from agents.supervisor import format_transcript
from agents.tools import assess_impact, validate_action

TOOL_FIELDS = {
    "create_ticket": ["title", "description", "priority"],
    "restart_server": ["server_name", "environment", "reason", "ticket_id"],
    "escalate_incident": ["ticket_id", "level", "reason"],
}

DEFAULT_QUESTION = (
    "Which action would you like me to take, and on what? "
    "For example: open a ticket, restart a server or escalate an incident."
)

PLACEHOLDER_QUESTION = (
    "I'm not sure what this request should be about. "
    "Could you describe the issue in one sentence?"
)

PLACEHOLDER_PATTERN = re.compile(r"\[[^\]]*\]|\binsert\b|\btbd\b", re.IGNORECASE)
REASON_PATTERN = re.compile(r"\b(?:because|since|due to)\b\s+(.+)", re.IGNORECASE)
NON_PROD_PATTERN = re.compile(
    r"non-?prod(?:uction)?|\bstaging\b|\bdev(?:elopment)?\b|\btest\b|\buat\b|\bqa\b", re.IGNORECASE
)
PROD_PATTERN = re.compile(r"\bprod(?:uction)?\b", re.IGNORECASE)
GENERIC_SERVER_WORDS = {"server", "servers", "host", "machine", "it", "this", "that"}
JUNK_REASONS = {"unknown", "n/a", "none", "not provided", "not specified", "unspecified"}


class ActionPlan(BaseModel):
    tool_name: Literal["create_ticket", "restart_server", "escalate_incident", "none"]
    title: Optional[str] = Field(default=None, description="Short ticket title, only for create_ticket.")
    description: Optional[str] = Field(default=None, description="What is wrong, only for create_ticket.")
    priority: Optional[Literal["P1", "P2", "P3", "P4"]] = None
    server_name: Optional[str] = Field(
        default=None, description="Server name exactly as the user wrote it. Null if the user gave none."
    )
    environment: Optional[Literal["production", "non-production"]] = None
    reason: Optional[str] = Field(
        default=None,
        description="Why the action is needed, copied from the user's own words, e.g. 'no progress' or 'the service is hung'.",
    )
    ticket_id: Optional[str] = Field(
        default=None, description="Ticket ID (INC- followed by digits), only if the user wrote one. Otherwise null."
    )
    level: Optional[Literal["L2", "L3", "L4"]] = None
    clarification: Optional[str] = Field(
        default=None,
        description="Only a question for the user, and only when a required detail is truly missing. Otherwise null.",
    )


PLANNER_PROMPT = """You prepare IT Service Desk actions. Choose one tool and fill in its arguments from the conversation.

Tools and their fields:
- create_ticket: title, description, priority
- restart_server: server_name, environment (production or non-production), reason, ticket_id (optional)
- escalate_incident: ticket_id, level (L2, L3 or L4), reason

Rules:
- Use only facts from the conversation. Only fill ticket_id and server_name if the user wrote them. Otherwise leave them null and ask in clarification.
- Fill reason with the cause the user gave. Example: "because the service is hung" gives reason "the service is hung". Never put a reason in clarification.
- clarification is only for a question to the user when a required field is truly missing. If nothing is missing, leave clarification null.
- If the user says "that" or "it", use the earlier conversation and the knowledge base evidence to write a clear title and description.
- Never write placeholders such as [insert ...]. If you cannot tell what "that" refers to, leave title and description null and ask in clarification.
- Priority: critical, urgent or outage means P1; high or high-priority means P2; medium or normal means P3; low means P4. If the user gives no priority, use P3.
- If the latest message is not asking for any of these actions, use tool_name none and put a question in clarification."""


def evidence_summary(docs: list[dict]) -> str:
    if not docs:
        return "(none)"
    lines = []
    for doc in docs[:3]:
        text = doc["content"].replace("\n", " ")[:300]
        lines.append(f"- {doc['source']} Section {doc['section_ref']}: {text}")
    return "\n".join(lines)


def plan_action(messages: list[AnyMessage], docs: list[dict]) -> ActionPlan:
    user_message = (
        f"Conversation so far:\n{format_transcript(messages[:-1]) or '(none)'}\n\n"
        f"Knowledge base evidence from the last answer:\n{evidence_summary(docs)}\n\n"
        f"Latest user request: {messages[-1].content}"
    )
    planner = get_llm().with_structured_output(ActionPlan)
    try:
        plan = planner.invoke([("system", PLANNER_PROMPT), ("human", user_message)])
    except Exception:
        return ActionPlan(
            tool_name="none",
            clarification="Sorry, I couldn't work out which action you want. Could you rephrase it?",
        )
    if isinstance(plan, ActionPlan):
        return plan
    return ActionPlan(tool_name="none", clarification=DEFAULT_QUESTION)


def conversation_text(messages: list[AnyMessage]) -> str:
    return " ".join(str(message.content) for message in messages)


def appears_in(value: str, text: str) -> bool:
    return re.search(rf"(?<![\w-]){re.escape(value)}(?![\w-])", text, re.IGNORECASE) is not None


def detect_environment(text: str) -> Optional[str]:
    if NON_PROD_PATTERN.search(text):
        return "non-production"
    if PROD_PATTERN.search(text):
        return "production"
    return None


def normalize_plan(plan: ActionPlan, messages: list[AnyMessage]) -> ActionPlan:
    """Do not trust the model for fields that must come from the user."""
    text = conversation_text(messages)
    latest = str(messages[-1].content)
    updates: dict = {}

    if plan.ticket_id and not appears_in(plan.ticket_id, text):
        updates["ticket_id"] = None

    if plan.server_name and (
        plan.server_name.strip().lower() in GENERIC_SERVER_WORDS or not appears_in(plan.server_name, text)
    ):
        updates["server_name"] = None

    if plan.tool_name == "restart_server":
        updates["environment"] = detect_environment(text)

    reason = plan.reason
    if reason and reason.strip().lower().rstrip(".") in JUNK_REASONS:
        reason = None
    if not reason:
        match = REASON_PATTERN.search(latest)
        if match:
            reason = match.group(1).strip().rstrip(".")
    updates["reason"] = reason

    return plan.model_copy(update=updates)


def plan_to_args(plan: ActionPlan) -> dict:
    values = {name: getattr(plan, name) for name in TOOL_FIELDS[plan.tool_name]}
    return {name: value for name, value in values.items() if value is not None}


def has_placeholder(plan: ActionPlan) -> bool:
    texts = (plan.title, plan.description, plan.reason)
    return any(PLACEHOLDER_PATTERN.search(text) for text in texts if text)


def is_question(text: Optional[str]) -> bool:
    return bool(text) and text.strip().endswith("?")


def ask_for_details(plan: ActionPlan, error: ValueError) -> str:
    if isinstance(error, ValidationError):
        fields = sorted({str(e["loc"][0]) for e in error.errors() if e["loc"]})
        return (
            "I need a few more details before I can prepare this request: "
            f"{', '.join(fields)}. Could you provide them?"
        )
    return f"I can't prepare that request: {error}"


def prepare_action(messages: list[AnyMessage], docs: list[dict]) -> dict:
    plan = plan_action(messages, docs)
    if plan.tool_name == "none":
        return {"question": plan.clarification or DEFAULT_QUESTION}
    if is_question(plan.clarification):
        return {"question": plan.clarification}
    if has_placeholder(plan):
        return {"question": PLACEHOLDER_QUESTION}
    plan = normalize_plan(plan, messages)
    try:
        args = validate_action(plan.tool_name, plan_to_args(plan))
    except ValueError as exc:
        return {"question": ask_for_details(plan, exc)}
    impact = assess_impact(plan.tool_name, args)
    return {
        "action": {
            "tool_name": plan.tool_name,
            "args": args,
            "risk": impact["risk"],
            "impact_summary": impact["summary"],
        }
    }


def action_planner_node(state: AgentChatState) -> dict:
    result = prepare_action(state["messages"], state.get("retrieved_docs", []))
    if "question" in result:
        return {
            "messages": [AIMessage(content=result["question"])],
            "pending_action": None,
            "approval_status": None,
        }
    action = result["action"]
    return {
        "messages": [
            AIMessage(
                content=f"I've prepared a {action['tool_name']} request. I need your approval before I run it."
            )
        ],
        "pending_action": action,
        "approval_status": None,
    }