from typing import Optional

from pydantic import BaseModel, Field

from agents.config import RETRIEVAL_TOP_K
from agents.evidence import format_context
from agents.llm import get_llm
from agents.retriever import retrieve


class RelevanceGrade(BaseModel):
    relevant: bool = Field(
        description="True only if the passages contain the specific facts needed to answer the question."
    )
    reason: str = Field(description="One short sentence explaining the decision.")


class SearchQuery(BaseModel):
    query: str = Field(description="A short, keyword-rich search query.")


GRADER_PROMPT = (
    "You are a strict relevance grader for an IT Service Desk knowledge base. "
    "You are given a question and retrieved passages. Set relevant to true only if "
    "the passages contain the specific facts needed to answer the question. "
    "If they are only loosely related or about a different topic, set relevant to false."
)

REWRITE_PROMPT = (
    "Rewrite the user's question as a short, keyword-rich search query for an IT "
    "Service Desk knowledge base (incident runbook, SLA policy, escalation matrix, "
    "VPN guide, server restart SOP, access management policy). Keep important terms "
    "such as priority levels, error codes and system names. Return only the query."
)


def grade_relevance(question: str, docs: list[dict]) -> RelevanceGrade:
    if not docs:
        return RelevanceGrade(relevant=False, reason="Nothing was retrieved.")
    grader = get_llm().with_structured_output(RelevanceGrade)
    user_message = f"Question: {question}\n\nPassages:\n{format_context(docs)}"
    try:
        grade = grader.invoke([("system", GRADER_PROMPT), ("human", user_message)])
    except Exception as exc:
        return RelevanceGrade(
            relevant=True,
            reason=f"Grader error ({type(exc).__name__}); keeping retrieved passages.",
        )
    if isinstance(grade, RelevanceGrade):
        return grade
    return RelevanceGrade(
        relevant=True, reason="Grader returned no verdict; keeping passages."
    )


def rewrite_query(question: str) -> str:
    rewriter = get_llm().with_structured_output(SearchQuery)
    try:
        result = rewriter.invoke([("system", REWRITE_PROMPT), ("human", question)])
    except Exception:
        return question
    return result.query.strip() or question


def corrective_retrieve(
    question: str, k: int = RETRIEVAL_TOP_K, filters: Optional[dict] = None
) -> dict:
    docs = retrieve(question, k=k, filters=filters)
    grade = grade_relevance(question, docs)
    if grade.relevant:
        return {
            "docs": docs,
            "query_used": question,
            "rewrote": False,
            "relevant": True,
            "reason": grade.reason,
        }

    new_query = rewrite_query(question)
    docs = retrieve(new_query, k=k, filters=filters)
    grade = grade_relevance(question, docs)
    return {
        "docs": docs if grade.relevant else [],
        "query_used": new_query,
        "rewrote": True,
        "relevant": grade.relevant,
        "reason": grade.reason,
    }