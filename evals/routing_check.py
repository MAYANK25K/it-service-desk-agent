from langchain_core.messages import AIMessage, HumanMessage

from agents.supervisor import classify_intent

P1_TARGET = [
    ("user", "What is the P1 resolution target?"),
    ("ai", "The P1 resolution target is 4 hours. [Source: sla_policy.md, Section 3]"),
]
P1_RESPONSE = [
    ("user", "What is the P1 response time?"),
    ("ai", "A P1 ticket gets a first response within 15 minutes. [Source: sla_policy.md, Section 3]"),
]
VPN_809 = [
    ("user", "How do I fix VPN error 809?"),
    ("ai", "Ask the user to try a different network. [Source: vpn_troubleshooting.md, Section 4.2]"),
]

CASES = [
    ([], "Hello there", "general"),
    ([], "Thanks, that helps a lot", "general"),
    ([], "What is the P1 response time?", "rag"),
    ([], "What does VPN error 809 mean?", "rag"),
    ([], "How do I restart a production server?", "rag"),
    ([], "Who must approve a server restart?", "rag"),
    ([], "Open a high-priority ticket for the VPN outage", "action"),
    ([], "Please restart server APP-02", "action"),
    ([], "Escalate this incident to level 2", "action"),
    (P1_TARGET, "Go ahead and open a high-priority ticket for that", "action"),
    (P1_RESPONSE, "What did I just ask you?", "general"),
    (VPN_809, "And what about error 691?", "rag"),
]


def build_messages(history: list[tuple[str, str]], text: str) -> list:
    messages = [
        HumanMessage(content=content) if role == "user" else AIMessage(content=content)
        for role, content in history
    ]
    messages.append(HumanMessage(content=text))
    return messages


def main() -> None:
    passed = 0
    for history, text, expected in CASES:
        decision = classify_intent(build_messages(history, text))
        ok = decision.intent == expected
        passed += ok
        print(f"{'PASS' if ok else 'FAIL'}  expected={expected:<8} got={decision.intent:<8} {text}")
    print(f"\nPassed {passed}/{len(CASES)}")


if __name__ == "__main__":
    main()