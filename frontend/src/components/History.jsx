export default function History({ state, groups, activeId, onSelect }) {
  return (
    <aside className="history glass" aria-label="Conversations">
      <h2>Chats</h2>
      <p className="sub">Your IT Service Desk conversations</p>

      <div className="history-scroll">
        {state === "loading" && <p className="note">Loading conversations…</p>}
        {state === "error" && <p className="note">Could not load conversations.</p>}
        {state === "ready" && groups.length === 0 && (
          <p className="note">No conversations yet. Ask something to start one.</p>
        )}

        {groups.map((group) => (
          <section key={group.label}>
            <h3 className="group-label">{group.label}</h3>
            {group.threads.map((thread) => (
              <button
                key={thread.thread_id}
                className={`thread-card${thread.thread_id === activeId ? " active" : ""}`}
                onClick={() => onSelect(thread.thread_id)}
              >
                <span className="thread-title">{thread.title || "Untitled conversation"}</span>
                <span className="thread-meta">
                  {thread.messages} messages
                  {thread.awaiting_approval && <span className="badge">Needs approval</span>}
                </span>
              </button>
            ))}
          </section>
        ))}
      </div>
    </aside>
  );
}