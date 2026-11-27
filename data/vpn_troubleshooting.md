# VPN Troubleshooting Guide

Document ID: KB-VPN-014 | Owner: Network Team | Version: 3.1

## 1. Overview

This guide helps the Service Desk diagnose employee VPN connection problems. The company VPN requires a valid account, a valid device certificate and multi-factor authentication (MFA).

## 2. Pre-Checks

1. Confirm the user has working internet access without the VPN.
2. Confirm the VPN client is the current approved version.
3. Confirm the user account is not locked (see POL-SEC-004).
4. Confirm the device clock is correct, because a wrong clock breaks certificates and MFA.

## 3. Common Error Codes

| Code | Meaning | First action |
|------|---------|--------------|
| 691 | Authentication failed | Check the password and whether the account is locked |
| 809 | Tunnel blocked by firewall or NAT | Ask the user to try a different network, then see Section 4.2 |
| 800 | Unable to establish the connection | Check the internet connection and restart the VPN client |
| VPN-ERR-4012 | Device certificate expired | Reissue the certificate through the endpoint portal |
| VPN-ERR-5003 | MFA approval timed out | Ask the user to retry and approve the prompt within 60 seconds |

## 4. Fix Procedures

### 4.1 Error 691
Reset the password only after verifying the user's identity as described in POL-SEC-004. Then ask the user to reconnect.

### 4.2 Error 809
Home routers often block the VPN ports. Ask the user to switch to a mobile hotspot. If it then works, advise the user to enable VPN passthrough on the home router.

### 4.3 Certificate errors
Run the certificate renewal from the endpoint portal and restart the client. A new certificate is valid for 365 days.

## 5. When to Escalate

If more than 20 users report VPN failures at the same time, treat it as a P1 incident under RUN-001 Section 2 and escalate to the network on-call engineer through the Escalation Matrix (POL-ESC-001).