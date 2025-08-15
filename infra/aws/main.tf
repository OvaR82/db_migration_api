terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

# ---------- ECR ----------
resource "aws_ecr_repository" "api" {
  name                  = "${var.project}-api"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
}

# ---------- VPC / Subnets ----------
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# ---------- Security Groups ----------
resource "aws_security_group" "rds" {
  name        = "${var.project}-rds-sg"
  description = "Allow Postgres from App Runner"
  vpc_id      = data.aws_vpc.default.id
}

resource "aws_security_group" "apprunner" {
  name        = "${var.project}-apprunner-sg"
  description = "App Runner VPC connector SG"
  vpc_id      = data.aws_vpc.default.id
}

# Allow 5432 from App Runner SG to RDS
resource "aws_security_group_rule" "rds_from_apprunner" {
  type                     = "ingress"
  security_group_id        = aws_security_group.rds.id
  source_security_group_id = aws_security_group.apprunner.id
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
}

# ---------- RDS PostgreSQL ----------
resource "aws_db_subnet_group" "db" {
  name       = "${var.project}-db-subnets"
  subnet_ids = data.aws_subnets.default.ids
}

resource "aws_db_instance" "postgres" {
  identifier             = "${var.project}-pg"
  engine                 = "postgres"
  engine_version         = "16"
  instance_class         = "db.t3.micro"
  allocated_storage      = 20

  username               = var.db_user
  password               = var.db_password
  db_name                = var.db_name

  db_subnet_group_name   = aws_db_subnet_group.db.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  publicly_accessible    = false
  skip_final_snapshot    = true
}

# ---------- Secrets Manager (DATABASE_URL) ----------
resource "aws_secretsmanager_secret" "db_url" {
  name = "${var.project}/DATABASE_URL"
}

resource "aws_secretsmanager_secret_version" "db_url_ver" {
  secret_id     = aws_secretsmanager_secret.db_url.id
  secret_string = "postgresql+psycopg://${var.db_user}:${var.db_password}@${aws_db_instance.postgres.address}:5432/${var.db_name}"
}

data "aws_iam_policy_document" "secrets_read" {
  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [aws_secretsmanager_secret.db_url.arn]
  }
}

resource "aws_iam_policy" "secrets_read" {
  name   = "${var.project}-apprunner-secrets-read"
  policy = data.aws_iam_policy_document.secrets_read.json
}

resource "aws_iam_role_policy_attachment" "attach" {
  role       = aws_iam_role.apprunner_role.name
  policy_arn = aws_iam_policy.secrets_read.arn
}

# ECS Fargate + ALB for the API

# Log group
resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/${var.project}-api"
  retention_in_days = 14
}

# ALB Security Group (public HTTP access)
resource "aws_security_group" "alb" {
  name        = "${var.project}-alb-sg"
  description = "ALB public"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "HTTP from anywhere"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ECS Service SG (allow traffic only from the ALB)
resource "aws_security_group" "service" {
  name        = "${var.project}-svc-sg"
  description = "ECS service"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "From ALB"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Allow ECS → RDS (replaces the previous App Runner rule)
resource "aws_security_group_rule" "rds_from_ecs" {
  type                     = "ingress"
  security_group_id        = aws_security_group.rds.id
  source_security_group_id = aws_security_group.service.id
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
}

# ALB
resource "aws_lb" "api" {
  name               = "${var.project}-alb"
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = data.aws_subnets.default.ids
}

resource "aws_lb_target_group" "api" {
  name        = "${var.project}-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = data.aws_vpc.default.id
  target_type = "ip"

  health_check {
    enabled             = true
    path                = "/health/ready"
    matcher             = "200-399"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.api.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

# ECS Cluster
resource "aws_ecs_cluster" "api" {
  name = "${var.project}-cluster"
}

# IAM Roles for ECS tasks
data "aws_iam_policy_document" "ecs_task_assume" {
  statement {
    effect = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ecs_task_execution" {
  name               = "${var.project}-task-exec"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume.json
}

# Attach default ECS execution policy (for ECR, logs, etc.)
resource "aws_iam_role_policy_attachment" "ecs_exec_policy" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Permission to read Secrets Manager (DATABASE_URL)
data "aws_iam_policy_document" "secrets_read" {
  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [aws_secretsmanager_secret.db_url.arn]
  }
}

resource "aws_iam_policy" "secrets_read" {
  name   = "${var.project}-ecs-secrets-read"
  policy = data.aws_iam_policy_document.secrets_read.json
}

resource "aws_iam_role_policy_attachment" "attach_secrets_read" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = aws_iam_policy.secrets_read.arn
}

# Fargate Task Definition
resource "aws_ecs_task_definition" "api" {
  family                   = "${var.project}-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn

  container_definitions = jsonencode([{
    name      = "api"
    image     = "${aws_ecr_repository.api.repository_url}:${var.image_tag}"
    essential = true
    portMappings = [{
      containerPort = 8000
      hostPort      = 8000
      protocol      = "tcp"
    }]
    environment = [{
      name  = "PORT"
      value = "8000"
    }]
    secrets = [{
      name      = "DATABASE_URL"
      valueFrom = aws_secretsmanager_secret.db_url.arn
    }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-region        = var.region
        awslogs-group         = aws_cloudwatch_log_group.api.name
        awslogs-stream-prefix = "ecs"
      }
    }
  }])
}

# ECS Service (Fargate tasks behind the ALB)
resource "aws_ecs_service" "api" {
  name            = "${var.project}-svc"
  cluster         = aws_ecs_cluster.api.arn
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = data.aws_subnets.default.ids
    security_groups = [aws_security_group.service.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }

  depends_on = [aws_lb_listener.http]
}
