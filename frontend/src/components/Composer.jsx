import { SendIcon } from "./Icons.jsx";

export default function Composer({ value, onChange, inputRef }) {
  return (
    <form className="composer" onSubmit={(event) => event.preventDefault()}>
      <input
        ref={inputRef}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Ask me anything…"
        aria-label="Message"
      />
      <button className="send" type="submit" disabled title="Sending arrives in the next step" aria-label="Send">
        <SendIcon />
      </button>
    </form>
  );
}