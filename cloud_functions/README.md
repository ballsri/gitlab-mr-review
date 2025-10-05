# Cloud Functions Deployment Guide

This directory contains deployment configurations for various cloud platforms.

## Supported Platforms

- **Google Cloud Functions** (`gcp/`)
- **AWS Lambda** (`aws/`)
- **DigitalOcean Functions** (`digitalocean/`)

## Prerequisites

### Google Cloud Functions

1. Install [gcloud CLI](https://cloud.google.com/sdk/docs/install)
2. Authenticate: `gcloud auth login`
3. Set project: `gcloud config set project YOUR_PROJECT_ID`
4. Enable Cloud Functions API

### AWS Lambda

1. Install [AWS CLI](https://aws.amazon.com/cli/)
2. Configure: `aws configure`
3. Create IAM role with Lambda execution permissions
4. Set `AWS_LAMBDA_ROLE_ARN` environment variable

### DigitalOcean Functions

1. Install [doctl](https://docs.digitalocean.com/reference/doctl/how-to/install/)
2. Authenticate: `doctl auth init`
3. Enable Functions in your DigitalOcean account

## Deployment Instructions

### Google Cloud Functions

```bash
cd gcp
export GOOGLE_API_KEY="your-gemini-api-key"
./deploy.sh
```

**Manual deployment:**
```bash
gcloud functions deploy gitlab-mr-review \
  --runtime python311 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point gitlab_mr_review_http \
  --set-env-vars GOOGLE_API_KEY=your-key \
  --region us-central1
```

### AWS Lambda

```bash
cd aws
export AWS_LAMBDA_ROLE_ARN="arn:aws:iam::ACCOUNT:role/ROLE_NAME"
export GOOGLE_API_KEY="your-gemini-api-key"
./deploy.sh
```

**Manual deployment:**
1. Package code: `pip install -r requirements.txt -t . && zip -r function.zip .`
2. Create/update function via AWS Console or CLI

### DigitalOcean Functions

```bash
cd digitalocean
export GOOGLE_API_KEY="your-gemini-api-key"
./deploy.sh
```

**Manual deployment:**
```bash
doctl serverless deploy .
```

## Environment Variables

Set these in your cloud platform:

- `GOOGLE_API_KEY` - For Gemini AI (required if using Gemini)
- `ANTHROPIC_API_KEY` - For Claude AI (optional)
- `OPENAI_API_KEY` - For OpenAI (optional)

## Testing Your Deployment

### Get Function URL

**GCP:**
```bash
gcloud functions describe gitlab-mr-review --region us-central1 --format='value(httpsTrigger.url)'
```

**AWS:**
Create API Gateway endpoint or use Function URL

**DigitalOcean:**
```bash
doctl serverless functions get gitlab-mr-review/review --url
```

### Test Request

```bash
curl -X POST YOUR_FUNCTION_URL \
  -H "Content-Type: application/json" \
  -d '{
    "gitlab_token": "glpat-xxx",
    "project_id": "12345",
    "merge_request_iid": "1",
    "gitlab_url": "https://gitlab.com",
    "ai_model": "gemini"
  }'
```

## Cost Estimation

### Google Cloud Functions
- Free tier: 2M invocations/month
- After: $0.40 per million invocations
- Memory: $0.0000025/GB-second

### AWS Lambda
- Free tier: 1M requests/month
- After: $0.20 per million requests
- Memory: $0.0000166667/GB-second

### DigitalOcean Functions
- Included in Basic plan: 90K GB-seconds
- After: $0.000018/GB-second

**Note:** Add AI API costs (Gemini, Claude, etc.) separately.

## Troubleshooting

### GCP: Permission Denied
```bash
gcloud auth application-default login
```

### AWS: Function Timeout
Increase timeout in deploy.sh or AWS Console (max 15 minutes)

### DigitalOcean: Build Failed
Check logs:
```bash
doctl serverless activations logs
```

## Monitoring

### GCP
```bash
gcloud functions logs read gitlab-mr-review --region us-central1
```

### AWS
View CloudWatch Logs in AWS Console

### DigitalOcean
```bash
doctl serverless activations list
doctl serverless activations logs ACTIVATION_ID
```

## Security Best Practices

1. **Never commit API keys** - Use environment variables
2. **Restrict function access** - Use IAM/authentication
3. **Enable HTTPS only** - All platforms support this by default
4. **Rotate credentials** - Regularly update API keys
5. **Monitor usage** - Set up billing alerts

## Support

For platform-specific issues:
- GCP: [Cloud Functions Docs](https://cloud.google.com/functions/docs)
- AWS: [Lambda Docs](https://docs.aws.amazon.com/lambda/)
- DigitalOcean: [Functions Docs](https://docs.digitalocean.com/products/functions/)
