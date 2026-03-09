output "vpc_id" {
  description = "The VPC ID"
  value       = aws_vpc.main.id
}

output "alb_dns_name" {
  description = "The ALB DNS name (server URL)"
  value       = aws_lb.main.dns_name
}
