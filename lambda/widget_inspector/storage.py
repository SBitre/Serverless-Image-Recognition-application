import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional

import boto3
from aws_lambda_powertools import Logger, Tracer

from config import get_config

logger = Logger(child=True)
tracer = Tracer()

_DDB = boto3.client("dynamodb")
_S3 = boto3.client("s3")


# Maps inspection status to its S3 prefix per docs/architecture.md §4.
# This is the SOURCE OF TRUTH — do not generate prefixes by lowercasing status.
STATUS_PREFIX = {
    "PASS": "passed",
    "FAIL": "failed",
    "NEEDS_REVIEW": "needs-review",
}


@dataclass
class InspectionResult:
    image_id: str
    image_s3_key: str
    image_size_bytes: int
    upload_timestamp: str
    inspection_timestamp: str
    status: str
    expected_labels: List[str]
    detected_labels: List[Dict[str, Any]]
    confirmed_labels: List[str]
    missing_labels: List[str]
    low_confidence_labels: List[Dict[str, Any]]
    pass_threshold: float
    review_threshold: float
    rekognition_request_id: Optional[str] = None


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


def build_result_key(status: str, inspection_timestamp: str, image_id: str) -> str:
    if status not in STATUS_PREFIX:
        raise ValueError(f"Unknown status: {status}. Expected one of {list(STATUS_PREFIX.keys())}")
    prefix = STATUS_PREFIX[status]
    date_part = inspection_timestamp.split("T")[0]
    year, month, day = date_part.split("-")
    return f"inspected/{prefix}/{year}/{month}/{day}/{image_id}.json"


@tracer.capture_method
def write_result_json(result: InspectionResult, lambda_request_id: str) -> str:
    config = get_config()
    bucket_name = config["inspected_bucket"]
    s3_key = build_result_key(result.status, result.inspection_timestamp, result.image_id)

    payload = {
        "schema_version": "1.0",
        "image_id": result.image_id,
        "image_s3_key": result.image_s3_key,
        "image_size_bytes": result.image_size_bytes,
        "upload_timestamp": result.upload_timestamp,
        "inspection_timestamp": result.inspection_timestamp,
        "status": result.status,
        "expected_labels": result.expected_labels,
        "detected_labels": [
            {"name": label["name"], "confidence": label["confidence"]}
            for label in result.detected_labels
        ],
        "confirmed_labels": result.confirmed_labels,
        "missing_labels": result.missing_labels,
        "low_confidence_labels": [
            {"label": label["label"], "confidence": label["confidence"]}
            for label in result.low_confidence_labels
        ],
        "thresholds": {
            "pass_confidence": result.pass_threshold,
            "review_confidence": result.review_threshold,
        },
        "lambda_request_id": lambda_request_id,
        "rekognition_request_id": result.rekognition_request_id or "",
    }

    _S3.put_object(
        Bucket=bucket_name,
        Key=s3_key,
        Body=json.dumps(payload, indent=2, cls=DecimalEncoder),
        ContentType="application/json",
    )
    return s3_key


@tracer.capture_method
def write_inspection_record(result: InspectionResult, lambda_request_id: str) -> None:
    config = get_config()
    table_name = config["dynamodb_table"]
    s3_key = build_result_key(result.status, result.inspection_timestamp, result.image_id)

    item = {
        "image_id": {"S": result.image_id},
        "image_s3_key": {"S": result.image_s3_key},
        "image_size_bytes": {"N": str(result.image_size_bytes)},
        "upload_timestamp": {"S": result.upload_timestamp},
        "inspection_timestamp": {"S": result.inspection_timestamp},
        "status": {"S": result.status},
        "expected_labels": {"L": [{"S": label} for label in result.expected_labels]},
        "detected_labels": {
            "L": [
                {"M": {"name": {"S": d["name"]}, "confidence": {"N": str(d["confidence"])}}}
                for d in result.detected_labels
            ]
        },
        "confirmed_labels": {"L": [{"S": label} for label in result.confirmed_labels]},
        "missing_labels": {"L": [{"S": label} for label in result.missing_labels]},
        "low_confidence_labels": {
            "L": [
                {"M": {"label": {"S": d["label"]}, "confidence": {"N": str(d["confidence"])}}}
                for d in result.low_confidence_labels
            ]
        },
        "result_s3_key": {"S": s3_key},
        "lambda_request_id": {"S": lambda_request_id},
        "rekognition_request_id": {"S": result.rekognition_request_id or ""},
    }

    _DDB.put_item(TableName=table_name, Item=item)