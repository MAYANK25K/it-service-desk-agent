from agents.config import RETRIEVAL_TOP_K
from agents.retriever import retrieve

SEARCH_DEPTH = 20

CASES = [
    ("How long until a P1 ticket gets a response?", "sla_policy.md", {"3"}),
    ("What is the resolution target for a P2 ticket?", "sla_policy.md", {"3"}),
    ("What does VPN error 809 mean?", "vpn_troubleshooting.md", {"3", "4.2"}),
    ("How long is a VPN certificate valid?", "vpn_troubleshooting.md", {"4.3"}),
    ("When can production servers be restarted?", "server_restart_sop.md", {"3"}),
    ("Who must approve a production server restart?", "server_restart_sop.md", {"2"}),
    ("How many failed logins lock an account?", "access_management_policy.md", {"4"}),
    ("What is the minimum password length?", "access_management_policy.md", {"2"}),
    ("Who gets notified if a P1 has no progress after 30 minutes?", "escalation_matrix.md", {"3"}),
    ("How often must stakeholders get P1 updates?", "incident_runbook.md", {"4"}),
]


def find_rank(question: str, source: str, refs: set[str]):
    results = retrieve(question, k=SEARCH_DEPTH)
    for rank, result in enumerate(results, start=1):
        if result["source"] == source and result["section_ref"] in refs:
            return rank
    return None


def main() -> None:
    passed = 0
    for question, source, refs in CASES:
        rank = find_rank(question, source, refs)
        ok = rank is not None and rank <= RETRIEVAL_TOP_K
        passed += ok
        shown = rank if rank else f">{SEARCH_DEPTH}"
        print(f"{'PASS' if ok else 'FAIL'}  rank={shown:<4} {question}")
    print(f"\nPassed {passed}/{len(CASES)} at top-{RETRIEVAL_TOP_K}")


if __name__ == "__main__":
    main()