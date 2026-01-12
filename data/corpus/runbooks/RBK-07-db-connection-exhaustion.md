# RBK-07: Database Connection Exhaustion
severity: P1
oncall_team: sre-database
escalation_policy: EP-DB-1
last_tested: 2025-03-20
related_services: core-db

## Symptoms
Spike in DB connection usage; requests queueing; timeouts.

## Actions
- Identify top connection consumers (service + query).
- Enforce pool limits; apply backpressure.
- Consider read replica shift if supported.
