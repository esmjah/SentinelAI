"""Scope guard: deterministic, before any language model is called.

SentinelAI advises; it does not operate equipment. A request phrased as a command to act on the well,
or to switch off a safety function, is refused without calling the model. Questions ABOUT such actions
("should we bleed the A-annulus?") are in scope and go to the agent.
"""
from __future__ import annotations

import re

ACT = r"(trip|shut[\s-]?in|shut down|close|open|bleed|stop|start|operate|actuate|execute|send|override|disable|bypass|inhibit|reset|silence|acknowledge)"
COMMAND = [
    re.compile(rf"^\s*(please\s+|now\s+|immediately\s+)?{ACT}\b(?!.*\?\s*$)", re.I),
    re.compile(rf"\b(you|sentinel(ai)?)\s+(must|should|can you|will|go and)\s+{ACT}\b", re.I),
    re.compile(r"\b(override|disable|bypass|inhibit|turn off|switch off)\b.*\b(sis|safety|gate|alarm|trip|interlock|guard)", re.I),
    re.compile(r"\b(ignore|forget)\b.*\b(rules|instructions|limits|policy)\b", re.I),
]


def check(question: str) -> str | None:
    """Return a refusal reason, or None if the question is in scope."""
    for rx in COMMAND:
        if rx.search(question):
            return ("SentinelAI is an advisory system. It cannot operate valves, trip or shut in the well, "
                    "or switch off safety functions, and it does not change its rules on request. "
                    "Trip authority stays with the safety instrumented system; diagnostic operations are "
                    "decided by a person with operating authority. Ask instead whether an action is advisable, "
                    "and the assessment will explain the evidence.")
    return None
