# IT Escalation Matrix

Document ID: POL-ESC-001 | Owner: IT Operations | Version: 1.2

## 1. Purpose

This document defines who must be contacted, and when, if an incident cannot be resolved at the current support level.

## 2. Escalation Levels

- **Level 1 - Service Desk:** First contact, triage, known-issue fixes and ticket handling.
- **Level 2 - Systems and Network Engineers:** Server, network and application troubleshooting.
- **Level 3 - Infrastructure Lead and vendors:** Architecture-level problems, vendor support cases and major outages.
- **Level 4 - IT Director:** Business-wide impact, major security events and executive communication.

## 3. Time-Based Escalation Triggers for P1 Incidents

- No progress after 30 minutes: escalate to Level 2.
- No resolution after 60 minutes: escalate to Level 3.
- No resolution after 2 hours: notify the IT Director and the Security Officer.

For P2 incidents, move up one level for every 4 hours without progress.

## 4. On-Call Contacts

| Role | Contact channel |
|------|-----------------|
| L2 Systems on-call | Pager rotation SYS-ONCALL, extension 4410 |
| L2 Network on-call | Pager rotation NET-ONCALL, extension 4420 |
| Infrastructure Lead | infra-lead@example.com |
| IT Director | it-director@example.com |

## 5. Security Incidents

Any suspected security incident, such as malware, phishing compromise or data exposure, must go to Security Operations immediately, whatever the ticket priority. Do not wait for the normal escalation timers.

## 6. Vendor Escalation

Open a vendor support case only after Level 3 approval. Record the vendor case number in the ticket and review its status every 2 hours for P1 incidents.