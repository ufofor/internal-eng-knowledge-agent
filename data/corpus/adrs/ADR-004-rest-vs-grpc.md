# ADR-004: REST vs gRPC for Internal APIs
status: approved
system: platform-api
owner_team: platform
version: 1.2
last_updated: 2025-04-18
supersedes: ADR-002

## Context
Internal APIs require strong contracts and safe evolution. Prior incidents showed brittle clients and inconsistent schemas.

## Decision
- Use gRPC for internal service-to-service APIs requiring typed contracts or streaming.
- Use REST for public/external APIs and high client diversity.

## Rationale
gRPC enables protobuf schemas, codegen, and strict compatibility practices.

## Consequences
- protobuf lint + CI breaking-change checks required.
- API gateway provides REST translation where needed.
