import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from typing import Literal, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from agents.config import OPS_DB

TICKET_ID_PATTERN = r"^INC-\d{4,}$"

SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    priority TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS restarts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    server_name TEXT NOT NULL,
    environment TEXT NOT NULL,
    reason TEXT NOT NULL,
    ticket_id TEXT,
    status TEXT NOT NULL DEFAULT 'queued',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS escalations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id TEXT NOT NULL,
    level TEXT NOT NULL,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


class CreateTicketArgs(BaseModel):
    title: str = Field(min_length=5, max_length=120, description="Short ticket title.")
    description: str = Field(min_length=10, description="What is wrong and what is needed.")
    priority: Literal["P1", "P2", "P3", "P4"]


class RestartServerArgs(BaseModel):
    server_name: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{1,62}$")
    environment: Literal["production", "non-production"]
    reason: str = Field(min_length=5)
    ticket_id: Optional[str] = Field(default=None, pattern=TICKET_ID_PATTERN)


class EscalateIncidentArgs(BaseModel):
    ticket_id: str = Field(pattern=TICKET_ID_PATTERN)
    level: Literal["L2", "L3", "L4"]
    reason: str = Field(min_length=5)


def _connect() -> sqlite3.Connection:
    OPS_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(OPS_DB)
    conn.executescript(SCHEMA)
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ticket_exists(ticket_id: str) -> bool:
    row_id = int(ticket_id.split("-")[1])
    with closing(_connect()) as conn:
        row = conn.execute("SELECT 1 FROM tickets WHERE id = ?", (row_id,)).fetchone()
    return row is not None


@tool(args_schema=CreateTicketArgs)
def create_ticket(title: str, description: str, priority: str) -> str:
    """Open a new IT support ticket with a title, description and priority (P1 to P4)."""
    with closing(_connect()) as conn, conn:
        cursor = conn.execute(
            "INSERT INTO tickets (title, description, priority, created_at) VALUES (?, ?, ?, ?)",
            (title, description, priority, _now()),
        )
        ticket_id = f"INC-{cursor.lastrowid:04d}"
    return f"Ticket {ticket_id} created with priority {priority}: {title}"


@tool(args_schema=RestartServerArgs)
def restart_server(
    server_name: str, environment: str, reason: str, ticket_id: Optional[str] = None
) -> str:
    """Queue a restart of a server."""
    with closing(_connect()) as conn, conn:
        cursor = conn.execute(
            "INSERT INTO restarts (server_name, environment, reason, ticket_id, created_at) VALUES (?, ?, ?, ?, ?)",
            (server_name, environment, reason, ticket_id, _now()),
        )
        reference = f"RST-{cursor.lastrowid:04d}"
    return f"Restart of {server_name} ({environment}) queued as {reference}."


@tool(args_schema=EscalateIncidentArgs)
def escalate_incident(ticket_id: str, level: str, reason: str) -> str:
    """Escalate an existing incident ticket to a higher support level (L2, L3 or L4)."""
    with closing(_connect()) as conn, conn:
        cursor = conn.execute(
            "INSERT INTO escalations (ticket_id, level, reason, created_at) VALUES (?, ?, ?, ?)",
            (ticket_id, level, reason, _now()),
        )
        reference = f"ESC-{cursor.lastrowid:04d}"
    return f"Incident {ticket_id} escalated to {level} ({reference})."


TOOLS = {
    "create_ticket": create_ticket,
    "restart_server": restart_server,
    "escalate_incident": escalate_incident,
}

ARG_MODELS = {
    "create_ticket": CreateTicketArgs,
    "restart_server": RestartServerArgs,
    "escalate_incident": EscalateIncidentArgs,
}


def validate_action(tool_name: str, args: dict) -> dict:
    model = ARG_MODELS.get(tool_name)
    if model is None:
        raise ValueError(f"Unknown tool: {tool_name}")
    validated = model(**args).model_dump(exclude_none=True)
    ticket_id = validated.get("ticket_id")
    if ticket_id and not ticket_exists(ticket_id):
        raise ValueError(f"Ticket {ticket_id} does not exist.")
    return validated


def assess_impact(tool_name: str, args: dict) -> dict:
    if tool_name == "create_ticket":
        return {
            "risk": "low",
            "summary": f"Creates a new {args['priority']} ticket titled '{args['title']}' in the service desk queue.",
        }
    if tool_name == "restart_server":
        if args["environment"] == "production":
            return {
                "risk": "high",
                "summary": (
                    f"Restarts PRODUCTION server {args['server_name']} and drops active user sessions. "
                    "SOP-SRV-007 allows production restarts only in the Saturday 22:00 to Sunday 02:00 IST "
                    "window, or as an approved P1 emergency."
                ),
            }
        return {
            "risk": "medium",
            "summary": f"Restarts non-production server {args['server_name']}; users of that environment lose their sessions.",
        }
    if tool_name == "escalate_incident":
        risk = "medium" if args["level"] == "L2" else "high"
        return {
            "risk": risk,
            "summary": f"Escalates {args['ticket_id']} to {args['level']} and notifies that support level.",
        }
    return {"risk": "high", "summary": "Unknown action."}