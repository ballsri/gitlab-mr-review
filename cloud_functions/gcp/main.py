"""
Google Cloud Functions entry point for GitLab MR Review

Deployment:
    gcloud functions deploy gitlab-mr-review \\
        --runtime python311 \\
        --trigger-http \\
        --allow-unauthenticated \\
        --entry-point gitlab_mr_review_http \\
        --set-env-vars GOOGLE_API_KEY=your-key

Environment Variables:
    GOOGLE_API_KEY: Google Gemini API key
    ANTHROPIC_API_KEY: Anthropic Claude API key (optional)
    OPENAI_API_KEY: OpenAI API key (optional)
"""

import functions_framework
from flask import Request
import json
import sys
import os

# Add parent directory to path to import gitlab_mr_review
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from gitlab_mr_review.main import main


@functions_framework.http
def gitlab_mr_review_http(request: Request):
    """
    HTTP Cloud Function entry point

    Args:
        request (flask.Request): The request object

    Returns:
        Response object with status code and JSON body
    """
    # Set CORS headers for preflight requests
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    # Set CORS headers for main request
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json'
    }

    try:
        # Parse request body
        request_json = request.get_json(silent=True)

        if not request_json:
            return (
                json.dumps({
                    'statusCode': 400,
                    'body': {'error': 'Request body must be JSON'}
                }),
                400,
                headers
            )

        # Call main function
        result = main(request_json)

        # Return response
        return (
            json.dumps(result.get('body', {})),
            result.get('statusCode', 500),
            headers
        )

    except Exception as e:
        return (
            json.dumps({
                'error': f'Internal server error: {str(e)}'
            }),
            500,
            headers
        )
