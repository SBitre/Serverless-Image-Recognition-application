import json
import os


class ConfigError(Exception):
    pass


def required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value


def get_config() -> dict:
    return {
        "inspected_bucket": required_env("INSPECTED_BUCKET"),
        "dynamodb_table": required_env("DYNAMODB_TABLE"),
        "manual_review_queue_url": required_env("MANUAL_REVIEW_QUEUE_URL"),
        "qc_topic_arn": required_env("QC_NOTIFICATION_TOPIC_ARN"),
        "manual_review_topic_arn": required_env("MANUAL_REVIEW_ALERT_TOPIC_ARN"),
        "expected_labels": json.loads(required_env("EXPECTED_LABELS")),
        "pass_threshold": float(required_env("PASS_CONFIDENCE_THRESHOLD")),
        "review_threshold": float(required_env("REVIEW_CONFIDENCE_THRESHOLD")),
        "log_level": os.environ.get("LOG_LEVEL", "INFO"),
    }