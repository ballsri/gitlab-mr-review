"""
Local testing script for the GitLab MR Review function

Usage:
1. Via Makefile (recommended):
   make test-local

2. Direct execution:
   export GOOGLE_API_KEY="your-api-key"
   export GITLAB_TOKEN="your-gitlab-token"
   export PROJECT_ID="12345"
   export MR_IID="1"
   python test_local.py

3. With arguments:
   python test_local.py --project-id 12345 --mr-iid 1
"""

import os
import sys
import json
import argparse
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import the main function from the package
from gitlab_mr_review.main import main


def test_review(args=None):
    """Test the review function locally"""

    # Parse command line arguments if provided
    parser = argparse.ArgumentParser(description='Test GitLab MR Review locally')
    parser.add_argument('--project-id', help='GitLab project ID')
    parser.add_argument('--mr-iid', help='Merge request IID')
    parser.add_argument('--gitlab-url', default='https://gitlab.com', help='GitLab URL')
    parser.add_argument('--ai-model', default='gemini', choices=['gemini', 'claude', 'openai'],
                        help='AI model to use')
    parser.add_argument('--model-name', help='Specific model name (e.g., gemini-2.5-pro, gpt-4o)')

    cli_args = parser.parse_args(args)

    # Get values from CLI args or environment variables
    project_id = cli_args.project_id or os.environ.get('PROJECT_ID')
    mr_iid = cli_args.mr_iid or os.environ.get('MR_IID')
    gitlab_url = os.environ.get('GITLAB_URL', cli_args.gitlab_url)
    ai_model = os.environ.get('AI_MODEL', cli_args.ai_model).lower()
    model_name = cli_args.model_name or os.environ.get('MODEL_NAME')

    # Check for GitLab token
    gitlab_token = os.environ.get('GITLAB_TOKEN')
    if not gitlab_token:
        print("❌ Error: GITLAB_TOKEN environment variable is not set")
        print("Run: export GITLAB_TOKEN='your-token'")
        sys.exit(1)

    # Check for appropriate API key
    api_key_vars = {
        'gemini': 'GOOGLE_API_KEY',
        'claude': 'ANTHROPIC_API_KEY',
        'openai': 'OPENAI_API_KEY'
    }

    required_api_key = api_key_vars.get(ai_model)
    if not required_api_key or not os.environ.get(required_api_key):
        print(f"❌ Error: {required_api_key} environment variable is not set")
        print(f"Run: export {required_api_key}='your-key'")
        sys.exit(1)

    # Check for project_id and mr_iid
    if not project_id or not mr_iid:
        missing = []
        if not project_id:
            missing.append('PROJECT_ID')
        if not mr_iid:
            missing.append('MR_IID')
        print(f"❌ Missing required parameters: {', '.join(missing)}")
        print("\nProvide via:")
        print("  Environment: export PROJECT_ID=12345 MR_IID=1")
        print("  Arguments: python test_local.py --project-id 12345 --mr-iid 1")
        print("  Makefile: make test-local (interactive)")
        sys.exit(1)

    print("🚀 Testing GitLab MR Review Function")
    print("-" * 50)

    # Prepare test arguments
    test_args = {
        'gitlab_token': gitlab_token,
        'project_id': project_id,
        'merge_request_iid': mr_iid,
        'gitlab_url': gitlab_url,
        'ai_model': ai_model
    }

    # Add model_name if specified
    if model_name:
        test_args['model_name'] = model_name

    print(f"AI Model: {test_args['ai_model']}")
    if model_name:
        print(f"Model Name: {model_name}")
    print(f"GitLab URL: {test_args['gitlab_url']}")
    print(f"Project ID: {test_args['project_id']}")
    print(f"MR IID: {test_args['merge_request_iid']}")
    print("-" * 50)

    # Run the function
    result = main(test_args)

    # Print results
    print("\n📊 Result:")
    print(json.dumps(result, indent=2))

    if result['statusCode'] == 200:
        print("\n✅ Review completed successfully!")
        body = result.get('body', {})
        print(f"AI Model: {body.get('model_name', 'unknown')}")
        print(f"Files reviewed: {body.get('files_reviewed', 0)}")
        print(f"Issues found: {body.get('issues_found', 0)}")
        print(f"Inline comments posted: {body.get('inline_comments_posted', 0)}")

        # Show metrics if available
        metrics = body.get('metrics', {})
        if metrics:
            print(f"\n📈 Metrics:")
            print(f"Duration: {metrics.get('duration_seconds', 0):.2f}s")
            print(f"API Calls: {metrics.get('api_calls', 1)}")
            
            # Handle nested tokens structure
            tokens = metrics.get('tokens', {})
            if tokens:
                print(f"\nToken Usage:")
                print(f"  Input tokens:  {tokens.get('input', 0):,}")
                print(f"  Output tokens: {tokens.get('output', 0):,}")
                print(f"  Total tokens:  {tokens.get('total', 0):,}")
            else:
                # Fallback to flat structure for backwards compatibility
                print(f"Input tokens: {metrics.get('input_tokens', 0):,}")
                print(f"Output tokens: {metrics.get('output_tokens', 0):,}")
            
            # Show pricing info if available
            pricing = metrics.get('pricing', {})
            if pricing:
                print(f"\nPricing:")
                print(f"  Input:  ${pricing.get('input_per_million_tokens', 0):.3f} per 1M tokens")
                print(f"  Output: ${pricing.get('output_per_million_tokens', 0):.3f} per 1M tokens")
            
            # Show cost breakdown if available
            cost = metrics.get('cost', {})
            if cost:
                print(f"\nCost Breakdown:")
                print(f"  Input cost:  ${cost.get('input_cost_usd', 0):.6f}")
                print(f"  Output cost: ${cost.get('output_cost_usd', 0):.6f}")
                print(f"  Total cost:  ${cost.get('total_cost_usd', 0):.6f}")
            else:
                # Fallback to single cost field
                est_cost = metrics.get('estimated_cost_usd', metrics.get('estimated_cost', 0))
                print(f"\nEstimated cost: ${est_cost:.6f}")
    else:
        print(f"\n❌ Review failed with status code: {result['statusCode']}")
        print(f"Error: {result.get('body', {}).get('error', 'Unknown error')}")


if __name__ == "__main__":
    test_review()
