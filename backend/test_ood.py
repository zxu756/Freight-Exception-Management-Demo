"""
Unit tests for out-of-distribution (OOD) detection in the event classifier.
分布外检测单元测试
"""
import os

os.environ["EVENT_CLASSIFIER_LEARNING"] = "false"
os.environ["LLM_ENABLED"] = "false"

import pytest
from event_classifier import classifier


def test_clear_match_is_automatic():
    """A message matching a known section template is classified automatically."""
    r = classifier.classify("vessel delayed due to port congestion")
    assert r["classification_decision"] == "automatic"
    assert r["is_ood"] is False
    assert r["ood_score"] < 0.5


def test_known_but_unfamiliar_is_not_ood():
    """A message in a known section but with different wording is not OOD."""
    r = classifier.classify("the ship got held up because the harbour was too busy")
    assert r["is_ood"] is False


def test_out_of_distribution_is_flagged():
    """A message unrelated to any known pattern is flagged as OOD."""
    r = classifier.classify("the main competitor launched an aggressive price war and took our biggest client")
    assert r["is_ood"] is True
    assert r["classification_decision"] == "ood"
    assert r["ood_score"] > 0.5


def test_novel_disruption_is_flagged_ood():
    """A genuinely novel disruption type is OOD and routed for escalation."""
    r = classifier.classify("a volcanic eruption closed the airport and all flights were grounded")
    assert r["is_ood"] is True
    assert r["classification_decision"] == "ood"


def test_classify_returns_ood_fields():
    """classify always returns ood_score and is_ood fields."""
    for msg in ["customs placed the shipment on hold pending document review", ""]:
        r = classifier.classify(msg)
        assert "ood_score" in r
        assert "is_ood" in r
