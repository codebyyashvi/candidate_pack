"""Extracts factual claims from an incident report text."""
import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ExtractedClaim:
    claim_text: str
    original_line_num: int
    has_speed: bool = False
    has_time: bool = False
    has_count: bool = False
    speeds: List[int] = None
    times: List[str] = None
    entities: List[str] = None
    action_keywords: List[str] = None


def is_factual_claim(text: str) -> bool:
    """Checks if a sentence makes a factual assertion with a predicate / verb.

    Filters out pure labels, titles, and synthetic watermark banners.
    """
    s = text.strip()
    if not s:
        return False

    # Disclaimers / watermarks
    if re.match(r"^SYNTHETIC(\s*-\s*FICTIONAL\s*CASE)?\.?$", s, flags=re.IGNORECASE):
        return False

    # Check for presence of common verbs or verbal forms asserting facts
    verb_patterns = [
        r"\b(?:observed|seen|saw|states|stated|shows|showed|show|logged|was\s+logged|were\s+logged)\b",
        r"\b(?:pulled|stopped|travelling|traveling|travelled|traveled|arrived|dispatched|reported)\b",
        r"\b(?:called|entered|exited|fled|pursued|recorded|indicated|noted|confirmed)\b",
        r"\b(?:was|were|is|are|had|has)\b",
    ]
    for vp in verb_patterns:
        if re.search(vp, s, flags=re.IGNORECASE):
            return True

    return False


def extract_claims(report_content: str) -> List[ExtractedClaim]:
    """Parses report content into individual factual claims as written in the report."""
    claims: List[ExtractedClaim] = []

    lines = report_content.splitlines()
    for line_idx, line in enumerate(lines):
        line_str = line.strip()
        if not line_str:
            continue

        # Strip synthetic banner prefix if at the start of a line
        cleaned_line = re.sub(
            r"^\s*SYNTHETIC\s*-\s*FICTIONAL\s*CASE\.?\s*", "", line_str, flags=re.IGNORECASE
        ).strip()
        if not cleaned_line:
            continue

        # Split into sentences using punctuation boundaries (. ! ?) avoiding decimals/times
        # e.g. '21:14' or '3.1' or 'approx.'
        raw_sents = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", cleaned_line)

        for sent in raw_sents:
            sent_str = sent.strip()
            if not sent_str:
                continue

            if not is_factual_claim(sent_str):
                continue

            # Extract metadata from claim
            speeds = [int(m) for m in re.findall(r"\b(\d{1,3})\s*(?:mph|zone)\b", sent_str, re.IGNORECASE)]
            times = re.findall(r"\b(\d{1,2}:\d{2}(?::\d{2})?)\b", sent_str)

            claim_obj = ExtractedClaim(
                claim_text=sent_str,
                original_line_num=line_idx + 1,
                has_speed=bool(speeds),
                has_time=bool(times) or ("minutes" in sent_str) or ("after the stop" in sent_str),
                has_count=("only" in sent_str) or ("one" in sent_str) or ("two" in sent_str),
                speeds=speeds,
                times=times,
                entities=[],
                action_keywords=[],
            )
            claims.append(claim_obj)

    return claims
