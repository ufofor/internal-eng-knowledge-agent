from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# Paths match your build_index.py outputs
INDEX_DIR = Path("data/indexes")
FAISS_INDEX_PATH = INDEX_DIR / "faiss.index"
CHUNKS_PATH = INDEX_DIR / "chunks.jsonl"

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@dataclass(frozen=True)
class RetrievedChunk:
    rank: int
    score: float
    chunk_id: str
    doc_id: str
    doc_type: str
    title: str
    source_path: str
    last_updated: str
    text_preview: str


def load_chunks(path: Path) -> List[Dict[str, Any]]:
    """
    Load chunks.jsonl created by scripts/build_index.py.
    Each line contains: chunk_id, doc_id, doc_type, text, meta.
    """
    chunks: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            chunks.append(json.loads(line))
    return chunks


def embed_query(model: SentenceTransformer, query: str) -> np.ndarray:
    """
    Embed query into a normalized float32 vector so we can use cosine similarity.
    """
    v = model.encode([query], normalize_embeddings=True)
    return np.asarray(v, dtype="float32")


def search(
    query: str,
    top_k: int = 5,
) -> List[RetrievedChunk]:
    """
    Run a vector search against FAISS and return top_k chunks with metadata.
    """
    if not FAISS_INDEX_PATH.exists():
        raise FileNotFoundError(f"Missing FAISS index at {FAISS_INDEX_PATH}. Run scripts/build_index.py first.")
    if not CHUNKS_PATH.exists():
        raise FileNotFoundError(f"Missing chunks.jsonl at {CHUNKS_PATH}. Run scripts/build_index.py first.")

    index = faiss.read_index(str(FAISS_INDEX_PATH))
    chunks = load_chunks(CHUNKS_PATH)

    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    qvec = embed_query(model, query)

    # index.search returns:
    #   D: similarity scores shape [1, top_k]
    #   I: indices into the vector store shape [1, top_k]
    D, I = index.search(qvec, top_k)

    results: List[RetrievedChunk] = []
    for rank, (score, idx) in enumerate(zip(D[0].tolist(), I[0].tolist()), start=1):
        if idx < 0 or idx >= len(chunks):
            continue

        rec = chunks[idx]
        meta = rec.get("meta", {})

        text = rec.get("text", "")
        preview = text.replace("\n", " ")
        if len(preview) > 220:
            preview = preview[:220] + "..."

        results.append(
            RetrievedChunk(
                rank=rank,
                score=float(score),
                chunk_id=rec.get("chunk_id", ""),
                doc_id=rec.get("doc_id", meta.get("doc_id", "")),
                doc_type=rec.get("doc_type", meta.get("doc_type", "")),
                title=meta.get("title", ""),
                source_path=meta.get("source_path", ""),
                last_updated=meta.get("last_updated", meta.get("date", "")),
                text_preview=preview,
            )
        )

    return results


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage:\n  python scripts/query_index.py \"your question here\" [top_k]\n")
        raise SystemExit(2)

    query = sys.argv[1].strip()
    top_k = int(sys.argv[2]) if len(sys.argv) >= 3 else 5

    results = search(query, top_k=top_k)

    print("\n🔎 Query:", query)
    print(f"📌 Top {top_k} results:\n")

    for r in results:
        print(f"{r.rank}. score={r.score:.4f} | {r.doc_id} ({r.doc_type})")
        if r.last_updated:
            print(f"   last_updated: {r.last_updated}")
        if r.title:
            print(f"   title: {r.title}")
        if r.source_path:
            print(f"   source: {r.source_path}")
        print(f"   preview: {r.text_preview}")
        print()

    if not results:
        print("⚠️ No results returned. Check that the index has vectors and chunks.jsonl aligns with index order.")


if __name__ == "__main__":
    main()
