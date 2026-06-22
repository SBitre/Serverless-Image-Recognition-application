variable "resource_prefix" {
  description = "Prefix for AWS resource names"
  type        = string
}

variable "aws_region" {
  description = "AWS region for dashboard rendering"
  type        = string
}

variable "lambda_function_name" {
  description = "Widget inspector Lambda function name"
  type        = string
}

variable "main_queue_name" {
  description = "Main SQS inspection queue name"
  type        = string
}

variable "dlq_name" {
  description = "DLQ name for inspection queue"
  type        = string
}

variable "manual_review_queue_name" {
  description = "Manual review SQS queue name"
  type        = string
}

variable "ops_alerts_topic_arn" {
  description = "SNS topic ARN for ops alerts (alarm actions)"
  type        = string
}