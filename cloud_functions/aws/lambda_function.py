"""
AWS Lambda entry point for GitLab MR Review

Deployment:
    1. Package: zip -r function.zip gitlab_mr_review/ lambda_function.py
    2. Upload to AWS Lambda via console or CLI
    3. Set environment variables in Lambda configuration

Environment Variables:
    GOOGLE_API_KEY: Google Gemini API key
    ANTHROPIC_API_KEY: Anthropic Claude API key (optional)
    OPENAI_API_KEY: OpenAI API key (optional)
"""

import json
import sys
import os

# Add parent directory to path to import gitlab_mr_review
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from gitlab_mr_review.main import main


def lambda_handler(event, context):
    """
    AWS Lambda handler function

    Args:
        event: Lambda event object containing request data
        context: Lambda context object

    Returns:
        Dict with statusCode and body
    """
    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', event)

        # Call main function
        result = main(body)

        # Format response for API Gateway
        return {
            'statusCode': result.get('statusCode', 500),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': json.dumps(result.get('body', {}))
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': f'Internal server error: {str(e)}'
            })
        }
