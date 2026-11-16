"""Data models and serialization structures for findings."""
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

FINDING_MATCH = "match"
FINDING_CONFLICT = "conflict"
FINDING_NOT_SETTLED = "not_settled"
FINDING_NOT_CHECKABLE = "not_checkable"

VALID_FINDINGS = {FINDING_MATCH, FINDING_CONFLICT, FINDING_NOT_SETTLED, FINDING_NOT_CHECKABLE}


@dataclass
class Citation:
    file: str
    row: int  # 1-based line number for CSV/JSON/text, or 1-based cue number for WebVTT

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": self.file,
            "row": self.row,
        }


@dataclass
class Finding:
    claim: str
    finding: str
    cite: Optional[Citation] = None
    quote: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "claim": self.claim,
            "finding": self.finding,
        }
        if self.finding in (FINDING_MATCH, FINDING_CONFLICT):
            if self.cite is not None:
                result["cite"] = self.cite.to_dict()
            if self.quote is not None:
                result["quote"] = self.quote
        return result
