#!/usr/bin/env python3
"""Chaos engineering tests for Clarvia automation system.

Simulates real failure scenarios and verifies self-healing behavior.
Tests actual module functions with their real signatures.
"""

import json
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

# Ensure automation scripts are importable
SCANNER_ROOT = Path(__file__).resolve().parent.parent
AUTOMATION_DIR = SCANNER_ROOT / "scripts" / "automation"
sys.path.insert(0, str(AUTOMATION_DIR))
sys.path.insert(0, str(SCANNER_ROOT / "scripts"))


def test_circuit_breaker_opens_on_failures():
    """Simulate 3 consecutive failures -> circuit should open."""
    from circuit_breaker import CircuitBreaker, CBState

    # Use a unique name to avoid interfering with real state
    cb = CircuitBreaker("chaos_test_open", failure_threshold=3, cooldown_seconds=1800)

    # Reset to known state
    cb.state = CBState.CLOSED
    cb.failure_count = 0

    assert cb.state == CBState.CLOSED, f"Expected CLOSED, got {cb.state}"
    cb.record_failure("test failure 1")
    cb.record_failure("test failure 2")
    cb.record_failure("test failure 3")
    assert cb.state == CBState.OPEN, f"Expected OPEN after 3 failures, got {cb.state}"
    assert not cb.allow_request(), "Should not allow requests when OPEN"
    print("PASS: Circuit breaker opens after 3 failures")


def test_circuit_breaker_recovers():
    """After cooldown, circuit should go to half-open and recover on success."""
    from circuit_breaker import CircuitBreaker, CBState

    cb = CircuitBreaker("chaos_test_recover", failure_threshold=3, cooldown_seconds=1)

    # Reset to known state
    cb.state = CBState.CLOSED
    cb.failure_count = 0

    cb.record_failure("fail 1")
    cb.record_failure("fail 2")
    cb.record_failure("fail 3")
    assert cb.state == CBState.OPEN

    time.sleep(1.5)  # Wait for cooldown
    assert cb.allow_request(), "Should allow request after cooldown (HALF_OPEN)"
    cb.record_success()
    assert cb.state == CBState.CLOSED, f"Expected CLOSED after success, got {cb.state}"
    print("PASS: Circuit breaker recovers after cooldown + success")


def test_quality_filter_rejects_low_quality():
    """Harvester should assign low scores to poor tools and high scores to good ones."""
    from harvester import compute_quality_score

    # Low quality: no stars, no description, old
    low_tool = {
        "source": "github",
        "stars": 0,
        "description": "",
        "last_updated": "2020-01-01T00:00:00Z",
        "has_docs": False,
        "readme_length": 0,
    }
    low = compute_quality_score(low_tool)
    assert low < 30, f"Expected <30 for low quality, got {low}"

    # High quality: many stars, good description, recent
    high_tool = {
        "source": "github",
        "stars": 500,
        "description": "A great MCP server for code review with comprehensive docs",
        "last_updated": "2026-03-01T00:00:00Z",
        "has_docs": True,
        "readme_length": 2000,
    }
    high = compute_quality_score(high_tool)
    assert high >= 30, f"Expected >=30 for high quality, got {high}"
    print(f"PASS: Quality filter works (low={low}, high={high})")


def test_classifier_accuracy():
    """Classifier should achieve >= 80% on known test cases."""
    from classifier import classify_tool, VALIDATION_FIXTURES

    correct = 0
    total = len(VALIDATION_FIXTURES)
    misses = []

    for fixture in VALIDATION_FIXTURES:
        result = classify_tool(
            fixture["name"],
            fixture.get("description", ""),
            tags=fixture.get("tags", []),
        )
        if result == fixture["expected"]:
            correct += 1
        else:
            misses.append(f"  {fixture['name']}: expected={fixture['expected']}, got={result}")

    accuracy = correct / total * 100
    assert accuracy >= 80, (
        f"Accuracy {accuracy:.1f}% < 80% ({correct}/{total})\n"
        + "\n".join(misses[:10])
    )
    print(f"PASS: Classifier accuracy {accuracy:.1f}% ({correct}/{total})")
    if misses:
        print(f"  Minor misclassifications ({len(misses)}):")
        for m in misses[:5]:
            print(m)


def test_schema_drift_detection():
    """Schema watchdog should detect when API response structure changes."""
    from schema_watchdog import compare_schemas

    original = {"name": "str", "stars": "int", "topics": ["str"]}

    # Additive change (MINOR)
    added = {"name": "str", "stars": "int", "topics": ["str"], "new_field": "bool"}
    changes = compare_schemas(original, added)
    minor_changes = [c for c in changes if c.severity == "MINOR"]
    assert len(minor_changes) > 0, f"Expected MINOR changes, got: {[c.to_dict() for c in changes]}"

    # Breaking change (MAJOR) - field removed
    removed = {"name": "str", "topics": ["str"]}  # stars removed
    changes = compare_schemas(original, removed)
    major_changes = [c for c in changes if c.severity == "MAJOR"]
    assert len(major_changes) > 0, f"Expected MAJOR changes, got: {[c.to_dict() for c in changes]}"

    print("PASS: Schema drift detection works correctly")


def test_data_auditor_detects_duplicates():
    """Data auditor should find duplicate URLs."""
    from data_auditor import check_duplicates

    tools = [
        {"service_name": "Tool A", "url": "https://example.com/a", "clarvia_score": 8.0},
        {"service_name": "Tool B", "url": "https://example.com/b", "clarvia_score": 7.0},
        {"service_name": "Tool A Copy", "url": "https://example.com/a", "clarvia_score": 6.0},
    ]

    result = check_duplicates(tools)
    assert result["exact_url_duplicates"] > 0, f"Should detect duplicate URL, got: {result}"
    print(f"PASS: Duplicate detection works (exact_url_duplicates={result['exact_url_duplicates']})")


def test_data_auditor_no_false_positives():
    """Data auditor should not flag unique tools as duplicates."""
    from data_auditor import check_duplicates

    tools = [
        {"service_name": "Alpha Tool", "url": "https://alpha.com"},
        {"service_name": "Beta Service", "url": "https://beta.com"},
        {"service_name": "Gamma App", "url": "https://gamma.com"},
    ]

    result = check_duplicates(tools)
    assert result["exact_url_duplicates"] == 0, f"Should not detect duplicates, got: {result}"
    assert result["fuzzy_name_duplicates"] == 0, f"Should not detect fuzzy dupes, got: {result}"
    print("PASS: No false positive duplicates")


def test_classifier_handles_empty_input():
    """Classifier should not crash on empty/null inputs."""
    from classifier import classify_tool

    # Empty strings
    result = classify_tool("", "")
    assert isinstance(result, str), f"Expected string result, got {type(result)}"

    # Unicode
    result = classify_tool("工具名", "这是一个AI工具")
    assert isinstance(result, str)

    # Very long input
    result = classify_tool("x" * 10000, "y" * 10000)
    assert isinstance(result, str)

    print("PASS: Classifier handles edge cases (empty, unicode, long input)")


def test_circuit_breaker_half_open_only_one_probe():
    """In HALF_OPEN state, only one probe request should be allowed."""
    from circuit_breaker import CircuitBreaker, CBState

    cb = CircuitBreaker("chaos_test_halfopen", failure_threshold=3, cooldown_seconds=600)

    cb.state = CBState.CLOSED
    cb.failure_count = 0

    cb.record_failure("f1")
    cb.record_failure("f2")
    cb.record_failure("f3")
    assert cb.state == CBState.OPEN

    # Manually set state to HALF_OPEN to test probe limiting
    cb.state = CBState.HALF_OPEN
    cb._half_open_probe_sent = False

    first = cb.allow_request()  # Should be True (probe)
    assert first, "First request in HALF_OPEN should be allowed"

    second = cb.allow_request()  # Should be False (only one probe)
    assert not second, "Second request in HALF_OPEN should be rejected"

    print("PASS: HALF_OPEN allows exactly one probe request")


if __name__ == "__main__":
    tests = [
        test_circuit_breaker_opens_on_failures,
        test_circuit_breaker_recovers,
        test_quality_filter_rejects_low_quality,
        test_classifier_accuracy,
        test_schema_drift_detection,
        test_data_auditor_detects_duplicates,
        test_data_auditor_no_false_positives,
        test_classifier_handles_empty_input,
        test_circuit_breaker_half_open_only_one_probe,
    ]

    passed = 0
    failed = 0
    errors = []

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            errors.append(f"FAIL: {test.__name__}: {e}")
            print(f"FAIL: {test.__name__}: {e}")

    print(f"\n{'='*60}")
    print(f"Chaos Tests: {passed} passed, {failed} failed out of {len(tests)}")
    if errors:
        print("Failures:")
        for e in errors:
            print(f"  {e}")

    sys.exit(1 if failed else 0)
