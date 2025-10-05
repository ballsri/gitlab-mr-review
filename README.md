# GitLab MR Review

AI-powered code review for GitLab merge requests. Automatically posts inline comments and review summaries using Google Gemini, Anthropic Claude, or OpenAI.

## Quick Start

```bash
# 1. Setup development environment
make dev

# 2. Configure API keys in .env
export GOOGLE_API_KEY="your-key"
export GITLAB_TOKEN="your-token"

# 3. Test locally
make test-local

# 4. Deploy to cloud
make deploy
```

## Features

- ✨ **AI-Powered Reviews** - Automated code analysis with Google Gemini (Claude & OpenAI support coming)
- 💬 **Inline Comments** - Posts feedback directly on specific code lines
- 📊 **Cost Tracking** - Built-in metrics for API usage and estimated costs
- ☁️ **Multi-Cloud** - Deploy to GCP, AWS Lambda, or DigitalOcean Functions
- 🎯 **Smart Filtering** - Automatically excludes lock files and large diffs

## Development

### Prerequisites

- Python 3.8+
- pip
- One of: Google Cloud SDK / AWS CLI / doctl (for deployment)

### Setup

```bash
# Clone repository
git clone <your-repo-url>
cd gitlab-mr-review

# Install dependencies
make install-dev

# Initialize environment
make init
```

Edit `.env` with your API keys:
```bash
GOOGLE_API_KEY=your-google-gemini-api-key
GITLAB_TOKEN=your-gitlab-token
```

### Makefile Commands

#### Installation
```bash
make install          # Install production dependencies
make install-dev      # Install development dependencies
make init             # Create .env from .env.example
make dev              # Quick setup (install-dev + init)
```

#### Code Quality
```bash
make format           # Format code with black
make lint             # Run flake8 linter
make check            # Run all checks (format + lint + type check)
```

#### Testing
```bash
make test             # Run unit tests (pytest)
make test-local       # Run local integration test (interactive prompts)
make check-env        # Verify environment variables
```

#### Deployment
```bash
make deploy           # Interactive deployment (choose provider)
make deploy-gcp       # Deploy to Google Cloud Functions
make deploy-aws       # Deploy to AWS Lambda
make deploy-digitalocean  # Deploy to DigitalOcean Functions
```

#### Utilities
```bash
make clean            # Remove temporary files and caches
make build            # Build package distribution
make help             # Show all commands
```

### Local Testing

**Option 1: Interactive (Makefile)**
```bash
make test-local
# Prompts for: Project ID, MR IID, AI Model, GitLab URL
```

**Option 2: Environment Variables**
```bash
export PROJECT_ID=12345
export MR_IID=1
python test_local.py
```

**Option 3: CLI Arguments**
```bash
python test_local.py --project-id 12345 --mr-iid 1 --ai-model gemini
```

### Code Quality

```bash
# Format code
make format

# Check formatting and lint
make check

# Run before committing
make check && make test
```

## Deployment

### 1. Google Cloud Functions

```bash
# Set environment
export GOOGLE_API_KEY="your-key"

# Deploy
make deploy-gcp

# Or manual
cd cloud_functions/gcp
./deploy.sh
```

**Environment variables:**
- `GOOGLE_API_KEY` - Required
- `GCP_REGION` - Optional (default: us-central1)

### 2. AWS Lambda

```bash
# Set environment
export GOOGLE_API_KEY="your-key"
export AWS_LAMBDA_ROLE_ARN="arn:aws:iam::ACCOUNT:role/ROLE"

# Deploy
make deploy-aws
```

**Environment variables:**
- `GOOGLE_API_KEY` - Required
- `AWS_LAMBDA_ROLE_ARN` - Required
- `AWS_REGION` - Optional (default: us-east-1)

### 3. DigitalOcean Functions

```bash
# Authenticate
doctl auth init

# Set environment
export GOOGLE_API_KEY="your-key"

```

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions.

## GitLab Webhook Setup

1. Deploy to your cloud platform and get the function URL
2. In GitLab project: **Settings → Webhooks**
3. Add webhook:
   - URL: Your cloud function URL
   - Trigger: "Merge request events"
   - SSL verification: Enabled
4. Test webhook

## Configuration

### Environment Variables

**Required (AI Provider - at least one):**
- `GOOGLE_API_KEY` - Google Gemini API key
- `ANTHROPIC_API_KEY` - Anthropic Claude API key (optional)
- `OPENAI_API_KEY` - OpenAI API key (optional)

**Required (GitLab):**
- `GITLAB_TOKEN` - GitLab personal access token with `api` scope

**Optional:**
- `GITLAB_URL` - Custom GitLab instance URL (default: https://gitlab.com)
- `AI_MODEL` - AI provider: gemini, claude, openai (default: gemini)

See [.env.example](.env.example) for all configuration options.

### Request Format

```json
{
  "gitlab_token": "glpat-xxx",
  "project_id": "12345",
  "merge_request_iid": "1",
  "gitlab_url": "https://gitlab.com",
  "ai_model": "gemini"
}
```

### Response Format

```json
{
  "statusCode": 200,
  "body": {
    "message": "Review completed successfully",
    "ai_model": "gemini",
    "model_name": "gemini-2.5-flash",
    "files_reviewed": 5,
    "issues_found": 12,
    "inline_comments_posted": 12,
    "metrics": {
      "duration_seconds": 8.5,
      "input_tokens": 15420,
      "output_tokens": 2845,
      "estimated_cost": 0.0024
    }
  }
}
```

## Project Structure

```
gitlab-mr-review/
├── gitlab_mr_review/        # Main package
│   ├── main.py             # Core review logic
│   ├── gitlab_client.py    # GitLab API client
│   ├── ai_adapters/        # AI provider adapters
│   └── ...
├── cloud_functions/        # Cloud deployment configs
│   ├── gcp/               # Google Cloud Functions
│   ├── aws/               # AWS Lambda
│   └── digitalocean/      # DigitalOcean Functions
├── Makefile               # Development commands
├── test_local.py          # Local testing script
├── setup.py               # Package setup
├── pyproject.toml         # Modern packaging config
└── requirements.txt       # Dependencies
```

## Development Workflow

1. **Make changes** to code in `gitlab_mr_review/`
2. **Format code**: `make format`
3. **Check quality**: `make check`
4. **Test locally**: `make test-local`
5. **Run tests**: `make test` (when tests are added)
6. **Deploy**: `make deploy`

## Troubleshooting

### Check Environment
```bash
make check-env
```

### Common Issues

**"GOOGLE_API_KEY not set"**
```bash
export GOOGLE_API_KEY="your-key"
```

**"Not authenticated with [platform]"**
```bash
# GCP
gcloud auth login

# AWS
aws configure

# DigitalOcean
doctl auth init
```

**"Module not found"**
```bash
make install-dev
```

## Cost Estimation

**Per review (typical 5-file MR with Gemini 2.5 Flash):**
- Cloud function: ~$0.0001
- Gemini API: ~$0.0024
- **Total: ~$0.0025 per review**

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed pricing.

## Documentation

- [cloud_functions/README.md](cloud_functions/README.md) - Cloud-specific docs
- [Makefile](Makefile) - All development commands

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and test
4. Run `make check` to ensure code quality
5. Submit a pull request

## License

MIT License - See [LICENSE](LICENSE)

## Support

- 📖 [Documentation](DEPLOYMENT.md)
- 🐛 [Report Issues](https://github.com/yourusername/gitlab-mr-review/issues)
- 💡 [Feature Requests](https://github.com/yourusername/gitlab-mr-review/issues)
