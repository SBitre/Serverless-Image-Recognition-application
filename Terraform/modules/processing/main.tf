# ============================================================
# SQS Queues — Main + DLQ + Manual Review
# ============================================================

resource "aws_sqs_queue" "inspection_dlq" {
  name                      = "${var.resource_prefix}-inspection-dlq"
  message_retention_seconds = 1209600 # 14 days (max)
  sqs_managed_sse_enabled   = true
}

resource "aws_sqs_queue" "inspection_main" {
  name                       = "${var.resource_prefix}-inspection-queue"
  visibility_timeout_seconds = 90 # Lambda timeout 30s + buffer
  message_retention_seconds  = 345600 # 4 days
  sqs_managed_sse_enabled    = true

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.inspection_dlq.arn
    maxReceiveCount     = 3
  })
}

resource "aws_sqs_queue" "manual_review" {
  name                       = "${var.resource_prefix}-manual-review-queue"
  visibility_timeout_seconds = 60
  message_retention_seconds  = 1209600 # 14 days
  sqs_managed_sse_enabled    = true
}

# Allow EventBridge to send messages to the main queue
resource "aws_sqs_queue_policy" "allow_eventbridge" {
  queue_url = aws_sqs_queue.inspection_main.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "events.amazonaws.com" }
      Action    = "sqs:SendMessage"
      Resource  = aws_sqs_queue.inspection_main.arn
      Condition = {
        ArnEquals = { "aws:SourceArn" = aws_cloudwatch_event_rule.s3_image_upload.arn }
      }
    }]
  })
}

# ============================================================
# EventBridge Rule — S3 ObjectCreated → SQS
# ============================================================

resource "aws_cloudwatch_event_rule" "s3_image_upload" {
  name        = "${var.resource_prefix}-s3-image-upload-rule"
  description = "Routes S3 image upload events to SQS inspection queue"

  event_pattern = jsonencode({
    source        = ["aws.s3"]
    "detail-type" = ["Object Created"]
    detail = {
      bucket = { name = [var.bucket_name] }
      object = {
        key = [
          { prefix = "uploads/" }
        ]
      }
    }
  })
}

resource "aws_cloudwatch_event_target" "to_sqs" {
  rule      = aws_cloudwatch_event_rule.s3_image_upload.name
  target_id = "SendToInspectionQueue"
  arn       = aws_sqs_queue.inspection_main.arn
}

# ============================================================
# IAM — Lambda Execution Role
# ============================================================

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda_exec" {
  name               = "${var.resource_prefix}-lambda-exec-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

# AWS-managed: CloudWatch Logs write
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# AWS-managed: X-Ray tracing
resource "aws_iam_role_policy_attachment" "lambda_xray" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

# Custom inline policy — application permissions per architecture.md §13
data "aws_iam_policy_document" "lambda_app" {
  statement {
    sid     = "S3ReadUploads"
    actions = ["s3:GetObject"]
    resources = ["${var.bucket_arn}/uploads/*"]
  }

  statement {
    sid     = "S3WriteInspected"
    actions = ["s3:PutObject"]
    resources = ["${var.bucket_arn}/inspected/*"]
  }

  statement {
    sid       = "RekognitionDetect"
    actions   = ["rekognition:DetectLabels"]
    resources = ["*"] # Rekognition doesn't support resource-level perms
  }

  statement {
    sid     = "DynamoDBWrite"
    actions = ["dynamodb:PutItem", "dynamodb:UpdateItem"]
    resources = [
      var.dynamodb_table_arn,
      "${var.dynamodb_table_arn}/index/*"
    ]
  }

  statement {
    sid     = "SQSConsumeMain"
    actions = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
      "sqs:ChangeMessageVisibility"
    ]
    resources = [aws_sqs_queue.inspection_main.arn]
  }

  statement {
    sid       = "SQSSendManualReview"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.manual_review.arn]
  }

  statement {
    sid       = "SNSPublish"
    actions   = ["sns:Publish"]
    resources = [
      var.qc_notifications_topic_arn,
      var.manual_review_alerts_topic_arn
    ]
  }
}

resource "aws_iam_role_policy" "lambda_app" {
  name   = "${var.resource_prefix}-lambda-app-policy"
  role   = aws_iam_role.lambda_exec.id
  policy = data.aws_iam_policy_document.lambda_app.json
}

# ============================================================
# Lambda Function
#
# NOTE: reserved_concurrent_executions intentionally omitted.
# This free-tier AWS account has a default account-wide concurrency
# pool of only 10, and AWS requires keeping at least 10 unreserved.
# Without reservation, Lambda uses the shared pool — fine for this
# workload, but no per-function cost protection. Documented in ADR.
# ============================================================

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.resource_prefix}-widget-inspector"
  retention_in_days = 14
}

resource "aws_lambda_function" "widget_inspector" {
  function_name    = "${var.resource_prefix}-widget-inspector"
  role             = aws_iam_role.lambda_exec.arn
  runtime          = "python3.12"
  handler          = "handler.lambda_handler"
  filename         = var.lambda_zip_path
  source_code_hash = filebase64sha256(var.lambda_zip_path)

  memory_size = var.lambda_memory_mb
  timeout     = var.lambda_timeout_seconds

  tracing_config {
    mode = "Active"
  }

  environment {
    variables = {
      INSPECTED_BUCKET              = var.bucket_name
      DYNAMODB_TABLE                = var.dynamodb_table_name
      MANUAL_REVIEW_QUEUE_URL       = aws_sqs_queue.manual_review.url
      QC_NOTIFICATION_TOPIC_ARN     = var.qc_notifications_topic_arn
      MANUAL_REVIEW_ALERT_TOPIC_ARN = var.manual_review_alerts_topic_arn
      EXPECTED_LABELS               = jsonencode(var.expected_labels)
      PASS_CONFIDENCE_THRESHOLD     = tostring(var.pass_confidence_threshold)
      REVIEW_CONFIDENCE_THRESHOLD   = tostring(var.review_confidence_threshold)
      LOG_LEVEL                     = "INFO"
      POWERTOOLS_SERVICE_NAME       = "widget-inspector"
      POWERTOOLS_METRICS_NAMESPACE  = "WidgetInspector"
    }
  }

  depends_on = [
    aws_iam_role_policy.lambda_app,
    aws_cloudwatch_log_group.lambda,
  ]
}

# Wire SQS → Lambda
resource "aws_lambda_event_source_mapping" "sqs_to_lambda" {
  event_source_arn = aws_sqs_queue.inspection_main.arn
  function_name    = aws_lambda_function.widget_inspector.arn
  batch_size       = 1
  enabled          = true
}