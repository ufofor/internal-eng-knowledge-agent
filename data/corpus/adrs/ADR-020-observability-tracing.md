# ADR-020: Distributed Tracing Standardization
status: approved
system: observability
owner_team: sre-observability
version: 1.0
last_updated: 2025-05-20
supersedes: none

## Decision
All services must propagate trace_id and span_id, emit OpenTelemetry traces, and include request_id in logs per STD-03.

## Rationale
Cross-service debugging requires consistent trace propagation.

## Consequences
Templates updated to include tracing middleware (TMP-01).
