resource "aws_secretsmanager_secret" "server_env" {
  name        = "${var.project_name}/server-env"
  description = "Environment variables for CodeAtlas server"

  tags = {
    Name = "${var.project_name}-server-env"
  }
}

resource "aws_secretsmanager_secret_version" "server_env" {
  secret_id = aws_secretsmanager_secret.server_env.id
  secret_string = jsonencode({
    PINECONE_API_KEY           = var.pinecone_api_key
    PINECONE_INDEX_NAME        = "codeatlas"
    PINECONE_CLOUD             = "aws"
    PINECONE_REGION            = "us-east-1"
    PINECONE_DIMENSION         = "1536"
    PINECONE_METRIC            = "cosine"
    AWS_REGION                 = "us-east-1"
    BEDROCK_MODEL_ID           = "arn:aws:bedrock:us-east-1:530743905127:application-inference-profile/q5rb8wci4a6f"
    CODEATLAS_NAMESPACE_MODE   = "repo"
    SQS_QUEUE_URL              = "https://sqs.us-east-1.amazonaws.com/530743905127/codeatlas-celery"
    SQS_REGION                 = "us-east-1"
    REDIS_URL                  = "rediss://master.codeatlas-redis.mvhwao.use1.cache.amazonaws.com:6379/0"
  })
}
