from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer


# ----------------------------
# Config
# ----------------------------

CORPUS_DIR = Path("data/corpus")
INDEX_DIR = Path("data/indexes")

FAISS_INDEX_PATH = INDEX_DIR / "faiss.index"
CHUNKS_PATH = INDEX_DIR / "chunks.jsonl"

# Good default for local RAG. Change later if you want higher quality vs speed.
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Chunking parameters (token-free heuristic based on characters)
MAX_CHARS = 1200
OVERLAP_CHARS = 200


# ----------------------------
# Data structures
# ----------------------------

@dataclass(frozen=True)
class ParsedDoc:
    """
    Represents a single markdown document after parsing:
    - doc_id: "ADR-004", "PM-2024-09", etc.
    - doc_type: ADR/STD/RBK/PM/TMP
    - title: full title line text
    - meta: parsed key/value metadata block
    - body: content after title/metadata
    - source_path: file location for traceability
    """
    doc_id: str
    doc_type: str
    title: str
    meta: Dict[str, str]
    body: str
    source_path: str


@dataclass(frozen=True)
class Chunk:
    """
    A retrieval unit (what we embed and search).
    """
    chunk_id: str
    doc_id: str
    doc_type: str
    text: str
    meta: Dict[str, str]


# ----------------------------
# Parsing helpers
# ----------------------------

META_LINE_RE = re.compile(r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*(.+?)\s*$")
TITLE_LINE_RE = re.compile(r"^#\s+(.+?)\s*$")

DOC_ID_RE = re.compile(r"^((?:ADR|STD|RBK|TMP)-\d{2,4}|PM-\d{4}-\d{2})\b")


def detect_doc_type_from_filename(path: Path) -> str:
    name = path.name
    if name.startswith("ADR-"):
        return "ADR"
    if name.startswith("STD-"):
        return "STD"
    if name.startswith("RBK-"):
        return "RBK"
    if name.startswith("PM-"):
        return "PM"
    if name.startswith("TMP-"):
        return "TMP"
    return "UNKNOWN"


def extract_doc_id_from_title(title: str) -> Optional[str]:
    """
    From '# ADR-004: ...' -> ADR-004
    From '# PM-2024-09: ...' -> PM-2024-09
    """
    m = DOC_ID_RE.search(title)
    return m.group(1) if m else None


def parse_markdown(path: Path) -> ParsedDoc:
    """
    Parse your markdown format:
    - Title line: '# <ID>: <Title>'
    - Metadata lines: 'key: value' immediately after title, until blank line
    - Body: rest of the markdown
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    # Find title line
    title_idx = None
    title_line = ""
    for i, line in enumerate(lines):
        if TITLE_LINE_RE.match(line.strip()):
            title_idx = i
            title_line = line.strip()
            break

    if title_idx is None:
        raise ValueError(f"Missing title line (# ...) in {path}")

    # Parse metadata block after title
    meta: Dict[str, str] = {}
    j = title_idx + 1
    while j < len(lines):
        line = lines[j].strip()
        if line == "":
            break
        m = META_LINE_RE.match(line)
        if not m:
            break
        key, value = m.group(1), m.group(2)
        meta[key] = value
        j += 1

    body = "\n".join(lines[j:]).strip()

    doc_type = detect_doc_type_from_filename(path)
    doc_id = extract_doc_id_from_title(title_line)
    if not doc_id:
        # fallback: attempt from filename stem
        m2 = DOC_ID_RE.match(path.stem)
        doc_id = m2.group(1) if m2 else path.stem

    return ParsedDoc(
        doc_id=doc_id,
        doc_type=doc_type,
        title=title_line,
        meta=meta,
        body=body,
        source_path=str(path),
    )


# ----------------------------
# Chunking
# ----------------------------

def normalize_text(s: str) -> str:
    # Basic cleanup: collapse excessive whitespace
    s = re.sub(r"\n{3,}", "\n\n", s)
    s = re.sub(r"[ \t]{2,}", " ", s)
    return s.strip()


def chunk_text(text: str, max_chars: int = MAX_CHARS, overlap_chars: int = OVERLAP_CHARS) -> List[str]:
    """
    Simple chunker by paragraphs.
    - Greedy pack paragraphs up to max_chars
    - Add overlap by reusing last overlap_chars from previous chunk
    """
    text = normalize_text(text)
    if not text:
        return []

    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: List[str] = []

    buf: List[str] = []
    buf_len = 0

    def flush():
        nonlocal buf, buf_len
        if not buf:
            return
        chunk = "\n\n".join(buf).strip()
        chunks.append(chunk)
        # prepare overlap for next chunk
        if overlap_chars > 0:
            tail = chunk[-overlap_chars:]
            buf = [tail]
            buf_len = len(tail)
        else:
            buf = []
            buf_len = 0

    for p in paras:
        if buf_len + len(p) + 2 <= max_chars:
            buf.append(p)
            buf_len += len(p) + 2
        else:
            flush()
            # if paragraph itself is huge, split it hard
            if len(p) > max_chars:
                for k in range(0, len(p), max_chars):
                    part = p[k:k + max_chars]
                    chunks.append(part)
                buf = []
                buf_len = 0
            else:
                buf = [p]
                buf_len = len(p)

    flush()
    return chunks


def make_chunks(doc: ParsedDoc) -> List[Chunk]:
    """
    Build chunks that include the title + metadata context so retrieval answers can cite properly.
    """
    # We include title + selected metadata in the chunk text to improve retrieval relevance.
    meta_hint = []
    for k in ["status", "system", "owner_team", "last_updated", "severity", "oncall_team"]:
        if k in doc.meta:
            meta_hint.append(f"{k}={doc.meta[k]}")
    meta_prefix = " | ".join(meta_hint)

    # Full content that will be chunked:
    full_text = f"{doc.title}\n{meta_prefix}\n\n{doc.body}".strip()

    raw_chunks = chunk_text(full_text)
    out: List[Chunk] = []
    for idx, ch in enumerate(raw_chunks):
        out.append(
            Chunk(
                chunk_id=f"{doc.doc_id}::chunk-{idx:03d}",
                doc_id=doc.doc_id,
                doc_type=doc.doc_type,
                text=ch,
                meta={
                    **doc.meta,
                    "doc_id": doc.doc_id,
                    "doc_type": doc.doc_type,
                    "title": doc.title,
                    "source_path": doc.source_path,
                    "chunk_index": str(idx),
                },
            )
        )
    return out


# ----------------------------
# Index building
# ----------------------------

def embed_chunks(model: SentenceTransformer, chunks: List[Chunk]) -> np.ndarray:
    """
    Embed chunk texts into a float32 matrix [n, dim].
    """
    texts = [c.text for c in chunks]
    vecs = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=True,
        normalize_embeddings=True,  # cosine similarity via inner product
    )
    vecs = np.asarray(vecs, dtype="float32")
    return vecs


def build_faiss_index(vectors: np.ndarray) -> faiss.Index:
    """
    Build FAISS index for cosine similarity using normalized vectors.
    We use IndexFlatIP (inner product) since embeddings are normalized.
    """
    dim = vectors.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(vectors)
    return index


def write_chunks_jsonl(path: Path, chunks: List[Chunk]) -> None:
    """
    Store chunk text + metadata for later retrieval/citation.
    """
    with path.open("w", encoding="utf-8") as f:
        for c in chunks:
            rec = {
                "chunk_id": c.chunk_id,
                "doc_id": c.doc_id,
                "doc_type": c.doc_type,
                "text": c.text,
                "meta": c.meta,
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    corpus_root = repo_root / CORPUS_DIR
    index_root = repo_root / INDEX_DIR
    index_root.mkdir(parents=True, exist_ok=True)

    if not corpus_root.exists():
        raise FileNotFoundError(f"Corpus directory not found: {corpus_root}")

    md_files = sorted(corpus_root.rglob("*.md"))
    if not md_files:
        raise FileNotFoundError(f"No markdown docs found under: {corpus_root}")

    print(f"✅ Repo root: {repo_root}")
    print(f"✅ Corpus files: {len(md_files)}")
    print(f"✅ Embedding model: {EMBEDDING_MODEL_NAME}")

    # Parse docs
    parsed_docs: List[ParsedDoc] = []
    for p in md_files:
        parsed_docs.append(parse_markdown(p))

    # Chunk docs
    chunks: List[Chunk] = []
    for d in parsed_docs:
        chunks.extend(make_chunks(d))

    if not chunks:
        raise RuntimeError("No chunks created. Check chunking logic or document contents.")

    print(f"✅ Total chunks: {len(chunks)}")

    # Embed + index
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    vectors = embed_chunks(model, chunks)
    index = build_faiss_index(vectors)

    # Persist
    faiss.write_index(index, str(repo_root / FAISS_INDEX_PATH))
    write_chunks_jsonl(repo_root / CHUNKS_PATH, chunks)

    print(f"✅ Wrote FAISS index: {FAISS_INDEX_PATH}")
    print(f"✅ Wrote chunks: {CHUNKS_PATH}")
    print("\nNext: you can run a quick retrieval smoke test (I can provide it).")


if __name__ == "__main__":
    main()
