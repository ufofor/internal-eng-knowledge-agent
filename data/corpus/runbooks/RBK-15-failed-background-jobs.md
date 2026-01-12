# RBK-15: Failed Background Jobs / DLQ Growth
severity: P1
oncall_team: sre-platform
escalation_policy: EP-PLATFORM-1
last_tested: 2025-02-15
related_services: queue, workers

## Symptoms
DLQ growth, backlog increases, job failure rates spike.

## Actions
- Identify failing job type and recent code changes.
- Pause consumers if failures are destructive.
- Reprocess with idempotency and retry budgets per STD-07.
