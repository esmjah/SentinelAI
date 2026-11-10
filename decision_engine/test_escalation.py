"""Escalation filter and monitoring helpers.   python -m pytest decision_engine/test_escalation.py

Pure functions, no artifact needed.
"""
import numpy as np

from .escalation import EscalationFilter, filter_stream, flips
from .monitoring import ece, psi


def test_isolated_alarm_is_not_surfaced():
    out = filter_stream([("NO_ACTION", None), ("ALARM", "EXPECTED_LOSS"), ("NO_ACTION", None)])
    assert "ALARM" not in out and out[1] == "TEST"


def test_sustained_alarm_latches_after_dwell_and_clears_with_hysteresis():
    f = EscalationFilter(raise_n=3, clear_n=4)
    raw = ["ALARM"] * 3 + ["NO_ACTION"] * 3 + ["NO_ACTION"]
    out = [f.update(a, "EXPECTED_LOSS") for a in raw]
    assert out[:2] == ["TEST", "TEST"] and out[2] == "ALARM"
    assert out[3:6] == ["ALARM"] * 3          # still latched after 1-3 quiet evaluations
    assert out[6] == "NO_ACTION"              # cleared on the 4th


def test_hard_limit_is_immediate():
    assert EscalationFilter().update("ALARM", "G2_LIMIT") == "ALARM"


def test_abstain_is_never_hidden_and_resets_dwell():
    f = EscalationFilter(raise_n=3)
    f.update("ALARM", "EXPECTED_LOSS"); f.update("ALARM", "EXPECTED_LOSS")
    assert f.update("ABSTAIN", "G1_DATA_QUALITY") == "ABSTAIN"
    assert f.update("ALARM", "EXPECTED_LOSS") == "TEST"     # dwell restarted


def test_chatter_is_reduced():
    raw = [("ALARM", "EXPECTED_LOSS"), ("TEST", None)] * 10
    assert flips(filter_stream(raw)) <= flips([a for a, _ in raw])
    assert "ALARM" not in filter_stream(raw)


def test_psi_zero_for_identical_and_large_for_shift():
    rng = np.random.default_rng(0)
    ref = 10 ** rng.normal(-3, 0.2, 500)
    assert psi(ref, ref) < 1e-6
    assert psi(ref, ref * 30) > 0.25


def test_ece_perfect_and_miscalibrated():
    p = np.array([0.1] * 10 + [0.9] * 10)
    y = np.array([1] + [0] * 9 + [1] * 9 + [0])
    assert ece(p, y) < 1e-9
    assert ece(np.full(10, 0.9), np.zeros(10)) > 0.8
