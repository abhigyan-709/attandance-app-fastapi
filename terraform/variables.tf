variable "aws_region" {
  type        = string
  description = "AWS region"
}

variable "bucket_name" {
  type        = string
  description = "Existing S3 bucket name"
}

variable "bucket_policy_json" {
  type        = string
  description = "Bucket policy JSON"
}
