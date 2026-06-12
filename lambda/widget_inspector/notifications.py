import json
import logging
from decimal import Decimal
import boto3
from config import get_config
from storage import InspectionResult

logger = logging.getLogger(__name__)

_SNS = boto3.client("sns")
_SQS = boto3.client("sqs")


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


def publish_qc_notification(result: InspectionResult, image_s3_url: str, result_s3_url: str) -> None:
    config = get_config()
    topic_arn = config["qc_topic_arn"]

    expected_count = len(result.expected_labels)
    missing_count = len(result.missing_labels)

    if result.status == "PASS":
        summary = f"Widget PASSED. All {expected_count} expected components detected with high confidence."
    else:
        summary = f"Widget FAILED. {missing_count} expected component(s) were not detected."

    payload = {
        "event_type": "inspection_complete",
        "status": result.status,
        "image_id": result.image_id,
        "image_s3_url": image_s3_url,
        "result_s3_url": result_s3_url,
        "summary": summary
    }

    subject = f"[Widget Inspection] {result.status}: {result.image_id[:8]}"

    # Boto3 client publish raises standard botocore exceptions on failure.
    # We do not catch them so they propagate to the caller to support retries.
    _SNS.publish(
        TopicArn=topic_arn,
        Subject=subject,
        Message=json.dumps(payload, indent=2, cls=DecimalEncoder)
    )


def publish_manual_review_alert(result: InspectionResult, image_s3_url: str) -> None:
    config = get_config()
    topic_arn = config["manual_review_topic_arn"]

    low_conf_count = len(result.low_confidence_labels)
    summary = f"Manual review required: {low_conf_count} expected label(s) detected with low confidence."

    payload = {
        "event_type": "manual_review_required",
        "image_id": result.image_id,
        "image_s3_url": image_s3_url,
        "low_confidence_labels": [
            {
                "label": label["label"],
                "confidence": label["confidence"]
            }
            for label in result.low_confidence_labels
        ],
        "summary": summary
    }

    subject = f"[Widget Inspection] {result.status}: {result.image_id[:8]}"

    _SNS.publish(
        TopicArn=topic_arn,
        Subject=subject,
        Message=json.dumps(payload, indent=2, cls=DecimalEncoder)
    )


def enqueue_manual_review(result: InspectionResult, image_s3_url: str) -> None:
    config = get_config()
    queue_url = config["manual_review_queue_url"]

    low_conf_count = len(result.low_confidence_labels)
    summary = f"Manual review required: {low_conf_count} expected label(s) detected with low confidence."

    payload = {
        "event_type": "manual_review_required",
        "image_id": result.image_id,
        "image_s3_url": image_s3_url,
        "low_confidence_labels": [
            {
                "label": label["label"],
                "confidence": label["confidence"]
            }
            for label in result.low_confidence_labels
        ],
        "summary": summary
    }

    _SQS.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(payload, cls=DecimalEncoder)
    )
