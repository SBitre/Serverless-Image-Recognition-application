output "qc_notifications_topic_arn" {
  description = "SNS topic ARN for PASS/FAIL notifications"
  value       = aws_sns_topic.qc_notifications.arn
}

output "manual_review_alerts_topic_arn" {
  description = "SNS topic ARN for NEEDS_REVIEW alerts"
  value       = aws_sns_topic.manual_review_alerts.arn
}

output "ops_alerts_topic_arn" {
  description = "SNS topic ARN for system alerts (Lambda errors, DLQ messages)"
  value       = aws_sns_topic.ops_alerts.arn
}