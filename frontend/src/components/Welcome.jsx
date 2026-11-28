const ACTIONS = [
  { label: "Fix my VPN", prompt: "My VPN shows error 809. How do I fix it?" },
  { label: "Open a ticket", prompt: "Open a ticket: " },
  { label: "Restart a server", prompt: "Restart the server " },
  { label: "Escalate an incident", prompt: "Escalate incident " },
];

function greeting(hour) {
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

export default function Welcome({ onPick }) {
  return (
    <section className="stage">
      <div className="orb" aria-hidden="true" />
      <h1 className="greeting">{greeting(new Date().getHours())}</h1>
      <p className="greeting-sub">How can I help with IT today?</p>
      <div className="chips">
        {ACTIONS.map((action) => (
          <button key={action.label} className="chip" onClick={() => onPick(action.prompt)}>
            {action.label}
          </button>
        ))}
      </div>
    </section>
  );
}