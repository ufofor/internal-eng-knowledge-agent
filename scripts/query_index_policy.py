from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

def run_policy_query(query: str, top_k: int = 5, candidates: int = 20) -> list[dict]:
    """
    Programmatic API for policy-aware retrieval.
    Used by both CLI (main) and evaluation harness.
    """

    if not FAISS_INDEX_PATH.exists():
        raise FileNotFoundError(f"Missing FAISS index at {FAISS_INDEX_PATH}. Run scripts/build_index.py first.")
    if not CHUNKS_PATH.exists():
        raise FileNotFoundError(f"Missing chunks.jsonl at {CHUNKS_PATH}. Run scripts/build_index.py first.")

    index = faiss.read_index(str(FAISS_INDEX_PATH))
    chunks = load_chunks(CHUNKS_PATH)

    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    qvec = embed_query(model, query)

    D, I = index.search(qvec, candidates)

    retrieved: List[Retrieved] = []

    for sim, idx in zip(D[0].tolist(), I[0].tolist()):
        if idx < 0 or idx >= len(chunks):
            continue

        item = Retrieved(idx=idx, sim=float(sim), chunk=chunks[idx])
        ok, _reason = hard_filter(item, allow_draft=False)
        if ok:
            retrieved.append(item)

    rescored_all = policy_rerank(query, retrieved)

    intent = intent_from_query(query)
    quotas = type_quota_for_intent(intent)
    selected = select_with_dedup_and_quotas(rescored_all, top_k=top_k, quotas=quotas)

    results: list[dict] = []
    for final_score, it, reasons in selected:
        rec = it.chunk
        meta = rec.get("meta", {})

        results.append(
            {
                "doc_id": rec.get("doc_id", meta.get("doc_id", "")),
                "doc_type": rec.get("doc_type", meta.get("doc_type", "")),
                "title": meta.get("title", ""),
                "last_updated": meta.get("last_updated", meta.get("date", "")),
                "score_final": float(final_score),
                "score_sim": float(it.sim),
                "reasons": reasons,
                "preview": rec.get("text", ""),
            }
        )

    return results

INDEX_DIR = Path("data/indexes")
FAISS_INDEX_PATH = INDEX_DIR / "faiss.index"
CHUNKS_PATH = INDEX_DIR / "chunks.jsonl"
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@dataclass(frozen=True)
class Retrieved:
    idx: int
    sim: float
    chunk: Dict[str, Any]


def load_chunks(path: Path) -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))
    return chunks


def embed_query(model: SentenceTransformer, query: str) -> np.ndarray:
    v = model.encode([query], normalize_embeddings=True)
    return np.asarray(v, dtype="float32")


def parse_iso(d: str) -> date | None:
    try:
        return date.fromisoformat(d.strip())
    except Exception:
        return None


def intent_from_query(q: str) -> Dict[str, bool]:
    ql = q.lower()
    return {
        "asks_standard": any(k in ql for k in ["standard", "policy", "rule", "guardrail"]),
        "asks_runbook": any(k in ql for k in ["runbook", "incident", "outage", "mitigation", "triage"]),
        "asks_postmortem": any(k in ql for k in ["postmortem", "what happened", "incident learning", "rca"]),
        "asks_adr": any(k in ql for k in ["adr", "decision record", "why did we choose", "precedent"]),
        "identity_related": any(k in ql for k in ["auth", "authentication", "oauth", "oidc", "jwt", "login"]),
        "billing_related": any(k in ql for k in ["billing", "invoice", "payment"]),
        "observability_related": any(k in ql for k in ["tracing", "logging", "otel", "observability"]),
    }


def policy_rerank(query: str, items: List[Retrieved]) -> List[Tuple[float, Retrieved, List[str]]]:
    """
    Rerank FAISS results with metadata-aware heuristics.
    Returns: list of (final_score, item, reasons)
    """
    intent = intent_from_query(query)
    rescored: List[Tuple[float, Retrieved, List[str]]] = []

    for it in items:
        rec = it.chunk
        meta = rec.get("meta", {})
        doc_type = rec.get("doc_type", meta.get("doc_type", ""))
        status = meta.get("status", "").lower()
        system = meta.get("system", "").lower()
        last_updated = meta.get("last_updated", meta.get("date", ""))

        score = it.sim
        reasons: List[str] = [f"sim={it.sim:.4f}"]

        # 1) Authority by intent
        if intent["asks_standard"]:
            if doc_type == "STD":
                score += 0.15
                reasons.append("boost: query asks standard + doc_type=STD")
            if doc_type == "ADR":
                score -= 0.05
                reasons.append("penalty: query asks standard + doc_type=ADR")
        if intent["asks_runbook"] and doc_type == "RBK":
            score += 0.15
            reasons.append("boost: query asks runbook + doc_type=RBK")
        if intent["asks_postmortem"] and doc_type == "PM":
            score += 0.10
            reasons.append("boost: query asks postmortem + doc_type=PM")

        # 2) Status gating
        if status == "approved":
            score += 0.08
            reasons.append("boost: status=approved")
        elif status == "deprecated":
            score -= 0.30
            reasons.append("penalty: status=deprecated")
        elif status == "draft":
            score -= 0.10
            reasons.append("penalty: status=draft")

        # 3) Freshness boost (newer = better)
        dt = parse_iso(last_updated) if last_updated else None
        if dt:
            days_old = (date.today() - dt).days
            if days_old <= 365:
                score += 0.05
                reasons.append("boost: updated <= 1y")
            elif days_old <= 730:
                score += 0.02
                reasons.append("boost: updated <= 2y")

        # 4) System relevance (light boost)
        if intent["identity_related"] and system == "identity":
            score += 0.06
            reasons.append("boost: system=identity")
        if intent["billing_related"] and system == "billing":
            score += 0.06
            reasons.append("boost: system=billing")
        if intent["observability_related"] and system == "observability":
            score += 0.06
            reasons.append("boost: system=observability")

        rescored.append((score, it, reasons))

    rescored.sort(key=lambda x: x[0], reverse=True)
    return rescored

def hard_filter(item: Retrieved, allow_draft: bool = False) -> Tuple[bool, str]:
    """
    Hard filters remove items before scoring.

    - Drop deprecated always (governance).
    - Optionally drop draft unless allow_draft=True.
    """
    meta = item.chunk.get("meta", {})
    status = (meta.get("status") or "").lower().strip()

    if status == "deprecated":
        return False, "filtered: status=deprecated"
    if status == "draft" and not allow_draft:
        return False, "filtered: status=draft"
    return True, ""


def type_quota_for_intent(intent: Dict[str, bool]) -> Dict[str, int]:
    """
    Decide doc-type quotas based on query intent.
    These quotas control the final TOP-K list composition.

    Example: if user asks 'standard', prefer STD strongly, allow 1 ADR for rationale.
    """
    if intent["asks_runbook"]:
        # operational question: runbook first, then standards/postmortems
        return {"RBK": 3, "STD": 2, "PM": 1, "ADR": 1, "TMP": 1}
    if intent["asks_postmortem"]:
        return {"PM": 3, "STD": 2, "ADR": 1, "RBK": 1, "TMP": 1}
    if intent["asks_standard"]:
        return {"STD": 3, "ADR": 1, "RBK": 1, "PM": 1, "TMP": 1}
    if intent["asks_adr"]:
        return {"ADR": 3, "STD": 2, "PM": 1, "RBK": 1, "TMP": 1}

    # default balanced policy
    return {"STD": 2, "ADR": 2, "RBK": 1, "PM": 1, "TMP": 1}


def select_with_dedup_and_quotas(
    rescored: List[Tuple[float, Retrieved, List[str]]],
    top_k: int,
    quotas: Dict[str, int],
) -> List[Tuple[float, Retrieved, List[str]]]:
    """
    Post-process ranked candidates:
    - Deduplicate by doc_id (only 1 chunk per document)
    - Enforce doc-type quotas (composition control)

    Returns the final selected list (<= top_k).
    """
    selected: List[Tuple[float, Retrieved, List[str]]] = []
    seen_doc_ids: set[str] = set()
    used: Dict[str, int] = {k: 0 for k in quotas.keys()}

    # Helper to check if we can take this type
    def can_take(doc_type: str) -> bool:
        if doc_type not in quotas:
            return False
        return used[doc_type] < quotas[doc_type]

    for final_score, it, reasons in rescored:
        meta = it.chunk.get("meta", {})
        doc_id = it.chunk.get("doc_id", meta.get("doc_id", ""))
        doc_type = it.chunk.get("doc_type", meta.get("doc_type", ""))

        if not doc_id or not doc_type:
            continue

        # Dedup: only one chunk per document
        if doc_id in seen_doc_ids:
            continue

        # Quota check
        if not can_take(doc_type):
            continue

        selected.append((final_score, it, reasons))
        seen_doc_ids.add(doc_id)
        used[doc_type] += 1

        if len(selected) >= top_k:
            break

    # If we didn't fill top_k due to quotas, relax quotas (fallback fill)
    if len(selected) < top_k:
        for final_score, it, reasons in rescored:
            meta = it.chunk.get("meta", {})
            doc_id = it.chunk.get("doc_id", meta.get("doc_id", ""))
            doc_type = it.chunk.get("doc_type", meta.get("doc_type", ""))

            if not doc_id or not doc_type:
                continue
            if doc_id in seen_doc_ids:
                continue

            # relaxed: allow any known doc_type
            selected.append((final_score, it, reasons))
            seen_doc_ids.add(doc_id)
            if len(selected) >= top_k:
                break

    return selected

def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python scripts/query_index_policy.py "your question" [top_k] [candidates]')
        raise SystemExit(2)

    query = sys.argv[1].strip()
    top_k = int(sys.argv[2]) if len(sys.argv) >= 3 else 5
    candidates = int(sys.argv[3]) if len(sys.argv) >= 4 else 20

    results = run_policy_query(query, top_k=top_k, candidates=candidates)

    print("\n🔎 Query:", query)
    print(f"📌 Top {top_k} results (policy reranked + dedup + quotas):\n")

    for rank, r in enumerate(results, start=1):
        print(
            f"{rank}. final={r['score_final']:.4f} | "
            f"sim={r['score_sim']:.4f} | "
            f"{r['doc_id']} ({r['doc_type']})"
        )

        if r["last_updated"]:
            print(f"   last_updated: {r['last_updated']}")
        if r["title"]:
            print(f"   title: {r['title']}")

        preview = r["preview"].replace("\n", " ")
        if len(preview) > 220:
            preview = preview[:220] + "..."

        print(f"   reasons: {', '.join(r['reasons'])}")
        print(f"   preview: {preview}\n")


if __name__ == "__main__":
    main()
