# STD-05: Secrets Management Rules
status: approved
system: platform
owner_team: security-platform
version: 1.1
last_updated: 2025-03-01

## Rules
- Secrets stored in Vault; retrieved at runtime via platform SDK.
- No secrets committed to repo or stored in plaintext config.
- Rotation required per policy; document exceptions in an ADR.
