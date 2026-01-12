# STD-06: Error Handling Conventions
status: approved
system: platform-api
owner_team: platform
version: 1.0
last_updated: 2024-11-10

## Rules
- Use stable error codes, not string matching.
- Client-visible messages must be safe and non-sensitive.
- Include request_id in all error responses.
