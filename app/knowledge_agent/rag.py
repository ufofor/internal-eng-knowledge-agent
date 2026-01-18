from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass(frozen=True)
class RagInput:
    query: str
    retrieved: List[Dict[str, Any]]  # output of run_policy_query()


def build_rag_prompt(inp: RagInput) -> str:
    """
    Builds a prompt that forces:
    - only use provided sources
    - cite using [DOC-ID] format
    - refuse if sources insufficient
    """
    allowed_ids = [r["doc_id"] for r in inp.retrieved]

    sources = []
    for r in inp.retrieved:
        sources.append(
            f"- {r['doc_id']} ({r['doc_type']} | updated={r.get('last_updated','')})\n"
            f"  title: {r.get('title','')}\n"
            f"  excerpt: {r.get('preview','')}\n"
        )

    return f"""
You are an internal engineering knowledge assistant.
You must answer the user's question using ONLY the SOURCES below.
If the sources do not contain enough information, say: "Insufficient information in provided sources."

Citation rules:
- Every factual claim MUST be backed by at least one citation in square brackets.
- Citations MUST be one of these doc IDs: {allowed_ids}
- Use this exact format: [DOC-ID] (example: [STD-02])
- Do not cite any other IDs.

User question:
{inp.query}

SOURCES:
{chr(10).join(sources)}

Return:
1) A short answer (4-8 bullets max)
2) A final line: "Citations: [ID1], [ID2], ..."
""".strip()


_CIT_RE = re.compile(r"\[([A-Z]{2,4}(?:-\d{2,4}|\-\d{4}\-\d{2}))\]")


def extract_citations(text: str) -> List[str]:
    return list(dict.fromkeys(_CIT_RE.findall(text)))  # dedupe, keep order


def validate_citations(text: str, allowed_ids: List[str]) -> None:
    """
    Enforce 'no hallucinated citations'.
    If model cites an ID not in allowed_ids => reject.
    """
    cited = extract_citations(text)
    illegal = [c for c in cited if c not in set(allowed_ids)]
    if illegal:
        raise ValueError(f"Model cited unknown doc IDs: {illegal}. Allowed: {allowed_ids}")