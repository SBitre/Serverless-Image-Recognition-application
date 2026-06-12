import boto3
from aws_lambda_powertools import Logger, Tracer

logger = Logger(child=True)
tracer = Tracer()

rekognition = boto3.client("rekognition")


@tracer.capture_method
def detect_labels(bucket: str, key: str, min_confidence: float = 70.0):
    response = rekognition.detect_labels(
        Image={"S3Object": {"Bucket": bucket, "Name": key}},
        MaxLabels=20,
        MinConfidence=min_confidence,
    )
    request_id = response.get("ResponseMetadata", {}).get("RequestId")
    labels = [
        {"name": label["Name"], "confidence": float(label["Confidence"])}
        for label in response.get("Labels", [])
    ]
    return labels, request_id


def evaluate_labels(expected_labels, detected_labels, pass_threshold, review_threshold):
    confirmed = []
    low_confidence = []
    missing = []

    detected_lookup = {label["name"].lower(): label for label in detected_labels}

    for expected in expected_labels:
        match = detected_lookup.get(expected.lower())
        if match is None:
            missing.append(expected)
        elif match["confidence"] < pass_threshold and match["confidence"] >= review_threshold:
            low_confidence.append({"label": expected, "confidence": match["confidence"]})
        elif match["confidence"] >= pass_threshold:
            confirmed.append(expected)
        else:
            missing.append(expected)

    if low_confidence:
        status = "NEEDS_REVIEW"
    elif missing:
        status = "FAIL"
    else:
        status = "PASS"

    return {
        "status": status,
        "confirmed_labels": confirmed,
        "missing_labels": missing,
        "low_confidence_labels": low_confidence,
    }


@tracer.capture_method
def inspect_image(bucket, key, expected_labels, pass_threshold, review_threshold):
    detected_labels, request_id = detect_labels(
        bucket=bucket, key=key, min_confidence=review_threshold
    )
    decision = evaluate_labels(
        expected_labels=expected_labels,
        detected_labels=detected_labels,
        pass_threshold=pass_threshold,
        review_threshold=review_threshold,
    )
    return {
        "detected_labels": detected_labels,
        "rekognition_request_id": request_id,
        **decision,
    }