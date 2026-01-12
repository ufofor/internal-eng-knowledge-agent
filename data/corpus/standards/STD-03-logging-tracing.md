# STD-03: Logging & Tracing Schema
status: approved
system: observability
owner_team: sre-observability
version: 1.3
last_updated: 2025-05-20

## Logging
- Structured JSON logs required.
- Required fields: timestamp, level, service, env, request_id, trace_id, span_id, user_id(optional), error_code(optional).

## Tracing
- OpenTelemetry spans for inbound requests and outbound calls.
- Propagate trace headers across service boundaries.
