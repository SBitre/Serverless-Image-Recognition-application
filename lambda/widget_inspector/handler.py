import json
import uuid
from datetime import datetime, timezone
from urllib.parse import unquote_plus

from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit

from config import get_config
from inspector import inspect_image
from storage import (
    DecimalEncoder,
    InspectionResult,
    write_inspection_record,
    write_result_json,
)
from notifications import (
    publish_qc_notification,
    publish_manual_review_alert,
    enqueue_manual_review,
)

logger = Logger()
tracer = Tracer()
metrics = Metrics(namespace="WidgetInspector")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@tracer.capture_method
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


@logger.inject_lambda_context(log_event=False)
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event, context):
    config = get_config()
    request_id = getattr(context, "aws_request_id", "local-test")

    record_count = len(event.get("Records", []))
    logger.info("Widget Inspector invoked", extra={"record_count": record_count})

    processed = []
    for record in event.get("Records", []):
        try:
            parsed = parse_sqs_record(record)
            source_bucket = parsed["bucket"]
            source_key = parsed["key"]

            image_id = get_image_id(source_key)
            inspection_timestamp = utc_now()

            logger.append_keys(image_id=image_id)
            logger.info("Processing image", extra={"bucket": source_bucket, "key": source_key})

            inspection = inspect_image(
                bucket=source_bucket,
                key=source_key,
                expected_labels=config["expected_labels"],
                pass_threshold=config["pass_threshold"],
                review_threshold=config["review_threshold"],
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
                rekognition_request_id=inspection["rekognition_request_id"],
            )

            result_key = write_result_json(result_obj, request_id)
            write_inspection_record(result_obj, request_id)

            image_s3_url = f"s3://{source_bucket}/{source_key}"
            result_s3_url = f"s3://{config['inspected_bucket']}/{result_key}"

            if result_obj.status == "NEEDS_REVIEW":
                publish_manual_review_alert(result_obj, image_s3_url)
                enqueue_manual_review(result_obj, image_s3_url)
                metrics.add_metric(name="InspectionsNeedsReview", unit=MetricUnit.Count, value=1)
            else:
                publish_qc_notification(result_obj, image_s3_url, result_s3_url)
                if result_obj.status == "PASS":
                    metrics.add_metric(name="InspectionsPassed", unit=MetricUnit.Count, value=1)
                else:
                    metrics.add_metric(name="InspectionsFailed", unit=MetricUnit.Count, value=1)

            logger.info(
                "Inspection complete",
                extra={"status": result_obj.status, "result_key": result_key},
            )

            processed.append(
                {
                    "image_id": image_id,
                    "status": result_obj.status,
                    "result_s3_key": result_key,
                }
            )
        except (KeyError, json.JSONDecodeError):
            logger.exception("Failed to parse SQS record")
            raise

    return {
        "statusCode": 200,
        "body": json.dumps({"processed": processed}, cls=DecimalEncoder),
    }