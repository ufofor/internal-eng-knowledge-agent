# ADR-001: Monolith → Microservices Migration
status: approved
system: platform
owner_team: platform
version: 1.0
last_updated: 2024-08-12
supersedes: none

## Context
The monolith has reached a scaling ceiling (deploy risk, coupled releases, shared DB contention). Teams need independent deployability.

## Decision
Adopt a domain-aligned microservices architecture with:
- clear bounded contexts
- per-service data ownership (no cross-service writes)
- platform-provided templates (TMP-01) and observability standards (STD-03)

## Rationale
Independent deploys reduce blast radius and improve throughput. Domain boundaries reduce coupling.

## Consequences
- Requires service ownership, SLOs, and runbooks per service.
- Increased operational complexity; mitigated by templates and SRE standards.
