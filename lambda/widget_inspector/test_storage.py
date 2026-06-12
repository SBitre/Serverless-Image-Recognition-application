import os
import json
import pytest
from decimal import Decimal
import boto3
from moto import mock_aws

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

@pytest.fixture
def sample_result():
    return InspectionResult(
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

def test_s3_key_naming_convention(mock_aws_resources, sample_result):
    s3, _ = mock_aws_resources
    s3_key = write_result_json(sample_result, "lambda-req-54321")
    
    # Conventions check: inspected/{status_lower_dashed}/{yyyy}/{mm}/{dd}/{image_id}.json
    assert s3_key == "inspected/needs-review/2026/06/05/550e8400-e29b-41d4-a716-446655440000.json"

def test_s3_result_json_schema(mock_aws_resources, sample_result):
    s3, _ = mock_aws_resources
    s3_key = write_result_json(sample_result, "lambda-req-54321")

    # Fetch and check content
    response = s3.get_object(Bucket="test-inspected-bucket", Key=s3_key)
    content = json.loads(response["Body"].read().decode("utf-8"))

    # Assert schema matches §11 specifications
    assert content["schema_version"] == "1.0"
    assert content["image_id"] == "550e8400-e29b-41d4-a716-446655440000"
    assert content["image_s3_key"] == "uploads/2026/06/05/550e8400-e29b-41d4-a716-446655440000.jpg"
    assert content["image_size_bytes"] == 248192
    assert content["upload_timestamp"] == "2026-06-05T14:29:55.000Z"
    assert content["inspection_timestamp"] == "2026-06-05T14:30:00.123Z"
    assert content["status"] == "NEEDS_REVIEW"
    assert content["expected_labels"] == ["Screw", "Wheel", "Circuit Board"]
    assert content["confirmed_labels"] == ["Screw"]
    assert content["missing_labels"] == ["Circuit Board"]
    assert content["thresholds"] == {
        "pass_confidence": 80.0,
        "review_confidence": 70.0
    }
    assert content["lambda_request_id"] == "lambda-req-54321"

def test_decimal_serialization_round_trip(mock_aws_resources, sample_result):
    s3, _ = mock_aws_resources
    
    # Ensures no serialization error occurs when converting decimals to float
    s3_key = write_result_json(sample_result, "lambda-req-54321")
    
    response = s3.get_object(Bucket="test-inspected-bucket", Key=s3_key)
    content = json.loads(response["Body"].read().decode("utf-8"))
    
    # Assert decimals round-trip correctly as floats in S3 json
    assert isinstance(content["detected_labels"][0]["confidence"], float)
    assert content["detected_labels"][0]["confidence"] == 92.5
    assert content["low_confidence_labels"][0]["confidence"] == 75.3

def test_dynamodb_record_schema_compliance(mock_aws_resources, sample_result):
    _, ddb = mock_aws_resources
    write_inspection_record(sample_result, "lambda-req-54321")

    # Verify table key schema
    table_desc = ddb.describe_table(TableName="wi-inspections")
    assert table_desc["Table"]["KeySchema"][0]["AttributeName"] == "image_id"

    # Get written record and verify types exactly matching §10
    db_response = ddb.get_item(
        TableName="wi-inspections",
        Key={"image_id": {"S": "550e8400-e29b-41d4-a716-446655440000"}}
    )
    assert "Item" in db_response
    item = db_response["Item"]

    # Assert correct types
    assert item["image_id"] == {"S": "550e8400-e29b-41d4-a716-446655440000"}
    assert item["image_s3_key"] == {"S": "uploads/2026/06/05/550e8400-e29b-41d4-a716-446655440000.jpg"}
    assert item["image_size_bytes"] == {"N": "248192"}
    assert item["upload_timestamp"] == {"S": "2026-06-05T14:29:55.000Z"}
    assert item["inspection_timestamp"] == {"S": "2026-06-05T14:30:00.123Z"}
    assert item["status"] == {"S": "NEEDS_REVIEW"}
    assert item["expected_labels"] == {"L": [{"S": "Screw"}, {"S": "Wheel"}, {"S": "Circuit Board"}]}
    assert item["confirmed_labels"] == {"L": [{"S": "Screw"}]}
    assert item["missing_labels"] == {"L": [{"S": "Circuit Board"}]}
    assert item["result_s3_key"] == {"S": "inspected/needs-review/2026/06/05/550e8400-e29b-41d4-a716-446655440000.json"}
    assert item["lambda_request_id"] == {"S": "lambda-req-54321"}
    assert item["rekognition_request_id"] == {"S": "rekog-12345"}

    # Assert detected confidence is stored as type N (number), not S
    detected_labels = item["detected_labels"]["L"]
    assert len(detected_labels) == 2
    assert detected_labels[0]["M"]["name"] == {"S": "Screw"}
    assert detected_labels[0]["M"]["confidence"] == {"N": "92.5"}

    # Assert low confidence labels is stored correctly
    low_conf_labels = item["low_confidence_labels"]["L"]
    assert len(low_conf_labels) == 1
    assert low_conf_labels[0]["M"]["label"] == {"S": "Wheel"}
    assert low_conf_labels[0]["M"]["confidence"] == {"N": "75.3"}

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
         patch("handler.publish_qc_notification"), \
         patch("handler.publish_manual_review_alert"), \
         patch("handler.enqueue_manual_review"):

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
