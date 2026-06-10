"""
Widget Inspector Lambda — STUB IMPLEMENTATION

This is a placeholder so the processing module can deploy a valid Lambda
before Hope's real implementation lands. It parses the SQS event envelope
to verify the wiring works (EventBridge → SQS → Lambda), logs the extracted
bucket+key, and exits cleanly.

REPLACE THIS FILE via PR once issues #1-#3 are merged.
"""

import json
import logging
import os

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))


def lambda_handler(event, context):
    """Stub handler — logs the parsed event and returns success."""
    logger.info("STUB Lambda invoked. Records: %d", len(event.get("Records", [])))

    for record in event.get("Records", []):
        try:
            # SQS body wraps the EventBridge event
            body = json.loads(record["body"])

            # EventBridge event detail has S3 info
            detail = body.get("detail", {})
            bucket = detail.get("bucket", {}).get("name")
            key = detail.get("object", {}).get("key")

            logger.info(
                "Stub processing: bucket=%s key=%s eventbridge_id=%s",
                bucket, key, body.get("id"),
            )
        except (KeyError, json.JSONDecodeError) as e:
            logger.exception("Failed to parse SQS record: %s", e)
            # Raise so SQS retries → eventually DLQ. Stub is intentionally strict.
            raise

    return {"statusCode": 200, "body": "stub processed"}