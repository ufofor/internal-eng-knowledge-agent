# TMP-01: New Backend Service Template Checklist
owner_team: platform
version: 1.0
last_updated: 2025-03-05

## Must Have
- /healthz and /readyz
- Structured logs + trace propagation (STD-03)
- Auth aligned with STD-02
- Retry/timeouts aligned with STD-07
- Runbook created for common failures (RBK)

## Before Production
- SLOs and dashboards created
- On-call ownership confirmed
