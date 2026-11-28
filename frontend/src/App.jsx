import { useEffect, useState } from "react";
import { getHealth } from "./api.js";

export default function App() {
  const [status, setStatus] = useState({ state: "checking" });

  useEffect(() => {
    getHealth()
      .then((health) => setStatus({ state: "ok", model: health.model }))
      .catch(() => setStatus({ state: "down" }));
  }, []);

  return (
    <main style={{ fontFamily: "sans-serif", padding: 32 }}>
      <h1>IT Service Desk</h1>
      {status.state === "checking" && <p>Checking the backend…</p>}
      {status.state === "ok" && <p>Backend connected · model {status.model}</p>}
      {status.state === "down" && <p>Backend not reachable. Is uvicorn running on port 8000?</p>}
    </main>
  );
}