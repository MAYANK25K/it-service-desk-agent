from typing import Annotated, Literal, Optional

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AgentChatState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    intent: Literal["general", "rag", "action"]
    retrieved_docs: list[dict]
    pending_action: Optional[dict]
    approval_status: Optional[Literal["approved", "edited", "rejected"]]