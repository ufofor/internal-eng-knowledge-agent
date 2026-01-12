# ADR-014: Event-driven Architecture for Billing Workflows
status: approved
system: billing
owner_team: billing
version: 1.1
last_updated: 2025-01-22
supersedes: none

## Context
Synchronous billing calls caused cascading failures and poor resilience during partial outages.

## Decision
Adopt async events for billing workflows:
- command API enqueues intents
- workers process with idempotency keys
- events stored with replay capability

## Rationale
Decoupling improves resilience and supports retries with budgets (STD-07). Prior incident PM-2024-09 showed retry storms can amplify failures.

## Consequences
- Requires event schema versioning
- Requires DLQ runbooks (RBK-15)
