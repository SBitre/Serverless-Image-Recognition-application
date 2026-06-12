import os

# Set environment variables for config BEFORE importing storage
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

import json
import pytest
from decimal import Decimal
import boto3
from moto import mock_aws

from storage import InspectionResult, write_result_json, write_inspection_record

@pytest.fixture
def mock_aws_resources():
    with mock_aws():
        # Setup S3
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-inspected-bucket")

        # Setup DynamoDB
        ddb = boto3.client("dynamodb", region_name="us-east-1")
        ddb.create_table(
            TableName="wi-inspections",
            KeySchema=[{"AttributeName": "image_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "image_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST"
        )
        yield s3, ddb

def test_storage_operations(mock_aws_resources):
    s3, ddb = mock_aws_resources

    result = InspectionResult(
        image_id="550e8400-e29b-41d4-a716-446655440000",
        image_s3_key="uploads/2026/06/05/550e8400-e29b-41d4-a716-446655440000.jpg",
        image_size_bytes=248192,
        upload_timestamp="2026-06-05T14:29:55.000Z",
        inspection_timestamp="2026-06-05T14:30:00.123Z",
        status="NEEDS_REVIEW",
        expected_labels=["Screw", "Wheel", "Circuit Board"],
        detected_labels=[
            {"name": "Screw", "confidence": Decimal("92.5")},
            {"name": "Wheel", "confidence": Decimal("75.3")}
        ],
        confirmed_labels=["Screw"],
        missing_labels=["Circuit Board"],
        low_confidence_labels=[
            {"label": "Wheel", "confidence": Decimal("75.3")}
        ],
        pass_threshold=80.0,
        review_threshold=70.0,
        rekognition_request_id="rekog-12345"
    )

    lambda_req_id = "lambda-req-54321"

    # 1. Test S3 write and key convention
    s3_key = write_result_json(result, lambda_req_id)
    assert s3_key == "inspected/needs-review/2026/06/05/550e8400-e29b-41d4-a716-446655440000.json"

    # Verify S3 content
    s3_response = s3.get_object(Bucket="test-inspected-bucket", Key=s3_key)
    s3_content = json.loads(s3_response["Body"].read().decode("utf-8"))

    assert s3_content["schema_version"] == "1.0"
    assert s3_content["image_id"] == "550e8400-e29b-41d4-a716-446655440000"
    assert s3_content["status"] == "NEEDS_REVIEW"
    assert isinstance(s3_content["detected_labels"][0]["confidence"], float)
    assert s3_content["detected_labels"][0]["confidence"] == 92.5
    assert s3_content["lambda_request_id"] == lambda_req_id
    assert s3_content["rekognition_request_id"] == "rekog-12345"

    # 2. Test DynamoDB write and schema
    write_inspection_record(result, lambda_req_id)

    # Verify table schema description
    table_desc = ddb.describe_table(TableName="wi-inspections")
    assert table_desc["Table"]["KeySchema"][0]["AttributeName"] == "image_id"

    # Verify database item types and exact match to §10
    db_response = ddb.get_item(
        TableName="wi-inspections",
        Key={"image_id": {"S": "550e8400-e29b-41d4-a716-446655440000"}}
    )
    assert "Item" in db_response
    item = db_response["Item"]

    assert item["image_id"] == {"S": "550e8400-e29b-41d4-a716-446655440000"}
    assert item["image_s3_key"] == {"S": "uploads/2026/06/05/550e8400-e29b-41d4-a716-446655440000.jpg"}
    assert item["image_size_bytes"] == {"N": "248192"}
    assert item["upload_timestamp"] == {"S": "2026-06-05T14:29:55.000Z"}
    assert item["inspection_timestamp"] == {"S": "2026-06-05T14:30:00.123Z"}
    assert item["status"] == {"S": "NEEDS_REVIEW"}
    
    # expected_labels: L
    expected_labels = item["expected_labels"]["L"]
    assert len(expected_labels) == 3
    assert expected_labels[0] == {"S": "Screw"}

    # detected_labels: L with M
    detected_labels = item["detected_labels"]["L"]
    assert len(detected_labels) == 2
    assert detected_labels[0]["M"]["name"] == {"S": "Screw"}
    assert detected_labels[0]["M"]["confidence"] == {"N": "92.5"} # Must be N type

    # Decimal round-trips correctly in DynamoDB get_item response
    assert float(detected_labels[0]["M"]["confidence"]["N"]) == 92.5

    assert item["result_s3_key"] == {"S": s3_key}
    assert item["lambda_request_id"] == {"S": lambda_req_id}
    assert item["rekognition_request_id"] == {"S": "rekog-12345"}

def test_lambda_handler_integration(mock_aws_resources):
    s3, ddb = mock_aws_resources
    from unittest.mock import patch, MagicMock
    from handler import lambda_handler

    # Mock context
    mock_context = MagicMock()
    mock_context.aws_request_id = "test-req-123"

    # Mock event containing a parsed EventBridge S3 Upload record
    sqs_event = {
        "Records": [
            {
                "body": json.dumps({
                    "detail": {
                        "bucket": {"name": "test-inspected-bucket"},
                        "object": {
                            "key": "uploads/2026/06/05/550e8400-e29b-41d4-a716-446655440000.jpg",
                            "size": 248192
                        }
                    },
                    "time": "2026-06-05T14:29:55.000Z"
                })
            }
        ]
    }

    # Dummy Rekognition response returned by inspect_image stub
    dummy_inspection = {
        "status": "PASS",
        "detected_labels": [{"name": "Screw", "confidence": 95.0}],
        "confirmed_labels": ["Screw"],
        "missing_labels": [],
        "low_confidence_labels": [],
        "rekognition_request_id": "rekog-request-777"
    }

    with patch("handler.inspect_image", return_value=dummy_inspection), \
         patch("handler.publish_notification") as mock_publish, \
         patch("handler.send_manual_review_message") as mock_send_message:

        response = lambda_handler(sqs_event, mock_context)

        # Check response status
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body["processed"]) == 1
        assert body["processed"][0]["image_id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert body["processed"][0]["status"] == "PASS"

        # Verify S3 JSON storage output matches
        expected_s3_key = body["processed"][0]["result_s3_key"]
        s3_response = s3.get_object(Bucket="test-inspected-bucket", Key=expected_s3_key)
        s3_content = json.loads(s3_response["Body"].read().decode("utf-8"))
        assert s3_content["image_id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert s3_content["status"] == "PASS"

        # Verify DynamoDB storage matches
        db_response = ddb.get_item(
            TableName="wi-inspections",
            Key={"image_id": {"S": "550e8400-e29b-41d4-a716-446655440000"}}
        )
        assert "Item" in db_response
        assert db_response["Item"]["status"] == {"S": "PASS"}

