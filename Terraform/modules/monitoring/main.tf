# ============================================================
# CloudWatch Alarms — Errors, DLQ, Duration
# ============================================================

resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${var.resource_prefix}-lambda-errors-alarm"
  alarm_description   = "Triggers when widget inspector Lambda errors in last 5 min"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = var.lambda_function_name
  }

  alarm_actions = [var.ops_alerts_topic_arn]
  ok_actions    = [var.ops_alerts_topic_arn]
}

resource "aws_cloudwatch_metric_alarm" "dlq_messages" {
  alarm_name          = "${var.resource_prefix}-dlq-messages-alarm"
  alarm_description   = "Triggers when messages land in the inspection DLQ"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Maximum"
  threshold           = 0
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = var.dlq_name
  }

  alarm_actions = [var.ops_alerts_topic_arn]
  ok_actions    = [var.ops_alerts_topic_arn]
}

resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  alarm_name          = "${var.resource_prefix}-lambda-duration-alarm"
  alarm_description   = "Triggers when Lambda p95 duration exceeds 10 seconds"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = 300
  extended_statistic  = "p95"
  threshold           = 10000 # ms
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = var.lambda_function_name
  }

  alarm_actions = [var.ops_alerts_topic_arn]
  ok_actions    = [var.ops_alerts_topic_arn]
}

# ============================================================
# CloudWatch Dashboard
# ============================================================

resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.resource_prefix}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      # Row 1: Lambda invocations + errors + duration
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", var.lambda_function_name],
            [".", "Errors", ".", "."],
            [".", "Throttles", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Lambda Invocations / Errors / Throttles"
          period  = 60
          stat    = "Sum"
        }
      },
      {
        type   = "metric"
        x      = 8
        y      = 0
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["AWS/Lambda", "Duration", "FunctionName", var.lambda_function_name, { stat = "Average" }],
            ["...", { stat = "p95" }],
            ["...", { stat = "Maximum" }]
          ]
          view   = "timeSeries"
          region = var.aws_region
          title  = "Lambda Duration (avg / p95 / max)"
          period = 60
          yAxis  = { left = { label = "milliseconds", showUnits = false } }
        }
      },
      {
        type   = "metric"
        x      = 16
        y      = 0
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["WidgetInspector", "ColdStart", "function_name", var.lambda_function_name, "service", "widget-inspector"]
          ]
          view   = "timeSeries"
          region = var.aws_region
          title  = "Lambda Cold Starts"
          period = 60
          stat   = "Sum"
        }
      },
      # Row 2: SQS queue depths
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", var.main_queue_name]
          ]
          view   = "timeSeries"
          region = var.aws_region
          title  = "Main Inspection Queue Depth"
          period = 60
          stat   = "Maximum"
        }
      },
      {
        type   = "metric"
        x      = 8
        y      = 6
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", var.dlq_name]
          ]
          view       = "timeSeries"
          region     = var.aws_region
          title      = "DLQ Depth (should be 0)"
          period     = 60
          stat       = "Maximum"
          annotations = {
            horizontal = [{ value = 0, label = "Healthy", color = "#2ca02c" }]
          }
        }
      },
      {
        type   = "metric"
        x      = 16
        y      = 6
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", var.manual_review_queue_name]
          ]
          view   = "timeSeries"
          region = var.aws_region
          title  = "Manual Review Queue Depth"
          period = 60
          stat   = "Maximum"
        }
      },
      # Row 3: Inspection outcomes (custom Powertools metrics)
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["WidgetInspector", "InspectionsPassed", "service", "widget-inspector", { label = "PASS", color = "#2ca02c" }],
            [".", "InspectionsFailed", ".", ".", { label = "FAIL", color = "#d62728" }],
            [".", "InspectionsNeedsReview", ".", ".", { label = "NEEDS_REVIEW", color = "#ff7f0e" }]
          ]
          view   = "timeSeries"
          region = var.aws_region
          title  = "Inspection Outcomes"
          period = 60
          stat   = "Sum"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 12
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["WidgetInspector", "InspectionsPassed", "service", "widget-inspector"],
            [".", "InspectionsFailed", ".", "."],
            [".", "InspectionsNeedsReview", ".", "."]
          ]
          view   = "pie"
          region = var.aws_region
          title  = "Outcome Distribution (last hour)"
          stat   = "Sum"
          period = 3600
        }
      },
      # Row 4: Recent logs
      {
        type   = "log"
        x      = 0
        y      = 18
        width  = 24
        height = 6
        properties = {
          query  = "SOURCE '/aws/lambda/${var.lambda_function_name}' | fields @timestamp, image_id, status, result_key | filter ispresent(status) | sort @timestamp desc | limit 20"
          region = var.aws_region
          title  = "Recent Inspections (structured log query)"
          view   = "table"
        }
      }
    ]
  })
}