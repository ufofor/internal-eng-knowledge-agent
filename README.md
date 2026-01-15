# Internal Engineering Knowledge Agent

A **governed internal engineering knowledge retrieval system** (portfolio project) that helps engineers and SREs find approved internal guidance such as:

- Architecture Decision Records (ADRs)
- Engineering standards & guardrails
- SRE runbooks
- Incident postmortems
- Service templates & checklists

> This system is **decision-support**, not a decision-maker.  
> It retrieves and cites documents; it does not invent standards.

---

## Why this project

Engineering orgs often struggle with:
- duplicated questions to senior engineers
- outdated or inconsistent standards
- slow incident response due to missing runbooks
- hard-to-find rationale behind past architecture decisions

This project demonstrates:
- **metadata governance** (validation before indexing)
- **local vector retrieval** (FAISS)
- **policy-aware reranking** (prefer authoritative + fresh docs)
- **reproducible workflows** (Make targets)

---

## High-level architecture

### Query-time flow

```mermaid
flowchart TD
  U[Engineer / User] --> Q[Natural language query]
  Q --> E[Embed query<br/>Sentence-Transformers]
  E --> F[FAISS vector search<br/>Top-N chunks]
  F --> R[Policy rerank<br/>metadata boosts & penalties]
  R --> D[Dedup by document ID<br/>1 chunk per document]
  D --> K[Doc-type quotas<br/>STD / ADR / RBK / PM / TMP]
  K --> O[Top-K results<br/>with citations]
  O --> U
  
  ## Run locally (API + UI)

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001