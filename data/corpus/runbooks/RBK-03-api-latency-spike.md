# RBK-03: API Latency Spike
severity: P1
oncall_team: sre-platform
escalation_policy: EP-PLATFORM-1
last_tested: 2025-04-10
related_services: api-gateway, edge-proxy

## Symptoms
p95 latency increased; error rate may be stable or rising.

## Triage
1) Check saturation (CPU/memory), connection pools, thread pools.
2) Inspect recent deploys/config changes.
3) Identify top endpoints via tracing (trace_id correlation).

## Mitigation
- Roll back offending deploy.
- Apply rate limiting at gateway.
- Reduce upstream timeouts temporarily if cascading.
