output "raw_bucket" {
  value = aws_s3_bucket.raw.bucket
}
output "lambda_name" {
  value = aws_lambda_function.processor.function_name
}
output "lessons_table" {
  value = aws_dynamodb_table.lessons.name
}
output "students_table" {
  value = aws_dynamodb_table.students.name
}
