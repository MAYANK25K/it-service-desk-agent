# IT Incident Response Runbook

Document ID: RUN-001 | Owner: IT Service Desk | Version: 2.3

## 1. Purpose and Scope

This runbook defines how the IT Service Desk detects, triages, communicates and resolves incidents affecting company systems. It applies to all employees, contractors and managed services.

## 2. Incident Severity Levels

- **P1 - Critical:** A business-critical service is fully down (email, ERP, payments, company-wide VPN) or a security breach affects production systems.
- **P2 - High:** A major service is degraded, or a whole department is unable to work.
- **P3 - Medium:** One user or a small team is affected and a workaround exists.
- **P4 - Low:** General questions, cosmetic issues and service requests.

## 3. First Response Checklist

1. Acknowledge the ticket and assign a severity level.
2. Confirm the scope: how many users and which services are affected.
3. Check the status dashboard and any changes made in the last 24 hours.
4. For P1 and P2, open an incident bridge call and name an incident commander.
5. Post the first update in the #it-incidents channel.

## 4. Communication During an Incident

- P1: update stakeholders every 30 minutes until resolved.
- P2: update stakeholders every 2 hours.
- P3 and P4: update the requester when status changes.
- Every update must state: current impact, actions taken, next steps and the time of the next update.

## 5. Common Incident Types

### 5.1 Email outage
Check the mail gateway queue on MAIL-GW-01. If the queue is above 5,000 messages, restart the mail relay service (this requires approval under SOP-SRV-007) and raise a P1.

### 5.2 Slow network
Check switch uplink utilisation. Utilisation above 85 percent for 10 minutes means you must notify the network team and raise a P2.

### 5.3 Application login failures
Confirm whether the identity provider is healthy. If many users fail at once, treat it as a P1. If one user fails, follow the account lockout steps in POL-SEC-004.

## 6. Resolution and Closure

Confirm the fix with the requester, record the root cause and the fix in the ticket, then close the ticket. Tickets are auto-closed after 3 days without a requester response.

## 7. Post-Incident Review

A written post-incident review is mandatory for every P1 within 3 business days. It must contain a timeline, root cause, customer impact and follow-up actions with owners.