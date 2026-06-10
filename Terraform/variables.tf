variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name used in tags"
  type        = string
  default     = "widget-inspector"
}

variable "resource_prefix" {
  description = "Prefix for AWS resource names"
  type        = string
  default     = "wi"
}

variable "team_name" {
  description = "Team identifier for Owner tag"
  type        = string
  default     = "team-northeastern-itc6450"
}

variable "expected_labels" {
  description = "Expected component labels for widget inspection"
  type        = list(string)
  default     = ["Screw", "Wheel", "Circuit Board"]
}

variable "pass_confidence_threshold" {
  description = "Rekognition confidence >= this value confirms a label"
  type        = number
  default     = 80
}

variable "review_confidence_threshold" {
  description = "Below pass threshold but >= this value triggers manual review"
  type        = number
  default     = 70
}

variable "lambda_memory_mb" {
  description = "Lambda function memory in MB"
  type        = number
  default     = 512
}

variable "lambda_timeout_seconds" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 30
}

variable "lambda_reserved_concurrency" {
  description = "Lambda reserved concurrency limit (cost protection)"
  type        = number
  default     = 10
}

variable "qc_notification_emails" {
  description = "Emails subscribed to qc-notifications SNS topic"
  type        = list(string)
  default     = []
}

variable "manual_review_emails" {
  description = "Emails subscribed to manual-review-alerts SNS topic"
  type        = list(string)
  default     = []
}

variable "ops_alert_emails" {
  description = "Emails subscribed to ops-alerts SNS topic"
  type        = list(string)
  default     = []
}

variable "lifecycle_ia_days" {
  description = "Days before transition to Standard-IA"
  type        = number
  default     = 90
}

variable "lifecycle_glacier_days" {
  description = "Days before transition to Glacier"
  type        = number
  default     = 365
}

variable "lifecycle_expire_days" {
  description = "Days before object expiration (3-year compliance)"
  type        = number
  default     = 1095
}

variable "billing_alarm_threshold_usd" {
  description = "Estimated charges threshold for billing alarm (USD)"
  type        = number
  default     = 5
}