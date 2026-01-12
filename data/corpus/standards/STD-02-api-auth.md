# STD-02: API Authentication & Service-to-Service Auth
status: approved
system: identity
owner_team: identity
version: 2.0
last_updated: 2025-02-10

## Standard
- External APIs: OAuth2/OIDC via auth gateway.
- Internal service-to-service: short-lived JWTs minted via identity service.
- No long-lived shared secrets in app configs.

## Requirements
- exp <= 15 minutes; validate issuer + audience.
- Never log raw tokens; log only metadata.
