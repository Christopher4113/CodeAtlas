# S3 bucket for CodeBuild source
resource "aws_s3_bucket" "codebuild_source" {
  bucket = "${var.project_name}-codebuild-source-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name = "${var.project_name}-codebuild-source"
  }
}

# CodeBuild IAM Role
resource "aws_iam_role" "codebuild" {
  name = "${var.project_name}-codebuild-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "codebuild.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-codebuild-role"
  }
}

resource "aws_iam_role_policy" "codebuild_ecr" {
  name = "${var.project_name}-codebuild-ecr"
  role = aws_iam_role.codebuild.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:PutImage"
        ]
        Resource = [
          aws_ecr_repository.server.arn
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy" "codebuild_logs" {
  name = "${var.project_name}-codebuild-logs"
  role = aws_iam_role.codebuild.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = [
          "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/codebuild/${var.project_name}-server-build",
          "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/codebuild/${var.project_name}-server-build:*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy" "codebuild_s3" {
  name = "${var.project_name}-codebuild-s3"
  role = aws_iam_role.codebuild.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion"
        ]
        Resource = [
          "${aws_s3_bucket.codebuild_source.arn}/*"
        ]
      }
    ]
  })
}

# CodeBuild Project
resource "aws_codebuild_project" "server" {
  name         = "${var.project_name}-server-build"
  description  = "Build and push CodeAtlas server Docker image to ECR"
  service_role = aws_iam_role.codebuild.arn

  artifacts {
    type = "NO_ARTIFACTS"
  }

  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "aws/codebuild/standard:7.0"
    type                        = "LINUX_CONTAINER"
    privileged_mode             = true
    image_pull_credentials_type = "CODEBUILD"

    environment_variable {
      name  = "AWS_ACCOUNT_ID"
      value = data.aws_caller_identity.current.account_id
    }

    environment_variable {
      name  = "ECR_REPO_URL"
      value = aws_ecr_repository.server.repository_url
    }
  }

  source {
    type     = "S3"
    location = "${aws_s3_bucket.codebuild_source.id}/server.zip"
    buildspec = <<-EOF
      version: 0.2
      phases:
        pre_build:
          commands:
            - echo Logging in to Amazon ECR...
            - aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 530743905127.dkr.ecr.us-east-1.amazonaws.com
        build:
          commands:
            - echo Building the Docker image...
            - docker build -t codeatlas-server .
            - docker tag codeatlas-server:latest 530743905127.dkr.ecr.us-east-1.amazonaws.com/codeatlas-server:latest
        post_build:
          commands:
            - echo Pushing the Docker image...
            - docker push 530743905127.dkr.ecr.us-east-1.amazonaws.com/codeatlas-server:latest
    EOF
  }

  tags = {
    Name = "${var.project_name}-server-build"
  }
}
