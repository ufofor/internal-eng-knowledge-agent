# ADR-017: Secrets Management with KMS + Vault
status: approved
system: platform
owner_team: security-platform
version: 1.0
last_updated: 2025-03-01
supersedes: none

## Decision
All secrets must be stored in Vault and rotated via KMS-backed workflows. No long-lived secrets in env vars beyond short-lived runtime tokens.

## Rationale
Reduces exposure and improves rotation compliance.

## Consequences
Services must use platform secret SDK and follow STD-05.
