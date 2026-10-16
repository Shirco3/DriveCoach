data "aws_caller_identity" "current" {}

resource "aws_s3_bucket" "raw" {
  bucket_prefix = "${var.project_name}-raw-"
  force_destroy = true
}
resource "aws_s3_bucket_public_access_block" "raw" {
  bucket                  = aws_s3_bucket.raw.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_server_side_encryption_configuration" "raw" {
  bucket = aws_s3_bucket.raw.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
resource "aws_s3_bucket_ownership_controls" "raw" {
  bucket = aws_s3_bucket.raw.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}
resource "aws_iam_role" "lambda_exec" {
  name = "${var.project_name}-lambda-exec"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
}
resource "aws_iam_role_policy" "lambda_access" {
  name = "${var.project_name}-lambda-access"
  role = aws_iam_role.lambda_exec.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["s3:GetObject"]
        Resource = ["${aws_s3_bucket.raw.arn}/*"]
      },
      {
        Effect = "Allow"
        Action = ["dynamodb:Scan", "dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem"]
        Resource = [aws_dynamodb_table.lessons.arn, aws_dynamodb_table.students.arn]
      },
      {
        Effect = "Allow"
        Action = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = ["arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${var.project_name}-processor:*"]
      }
    ]
  })
}
resource "aws_cloudwatch_log_group" "processor" {
  name = "/aws/lambda/${var.project_name}-processor"
  retention_in_days = 3
}
data "archive_file" "lambda_zip" {
  type = "zip"
  source_dir = "${path.module}/../lambda_package"
  output_path = "${path.module}/lambda_build.zip"
}
resource "aws_lambda_function" "processor" {
  function_name = "${var.project_name}-processor"
  role = aws_iam_role.lambda_exec.arn
  filename = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  runtime = "python3.12"
  handler = "lambda_handler.lambda_handler"
  timeout = 120
  memory_size = 512
  reserved_concurrent_executions = 1
  environment {
    variables = {
      LESSONS_TABLE = aws_dynamodb_table.lessons.name
      STUDENTS_TABLE = aws_dynamodb_table.students.name
    }
  }
  depends_on = [aws_iam_role_policy.lambda_access, aws_cloudwatch_log_group.processor]
}
resource "aws_lambda_permission" "s3" {
  statement_id = "AllowS3Invoke"
  action = "lambda:InvokeFunction"
  function_name = aws_lambda_function.processor.function_name
  principal = "s3.amazonaws.com"
  source_arn = aws_s3_bucket.raw.arn
  source_account = data.aws_caller_identity.current.account_id
}
resource "aws_s3_bucket_notification" "upload" {
  bucket = aws_s3_bucket.raw.id
  lambda_function {
    lambda_function_arn = aws_lambda_function.processor.arn
    events = ["s3:ObjectCreated:*"]
    filter_prefix = "incoming/"
    filter_suffix = ".csv"
  }
  depends_on = [aws_lambda_permission.s3]
}
