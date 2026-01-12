# RBK-11: Authentication Outage
severity: P0
oncall_team: sre-identity
escalation_policy: EP-IDENTITY-1
last_tested: 2025-05-01
related_services: identity-service, auth-gateway

## Symptoms
Elevated 401/403 across services; token validation errors; login failures.

## Immediate Actions
1) Check dashboards: 401 rate, token mint rate, p95 latency.
2) Check recent deploys/config rollouts.
3) Validate KMS/key rotation events.

## Mitigations
- Roll back last config if correlated.
- Enable key verification grace window if supported.
- Apply circuit breakers to reduce token mint pressure.
