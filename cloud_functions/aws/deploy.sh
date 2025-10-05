#!/bin/bash
# Deploy to AWS Lambda

set -e  # Exit on error

# Configuration
FUNCTION_NAME="${FUNCTION_NAME:-gitlab-mr-review}"
RUNTIME="python3.11"
HANDLER="lambda_function.lambda_handler"
ROLE_ARN="${AWS_LAMBDA_ROLE_ARN}"
REGION="${AWS_REGION:-us-east-1}"
MEMORY="${MEMORY:-512}"
TIMEOUT="${TIMEOUT:-300}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== AWS Lambda Deployment ===${NC}"
echo ""

# Check if aws CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}✗ Error: AWS CLI is not installed${NC}"
    echo "Install from: https://aws.amazon.com/cli/"
    exit 1
fi
echo -e "${GREEN}✓${NC} AWS CLI found"

# Check for required environment variables
if [ -z "$AWS_LAMBDA_ROLE_ARN" ]; then
    echo -e "${RED}✗ Error: AWS_LAMBDA_ROLE_ARN environment variable is not set${NC}"
    echo "Create an IAM role with Lambda execution permissions and set the ARN"
    exit 1
fi
echo -e "${GREEN}✓${NC} AWS_LAMBDA_ROLE_ARN is set"

if [ -z "$GOOGLE_API_KEY" ]; then
    echo -e "${RED}✗ Error: GOOGLE_API_KEY environment variable is not set${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} GOOGLE_API_KEY is set"

echo ""
echo -e "${BLUE}Deployment Configuration:${NC}"
echo "  Function: $FUNCTION_NAME"
echo "  Region: $REGION"
echo "  Runtime: $RUNTIME"
echo "  Memory: ${MEMORY}MB"
echo "  Timeout: ${TIMEOUT}s"
echo ""

echo -e "${YELLOW}Building deployment package...${NC}"

# Create temporary directory
BUILD_DIR=$(mktemp -d)
cd $BUILD_DIR

# Copy the package
cp -r $OLDPWD/../../gitlab_mr_review .
cp $OLDPWD/lambda_function.py .
echo -e "${GREEN}✓${NC} Package copied"

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -r $OLDPWD/requirements.txt -t . --quiet
echo -e "${GREEN}✓${NC} Dependencies installed"

# Create deployment package
echo -e "${YELLOW}Creating deployment package...${NC}"
zip -r function.zip . -x "*.pyc" "__pycache__/*" -q
echo -e "${GREEN}✓${NC} Package created ($(du -h function.zip | cut -f1))"

echo ""
echo -e "${YELLOW}Deploying to AWS Lambda...${NC}"

# Check if function exists
if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION 2>/dev/null; then
    echo -e "${YELLOW}Updating existing function...${NC}"
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://function.zip \
        --region $REGION \
        --output text > /dev/null

    aws lambda update-function-configuration \
        --function-name $FUNCTION_NAME \
        --environment "Variables={GOOGLE_API_KEY=$GOOGLE_API_KEY}" \
        --region $REGION \
        --output text > /dev/null
    echo -e "${GREEN}✓${NC} Function updated"
else
    echo -e "${YELLOW}Creating new function...${NC}"
    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime $RUNTIME \
        --role $ROLE_ARN \
        --handler $HANDLER \
        --zip-file fileb://function.zip \
        --memory-size $MEMORY \
        --timeout $TIMEOUT \
        --environment "Variables={GOOGLE_API_KEY=$GOOGLE_API_KEY}" \
        --region $REGION \
        --output text > /dev/null
    echo -e "${GREEN}✓${NC} Function created"
fi

# Clean up
cd $OLDPWD
rm -rf $BUILD_DIR

echo ""
echo -e "${GREEN}✓ Deployment complete!${NC}"
echo ""
echo -e "${BLUE}Function ARN:${NC}"
FUNCTION_ARN=$(aws lambda get-function --function-name $FUNCTION_NAME --region $REGION --query 'Configuration.FunctionArn' --output text)
echo "$FUNCTION_ARN"
echo ""
echo -e "${YELLOW}Note:${NC} Create an API Gateway or Function URL to make it publicly accessible"
