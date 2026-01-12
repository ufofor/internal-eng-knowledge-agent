from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple



# ---- Config ----

CORPUS_DIR = Path("data/corpus")

ALLOWED_STATUS = {"approved", "deprecated", "draft"}

DOC_TYPE_RULES: Dict[str, Dict[str, object]] = {
    "ADR": {
        "required": {"status", "system", "owner_team", "version", "last_updated", "supersedes"},
        "optional": set(),
    },
    "STD": {
        "required": {"status", "system", "owner_team", "version", "last_updated"},
        "optional": set(),
    },
    "RBK": {
        "required": {"severity", "oncall_team", "escalation_policy", "last_tested", "related_services"},
        "optional": {"system"},
    },
    "PM": {
        "required": {"system", "date", "severity", "owner_team", "last_updated"},
        "optional": set(),
    },
    "TMP": {
        "required": {"owner_team", "version", "last_updated"},
        "optional": set(),
    },
}

SEVERITY_ALLOWED = {"P0", "P1", "P2", "P3"}

# metadata line pattern: key: value
META_LINE_RE = re.compile(r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*(.+?)\s*$")
# Accept:
# - ADR-001, STD-02, RBK-11, TMP-01
# - PM-2024-09 (year-month)
TITLE_ID_RE = re.compile(r"^#\s+((?:ADR|STD|RBK|TMP)-\d{2,4}|PM-\d{4}-\d{2})\s*:")


@dataclass(frozen=True)
class DocIssue:
    path: Path
    level: str  # "ERROR" or "WARN"
    message: str


def parse_iso_date(s: str) -> Optional[date]:
    try:
        return date.fromisoformat(s.strip())
    except Exception:
        return None


def detect_doc_type(path: Path) -> Optional[str]:
    """
    Determine doc type from filename prefix: ADR-xxx, STD-xx, RBK-xx, PM-YYYY-MM, TMP-xx
    """
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
    return None


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_metadata_block(text: str) -> Tuple[Dict[str, str], str]:
    """
    Parse "YAML-like" metadata at the top of the markdown:
      - Title line: '# ...' (not metadata)
      - Following consecutive 'key: value' lines until first blank line.

    Returns: (metadata_dict, title_line)
    """
    lines = text.splitlines()
    title_line = ""
    meta: Dict[str, str] = {}

    # Find first title line
    for i, line in enumerate(lines):
        if line.strip().startswith("# "):
            title_line = line.strip()
            start = i + 1
            break
    else:
        start = 0

    # Parse metadata lines until blank line or non meta
    for j in range(start, len(lines)):
        line = lines[j].strip()
        if line == "":
            break
        m = META_LINE_RE.match(line)
        if not m:
            # stop if metadata section ended (first non key:value line)
            break
        key, value = m.group(1), m.group(2)
        meta[key.strip()] = value.strip()

    return meta, title_line


def extract_title_id(title_line: str) -> Optional[str]:
    """
    From '# ADR-001: Something' -> 'ADR-001'
    """
    m = TITLE_ID_RE.match(title_line.strip())
    if not m:
        return None
    return m.group(1)


def extract_filename_id(path: Path, doc_type: str) -> Optional[str]:
    """
    Extract doc id from filename.
    Examples:
      ADR-001-xxx.md -> ADR-001
      STD-02-xxx.md  -> STD-02
      RBK-11-xxx.md  -> RBK-11
      TMP-01-xxx.md  -> TMP-01
      PM-2024-09-xxx.md -> PM-2024-09  (special)
    """
    name = path.stem  # without .md
    if doc_type in {"ADR", "STD", "RBK", "TMP"}:
        m = re.match(r"^(" + doc_type + r"-\d{2,4})\b", name)
        return m.group(1) if m else None
    if doc_type == "PM":
        m = re.match(r"^(PM-\d{4}-\d{2})\b", name)
        return m.group(1) if m else None
    return None


def validate_doc(path: Path) -> List[DocIssue]:
    issues: List[DocIssue] = []
    doc_type = detect_doc_type(path)
    if doc_type is None:
        issues.append(DocIssue(path, "WARN", "Unknown doc type from filename prefix; skipping strict checks."))
        return issues

    text = read_text(path)
    meta, title_line = parse_metadata_block(text)

    # Title checks
    title_id = extract_title_id(title_line) if title_line else None
    file_id = extract_filename_id(path, doc_type)

    if not title_line:
        issues.append(DocIssue(path, "ERROR", "Missing markdown title line starting with '# '"))
    if title_line and title_id is None:
        issues.append(DocIssue(path, "ERROR", f"Title does not start with expected ID format (e.g., '# {doc_type}-001: ...')"))
    if file_id is None:
        issues.append(DocIssue(path, "ERROR", f"Filename does not start with expected ID format for {doc_type}"))
    if title_id and file_id and title_id != file_id:
        issues.append(DocIssue(path, "ERROR", f"Title ID '{title_id}' does not match filename ID '{file_id}'"))

    # Required fields by doc type
    rules = DOC_TYPE_RULES[doc_type]
    required = set(rules["required"])  # type: ignore[arg-type]
    optional = set(rules["optional"])  # type: ignore[arg-type]

    missing = sorted([k for k in required if k not in meta])
    if missing:
        issues.append(DocIssue(path, "ERROR", f"Missing required metadata fields for {doc_type}: {missing}"))

    # Unknown fields (warn)
    allowed_keys = required | optional
    unknown = sorted([k for k in meta.keys() if k not in allowed_keys])
    if unknown:
        issues.append(DocIssue(path, "WARN", f"Unknown metadata keys for {doc_type}: {unknown}"))

    # Validate common fields if present
    if "status" in meta and meta["status"] not in ALLOWED_STATUS:
        issues.append(DocIssue(path, "ERROR", f"Invalid status='{meta['status']}'. Allowed: {sorted(ALLOWED_STATUS)}"))

    if "version" in meta:
        # allow 1.0, 1.2, 2.0 etc.
        if not re.match(r"^\d+(\.\d+)?$", meta["version"]):
            issues.append(DocIssue(path, "WARN", f"version='{meta['version']}' is not numeric like '1.0'"))

    # Date fields
    for dkey in ("last_updated", "last_tested", "date"):
        if dkey in meta:
            if parse_iso_date(meta[dkey]) is None:
                issues.append(DocIssue(path, "ERROR", f"{dkey}='{meta[dkey]}' must be ISO date YYYY-MM-DD"))

    # Severity checks (RBK + PM)
    if "severity" in meta and meta["severity"] not in SEVERITY_ALLOWED:
        issues.append(DocIssue(path, "ERROR", f"severity='{meta['severity']}' invalid. Allowed: {sorted(SEVERITY_ALLOWED)}"))

    # Supersedes checks (ADRs)
    if doc_type == "ADR" and "supersedes" in meta:
        # allow "none" or ADR-xxx
        val = meta["supersedes"].strip()
        if val != "none" and not re.match(r"^ADR-\d{2,4}$", val):
            issues.append(DocIssue(path, "WARN", f"supersedes='{val}' should be 'none' or like 'ADR-002'"))

    # related_services list checks (RBK)
    if doc_type == "RBK" and "related_services" in meta:
        # Encourage comma-separated list with at least one token
        if len([x.strip() for x in meta["related_services"].split(",") if x.strip()]) == 0:
            issues.append(DocIssue(path, "ERROR", "related_services must include at least one service name"))

    return issues


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    corpus_root = repo_root / CORPUS_DIR

    if not corpus_root.exists():
        print(f"ERROR: Corpus directory not found: {corpus_root}")
        return 2

    md_files = sorted(corpus_root.rglob("*.md"))
    if not md_files:
        print(f"ERROR: No markdown files found under: {corpus_root}")
        return 2

    issues: List[DocIssue] = []
    for path in md_files:
        issues.extend(validate_doc(path))

    # Print report
    errors = [i for i in issues if i.level == "ERROR"]
    warns = [i for i in issues if i.level == "WARN"]

    print(f"✅ Repo root: {repo_root}")
    print(f"✅ Corpus root: {corpus_root}")
    print(f"✅ Files scanned: {len(md_files)}")
    print(f"⚠️  Warnings: {len(warns)}")
    print(f"❌ Errors: {len(errors)}\n")

    # Group by file for readability
    by_file: Dict[Path, List[DocIssue]] = {}
    for i in issues:
        by_file.setdefault(i.path, []).append(i)

    for path, its in by_file.items():
        # show only files with issues
        if not its:
            continue
        rel = path.relative_to(repo_root)
        print(f"--- {rel} ---")
        for it in its:
            print(f"[{it.level}] {it.message}")
        print()

    if errors:
        print("❌ Validation failed. Fix errors above.")
        return 1

    print("✅ Validation passed (no errors).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
