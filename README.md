# IT Service Desk Agent

A local, stateful, multi-agent IT Service Desk assistant. It answers questions
from internal runbooks using RAG and performs operational actions (tickets,
server restarts, escalations) only after human approval.

**Status:** work in progress

## Planned stack

- Python, LangChain, LangGraph
- Ollama (local LLM and embeddings)
- ChromaDB (local vector store)
- FastAPI + React (web UI)