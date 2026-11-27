# Server Restart Standard Operating Procedure

Document ID: SOP-SRV-007 | Owner: Infrastructure Team | Version: 2.0

## 1. Purpose

This SOP defines how servers are restarted safely so that restarts do not cause avoidable outages or data loss.

## 2. Approval Requirements

- Every restart of a production server requires explicit human approval before it runs.
- Non-production servers may be approved by a Level 2 engineer.
- The request must include: server name, reason for the restart, linked ticket ID and the name of the requester.

## 3. Maintenance Windows

- Production restarts are allowed only during the weekly window: Saturday 22:00 to Sunday 02:00 IST.
- Emergency restarts outside the window are allowed only for P1 incidents and need approval from the on-call manager.
- Non-production servers can be restarted at any time during business hours.

## 4. Pre-Restart Checklist

1. Confirm a recent backup or VM snapshot exists.
2. Check the number of active user sessions and notify affected users.
3. Confirm no deployment or batch job is running on the server.
4. Record the current service status so it can be compared afterwards.

## 5. Restart Procedure

1. Stop application services gracefully and wait for them to exit.
2. Restart the server using the approved console or command.
3. Wait for the server to come back and start dependent services in order: database, application, web.

## 6. Post-Restart Verification

Run the service health checks and confirm that all services show healthy. Check the logs for errors during the first 15 minutes and update the ticket with the result.

## 7. Rollback

If services do not recover within 20 minutes, restore the VM snapshot taken in the pre-restart checklist and escalate to Level 3 through the Escalation Matrix (POL-ESC-001).