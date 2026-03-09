# ElastiCache Subnet Group (private subnets)
resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.project_name}-redis-subnet-group"
  subnet_ids = [aws_subnet.private_1.id, aws_subnet.private_2.id]

  tags = {
    Name = "${var.project_name}-redis-subnet-group"
  }
}

# ElastiCache Redis Cluster (single node)
resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "${var.project_name}-redis"
  engine               = "redis"
  engine_version       = "7.1"
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
  subnet_group_name    = aws_elasticache_subnet_group.main.name
  security_group_ids           = [aws_security_group.redis.id]
  transit_encryption_enabled   = true

  tags = {
    Name = "${var.project_name}-redis"
  }
}
