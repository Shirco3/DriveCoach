resource "aws_dynamodb_table" "students" {
  name = "${var.project_name}-students"
  billing_mode = "PAY_PER_REQUEST"
  hash_key = "student_id"
  attribute {
    name = "student_id"
    type = "S"
  }
  server_side_encryption {
    enabled = true
  }
  point_in_time_recovery {
    enabled = false
  }
}
resource "aws_dynamodb_table" "lessons" {
  name = "${var.project_name}-lessons"
  billing_mode = "PAY_PER_REQUEST"
  hash_key = "lesson_id"
  attribute {
    name = "lesson_id"
    type = "S"
  }
  server_side_encryption {
    enabled = true
  }
  point_in_time_recovery {
    enabled = false
  }
}
