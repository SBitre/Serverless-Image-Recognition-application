# Random suffix for globally-unique resource names (S3 bucket)
resource "random_id" "suffix" {
  byte_length = 4
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
  region     = data.aws_region.current.name

  # S3 bucket name must be globally unique across all AWS
  bucket_name = "${var.resource_prefix}-storage-${local.account_id}-${random_id.suffix.hex}"
}

module "storage" {
  source = "./modules/storage"

  bucket_name            = local.bucket_name
  dynamodb_table_name    = "${var.resource_prefix}-inspections"
  lifecycle_ia_days      = var.lifecycle_ia_days
  lifecycle_glacier_days = var.lifecycle_glacier_days
  lifecycle_expire_days  = var.lifecycle_expire_days
}

module "notifications" {
  source = "./modules/notifications"

  resource_prefix        = var.resource_prefix
  qc_notification_emails = var.qc_notification_emails
  manual_review_emails   = var.manual_review_emails
  ops_alert_emails       = var.ops_alert_emails
}