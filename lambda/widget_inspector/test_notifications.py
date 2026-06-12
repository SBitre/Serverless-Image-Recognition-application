import os
import json
import pytest
from decimal import Decimal
import boto3
from moto import mock_aws
from botocore.exceptions import ClientError
from unittest.mock import patch, MagicMock

# Set environment variables for config BEFORE importing notifications
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_SECURITY_TOKEN"] = "testing"
os.environ["AWS_SESSION_TOKEN"] = "testing"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["INSPECTED_BUCKET"] = "test-inspected-bucket"
os.environ["DYNAMODB_TABLE"] = "wi-inspections"
os.environ["MANUAL_REVIEW_QUEUE_URL"] = "https://sqs.us-east-1.amazonaws.com/123456789012/wi-manual-review-queue"
os.environ["QC_NOTIFICATION_TOPIC_ARN"] = "arn:aws:sns:us-east-1:123456789012:wi-qc-notifications"
os.environ["MANUAL_REVIEW_ALERT_TOPIC_ARN"] = "arn:aws:sns:us-east-1:123456789012:wi-manual-review-alerts"
os.environ["EXPECTED_LABELS"] = '["Screw","Wheel","Circuit Board"]'
os.environ["PASS_CONFIDENCE_THRESHOLD"] = "80"
os.environ["REVIEW_CONFIDENCE_THRESHOLD"] = "70"

from storage import InspectionResult
from notifications import (
    publish_qc_notification,
    publish_manual_review_alert,
    enqueue_manual_review
)

@pytest.fixture
def mock_aws_resources():
    with mock_aws():
        # Setup SQS
        sqs = boto3.resource("sqs", region_name="us-east-1")
        queue = sqs.create_queue(QueueName="wi-manual-review-queue")

        # Setup SNS
        sns = boto3.client("sns", region_name="us-east-1")
        
        # We create topics with matching names to the configured ARNs
        qc_topic = sns.create_topic(Name="wi-qc-notifications")
        review_topic = sns.create_topic(Name="wi-manual-review-alerts")
        
        # Subscribe SQS to topics to capture published messages easily
        sns.subscribe(
            TopicArn=qc_topic["TopicArn"],
            Protocol="sqs",
            Endpoint=queue.attributes["QueueArn"]
        )
        sns.subscribe(
            TopicArn=review_topic["TopicArn"],
            Protocol="sqs",
            Endpoint=queue.attributes["QueueArn"]
        )

        yield sns, queue

@pytest.fixture
def sample_result():
    return InspectionResult(
        image_id="550e8400-e29b-41d4-a716-446655440000",
        image_s3_key="uploads/2026/06/05/550e8400-e29b-41d4-a716-446655440000.jpg",
        image_size_bytes=248192,
        upload_timestamp="2026-06-05T14:29:55.000Z",
        inspection_timestamp="2026-06-05T14:30:00.123Z",
        status="PASS",
        expected_labels=["Screw", "Wheel", "Circuit Board"],
        detected_labels=[
            {"name": "Screw", "confidence": Decimal("92.5")},
            {"name": "Wheel", "confidence": Decimal("85.3")},
            {"name": "Circuit Board", "confidence": Decimal("88.1")}
        ],
        confirmed_labels=["Screw", "Wheel", "Circuit Board"],
        missing_labels=[],
        low_confidence_labels=[],
        pass_threshold=80.0,
        review_threshold=70.0,
        rekognition_request_id="rekog-12345"
    )

@pytest.fixture
def sample_result_review():
    return InspectionResult(
        image_id="660e8400-e29b-41d4-a716-446655440000",
        image_s3_key="uploads/2026/06/05/660e8400-e29b-41d4-a716-446655440000.jpg",
        image_size_bytes=248192,
        upload_timestamp="2026-06-05T14:29:55.000Z",
        inspection_timestamp="2026-06-05T14:30:00.123Z",
        status="NEEDS_REVIEW",
        expected_labels=["Screw", "Wheel", "Circuit Board"],
        detected_labels=[
            {"name": "Screw", "confidence": Decimal("92.5")},
            {"name": "Wheel", "confidence": Decimal("75.3")},
            {"name": "Circuit Board", "confidence": Decimal("88.1")}
        ],
        confirmed_labels=["Screw", "Circuit Board"],
        missing_labels=[],
        low_confidence_labels=[
            {"label": "Wheel", "confidence": Decimal("75.3")}
        ],
        pass_threshold=80.0,
        review_threshold=70.0,
        rekognition_request_id="rekog-12345"
    )

def test_publish_qc_notification_pass_schema(mock_aws_resources, sample_result):
    sns, queue = mock_aws_resources
    
    image_url = "s3://test-bucket/uploads/image.jpg"
    result_url = "s3://test-bucket/inspected/passed/result.json"

    # Publish notification
    publish_qc_notification(sample_result, image_url, result_url)
    
    # Receive from SQS queue (subscribed to SNS topic)
    messages = queue.receive_messages(MaxNumberOfMessages=1)
    assert len(messages) == 1
    
    # SQS SNS message structure: message is wrapped in an SNS envelope
    sqs_body = json.loads(messages[0].body)
    assert sqs_body["Subject"] == "[Widget Inspection] PASS: 550e8400"
    
    payload = json.loads(sqs_body["Message"])
    assert payload["event_type"] == "inspection_complete"
    assert payload["status"] == "PASS"
    assert payload["image_id"] == "550e8400-e29b-41d4-a716-446655440000"
    assert payload["image_s3_url"] == image_url
    assert payload["result_s3_url"] == result_url
    assert payload["summary"] == "Widget PASSED. All 3 expected components detected with high confidence."

def test_publish_qc_notification_fail_schema(mock_aws_resources, sample_result):
    sns, queue = mock_aws_resources
    sample_result.status = "FAIL"
    sample_result.missing_labels = ["Wheel"]
    
    image_url = "s3://test-bucket/uploads/image.jpg"
    result_url = "s3://test-bucket/inspected/failed/result.json"

    # Publish notification
    publish_qc_notification(sample_result, image_url, result_url)
    
    # Receive from SQS
    messages = queue.receive_messages(MaxNumberOfMessages=1)
    assert len(messages) == 1
    sqs_body = json.loads(messages[0].body)
    assert sqs_body["Subject"] == "[Widget Inspection] FAIL: 550e8400"
    
    payload = json.loads(sqs_body["Message"])
    assert payload["event_type"] == "inspection_complete"
    assert payload["status"] == "FAIL"
    assert payload["summary"] == "Widget FAILED. 1 expected component(s) were not detected."

def test_publish_manual_review_alert_schema(mock_aws_resources, sample_result_review):
    sns, queue = mock_aws_resources
    image_url = "s3://test-bucket/uploads/image.jpg"

    publish_manual_review_alert(sample_result_review, image_url)

    messages = queue.receive_messages(MaxNumberOfMessages=1)
    assert len(messages) == 1
    sqs_body = json.loads(messages[0].body)
    
    assert sqs_body["Subject"] == "[Widget Inspection] NEEDS_REVIEW: 660e8400"
    
    payload = json.loads(sqs_body["Message"])
    assert payload["event_type"] == "manual_review_required"
    assert payload["image_id"] == "660e8400-e29b-41d4-a716-446655440000"
    assert payload["image_s3_url"] == image_url
    assert len(payload["low_confidence_labels"]) == 1
    assert payload["low_confidence_labels"][0] == {"label": "Wheel", "confidence": 75.3}
    assert payload["summary"] == "Manual review required: 1 expected label(s) detected with low confidence."

def test_enqueue_manual_review(mock_aws_resources, sample_result_review):
    _, queue = mock_aws_resources
    # Purge queue subscription leftovers
    queue.purge()

    image_url = "s3://test-bucket/uploads/image.jpg"
    
    # Send directly to SQS queue
    enqueue_manual_review(sample_result_review, image_url)

    messages = queue.receive_messages(MaxNumberOfMessages=1)
    assert len(messages) == 1
    
    # Directly SQS message body (not SNS-wrapped)
    payload = json.loads(messages[0].body)
    assert payload["event_type"] == "manual_review_required"
    assert payload["image_id"] == "660e8400-e29b-41d4-a716-446655440000"
    assert payload["image_s3_url"] == image_url
    assert len(payload["low_confidence_labels"]) == 1
    assert payload["low_confidence_labels"][0] == {"label": "Wheel", "confidence": 75.3}

def test_sns_publish_failure_propagates(sample_result):
    image_url = "s3://test-bucket/uploads/image.jpg"
    result_url = "s3://test-bucket/inspected/passed/result.json"

    # Patch Sns client publish call to raise error
    with patch("notifications._SNS.publish", side_effect=ClientError(
        {"Error": {"Code": "InternalError", "Message": "SNS failure"}}, "publish"
    )):
        with pytest.raises(ClientError) as exc_info:
            publish_qc_notification(sample_result, image_url, result_url)
        assert exc_info.value.response["Error"]["Code"] == "InternalError"
