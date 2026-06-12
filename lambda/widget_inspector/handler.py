import json
import logging
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import unquote_plus

import boto3

from config import get_config
from inspector import inspect_image
from storage import DecimalEncoder, InspectionResult, write_inspection_record, write_result_json

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

sns = boto3.client("sns")
sqs = boto3.client("sqs")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_sqs_record(record: dict) -> dict:
    body = json.loads(record["body"])

    detail = body.get("detail", {})
    bucket = detail.get("bucket", {}).get("name")
    key = detail.get("object", {}).get("key")
    size = detail.get("object", {}).get("size", 0)
    upload_timestamp = body.get("time")

    if not bucket or not key:
        s3_record = body["Records"][0]["s3"]
        bucket = s3_record["bucket"]["name"]
        key = s3_record["object"]["key"]
        size = s3_record["object"].get("size", 0)
        upload_timestamp = body["Records"][0].get("eventTime")

    key = unquote_plus(key)

    return {
        "bucket": bucket,
        "key": key,
        "size": int(size or 0),
        "upload_timestamp": upload_timestamp,
    }


def get_image_id(key: str) -> str:
    filename = key.split("/")[-1]
    image_id = filename.rsplit(".", 1)[0]

    try:
        uuid.UUID(image_id)
        return image_id
    except ValueError:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, key))



def build_result_payload(
    image_id: str,
    source_key: str,
    image_size: int,
    upload_timestamp: str,
    inspection_timestamp: str,
    inspection: dict,
    config: dict,
    lambda_request_id: str,
) -> dict:
    return {
        "schema_version": "1.0",
        "image_id": image_id,
        "image_s3_key": source_key,
        "image_size_bytes": image_size,
        "upload_timestamp": upload_timestamp,
        "inspection_timestamp": inspection_timestamp,
        "status": inspection["status"],
        "expected_labels": config["expected_labels"],
        "detected_labels": inspection["detected_labels"],
        "confirmed_labels": inspection["confirmed_labels"],
        "missing_labels": inspection["missing_labels"],
        "low_confidence_labels": inspection["low_confidence_labels"],
        "thresholds": {
            "pass_confidence": config["pass_threshold"],
            "review_confidence": config["review_threshold"],
        },
        "lambda_request_id": lambda_request_id,
        "rekognition_request_id": inspection["rekognition_request_id"],
    }





def build_sns_message(payload: dict, source_bucket: str, result_bucket: str, result_key: str) -> dict:
    status = payload["status"]
    expected_count = len(payload["expected_labels"])
    missing_count = len(payload["missing_labels"])
    low_conf_count = len(payload["low_confidence_labels"])

    if status == "PASS":
        summary = f"Widget PASSED. All {expected_count} expected components detected with high confidence."
        event_type = "inspection_complete"
    elif status == "FAIL":
        summary = f"Widget FAILED. {missing_count} expected component(s) were not detected."
        event_type = "inspection_complete"
    else:
        summary = f"Manual review required: {low_conf_count} expected label(s) detected with low confidence."
        event_type = "manual_review_required"

    return {
        "event_type": event_type,
        "status": status,
        "image_id": payload["image_id"],
        "image_s3_url": f"s3://{source_bucket}/{payload['image_s3_key']}",
        "result_s3_url": f"s3://{result_bucket}/{result_key}",
        "missing_labels": payload["missing_labels"],
        "low_confidence_labels": payload["low_confidence_labels"],
        "summary": summary,
    }


def publish_notification(topic_arn: str, payload: dict, source_bucket: str, result_bucket: str, result_key: str) -> None:
    message = build_sns_message(payload, source_bucket, result_bucket, result_key)
    subject = f"[Widget Inspection] {payload['status']}: {payload['image_id'][:8]}"

    sns.publish(
        TopicArn=topic_arn,
        Subject=subject,
        Message=json.dumps(message, indent=2, cls=DecimalEncoder),
    )


def send_manual_review_message(queue_url: str, payload: dict, result_key: str) -> None:
    message = {
        "event_type": "manual_review_required",
        "image_id": payload["image_id"],
        "status": payload["status"],
        "image_s3_key": payload["image_s3_key"],
        "result_s3_key": result_key,
        "low_confidence_labels": payload["low_confidence_labels"],
        "inspection_timestamp": payload["inspection_timestamp"],
    }

    sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(message, cls=DecimalEncoder),
    )


def lambda_handler(event, context):
    config = get_config()
    request_id = getattr(context, "aws_request_id", "local-test")

    logger.info("Widget Inspector invoked. Records=%d", len(event.get("Records", [])))

    processed = []

    for record in event.get("Records", []):
        parsed = parse_sqs_record(record)

        source_bucket = parsed["bucket"]
        source_key = parsed["key"]
        image_id = get_image_id(source_key)
        inspection_timestamp = utc_now()

        logger.info("Processing image_id=%s bucket=%s key=%s", image_id, source_bucket, source_key)

        inspection = inspect_image(
            bucket=source_bucket,
            key=source_key,
            expected_labels=config["expected_labels"],
            pass_threshold=config["pass_threshold"],
            review_threshold=config["review_threshold"],
        )

        result_payload = build_result_payload(
            image_id=image_id,
            source_key=source_key,
            image_size=parsed["size"],
            upload_timestamp=parsed["upload_timestamp"],
            inspection_timestamp=inspection_timestamp,
            inspection=inspection,
            config=config,
            lambda_request_id=request_id,
        )

        result_obj = InspectionResult(
            image_id=image_id,
            image_s3_key=source_key,
            image_size_bytes=parsed["size"],
            upload_timestamp=parsed["upload_timestamp"],
            inspection_timestamp=inspection_timestamp,
            status=inspection["status"],
            expected_labels=config["expected_labels"],
            detected_labels=inspection["detected_labels"],
            confirmed_labels=inspection["confirmed_labels"],
            missing_labels=inspection["missing_labels"],
            low_confidence_labels=inspection["low_confidence_labels"],
            pass_threshold=config["pass_threshold"],
            review_threshold=config["review_threshold"],
            rekognition_request_id=inspection.get("rekognition_request_id") or "",
        )

        result_key = write_result_json(result_obj, request_id)
        write_inspection_record(result_obj, request_id)

        if result_payload["status"] == "NEEDS_REVIEW":
            publish_notification(
                topic_arn=config["manual_review_topic_arn"],
                payload=result_payload,
                source_bucket=source_bucket,
                result_bucket=config["inspected_bucket"],
                result_key=result_key,
            )
            send_manual_review_message(
                queue_url=config["manual_review_queue_url"],
                payload=result_payload,
                result_key=result_key,
            )
        else:
            publish_notification(
                topic_arn=config["qc_topic_arn"],
                payload=result_payload,
                source_bucket=source_bucket,
                result_bucket=config["inspected_bucket"],
                result_key=result_key,
            )

        logger.info("Inspection complete image_id=%s status=%s result_key=%s", image_id, result_payload["status"], result_key)

        processed.append(
            {
                "image_id": image_id,
                "status": result_payload["status"],
                "result_s3_key": result_key,
            }
        )

    return {
        "statusCode": 200,
        "body": json.dumps({"processed": processed}, cls=DecimalEncoder),
    }