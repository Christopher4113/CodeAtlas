# Dead-letter queue for failed Celery tasks
resource "aws_sqs_queue" "celery_dlq" {
  name                      = "${var.project_name}-celery-dlq"
  message_retention_seconds = 345600 # 4 days
  receive_wait_time_seconds = 20     # long polling

  tags = {
    Name = "${var.project_name}-celery-dlq"
  }
}

# Main Celery task queue
resource "aws_sqs_queue" "celery" {
  name                       = "${var.project_name}-celery"
  visibility_timeout_seconds = 3600   # 1 hour (long-running analyses)
  message_retention_seconds  = 345600 # 4 days
  receive_wait_time_seconds  = 20     # long polling

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.celery_dlq.arn
    maxReceiveCount     = 3
  })

  tags = {
    Name = "${var.project_name}-celery"
  }
}
