flowchart TD
  U[User / Engineer] --> Q[Query: natural language]
  Q --> E[Embed query<br/>Sentence-Transformers]
  E --> F[FAISS Search<br/>Top-N candidates]
  F --> R[Policy Rerank<br/>metadata boosts/penalties]
  R --> D[Dedup by doc_id<br/>1 chunk per doc]
  D --> K[Doc-type quotas<br/>STD/ADR/RBK/PM/TMP]
  K --> O[Top-K chunks + citations metadata]
  O --> U
  
  flowchart LR
  A[make corpus] --> B[Markdown docs created<br/>data/corpus/**]
  B --> C[make validate<br/>schema & ID checks]
  C --> D[make index<br/>chunk + embed + FAISS]
  D --> E[make query / query_policy<br/>retrieval smoke test]
  
                  (Build time)                                  (Query time)
┌──────────────────────────────────────┐            ┌───────────────────────────────────┐
│ 1) Corpus (.md docs + metadata)      │            │ User question                     │
│    data/corpus/**                    │            └───────────────┬───────────────────┘
└───────────────┬──────────────────────┘                            │
                │                                                   ▼
                ▼                                       ┌───────────────────────────────┐
┌──────────────────────────────────────┐               │ Embed query (local model)      │
│ 2) Validate corpus (governance)      │               └───────────────┬───────────────┘
│    scripts/validate_metadata.py      │                               │
└───────────────┬──────────────────────┘                               ▼
                │                                       ┌───────────────────────────────┐
                ▼                                       │ FAISS similarity search        │
┌──────────────────────────────────────┐               │ (Top-N candidate chunks)       │
│ 3) Index build (chunk+embed+FAISS)   │               └───────────────┬───────────────┘
│    scripts/build_index.py            │                               │
│    outputs: faiss.index + chunks.jsonl                               ▼
└───────────────┬──────────────────────┘               ┌───────────────────────────────┐
                │                                       │ Policy rerank (metadata-aware)│
                │                                       │ + hard filters                │
                │                                       └───────────────┬───────────────┘
                │                                                       │
                │                                                       ▼
                │                                       ┌───────────────────────────────┐
                │                                       │ Dedup + doc-type quotas        │
                │                                       └───────────────┬───────────────┘
                │                                                       │
                └───────────────────────────────────────────────────────▼
                                                        ┌───────────────────────────────┐
                                                        │ Top-K chunks + citations       │
                                                        └───────────────────────────────┘
                                                        
                                                        # Internal Engineering Knowledge Agent (Portfolio Project)

A synthetic-but-realistic **Internal Engineering Knowledge Agent** for a SaaS platform.
This repo focuses on **governed knowledge retrieval**: standards, runbooks, ADRs, and incident learnings.

**This is a decision-support system, not a decision-maker.**
It never invents policies; it retrieves approved internal docs and cites sources.

---

## What’s included (Part A)

✅ Corpus generator (20 starter docs)  
✅ Metadata validator (governance checks)  
✅ Local vector index builder (Sentence-Transformers + FAISS)  
✅ Retrieval smoke tests:
- pure semantic search
- **metadata-aware rerank** (prefer standards, approved, fresh, relevant system)
- optional **dedup + doc-type quotas** (production-ish results)

---

## Repository structure

```text
internal-eng-knowledge-agent/
├── Makefile
├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── data/
│   ├── corpus/
│   │   ├── adrs/
│   │   ├── standards/
│   │   ├── runbooks/
│   │   ├── postmortems/
│   │   └── templates/
│   └── indexes/
│       ├── faiss.index
│       └── chunks.jsonl
└── scripts/
    ├── make_corpus.py
    ├── validate_metadata.py
    ├── build_index.py
    ├── query_index.py
    └── query_index_policy.py