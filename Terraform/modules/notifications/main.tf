# ============================================================
# SNS Topics — QC, Manual Review, Ops Alerts
# ============================================================

resource "aws_sns_topic" "qc_notifications" {
  name = "${var.resource_prefix}-qc-notifications"
}

resource "aws_sns_topic" "manual_review_alerts" {
  name = "${var.resource_prefix}-manual-review-alerts"
}

resource "aws_sns_topic" "ops_alerts" {
  name = "${var.resource_prefix}-ops-alerts"
}

# ============================================================
# Email subscriptions — confirmation emails sent on apply
# ============================================================

resource "aws_sns_topic_subscription" "qc_emails" {
  for_each  = toset(var.qc_notification_emails)
  topic_arn = aws_sns_topic.qc_notifications.arn
  protocol  = "email"
  endpoint  = each.value
}

resource "aws_sns_topic_subscription" "manual_review_emails" {
  for_each  = toset(var.manual_review_emails)
  topic_arn = aws_sns_topic.manual_review_alerts.arn
  protocol  = "email"
  endpoint  = each.value
}

resource "aws_sns_topic_subscription" "ops_emails" {
  for_each  = toset(var.ops_alert_emails)
  topic_arn = aws_sns_topic.ops_alerts.arn
  protocol  = "email"
  endpoint  = each.value
}