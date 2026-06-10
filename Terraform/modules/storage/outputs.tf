output "bucket_name" {
  description = "S3 bucket name"
  value       = aws_s3_bucket.storage.id
}

output "bucket_arn" {
  description = "S3 bucket ARN"
  value       = aws_s3_bucket.storage.arn
}

output "bucket_regional_domain_name" {
  description = "S3 bucket regional domain name"
  value       = aws_s3_bucket.storage.bucket_regional_domain_name
}

output "dynamodb_table_name" {
  description = "DynamoDB table name"
  value       = aws_dynamodb_table.inspections.name
}

output "dynamodb_table_arn" {
  description = "DynamoDB table ARN"
  value       = aws_dynamodb_table.inspections.arn
}

output "dynamodb_status_index_arn" {
  description = "DynamoDB status-timestamp GSI ARN (for IAM policies)"
  value       = "${aws_dynamodb_table.inspections.arn}/index/status-timestamp-index"
}