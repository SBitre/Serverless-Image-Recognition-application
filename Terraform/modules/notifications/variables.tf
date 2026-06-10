variable "resource_prefix" {
  description = "Prefix for AWS resource names"
  type        = string
}

variable "qc_notification_emails" {
  description = "Emails subscribed to QC notifications topic"
  type        = list(string)
  default     = []
}

variable "manual_review_emails" {
  description = "Emails subscribed to manual review alerts topic"
  type        = list(string)
  default     = []
}

variable "ops_alert_emails" {
  description = "Emails subscribed to ops alerts topic"
  type        = list(string)
  default     = []
}