# STD-07: Retry & Timeout Standard
status: approved
system: platform
owner_team: sre-platform
version: 1.0
last_updated: 2024-10-01

## Policy
- Retries must be bounded (max attempts) and use jittered backoff.
- Do not retry non-idempotent operations unless protected by idempotency keys.
- Timeouts must be set per dependency; no infinite waits.

## Motivation
Created after PM-2024-09 retry storm.
