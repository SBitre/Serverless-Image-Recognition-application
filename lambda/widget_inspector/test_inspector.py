import os

os.environ["POWERTOOLS_TRACE_DISABLED"] = "1"
os.environ["POWERTOOLS_SERVICE_NAME"] = "widget-inspector"

from unittest.mock import patch, MagicMock

import pytest

from inspector import evaluate_labels, inspect_image


# --- evaluate_labels: decision logic unit tests ---

def test_all_pass_when_all_expected_high_confidence():
    detected = [
        {"name": "Screw", "confidence": 95.0},
        {"name": "Wheel", "confidence": 92.0},
        {"name": "Circuit Board", "confidence": 88.0},
    ]
    result = evaluate_labels(
        expected_labels=["Screw", "Wheel", "Circuit Board"],
        detected_labels=detected,
        pass_threshold=80.0,
        review_threshold=70.0,
    )
    assert result["status"] == "PASS"
    assert result["confirmed_labels"] == ["Screw", "Wheel", "Circuit Board"]
    assert result["missing_labels"] == []
    assert result["low_confidence_labels"] == []


def test_fail_when_one_expected_label_missing():
    detected = [
        {"name": "Screw", "confidence": 95.0},
        {"name": "Wheel", "confidence": 92.0},
    ]
    result = evaluate_labels(
        expected_labels=["Screw", "Wheel", "Circuit Board"],
        detected_labels=detected,
        pass_threshold=80.0,
        review_threshold=70.0,
    )
    assert result["status"] == "FAIL"
    assert "Circuit Board" in result["missing_labels"]
    assert "Screw" in result["confirmed_labels"]


def test_needs_review_when_label_low_confidence():
    detected = [
        {"name": "Screw", "confidence": 95.0},
        {"name": "Wheel", "confidence": 75.0},  # between thresholds
        {"name": "Circuit Board", "confidence": 88.0},
    ]
    result = evaluate_labels(
        expected_labels=["Screw", "Wheel", "Circuit Board"],
        detected_labels=detected,
        pass_threshold=80.0,
        review_threshold=70.0,
    )
    assert result["status"] == "NEEDS_REVIEW"
    assert len(result["low_confidence_labels"]) == 1
    assert result["low_confidence_labels"][0] == {"label": "Wheel", "confidence": 75.0}


def test_needs_review_takes_priority_over_missing():
    detected = [
        {"name": "Screw", "confidence": 95.0},
        {"name": "Wheel", "confidence": 75.0},
    ]
    result = evaluate_labels(
        expected_labels=["Screw", "Wheel", "Circuit Board"],
        detected_labels=detected,
        pass_threshold=80.0,
        review_threshold=70.0,
    )
    assert result["status"] == "NEEDS_REVIEW"
    assert "Circuit Board" in result["missing_labels"]
    assert len(result["low_confidence_labels"]) == 1


def test_case_insensitive_label_matching():
    detected = [
        {"name": "SCREW", "confidence": 95.0},
        {"name": "wheel", "confidence": 92.0},
        {"name": "Circuit Board", "confidence": 88.0},
    ]
    result = evaluate_labels(
        expected_labels=["Screw", "Wheel", "Circuit Board"],
        detected_labels=detected,
        pass_threshold=80.0,
        review_threshold=70.0,
    )
    assert result["status"] == "PASS"


def test_empty_detected_labels_means_all_missing():
    result = evaluate_labels(
        expected_labels=["Screw", "Wheel"],
        detected_labels=[],
        pass_threshold=80.0,
        review_threshold=70.0,
    )
    assert result["status"] == "FAIL"
    assert result["missing_labels"] == ["Screw", "Wheel"]


# --- inspect_image: integration with mocked Rekognition ---

def test_inspect_image_calls_rekognition_and_returns_full_result():
    mock_response = {
        "Labels": [
            {"Name": "Screw", "Confidence": 95.0},
            {"Name": "Wheel", "Confidence": 88.0},
            {"Name": "Circuit Board", "Confidence": 87.0},
        ],
        "ResponseMetadata": {"RequestId": "test-rekog-id-123"},
    }
    with patch("inspector.rekognition.detect_labels", return_value=mock_response) as mock_call:
        result = inspect_image(
            bucket="test-bucket",
            key="uploads/foo.jpg",
            expected_labels=["Screw", "Wheel", "Circuit Board"],
            pass_threshold=80.0,
            review_threshold=70.0,
        )

        mock_call.assert_called_once_with(
            Image={"S3Object": {"Bucket": "test-bucket", "Name": "uploads/foo.jpg"}},
            MaxLabels=20,
            MinConfidence=70.0,
        )
        assert result["status"] == "PASS"
        assert result["rekognition_request_id"] == "test-rekog-id-123"
        assert len(result["detected_labels"]) == 3