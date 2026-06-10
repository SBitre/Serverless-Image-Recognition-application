# ============================================================
# S3 bucket — single bucket, prefix-separated for uploads/ and inspected/
# ============================================================

resource "aws_s3_bucket" "storage" {
  bucket = var.bucket_name
}

resource "aws_s3_bucket_versioning" "storage" {
  bucket = aws_s3_bucket.storage.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "storage" {
  bucket = aws_s3_bucket.storage.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "storage" {
  bucket = aws_s3_bucket.storage.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable EventBridge notifications for this bucket — required for the
# EventBridge rule in the processing module to receive S3 events.
resource "aws_s3_bucket_notification" "storage" {
  bucket      = aws_s3_bucket.storage.id
  eventbridge = true
}

# Lifecycle policy: Standard -> IA (90d) -> Glacier (365d) -> Expire (1095d)
# Applies to all prefixes — uploads/ AND inspected/ both archive on the
# same schedule, which matches the 3-year compliance requirement.
resource "aws_s3_bucket_lifecycle_configuration" "storage" {
  bucket = aws_s3_bucket.storage.id

  rule {
    id     = "compliance-archive"
    status = "Enabled"

    # Empty filter = applies to all objects in the bucket
    filter {}

    transition {
      days          = var.lifecycle_ia_days
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = var.lifecycle_glacier_days
      storage_class = "GLACIER"
    }

    expiration {
      days = var.lifecycle_expire_days
    }

    # Clean up noncurrent versions (versioning is on)
    noncurrent_version_transition {
      noncurrent_days = var.lifecycle_ia_days
      storage_class   = "STANDARD_IA"
    }

    noncurrent_version_expiration {
      noncurrent_days = var.lifecycle_expire_days
    }

    # Abort multipart uploads stuck >7 days
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# ============================================================
# DynamoDB — inspection records table with status GSI
# ============================================================

resource "aws_dynamodb_table" "inspections" {
  name         = var.dynamodb_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "image_id"

  attribute {
    name = "image_id"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  attribute {
    name = "inspection_timestamp"
    type = "S"
  }

  # GSI: query all PASS / FAIL / NEEDS_REVIEW records sorted by time
  global_secondary_index {
    name            = "status-timestamp-index"
    hash_key        = "status"
    range_key       = "inspection_timestamp"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }
}