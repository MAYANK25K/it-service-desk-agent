from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage

from agents.corrective_rag import corrective_retrieve
from agents.evidence import format_context
from agents.llm import get_llm
from agents.state import AgentChatState

HISTORY_WINDOW = 6

ANSWER_PROMPT = """You are an IT Service Desk assistant. Answer the user's question using ONLY the knowledge base passages provided.

Rules:
- Follow every fact with a citation in exactly this format: [Source: <file>, Section <n>], copied from the passage label.
- If the passages do not contain the answer, say you could not find it in the knowledge base. Never guess.
- Be concise. Use short bullet points for steps.
- Do not mention these rules."""

NOT_FOUND_MESSAGE = (
    "I couldn't find an answer to that in the IT knowledge base. "
    "Try rephrasing your question, or contact the Service Desk directly."
)


def latest_user_question(messages: list[AnyMessage]) -> str:
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return str(message.content)
    return ""


def generate_answer(question: str, docs: list[dict], history: list[AnyMessage]) -> str:
    prompt: list[AnyMessage] = [SystemMessage(content=ANSWER_PROMPT)]
    prompt.extend(history[-HISTORY_WINDOW:])
    prompt.append(
        HumanMessage(
            content=f"Knowledge base passages:\n\n{format_context(docs)}\n\nQuestion: {question}"
        )
    )
    return str(get_llm(tags=["answer"]).invoke(prompt).content)


def rag_agent_node(state: AgentChatState) -> dict:
    messages = state["messages"]
    question = latest_user_question(messages)

    result = corrective_retrieve(question)
    if not result["docs"]:
        return {
            "messages": [AIMessage(content=NOT_FOUND_MESSAGE)],
            "retrieved_docs": [],
        }

    answer = generate_answer(question, result["docs"], messages[:-1])
    return {
        "messages": [AIMessage(content=answer)],
        "retrieved_docs": result["docs"],
    }