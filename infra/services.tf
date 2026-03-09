# ECS Task Definition for Server (FastAPI)
resource "aws_ecs_task_definition" "server" {
  family                   = "${var.project_name}-server"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.ecs_exec.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "server"
      image     = "${aws_ecr_repository.server.repository_url}:latest"
      essential = true
      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]
      secrets = [
        { name = "PINECONE_API_KEY", valueFrom = "${aws_secretsmanager_secret.server_env.arn}:PINECONE_API_KEY::" },
        { name = "PINECONE_INDEX_NAME", valueFrom = "${aws_secretsmanager_secret.server_env.arn}:PINECONE_INDEX_NAME::" },
        { name = "PINECONE_CLOUD", valueFrom = "${aws_secretsmanager_secret.server_env.arn}:PINECONE_CLOUD::" },
        { name = "PINECONE_REGION", valueFrom = "${aws_secretsmanager_secret.server_env.arn}:PINECONE_REGION::" },
        { name = "PINECONE_DIMENSION", valueFrom = "${aws_secretsmanager_secret.server_env.arn}:PINECONE_DIMENSION::" },
        { name = "PINECONE_METRIC", valueFrom = "${aws_secretsmanager_secret.server_env.arn}:PINECONE_METRIC::" },
        { name = "AWS_REGION", valueFrom = "${aws_secretsmanager_secret.server_env.arn}:AWS_REGION::" },
        { name = "BEDROCK_MODEL_ID", valueFrom = "${aws_secretsmanager_secret.server_env.arn}:BEDROCK_MODEL_ID::" },
        { name = "CODEATLAS_NAMESPACE_MODE", valueFrom = "${aws_secretsmanager_secret.server_env.arn}:CODEATLAS_NAMESPACE_MODE::" },
        { name = "SQS_QUEUE_URL", valueFrom = "${aws_secretsmanager_secret.server_env.arn}:SQS_QUEUE_URL::" },
        { name = "SQS_REGION", valueFrom = "${aws_secretsmanager_secret.server_env.arn}:SQS_REGION::" },
        { name = "REDIS_URL", valueFrom = "${aws_secretsmanager_secret.server_env.arn}:REDIS_URL::" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.server.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "server"
        }
      }
    }
  ])

  tags = {
    Name = "${var.project_name}-server"
  }
}

# ECS Task Definition for Worker (Celery)
resource "aws_ecs_task_definition" "worker" {
  family                   = "${var.project_name}-worker"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "1024"
  memory                   = "2048"
  execution_role_arn       = aws_iam_role.ecs_exec.arn
  task_role_arn            = aws_iam_role.ecs_task_worker.arn

  container_definitions = jsonencode([
    {
      name      = "worker"
      image     = "${aws_ecr_repository.server.repository_url}:latest"
      essential = true
      command   = ["celery", "-A", "celery_app", "worker", "--loglevel=info", "--concurrency=2"]
      secrets = [
        { name = "PINECONE_API_KEY", valueFrom = "${aws_secretsmanager_secret.server_env.arn}:PINECONE_API_KEY::" },
        { name = "PINECONE_INDEX_NAME", valueFrom = "${aws_secretsmanager_secret.server_env.arn}:PINECONE_INDEX_NAME::" },
        { name = "PINECONE_CLOUD", valueFrom = "${aws_secretsmanager_secret.server_env.arn}:PINECONE_CLOUD::" },
        { name = "PINECONE_REGION", valueFrom = "${aws_secretsmanager_secret.server_env.arn}:PINECONE_REGION::" },
        { name = "PINECONE_DIMENSION", valueFrom = "${aws_secretsmanager_secret.server_env.arn}:PINECONE_DIMENSION::" },
        { name = "PINECONE_METRIC", valueFrom = "${aws_secretsmanager_secret.server_env.arn}:PINECONE_METRIC::" },
        { name = "AWS_REGION", valueFrom = "${aws_secretsmanager_secret.server_env.arn}:AWS_REGION::" },
        { name = "BEDROCK_MODEL_ID", valueFrom = "${aws_secretsmanager_secret.server_env.arn}:BEDROCK_MODEL_ID::" },
        { name = "CODEATLAS_NAMESPACE_MODE", valueFrom = "${aws_secretsmanager_secret.server_env.arn}:CODEATLAS_NAMESPACE_MODE::" },
        { name = "SQS_QUEUE_URL", valueFrom = "${aws_secretsmanager_secret.server_env.arn}:SQS_QUEUE_URL::" },
        { name = "SQS_REGION", valueFrom = "${aws_secretsmanager_secret.server_env.arn}:SQS_REGION::" },
        { name = "REDIS_URL", valueFrom = "${aws_secretsmanager_secret.server_env.arn}:REDIS_URL::" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.worker.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "worker"
        }
      }
    }
  ])

  tags = {
    Name = "${var.project_name}-worker"
  }
}

# ECS Service for Server
resource "aws_ecs_service" "server" {
  name            = "${var.project_name}-server"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.server.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = [aws_subnet.private_1.id, aws_subnet.private_2.id]
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.server.arn
    container_name   = "server"
    container_port   = 8000
  }

  depends_on = [aws_lb_listener.http]

  tags = {
    Name = "${var.project_name}-server"
  }
}

# ECS Service for Worker
resource "aws_ecs_service" "worker" {
  name            = "${var.project_name}-worker"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.worker.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = [aws_subnet.private_1.id, aws_subnet.private_2.id]
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  tags = {
    Name = "${var.project_name}-worker"
  }
}
