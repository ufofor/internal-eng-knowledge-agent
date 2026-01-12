# PM-2025-02: Login Failures After Config Rollout
system: identity
date: 2025-02-03
severity: P0
owner_team: identity
last_updated: 2025-02-20

## Summary
Login failures occurred after a config rollout that changed token validation audience settings.

## Root Cause
- Misconfigured audience validation rejected valid tokens.
- Canary coverage insufficient.

## Follow-ups
- RBK-19 updated for config regressions
- Added validation tests to deployment pipeline
