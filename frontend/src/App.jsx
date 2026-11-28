import { useEffect, useMemo, useRef, useState } from "react";
import { getHealth, getThreads } from "./api.js";
import { groupThreads } from "./groupThreads.js";
import Rail from "./components/Rail.jsx";
import History from "./components/History.jsx";
import Welcome from "./components/Welcome.jsx";
import Composer from "./components/Composer.jsx";

function statusText(health) {
  if (health.state === "ok") return health.model;
  if (health.state === "down") return "Backend offline";
  return "Connecting…";
}

export default function App() {
  const [health, setHealth] = useState({ state: "checking" });
  const [threads, setThreads] = useState({ state: "loading", items: [] });
  const [activeId, setActiveId] = useState(null);
  const [draft, setDraft] = useState("");
  const inputRef = useRef(null);

  useEffect(() => {
    getHealth()
      .then((h) => setHealth({ state: "ok", model: h.model }))
      .catch(() => setHealth({ state: "down" }));
    getThreads()
      .then((items) => setThreads({ state: "ready", items }))
      .catch(() => setThreads({ state: "error", items: [] }));
  }, []);

  const groups = useMemo(() => groupThreads(threads.items), [threads.items]);

  function newChat() {
    setActiveId(null);
    setDraft("");
    inputRef.current?.focus();
  }

  function pickAction(prompt) {
    setDraft(prompt);
    inputRef.current?.focus();
  }

  return (
    <div className="shell">
      <Rail onNewChat={newChat} />
      <History state={threads.state} groups={groups} activeId={activeId} onSelect={setActiveId} />
      <main className="main glass">
        <header className="topbar">
          <span className="status">
            <span className={`dot ${health.state}`} />
            {statusText(health)}
          </span>
        </header>
        <Welcome onPick={pickAction} />
        <Composer value={draft} onChange={setDraft} inputRef={inputRef} />
      </main>
    </div>
  );
}