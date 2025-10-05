"""
GitLab MR Code Review with AI
DigitalOcean Serverless Function - Main Entry Point

Environment Variables Required:
- GOOGLE_API_KEY: For Gemini (if using Gemini)
- ANTHROPIC_API_KEY: For Claude (if using Claude)
- OPENAI_API_KEY: For OpenAI (if using OpenAI)
- AI_MODEL: Default model to use (optional, defaults to 'gemini')

Request Body:
- gitlab_token: GitLab API token with 'api' scope
- project_id: GitLab project ID
- merge_request_iid: MR internal ID
- gitlab_url: GitLab instance URL (default: https://gitlab.com)
- action: 'opened' or 'update' (optional, auto-detected)
- ai_model: AI model to use: 'gemini', 'claude', or 'openai' (optional)
- model_name: Specific model name (optional)
"""

import os
import requests
from typing import Dict, Any

# Import local modules
from .config import (
    MAX_FILES, MAX_DIFF_LENGTH, EXCLUDED_FILE_PATTERNS, 
    DEFAULT_AI_MODEL, GOOGLE_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY
)
from .metrics import ReviewMetrics
from .gitlab_client import GitLabClient
from .formatters import format_summary_comment, format_inline_comment
from .ai_adapters import create_ai_adapter


def get_api_key_for_provider(provider: str) -> str:
    """Get API key for specified provider"""
    provider_key = provider.lower()
    keys = {
        'gemini': GOOGLE_API_KEY,
        'claude': ANTHROPIC_API_KEY,
        'anthropic': ANTHROPIC_API_KEY,
        'openai': OPENAI_API_KEY
    }

    api_key = keys.get(provider_key)
    if not api_key:
        raise ValueError(f"API key not found for provider: {provider}. Set the appropriate environment variable.")
    
    return api_key


def main(args):
    """
    Main function for DigitalOcean serverless function
    
    Args:
        args: Dictionary containing request parameters
        
    Returns:
        Dictionary with statusCode and body
    """
    # Initialize metrics tracking
    metrics = ReviewMetrics()
    
    try:
        # Validate required parameters
        required_params = ['gitlab_token', 'project_id', 'merge_request_iid']
        missing_params = [p for p in required_params if not args.get(p)]
        
        if missing_params:
            return {
                'statusCode': 400,
                'body': {
                    'error': f"Missing required parameters: {', '.join(missing_params)}"
                }
            }
        
        # Extract parameters
        gitlab_token = args.get('gitlab_token')
        project_id = args.get('project_id')
        mr_iid = args.get('merge_request_iid')
        gitlab_url = args.get('gitlab_url', 'https://gitlab.devcula.com')
        action = args.get('action', 'opened')  # 'opened' or 'update'
        
        # AI model configuration
        ai_provider = args.get('ai_model', DEFAULT_AI_MODEL).lower()
        model_name = args.get('model_name')  # Optional specific model

        print(f"Starting review for MR !{mr_iid} in project {project_id}")
        print(f"AI Provider: {ai_provider}, Action: {action}")
        
        # Get API key for the provider
        try:
            api_key = get_api_key_for_provider(ai_provider)
        except ValueError as e:
            return {
                'statusCode': 500,
                'body': {'error': str(e)}
            }
        
        # Initialize clients
        gitlab = GitLabClient(gitlab_url, gitlab_token, project_id)
        
        # Create AI adapter
        try:
            ai_adapter = create_ai_adapter(ai_provider, api_key, model_name)
            metrics.model_name = getattr(ai_adapter, "model_display_name", ai_adapter.model_name)
            print(f"Using AI model: {metrics.model_name} ({ai_adapter.model_name})")
        except ValueError as e:
            return {
                'statusCode': 400,
                'body': {'error': str(e)}
            }
        
        # Fetch MR data
        print("Fetching MR details...")
        mr_data = gitlab.get_merge_request(mr_iid)
        
        # Detect action from MR state if not explicitly provided
        if action == 'opened' and mr_data.get('state') == 'opened':
            # Check if this is first review or update
            if mr_data.get('user_notes_count', 0) > 0:
                action = 'update'
        
        print("Fetching MR changes...")
        changes_data = gitlab.get_merge_request_changes(mr_iid)
        changes = changes_data.get('changes', [])
        
        print(f"Found {len(changes)} file changes")
        
        # Review code with AI
        print(f"Reviewing code with {ai_provider}...")
        review_data, usage_metadata = ai_adapter.review_code(
            mr_data, 
            changes,
        )
        
        # Track API metrics
        if usage_metadata:
            metrics.add_api_call(usage_metadata, ai_adapter.pricing)
        
        # Count files reviewed
        files_reviewed = len(ai_adapter.filter_changes(changes, EXCLUDED_FILE_PATTERNS, MAX_FILES))
        
        # Post summary comment only for 'opened' action
        if action == 'opened':
            print("Posting summary comment...")
            summary = format_summary_comment(review_data, files_reviewed, metrics, action)
            gitlab.post_comment(mr_iid, summary)
        else:
            print("Skipping summary comment (action: update)")
        
        # Post inline comments
        issues = review_data.get('issues', [])
        print(f"Posting {len(issues)} inline comments...")
        
        posted_count = 0
        failed_count = 0
        for issue in issues:
            try:
                file_path = issue.get('file')
                start_line = issue.get('start_line')
                end_line = issue.get('end_line')
                
                # Support both old 'line' field and new 'start_line'/'end_line' fields
                if not start_line:
                    start_line = issue.get('line')
                if not end_line:
                    end_line = start_line
                
                # Validate inputs
                if not file_path or not start_line:
                    print(f"Skipping issue without file/line: {issue.get('issue', 'Unknown')}")
                    failed_count += 1
                    continue
                
                # Validate line range
                if start_line <= 0 or end_line < start_line:
                    print(f"Skipping issue with invalid line range {start_line}-{end_line}: {issue.get('issue', 'Unknown')}")
                    failed_count += 1
                    continue
                
                # Debug output
                severity = issue.get('severity', 'unknown')
                issue_summary = issue.get('issue', 'Unknown issue')[:50]
                if start_line == end_line:
                    print(f"Posting {severity} issue on {file_path}:{start_line}: {issue_summary}")
                else:
                    print(f"Posting {severity} issue on {file_path}:{start_line}-{end_line}: {issue_summary}")
                
                inline_comment = format_inline_comment(issue)
                start_line_code = issue.get('line_code_start')
                end_line_code = issue.get('line_code_end')
                result = gitlab.post_inline_comment(
                    mr_iid,
                    mr_data,
                    file_path,
                    end_line,
                    inline_comment,
                    start_line,
                    end_line,
                    start_line_code=start_line_code,
                    end_line_code=end_line_code
                )
                
                if result:
                    posted_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                print(f"Failed to post issue: {str(e)}")
                print(f"  Issue: {issue.get('issue', 'Unknown')[:60]}")
                print(f"  File: {issue.get('file', 'Unknown')}")
                failed_count += 1
                continue
        
        print(f"Review completed: {posted_count}/{len(issues)} inline comments posted ({failed_count} failed)")
        
        # Log metrics
        metrics.log()
        
        return {
            'statusCode': 200,
            'body': {
                'message': 'Review completed successfully',
                'ai_model': ai_provider,
                'model_name': ai_adapter.model_name,
                'action': action,
                'files_reviewed': files_reviewed,
                'issues_found': len(issues),
                'inline_comments_posted': posted_count,
                'inline_comments_failed': failed_count,
                'metrics': metrics.to_dict()
            }
        }
        
    except requests.exceptions.RequestException as e:
        error_msg = f"GitLab API error: {str(e)}"
        print(error_msg)
        metrics.log()
        return {
            'statusCode': 502,
            'body': {
                'error': error_msg,
                'metrics': metrics.to_dict()
            }
        }
    
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        metrics.log()
        return {
            'statusCode': 500,
            'body': {
                'error': error_msg,
                'metrics': metrics.to_dict()
            }
        }


# For local testing
if __name__ == "__main__":
    import json
    
    # Example test payload
    test_args = {
        'gitlab_token': os.environ.get('GITLAB_TOKEN'),
        'project_id': os.environ.get('PROJECT_ID'),
        'merge_request_iid': os.environ.get('MR_IID'),
        'gitlab_url': os.environ.get('GITLAB_URL', 'https://gitlab.devcula.com'),
        'ai_model': os.environ.get('AI_MODEL', 'gemini')
    }
    
    result = main(test_args)
    print(json.dumps(result, indent=2))