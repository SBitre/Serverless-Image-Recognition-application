variable "bucket_name" {
  description = "S3 bucket name (must be globally unique)"
  type        = string
}

variable "dynamodb_table_name" {
  description = "DynamoDB table name"
  type        = string
}

variable "lifecycle_ia_days" {
  description = "Days before transition to Standard-IA"
  type        = number
}

variable "lifecycle_glacier_days" {
  description = "Days before transition to Glacier"
  type        = number
}

variable "lifecycle_expire_days" {
  description = "Days before expiration"
  type        = number
}