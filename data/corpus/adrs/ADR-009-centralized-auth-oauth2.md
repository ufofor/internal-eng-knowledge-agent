# ADR-009: Centralized Authentication using OAuth2/OIDC
status: approved
system: identity
owner_team: identity
version: 2.0
last_updated: 2025-02-10
supersedes: ADR-006

## Context
Multiple services implemented custom auth with inconsistent token validation and key rotation handling.

## Decision
All external auth flows must use centralized OAuth2/OIDC via the auth gateway. Internal service-to-service uses short-lived tokens per STD-02.

## Rationale
Centralizing auth reduces implementation drift and improves security posture.

## Consequences
- Services must integrate token validation middleware from platform.
- Tokens must not be logged; follow STD-03 logging.
