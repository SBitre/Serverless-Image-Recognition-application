import json
import os


class ConfigError(Exception):
    pass


def required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value


# Module-level singleton — populated on first call, reused across warm invocations
_CONFIG = None


def get_config() -> dict:
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = {
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
    return _CONFIG


def reset_config_cache() -> None:
    """Test helper — clears the singleton so env changes take effect."""
    global _CONFIG
    _CONFIG = None