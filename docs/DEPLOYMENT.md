# Deployment Guide

## AWS Infrastructure Setup

### 1. RDS Database

```bash
aws rds create-db-instance \
  --db-instance-identifier health-app-prod \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username postgres \
  --master-user-password <strong-password> \
  --allocated-storage 100 \
  --storage-type gp3 \
  --vpc-security-group-ids <security-group-id> \
  --db-subnet-group-name <subnet-group-name> \
  --backup-retention-period 7 \
  --storage-encrypted \
  --multi-az
```

**Configuration:**
- Instance class: `db.t3.micro` (upgrade to `db.t3.small` or larger for production)
- Storage: 100GB with GP3 storage type
- Encryption: Enabled at rest
- Multi-AZ: Enabled for high availability
- Backup retention: 7 days (HIPAA requirement)

**Security:**
- Database in private subnet
- Security group allows access only from ECS tasks
- SSL/TLS required for connections

### 2. ElastiCache (Redis)

```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id health-app-redis \
  --engine redis \
  --cache-node-type cache.t3.micro
```

**Configuration:**
- Node type: `cache.t3.micro` (upgrade for production)
- Encryption: Enable at rest and in transit for production
- Auth token: Required for access

### 3. ECR Repository

```bash
aws ecr create-repository --repository-name health-app
```

**Image Security:**
- Vulnerability scanning: Enable in repository settings
- Encryption: Configure in repository settings

### 4. ECS Cluster

```bash
aws ecs create-cluster --cluster-name health-app-prod
```

**Cluster Configuration:**
- Launch type: Fargate (serverless)
- Capacity providers: Configure as needed
- Auto-scaling: Configured based on CPU/memory metrics

### 5. Request SSL Certificate

```bash
aws acm request-certificate \
  --domain-name yourapp.com \
  --validation-method DNS
```

**Certificate Configuration:**
- Domain: Replace `yourapp.com` with your actual domain
- Validation: DNS validation (add CNAME records to DNS)
- Region: Must be in `us-east-1` for ALB use
- After validation, note the certificate ARN for ALB configuration

### 6. Application Load Balancer

```bash
aws elbv2 create-load-balancer \
  --name health-app-alb \
  --subnets <subnet-1> <subnet-2> \
  --security-groups <alb-security-group-id> \
  --scheme internet-facing \
  --type application \
  --ip-address-type ipv4
```

**Load Balancer Configuration:**
- Type: Application Load Balancer
- Scheme: Internet-facing
- SSL/TLS: HTTPS listener on port 443 with ACM certificate
- HTTP to HTTPS redirect: Configure redirect rule
- Health checks: Configured for `/health` endpoint

**Attach Certificate to ALB:**
```bash
# Create HTTPS listener with certificate
aws elbv2 create-listener \
  --load-balancer-arn <alb-arn> \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=<certificate-arn> \
  --default-actions Type=forward,TargetGroupArn=<target-group-arn>

# Create HTTP listener with redirect to HTTPS
aws elbv2 create-listener \
  --load-balancer-arn <alb-arn> \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=redirect,RedirectConfig='{Protocol=HTTPS,Port=443,StatusCode=HTTP_301}'
```

**Security Groups:**
- ALB Security Group: Allow inbound HTTPS (443) and HTTP (80) from 0.0.0.0/0
- Outbound: All traffic to ECS security group

### 7. ECS Task Definition

```json
{
  "family": "health-app",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "containerDefinitions": [
    {
      "name": "health-app",
      "image": "<account-id>.dkr.ecr.<region>.amazonaws.com/health-app:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DATABASE_URL",
          "value": "postgresql://..."
        },
        {
          "name": "REDIS_URL",
          "value": "redis://..."
        }
      ],
      "secrets": [
        {
          "name": "SECRET_KEY",
          "valueFrom": "arn:aws:secretsmanager:..."
        },
        {
          "name": "OPENAI_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:..."
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/health-app",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3
      }
    }
  ]
}
```

### 8. ECS Service

```bash
aws ecs create-service \
  --cluster health-app-prod \
  --service-name health-app \
  --task-definition health-app \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-1,subnet-2],securityGroups=[sg-xxx],assignPublicIp=DISABLED}" \
  --load-balancers "targetGroupArn=<target-group-arn>,containerName=health-app,containerPort=8000" \
  --health-check-grace-period-seconds 60
```

**Service Configuration:**
- Desired count: 2 (minimum for high availability)
- Launch type: Fargate
- Network: Private subnets with NAT gateway
- Load balancer: Connected to ALB target group
- Auto-scaling: Configured for CPU/memory metrics

### 9. Secrets Management

```bash
# Store secrets in AWS Secrets Manager
aws secretsmanager create-secret \
  --name health-app/prod/secret-key \
  --secret-string "<secret-key>"

aws secretsmanager create-secret \
  --name health-app/prod/openai-api-key \
  --secret-string "<openai-api-key>"

aws secretsmanager create-secret \
  --name health-app/prod/db-password \
  --secret-string "<db-password>"
```

**Security Best Practices:**
- Use AWS Secrets Manager for sensitive data
- Rotate secrets regularly
- Grant ECS task role access to secrets
- Enable CloudTrail for audit logging

## Deployment Process

### 5. Deploy via ECS

```bash
# Build and push Docker image
docker build -t 123456789.dkr.ecr.us-east-1.amazonaws.com/health-app:latest .

aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com

docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/health-app:latest

# Create ECS task definition and service
# (Use CloudFormation or Terraform for IaC)
```

**Note:** Replace `123456789` with your AWS account ID.

### 2. Update ECS Service

```bash
# Update task definition with new image
aws ecs update-service \
  --cluster health-app-prod \
  --service health-app \
  --force-new-deployment \
  --region us-east-1
```

### 3. Monitor Deployment

```bash
# Check service status
aws ecs describe-services \
  --cluster health-app-prod \
  --services health-app

# View logs
aws logs tail /ecs/health-app --follow
```

## CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/deploy.yml`) automatically:
1. Builds Docker image on push to `main` or version tags
2. Pushes image to ECR
3. Updates ECS service with new deployment

**Manual Deployment:**
- Push to `main` branch triggers automatic deployment
- Version tags (e.g., `v1.0.0`) also trigger deployment
- Monitor deployment in GitHub Actions tab

## Environment Variables

### Required Variables

Set in ECS task definition or Secrets Manager:

- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `SECRET_KEY` - Application secret key (from Secrets Manager)
- `OPENAI_API_KEY` - OpenAI API key (from Secrets Manager)
- `DEBUG` - Set to `false` in production
- `LOG_LEVEL` - Set to `INFO` in production
- `ENVIRONMENT` - Set to `production`

### Optional Variables

- `SENTRY_DSN` - Sentry error tracking DSN (from Secrets Manager)
- `CORS_ORIGINS` - Allowed CORS origins
- `ALLOWED_ORIGINS` - Frontend URL
- `SMTP_SERVER` - Email server configuration
- `FITBIT_CLIENT_ID` - Fitbit OAuth client ID
- `FITBIT_CLIENT_SECRET` - Fitbit OAuth secret

## Database Migrations

### Run Migrations on Deployment

```bash
# SSH into ECS task or use ECS Exec
aws ecs execute-command \
  --cluster health-app-prod \
  --task <task-id> \
  --container health-app \
  --command "/bin/sh" \
  --interactive

# Inside container
cd /app/backend
alembic upgrade head
```

### Automated Migration Script

Add to Dockerfile or deployment script:
```bash
alembic upgrade head
```

## Monitoring and Logging

### CloudWatch

**Log Group:**
- Log group: `/ecs/health-app`
- Retention: 30 days (configurable)
- Log streams: Per container instance

**Metrics:**
- **CPU**: ECS service CPU utilization
- **Memory**: ECS service memory utilization
- **Requests**: ALB request count
- **Errors**: ALB 4xx/5xx error rates
- **Latency**: ALB target response time

**Alarms:**
- **High Error Rate**: Alert when 5xx errors > 5% of requests
- **High Latency**: Alert when p95 latency > 2 seconds
- **Low Healthy Hosts**: Alert when healthy targets < 1
- **High CPU**: Alert when CPU utilization > 80%

**Create CloudWatch Alarms:**
```bash
# High error rate alarm
aws cloudwatch put-metric-alarm \
  --alarm-name health-app-high-error-rate \
  --alarm-description "Alert on high error rate" \
  --metric-name HTTPCode_Target_5XX_Count \
  --namespace AWS/ApplicationELB \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2

# High latency alarm
aws cloudwatch put-metric-alarm \
  --alarm-name health-app-high-latency \
  --alarm-description "Alert on high latency" \
  --metric-name TargetResponseTime \
  --namespace AWS/ApplicationELB \
  --statistic Average \
  --period 300 \
  --threshold 2.0 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2
```

### Sentry (Error Tracking)

**Installation:**
Add to `backend/requirements.txt`:
```
sentry-sdk[fastapi]==1.38.0
```

**Configuration in `backend/app/main.py`:**
```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from app.config import get_settings

settings = get_settings()

if settings.ENVIRONMENT == "production" and settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[FastApiIntegration()],
        traces_sample_rate=0.1,
        environment=settings.ENVIRONMENT,
    )
```

**Environment Variable:**
- `SENTRY_DSN`: Your Sentry project DSN (from Secrets Manager)

**Features:**
- Automatic error tracking and reporting
- Performance monitoring (10% of transactions)
- Release tracking
- User context and breadcrumbs

### Health Checks

- ALB health check: `/health` endpoint
- ECS health check: Container health check command
- Interval: 30 seconds
- Timeout: 5 seconds
- Healthy threshold: 2
- Unhealthy threshold: 3

## Scaling Configuration

### Auto Scaling

```bash
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --scalable-dimension ecs:service:DesiredCount \
  --resource-id service/health-app-prod/health-app \
  --min-capacity 2 \
  --max-capacity 10

aws application-autoscaling put-scaling-policy \
  --service-namespace ecs \
  --scalable-dimension ecs:service:DesiredCount \
  --resource-id service/health-app-prod/health-app \
  --policy-name cpu-scaling \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{
    "TargetValue": 70.0,
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
    }
  }'
```

**Scaling Configuration:**
- Min capacity: 2 tasks
- Max capacity: 10 tasks
- Target CPU: 70%
- Scale up: When CPU > 70% for 2 minutes
- Scale down: When CPU < 50% for 5 minutes

## Security Configuration

### Security Groups

**ALB Security Group:**
- Inbound: HTTPS (443) from 0.0.0.0/0
- Outbound: All traffic

**ECS Security Group:**
- Inbound: HTTP (8000) from ALB security group
- Outbound: HTTPS (443) to RDS, ElastiCache, Secrets Manager

**RDS Security Group:**
- Inbound: PostgreSQL (5432) from ECS security group
- Outbound: None

### IAM Roles

**ECS Task Role:**
- Permissions to read from Secrets Manager
- Permissions to write to CloudWatch Logs
- Permissions to access S3 (if needed)

**ECS Execution Role:**
- Permissions to pull from ECR
- Permissions to write to CloudWatch Logs

## Backup and Disaster Recovery

### Database Backups

```bash
# Automated daily backups (RDS)
# Retention: 35 days
# Test restore procedure monthly
```

**Backup Configuration:**
- Automated daily backups (RDS)
- Retention: 35 days
- Point-in-time recovery: Enabled
- Backup window: Configured during low-traffic hours
- **Monthly restore testing**: Test restore procedure monthly to verify backup integrity

### Application Backups

- Docker images: Stored in ECR (versioned)
- Configuration: Stored in version control
- Secrets: Stored in Secrets Manager (versioned)

### Disaster Recovery Plan

1. **RTO (Recovery Time Objective):** 4 hours
2. **RPO (Recovery Point Objective):** 1 hour
3. **Backup restoration:** From RDS snapshots
4. **Service restoration:** From ECS task definitions

## Cost Optimization

### Recommendations

1. **Use Fargate Spot:** 70% cost savings for non-critical workloads
2. **Right-size instances:** Monitor and adjust task CPU/memory
3. **Reserved capacity:** Consider for predictable workloads
4. **Auto-scaling:** Scale down during low-traffic periods
5. **CloudWatch retention:** Adjust log retention periods

### Estimated Monthly Costs

- RDS (db.t3.micro): ~$15/month
- ElastiCache (cache.t3.micro): ~$12/month
- ECS Fargate (2 tasks): ~$60/month
- ALB: ~$20/month
- Data transfer: Variable
- **Total:** ~$107/month + data transfer

## Troubleshooting

### Common Issues

1. **Service won't start:**
   - Check CloudWatch logs
   - Verify secrets are accessible
   - Check security group rules
   - Verify task definition

2. **Database connection errors:**
   - Verify RDS security group allows ECS
   - Check DATABASE_URL format
   - Verify database is accessible from VPC

3. **High latency:**
   - Check CloudWatch metrics
   - Review ALB target health
   - Consider scaling up tasks
   - Review database performance

### Useful Commands

```bash
# View service events
aws ecs describe-services --cluster health-app-prod --services health-app

# View task logs
aws logs tail /ecs/health-app --follow

# Execute command in container
aws ecs execute-command --cluster health-app-prod --task <task-id> --container health-app --command "/bin/sh" --interactive

# Check ALB target health
aws elbv2 describe-target-health --target-group-arn <target-group-arn>
```

## Version History

- **v1.0** (2024): Initial deployment guide
- Regular updates as infrastructure evolves
