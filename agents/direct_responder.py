from langchain_core.messages import AIMessage, SystemMessage

from agents.llm import get_llm
from agents.state import AgentChatState

HISTORY_WINDOW = 10

DIRECT_PROMPT = """You are a friendly IT Service Desk assistant. Reply briefly to greetings, thanks and questions about the conversation itself, using only what was said earlier in this chat.

Never invent company policies, SLA numbers or procedures. If the user asks for IT policy or procedure details that are not already in the conversation, tell them to ask that question directly so you can look it up in the knowledge base."""


def direct_responder_node(state: AgentChatState) -> dict:
    history = state["messages"][-HISTORY_WINDOW:]
    reply = get_llm(temperature=0.3, tags=["answer"]).invoke(
        [SystemMessage(content=DIRECT_PROMPT), *history]
    )
    return {"messages": [AIMessage(content=str(reply.content))]}