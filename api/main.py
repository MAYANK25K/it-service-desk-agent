import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agents.graph import build_graph
from agents.persistence import open_checkpointer
from api.routes import router

ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


def create_app(checkpointer=None, graph=None) -> FastAPI:
    """Build the API. Tests pass their own checkpointer and graph."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        saver = checkpointer or open_checkpointer()
        app.state.checkpointer = saver
        app.state.decision_lock = threading.Lock()
        app.state.graph = graph or build_graph(saver)
        yield

    app = FastAPI(title="IT Service Desk Agent API", version="0.6.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router, prefix="/api")
    return app


app = create_app()