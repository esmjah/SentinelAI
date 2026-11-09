"""Ingestion-time screening of untrusted text for instruction injection.

Ingested documents are data. Text that tries to address the assistant, change its rules or set limits
is flagged. Flagged chunks are stored but QUARANTINED: retrieval returns their metadata and the reason,
never their text, and the grounding gate rejects any answer that cites them (rule R8).
The patterns are deliberately broad: a false positive costs one withheld passage, a false negative
can cost a wrong recommendation.
"""
from __future__ import annotations

import re

PATTERNS = [
    (r"\b(ignore|disregard|forget)\b[^.\n]{0,40}\b(instruction|rule|limit|previous|above)s?\b", "override attempt"),
    (r"\b(ai|assistant|chatbot|model|llm|copilot)\b[^.\n]{0,30}\b(must|should|always|never|note|instruction)", "addresses the assistant"),
    (r"\bnote to the (ai|assistant|model)\b", "addresses the assistant"),
    (r"\b(system prompt|you are now|act as|new instructions?)\b", "role manipulation"),
    (r"\balways (answer|respond|reply|recommend)\b", "output steering"),
    (r"\bdo not (mention|report|disclose|tell)\b", "concealment request"),
    (r"\b(maasp|mawop|limit)\b[^.\n]{0,25}\bis now\b", "unauthorised limit change"),
]
_RX = [(re.compile(p, re.I), why) for p, why in PATTERNS]


def screen(text: str) -> list[str]:
    """Return the reasons a text looks like an injection attempt (empty list = clean)."""
    return sorted({why for rx, why in _RX if rx.search(text)})


def apply(chunks) -> int:
    n = 0
    for c in chunks:
        reasons = screen(c.content)
        c.injection_suspect, c.injection_reasons = bool(reasons), reasons
        n += bool(reasons)
    return n
