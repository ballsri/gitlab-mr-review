"""
DigitalOcean Functions entry point for GitLab MR Review

Deployment:
    doctl serverless deploy .

Environment Variables:
    Set in .env file or DigitalOcean dashboard:
    - GOOGLE_API_KEY: Google Gemini API key
    - ANTHROPIC_API_KEY: Anthropic Claude API key (optional)
    - OPENAI_API_KEY: OpenAI API key (optional)
"""

import json
import sys
import os

# Add parent directory to path to import gitlab_mr_review
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from gitlab_mr_review.main import main


def main_handler(args):
    """
    DigitalOcean Functions main handler

    Args:
        args: Dictionary containing request parameters

    Returns:
        Dict with statusCode and body
    """
    try:
        # Call main function
        result = main(args)

        return result

    except Exception as e:
        return {
            'statusCode': 500,
            'body': {
                'error': f'Internal server error: {str(e)}'
            }
        }


# DigitalOcean Functions entry point
def main(args):
    """
    DigitalOcean Functions entry point wrapper

    Args:
        args: Request arguments

    Returns:
        Response dictionary
    """
    return main_handler(args)
