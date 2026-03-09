output "vpc_id" {
  description = "The VPC ID"
  value       = aws_vpc.main.id
}

output "alb_dns_name" {
  description = "The ALB DNS name (server URL)"
  value       = aws_lb.main.dns_name
}

output "ecr_repository_url" {
  description = "The ECR repository URL for pushing images"
  value       = aws_ecr_repository.server.repository_url
}

output "sqs_queue_url" {
  description = "The SQS queue URL for Celery broker config"
  value       = aws_sqs_queue.celery.url
}

output "sqs_dlq_url" {
  description = "The SQS dead-letter queue URL"
  value       = aws_sqs_queue.celery_dlq.url
}

output "redis_endpoint" {
  description = "The ElastiCache Redis endpoint for job store"
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
}
