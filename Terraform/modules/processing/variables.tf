variable "resource_prefix" {
  description = "Prefix for AWS resource names"
  type        = string
}

variable "bucket_name" {
  description = "S3 bucket name (uploads + inspected)"
  type        = string
}

variable "bucket_arn" {
  description = "S3 bucket ARN"
  type        = string
}

variable "dynamodb_table_name" {
  description = "DynamoDB inspections table name"
  type        = string
}

variable "dynamodb_table_arn" {
  description = "DynamoDB inspections table ARN"
  type        = string
}

variable "qc_notifications_topic_arn" {
  description = "SNS topic ARN for QC notifications"
  type        = string
}

variable "manual_review_alerts_topic_arn" {
  description = "SNS topic ARN for manual review alerts"
  type        = string
}

variable "lambda_zip_path" {
  description = "Path to the Lambda deployment zip"
  type        = string
}

variable "expected_labels" {
  description = "Expected component labels"
  type        = list(string)
}

variable "pass_confidence_threshold" {
  description = "Rekognition confidence >= this confirms a label"
  type        = number
}

variable "review_confidence_threshold" {
  description = "Below pass but >= this triggers manual review"
  type        = number
}

variable "lambda_memory_mb" {
  description = "Lambda memory in MB"
  type        = number
}

variable "lambda_timeout_seconds" {
  description = "Lambda timeout in seconds"
  type        = number
}

variable "lambda_reserved_concurrency" {
  description = "Lambda reserved concurrency limit"
  type        = number
}