import { ChatIcon, PlusIcon } from "./Icons.jsx";

export default function Rail({ onNewChat }) {
  return (
    <nav className="rail glass" aria-label="Main">
      <div className="logo" aria-hidden="true">SD</div>
      <button className="rail-btn" onClick={onNewChat} title="New chat" aria-label="New chat">
        <PlusIcon />
      </button>
      <button className="rail-btn active" title="Chats" aria-label="Chats" aria-current="page">
        <ChatIcon />
      </button>
      <div className="rail-spacer" />
      <div className="avatar" title="You">MK</div>
    </nav>
  );
}