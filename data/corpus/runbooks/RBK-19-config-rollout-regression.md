# RBK-19: Regression After Config Rollout
severity: P0
oncall_team: sre-platform
escalation_policy: EP-PLATFORM-1
last_tested: 2025-06-01
related_services: config-service

## Symptoms
Sharp increase in errors or latency correlated with config changes.

## Actions
- Identify rollout diff and affected services.
- Roll back config to last known good.
- Freeze further rollouts until root cause is isolated.
