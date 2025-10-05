#!/bin/bash
# Deploy to Google Cloud Functions

set -e  # Exit on error

# Configuration
FUNCTION_NAME="${FUNCTION_NAME:-gitlab-mr-review}"
REGION="${GCP_REGION:-asia-southeast1}"
RUNTIME="python311"
ENTRY_POINT="gitlab_mr_review_http"
MEMORY="${MEMORY:-512MB}"
TIMEOUT="${TIMEOUT:-540s}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Google Cloud Functions Deployment ===${NC}"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}✗ Error: gcloud CLI is not installed${NC}"
    echo "Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi
echo -e "${GREEN}✓${NC} gcloud CLI found"

# Check authentication
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    echo -e "${RED}✗ Error: Not authenticated with Google Cloud${NC}"
    echo "Run: gcloud auth login"
    exit 1
fi
echo -e "${GREEN}✓${NC} Authenticated with Google Cloud"

# Check for required environment variables
if [ -z "$GOOGLE_API_KEY" ] && [ -z "$ANTHROPIC_API_KEY" ] && [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${RED}✗ Error: No AI API key found${NC}"
    echo "Set at least one: GOOGLE_API_KEY, ANTHROPIC_API_KEY, or OPENAI_API_KEY"
    exit 1
fi

# Show which API keys are set
echo -e "${YELLOW}API Keys configured:${NC}"
[ -n "$GOOGLE_API_KEY" ] && echo -e "  ${GREEN}✓${NC} GOOGLE_API_KEY" || echo -e "  ${YELLOW}○${NC} GOOGLE_API_KEY (not set)"
[ -n "$ANTHROPIC_API_KEY" ] && echo -e "  ${GREEN}✓${NC} ANTHROPIC_API_KEY" || echo -e "  ${YELLOW}○${NC} ANTHROPIC_API_KEY (not set)"
[ -n "$OPENAI_API_KEY" ] && echo -e "  ${GREEN}✓${NC} OPENAI_API_KEY" || echo -e "  ${YELLOW}○${NC} OPENAI_API_KEY (not set)"

echo ""
echo -e "${BLUE}Deployment Configuration:${NC}"
echo "  Function: $FUNCTION_NAME"
echo "  Region: $REGION"
echo "  Runtime: $RUNTIME"
echo "  Memory: $MEMORY"
echo "  Timeout: $TIMEOUT"
echo ""

# Copy the package to the deployment directory
echo -e "${YELLOW}Preparing deployment package...${NC}"
rm -rf gitlab_mr_review
cp -r ../../gitlab_mr_review .
echo -e "${GREEN}✓${NC} Package copied"

# Deploy
echo ""
echo -e "${YELLOW}Deploying to Google Cloud Functions...${NC}"

# Build environment variables string
ENV_VARS=""
[ -n "$GOOGLE_API_KEY" ] && ENV_VARS="GOOGLE_API_KEY=$GOOGLE_API_KEY"
[ -n "$ANTHROPIC_API_KEY" ] && ENV_VARS="$ENV_VARS,ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY"
[ -n "$OPENAI_API_KEY" ] && ENV_VARS="$ENV_VARS,OPENAI_API_KEY=$OPENAI_API_KEY"

# Remove leading comma if present
ENV_VARS="${ENV_VARS#,}"

gcloud functions deploy $FUNCTION_NAME \
    --runtime $RUNTIME \
    --trigger-http \
    --allow-unauthenticated \
    --entry-point $ENTRY_POINT \
    --region $REGION \
    --memory $MEMORY \
    --timeout $TIMEOUT \
    --set-env-vars "$ENV_VARS" \
    --source . \
    --quiet

# Clean up
rm -rf gitlab_mr_review

echo ""
echo -e "${GREEN}✓ Deployment complete!${NC}"
echo ""
echo -e "${BLUE}Function URL:${NC}"
FUNCTION_URL=$(gcloud functions describe $FUNCTION_NAME --region $REGION --format='value(httpsTrigger.url)')
echo "$FUNCTION_URL"
echo ""
echo -e "${YELLOW}Test with:${NC}"
echo "curl -X POST \"$FUNCTION_URL\" -H \"Content-Type: application/json\" -d '{\"gitlab_token\":\"TOKEN\",\"project_id\":\"ID\",\"merge_request_iid\":\"IID\"}'"
