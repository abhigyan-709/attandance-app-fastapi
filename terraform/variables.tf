variable "aws_region" {
  type        = string
  description = "AWS region (e.g., ap-south-1)"
}

variable "bucket_name" {
  type        = string
  description = "Existing S3 bucket name"
}

variable "bucket_policy_json" {
  type        = string
  description = "Bucket policy JSON"
}
