output "dashboard_name" {
  description = "CloudWatch dashboard name"
  value       = aws_cloudwatch_dashboard.main.dashboard_name
}

output "dashboard_url" {
  description = "Direct link to the CloudWatch dashboard"
  value       = "https://${var.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.main.dashboard_name}"
}

output "lambda_errors_alarm_arn" {
  description = "ARN of the Lambda errors alarm"
  value       = aws_cloudwatch_metric_alarm.lambda_errors.arn
}

output "dlq_messages_alarm_arn" {
  description = "ARN of the DLQ messages alarm"
  value       = aws_cloudwatch_metric_alarm.dlq_messages.arn
}