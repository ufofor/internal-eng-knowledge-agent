from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple


@dataclass(frozen=True)
class Doc:
    """
    Represents one knowledge-base document.

    We keep:
    - rel_path: where to write it relative to repo root
    - content: markdown text
    """
    rel_path: str
    content: str


def build_docs() -> Dict[str, Doc]:
    """
    Returns a dictionary of all documents to generate.

    Key is a stable doc id for debugging/logging.
    """
    docs: Dict[str, Doc] = {}

    # -------------------------
    # ADRs (6)
    # -------------------------
    docs["ADR-001"] = Doc(
        rel_path="data/corpus/adrs/ADR-001-monolith-to-microservices.md",
        content="""# ADR-001: Monolith → Microservices Migration
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
""",
    )

    docs["ADR-004"] = Doc(
        rel_path="data/corpus/adrs/ADR-004-rest-vs-grpc.md",
        content="""# ADR-004: REST vs gRPC for Internal APIs
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
""",
    )

    docs["ADR-009"] = Doc(
        rel_path="data/corpus/adrs/ADR-009-centralized-auth-oauth2.md",
        content="""# ADR-009: Centralized Authentication using OAuth2/OIDC
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
""",
    )

    docs["ADR-014"] = Doc(
        rel_path="data/corpus/adrs/ADR-014-event-driven-billing.md",
        content="""# ADR-014: Event-driven Architecture for Billing Workflows
status: approved
system: billing
owner_team: billing
version: 1.1
last_updated: 2025-01-22
supersedes: none

## Context
Synchronous billing calls caused cascading failures and poor resilience during partial outages.

## Decision
Adopt async events for billing workflows:
- command API enqueues intents
- workers process with idempotency keys
- events stored with replay capability

## Rationale
Decoupling improves resilience and supports retries with budgets (STD-07). Prior incident PM-2024-09 showed retry storms can amplify failures.

## Consequences
- Requires event schema versioning
- Requires DLQ runbooks (RBK-15)
""",
    )

    docs["ADR-017"] = Doc(
        rel_path="data/corpus/adrs/ADR-017-secrets-management.md",
        content="""# ADR-017: Secrets Management with KMS + Vault
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
""",
    )

    docs["ADR-020"] = Doc(
        rel_path="data/corpus/adrs/ADR-020-observability-tracing.md",
        content="""# ADR-020: Distributed Tracing Standardization
status: approved
system: observability
owner_team: sre-observability
version: 1.0
last_updated: 2025-05-20
supersedes: none

## Decision
All services must propagate trace_id and span_id, emit OpenTelemetry traces, and include request_id in logs per STD-03.

## Rationale
Cross-service debugging requires consistent trace propagation.

## Consequences
Templates updated to include tracing middleware (TMP-01).
""",
    )

    # -------------------------
    # Standards (6)
    # -------------------------
    docs["STD-02"] = Doc(
        rel_path="data/corpus/standards/STD-02-api-auth.md",
        content="""# STD-02: API Authentication & Service-to-Service Auth
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
""",
    )

    docs["STD-03"] = Doc(
        rel_path="data/corpus/standards/STD-03-logging-tracing.md",
        content="""# STD-03: Logging & Tracing Schema
status: approved
system: observability
owner_team: sre-observability
version: 1.3
last_updated: 2025-05-20

## Logging
- Structured JSON logs required.
- Required fields: timestamp, level, service, env, request_id, trace_id, span_id, user_id(optional), error_code(optional).

## Tracing
- OpenTelemetry spans for inbound requests and outbound calls.
- Propagate trace headers across service boundaries.
""",
    )

    docs["STD-05"] = Doc(
        rel_path="data/corpus/standards/STD-05-secrets.md",
        content="""# STD-05: Secrets Management Rules
status: approved
system: platform
owner_team: security-platform
version: 1.1
last_updated: 2025-03-01

## Rules
- Secrets stored in Vault; retrieved at runtime via platform SDK.
- No secrets committed to repo or stored in plaintext config.
- Rotation required per policy; document exceptions in an ADR.
""",
    )

    docs["STD-06"] = Doc(
        rel_path="data/corpus/standards/STD-06-error-handling.md",
        content="""# STD-06: Error Handling Conventions
status: approved
system: platform-api
owner_team: platform
version: 1.0
last_updated: 2024-11-10

## Rules
- Use stable error codes, not string matching.
- Client-visible messages must be safe and non-sensitive.
- Include request_id in all error responses.
""",
    )

    docs["STD-07"] = Doc(
        rel_path="data/corpus/standards/STD-07-retries-timeouts.md",
        content="""# STD-07: Retry & Timeout Standard
status: approved
system: platform
owner_team: sre-platform
version: 1.0
last_updated: 2024-10-01

## Policy
- Retries must be bounded (max attempts) and use jittered backoff.
- Do not retry non-idempotent operations unless protected by idempotency keys.
- Timeouts must be set per dependency; no infinite waits.

## Motivation
Created after PM-2024-09 retry storm.
""",
    )

    docs["STD-09"] = Doc(
        rel_path="data/corpus/standards/STD-09-backward-compat.md",
        content="""# STD-09: Backward Compatibility Requirements
status: approved
system: platform-api
owner_team: platform
version: 1.0
last_updated: 2025-01-05

## Requirements
- Additive changes preferred; breaking changes require version bump + migration plan.
- For protobuf: follow reserved fields and avoid renumbering.
""",
    )

    # -------------------------
    # Runbooks (5)
    # -------------------------
    docs["RBK-03"] = Doc(
        rel_path="data/corpus/runbooks/RBK-03-api-latency-spike.md",
        content="""# RBK-03: API Latency Spike
severity: P1
oncall_team: sre-platform
escalation_policy: EP-PLATFORM-1
last_tested: 2025-04-10
related_services: api-gateway, edge-proxy

## Symptoms
p95 latency increased; error rate may be stable or rising.

## Triage
1) Check saturation (CPU/memory), connection pools, thread pools.
2) Inspect recent deploys/config changes.
3) Identify top endpoints via tracing (trace_id correlation).

## Mitigation
- Roll back offending deploy.
- Apply rate limiting at gateway.
- Reduce upstream timeouts temporarily if cascading.
""",
    )

    docs["RBK-07"] = Doc(
        rel_path="data/corpus/runbooks/RBK-07-db-connection-exhaustion.md",
        content="""# RBK-07: Database Connection Exhaustion
severity: P1
oncall_team: sre-database
escalation_policy: EP-DB-1
last_tested: 2025-03-20
related_services: core-db

## Symptoms
Spike in DB connection usage; requests queueing; timeouts.

## Actions
- Identify top connection consumers (service + query).
- Enforce pool limits; apply backpressure.
- Consider read replica shift if supported.
""",
    )

    docs["RBK-11"] = Doc(
        rel_path="data/corpus/runbooks/RBK-11-auth-outage.md",
        content="""# RBK-11: Authentication Outage
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
""",
    )

    docs["RBK-15"] = Doc(
        rel_path="data/corpus/runbooks/RBK-15-failed-background-jobs.md",
        content="""# RBK-15: Failed Background Jobs / DLQ Growth
severity: P1
oncall_team: sre-platform
escalation_policy: EP-PLATFORM-1
last_tested: 2025-02-15
related_services: queue, workers

## Symptoms
DLQ growth, backlog increases, job failure rates spike.

## Actions
- Identify failing job type and recent code changes.
- Pause consumers if failures are destructive.
- Reprocess with idempotency and retry budgets per STD-07.
""",
    )

    docs["RBK-19"] = Doc(
        rel_path="data/corpus/runbooks/RBK-19-config-rollout-regression.md",
        content="""# RBK-19: Regression After Config Rollout
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
""",
    )

    # -------------------------
    # Postmortems (2)
    # -------------------------
    docs["PM-2024-09"] = Doc(
        rel_path="data/corpus/postmortems/PM-2024-09-billing-retry-storm.md",
        content="""# PM-2024-09: Billing Outage Caused by Retry Storm
system: billing
date: 2024-09-12
severity: P0
owner_team: billing
last_updated: 2024-10-01

## Summary
Billing experienced cascading failures due to unbounded retries and high concurrency.

## Root Cause
- Client retried 5xx with no jitter and no retry budget.
- Dependency timeouts were misconfigured.

## Follow-ups
- STD-07 created for retry/timeouts
- ADR-014 adopted event-driven billing
""",
    )

    docs["PM-2025-02"] = Doc(
        rel_path="data/corpus/postmortems/PM-2025-02-login-failures-config-rollout.md",
        content="""# PM-2025-02: Login Failures After Config Rollout
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
""",
    )

    # -------------------------
    # Templates (1)
    # -------------------------
    docs["TMP-01"] = Doc(
        rel_path="data/corpus/templates/TMP-01-new-service-checklist.md",
        content="""# TMP-01: New Backend Service Template Checklist
owner_team: platform
version: 1.0
last_updated: 2025-03-05

## Must Have
- /healthz and /readyz
- Structured logs + trace propagation (STD-03)
- Auth aligned with STD-02
- Retry/timeouts aligned with STD-07
- Runbook created for common failures (RBK)

## Before Production
- SLOs and dashboards created
- On-call ownership confirmed
""",
    )

    return docs


def ensure_dirs(repo_root: Path) -> None:
    """
    Create the required directory structure if it doesn't exist.
    """
    dirs = [
        repo_root / "data" / "corpus" / "adrs",
        repo_root / "data" / "corpus" / "standards",
        repo_root / "data" / "corpus" / "runbooks",
        repo_root / "data" / "corpus" / "postmortems",
        repo_root / "data" / "corpus" / "templates",
        repo_root / "data" / "indexes",
        repo_root / "scripts",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


def write_docs(repo_root: Path, docs: Dict[str, Doc], overwrite: bool = False) -> Tuple[int, int]:
    """
    Write all docs to disk.

    overwrite=False is safer for portfolio work: it prevents accidentally wiping edits.
    Returns (written_count, skipped_count).
    """
    written = 0
    skipped = 0

    for doc_id, doc in docs.items():
        out_path = repo_root / doc.rel_path
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if out_path.exists() and not overwrite:
            skipped += 1
            continue

        out_path.write_text(doc.content, encoding="utf-8")
        written += 1

    return written, skipped


def main() -> None:
    """
    Entry point:
    - ensures folder structure exists
    - writes the starter corpus markdown docs
    """
    repo_root = Path(__file__).resolve().parents[1]  # scripts/ -> repo root
    ensure_dirs(repo_root)

    docs = build_docs()
    written, skipped = write_docs(repo_root, docs, overwrite=False)

    print(f"✅ Repo root: {repo_root}")
    print(f"✅ Documents total: {len(docs)}")
    print(f"✅ Written: {written}")
    print(f"⚠️  Skipped (already existed): {skipped}")
    print("\nNext: open 'data/corpus/' and review documents.")


if __name__ == "__main__":
    main()
