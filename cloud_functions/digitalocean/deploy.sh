#!/bin/bash
# Deploy to DigitalOcean Functions

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== DigitalOcean Functions Deployment ===${NC}"
echo ""

# Check if doctl is installed
if ! command -v doctl &> /dev/null; then
    echo -e "${RED}✗ Error: doctl CLI is not installed${NC}"
    echo "Install from: https://docs.digitalocean.com/reference/doctl/how-to/install/"
    exit 1
fi
echo -e "${GREEN}✓${NC} doctl CLI found"

# Check authentication
if ! doctl auth list &> /dev/null; then
    echo -e "${RED}✗ Error: Not authenticated with DigitalOcean${NC}"
    echo "Run: doctl auth init"
    exit 1
fi
echo -e "${GREEN}✓${NC} Authenticated with DigitalOcean"

echo ""
echo -e "${YELLOW}Preparing deployment package...${NC}"

# Create packages directory structure
rm -rf packages
mkdir -p packages/gitlab-mr-review/review

# Copy gitlab_mr_review package into the review function directory
cp -r ../../gitlab_mr_review packages/gitlab-mr-review/review/

# Copy the function handler and build assets into review directory
cp __main__.py packages/gitlab-mr-review/review/
cp requirements.txt packages/gitlab-mr-review/review/
cp build.sh packages/gitlab-mr-review/review/
chmod +x packages/gitlab-mr-review/review/build.sh

echo -e "${GREEN}✓${NC} Package copied"

# Check for required environment variables
if [ -z "$GOOGLE_API_KEY" ] && [ -z "$ANTHROPIC_API_KEY" ] && [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${RED}✗ Error: No AI API key found${NC}"
    echo "Set at least one: GOOGLE_API_KEY, ANTHROPIC_API_KEY, or OPENAI_API_KEY"
    exit 1
fi

# Show which API keys are set
echo ""
echo -e "${YELLOW}API Keys configured:${NC}"
[ -n "$GOOGLE_API_KEY" ] && echo -e "  ${GREEN}✓${NC} GOOGLE_API_KEY" || echo -e "  ${YELLOW}○${NC} GOOGLE_API_KEY (not set)"
[ -n "$ANTHROPIC_API_KEY" ] && echo -e "  ${GREEN}✓${NC} ANTHROPIC_API_KEY" || echo -e "  ${YELLOW}○${NC} ANTHROPIC_API_KEY (not set)"
[ -n "$OPENAI_API_KEY" ] && echo -e "  ${GREEN}✓${NC} OPENAI_API_KEY" || echo -e "  ${YELLOW}○${NC} OPENAI_API_KEY (not set)"

# Create .env file for deployment (only includes keys that are set)
echo -e "${YELLOW}Configuring environment...${NC}"
> .env
[ -n "$GOOGLE_API_KEY" ] && echo "GOOGLE_API_KEY=$GOOGLE_API_KEY" >> .env
[ -n "$ANTHROPIC_API_KEY" ] && echo "ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY" >> .env
[ -n "$OPENAI_API_KEY" ] && echo "OPENAI_API_KEY=$OPENAI_API_KEY" >> .env
echo -e "${GREEN}✓${NC} Environment configured"

# Deploy
echo ""
echo -e "${YELLOW}Deploying to DigitalOcean Functions...${NC}"
doctl serverless deploy . --remote-build --verbose-build

# Get function URL
FUNCTION_URL=$(doctl serverless functions get gitlab-mr-review/review --url 2>/dev/null || echo "")

# Clean up
rm -rf packages
rm .env

echo ""
echo -e "${GREEN}✓ Deployment complete!${NC}"
echo ""

if [ -n "$FUNCTION_URL" ]; then
    echo -e "${BLUE}Function URL:${NC}"
    echo "$FUNCTION_URL"
    echo ""
    echo -e "${YELLOW}Test with:${NC}"
    echo "curl -X POST \"$FUNCTION_URL\" -H \"Content-Type: application/json\" -d '{\"gitlab_token\":\"TOKEN\",\"project_id\":\"ID\",\"merge_request_iid\":\"IID\"}'"
else
    echo -e "${YELLOW}Get function URL with:${NC}"
    echo "doctl serverless functions get gitlab-mr-review/review --url"
fi
