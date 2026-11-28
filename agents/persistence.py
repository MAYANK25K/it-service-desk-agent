import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver

from agents.config import CHECKPOINT_DB


def open_checkpointer(path=None) -> SqliteSaver:
    conn = sqlite3.connect(path or CHECKPOINT_DB, check_same_thread=False)
    saver = SqliteSaver(conn)
    saver.setup()
    return saver


def list_threads(checkpointer, graph, limit: int = 20) -> list[dict]:
    with checkpointer.lock:
        rows = checkpointer.conn.execute(
            "SELECT thread_id FROM checkpoints "
            "GROUP BY thread_id ORDER BY MAX(checkpoint_id) DESC LIMIT ?",
            (limit,),
        ).fetchall()

    threads = []
    for (thread_id,) in rows:
        state = graph.get_state({"configurable": {"thread_id": thread_id}})
        messages = state.values.get("messages", [])
        title = next((m.content for m in messages if m.type == "human"), "(no messages)")
        threads.append(
            {
                "thread_id": thread_id,
                "title": title if len(title) <= 60 else title[:57] + "...",
                "messages": len(messages),
                "awaiting_approval": "tool_executor" in state.next,
                "updated_at": state.created_at,
            }
        )
    return threads