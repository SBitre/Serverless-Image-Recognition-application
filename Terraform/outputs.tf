output "bucket_name" {
  description = "S3 bucket name (uploads/ and inspected/ prefixes)"
  value       = module.storage.bucket_name
}

output "bucket_arn" {
  description = "S3 bucket ARN"
  value       = module.storage.bucket_arn
}

output "dynamodb_table_name" {
  description = "DynamoDB inspection records table"
  value       = module.storage.dynamodb_table_name
}

output "dynamodb_table_arn" {
  description = "DynamoDB inspection records table ARN"
  value       = module.storage.dynamodb_table_arn
}

output "qc_notifications_topic_arn" {
  description = "SNS topic for QC PASS/FAIL notifications"
  value       = module.notifications.qc_notifications_topic_arn
}

output "manual_review_alerts_topic_arn" {
  description = "SNS topic for manual review alerts"
  value       = module.notifications.manual_review_alerts_topic_arn
}

output "ops_alerts_topic_arn" {
  description = "SNS topic for system/ops alerts"
  value       = module.notifications.ops_alerts_topic_arn
}