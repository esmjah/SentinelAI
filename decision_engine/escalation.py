"""decision_engine.escalation - dwell and hysteresis on the decision stream (operator-facing state).

The engine decides per evaluation. A stream of evaluations near a threshold can chatter
(ALARM, TEST, ALARM, ...), which is how alarm fatigue starts. This filter sits AFTER the engine and
BEFORE the operator. It never changes the engine's decision; it only changes what is surfaced.

    raise  : ALARM is surfaced after RAISE_N consecutive raw ALARM evaluations (dwell); until then it is
             surfaced as TEST. Hard-limit gates (G2_*) are surfaced immediately: a limit breach is not noise.
    clear  : a surfaced ALARM is cleared only after CLEAR_N consecutive non-ALARM evaluations (hysteresis).
    ABSTAIN: always surfaced at once (bad data or invalid model must never be hidden by a filter).
    TEST / NO_ACTION: surfaced as is while no alarm is latched.

The filter is advisory like the rest of the stack: it does not trip anything, and a latched alarm still
needs human confirmation. Constants are code constants for now; they belong on the policy node
(see Limitations in README.md).
"""
from __future__ import annotations

from dataclasses import dataclass, field

RAISE_N = 3          # consecutive raw ALARM evaluations before an alarm is surfaced
CLEAR_N = 6          # consecutive non-ALARM evaluations before a latched alarm is cleared
IMMEDIATE_GATES = ("G2_LIMIT", "G2_MARGIN")


@dataclass
class EscalationFilter:
    raise_n: int = RAISE_N
    clear_n: int = CLEAR_N
    latched: bool = False
    _up: int = field(default=0, repr=False)
    _down: int = field(default=0, repr=False)

    def update(self, action: str, gate: str | None = None) -> str:
        """Feed one raw engine decision; return the action surfaced to the operator."""
        if action == "ABSTAIN":
            self._up = 0
            return "ABSTAIN"
        if action == "ALARM":
            self._up += 1
            self._down = 0
            if gate in IMMEDIATE_GATES or self._up >= self.raise_n:
                self.latched = True
        else:
            self._up = 0
            if self.latched:
                self._down += 1
                if self._down >= self.clear_n:
                    self.latched = False
                    self._down = 0
        if self.latched:
            return "ALARM"
        return "TEST" if action == "ALARM" else action   # a pending alarm is surfaced one level lower


def filter_stream(decisions: list[tuple[str, str | None]], **kw) -> list[str]:
    f = EscalationFilter(**kw)
    return [f.update(a, g) for a, g in decisions]


def flips(actions: list[str]) -> int:
    """Number of changes between consecutive actions - the chatter count."""
    return sum(1 for a, b in zip(actions, actions[1:]) if a != b)
