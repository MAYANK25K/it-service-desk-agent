import tempfile
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage

from agents import tools
from agents.action_planner import PLACEHOLDER_PATTERN, prepare_action

VPN_DOCS = [
    {
        "content": "[VPN Troubleshooting Guide | KB-VPN-014 | Error 809]\nError 809 means the VPN connection could not be established, usually because a firewall is blocking the VPN ports.",
        "source": "vpn_troubleshooting.md",
        "section_ref": "3",
    }
]
VPN_HISTORY = [
    HumanMessage(content="I get VPN error 809, how do I fix it?"),
    AIMessage(
        content="Error 809 usually means a firewall is blocking the VPN ports. [Source: vpn_troubleshooting.md, Section 3]"
    ),
]

# (message, history, docs, expected tool or None, expected args, word the text must mention)
CASES = [
    ("Open a high-priority ticket for the VPN outage", [], [], "create_ticket", {"priority": "P2"}, "vpn"),
    ("Open a critical ticket: email is down for everyone", [], [], "create_ticket", {"priority": "P1"}, "email"),
    (
        "That didn't work. Go ahead and open a high-priority ticket for that",
        VPN_HISTORY, VPN_DOCS, "create_ticket", {"priority": "P2"}, "vpn",
    ),
    (
        "Restart server APP-02 in production because the service is hung",
        [], [], "restart_server",
        {"server_name": "APP-02", "environment": "production"}, "hung",
    ),
    (
        "Escalate INC-0001 to level 3 because there is no progress",
        [], [], "escalate_incident",
        {"ticket_id": "INC-0001", "level": "L3"}, "progress",
    ),
    ("Please restart the server", [], [], None, {}, None),
    ("Escalate this incident to level 2", [], [], None, {}, None),
]


def main() -> None:
    tools.OPS_DB = Path(tempfile.mkdtemp()) / "action_check.db"
    tools.create_ticket.invoke(
        {"title": "Seed ticket", "description": "Seed ticket for the action check", "priority": "P3"}
    )

    passed = 0
    for text, history, docs, expected_tool, expected_args, mention in CASES:
        result = prepare_action([*history, HumanMessage(content=text)], docs)
        if expected_tool is None:
            ok = "question" in result
            detail = result.get("question", "unexpected action prepared")
        else:
            action = result.get("action")
            ok = bool(action) and action["tool_name"] == expected_tool and all(
                action["args"].get(k) == v for k, v in expected_args.items()
            )
            detail = action["args"] if action else result.get("question")
            if ok:
                blob = " ".join(str(v) for v in action["args"].values())
                ok = mention.lower() in blob.lower() and not PLACEHOLDER_PATTERN.search(blob)
        passed += ok
        print(f"{'PASS' if ok else 'FAIL'}  {text}\n      -> {detail}")
    print(f"\nPassed {passed}/{len(CASES)}")


if __name__ == "__main__":
    main()