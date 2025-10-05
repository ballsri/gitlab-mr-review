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

# Check for required environment variables
if [ -z "$GOOGLE_API_KEY" ]; then
    echo -e "${RED}✗ Error: GOOGLE_API_KEY environment variable is not set${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} GOOGLE_API_KEY is set"

echo ""
echo -e "${YELLOW}Preparing deployment package...${NC}"

# Copy the package to the deployment directory
rm -rf gitlab_mr_review
cp -r ../../gitlab_mr_review .
echo -e "${GREEN}✓${NC} Package copied"

# Create .env file for deployment
cat > .env << EOF
GOOGLE_API_KEY=$GOOGLE_API_KEY
EOF
echo -e "${GREEN}✓${NC} Environment configured"

# Deploy
echo ""
echo -e "${YELLOW}Deploying to DigitalOcean Functions...${NC}"
doctl serverless deploy . --remote-build

# Get function URL
FUNCTION_URL=$(doctl serverless functions get gitlab-mr-review/review --url 2>/dev/null || echo "")

# Clean up
rm -rf gitlab_mr_review
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
