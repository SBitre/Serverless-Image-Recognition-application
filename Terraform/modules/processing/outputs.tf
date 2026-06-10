output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.widget_inspector.function_name
}

output "lambda_function_arn" {
  description = "Lambda function ARN"
  value       = aws_lambda_function.widget_inspector.arn
}

output "lambda_role_arn" {
  description = "Lambda execution role ARN"
  value       = aws_iam_role.lambda_exec.arn
}

output "inspection_queue_url" {
  description = "Main SQS inspection queue URL"
  value       = aws_sqs_queue.inspection_main.url
}

output "inspection_queue_arn" {
  description = "Main SQS inspection queue ARN"
  value       = aws_sqs_queue.inspection_main.arn
}

output "inspection_dlq_url" {
  description = "Inspection DLQ URL"
  value       = aws_sqs_queue.inspection_dlq.url
}

output "inspection_dlq_arn" {
  description = "Inspection DLQ ARN"
  value       = aws_sqs_queue.inspection_dlq.arn
}

output "manual_review_queue_url" {
  description = "Manual review SQS queue URL"
  value       = aws_sqs_queue.manual_review.url
}

output "manual_review_queue_arn" {
  description = "Manual review SQS queue ARN"
  value       = aws_sqs_queue.manual_review.arn
}

output "eventbridge_rule_arn" {
  description = "EventBridge rule ARN"
  value       = aws_cloudwatch_event_rule.s3_image_upload.arn
}

output "lambda_log_group_name" {
  description = "CloudWatch log group for Lambda"
  value       = aws_cloudwatch_log_group.lambda.name
}