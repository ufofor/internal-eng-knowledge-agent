# PM-2024-09: Billing Outage Caused by Retry Storm
system: billing
date: 2024-09-12
severity: P0
owner_team: billing
last_updated: 2024-10-01

## Summary
Billing experienced cascading failures due to unbounded retries and high concurrency.

## Root Cause
- Client retried 5xx with no jitter and no retry budget.
- Dependency timeouts were misconfigured.

## Follow-ups
- STD-07 created for retry/timeouts
- ADR-014 adopted event-driven billing
