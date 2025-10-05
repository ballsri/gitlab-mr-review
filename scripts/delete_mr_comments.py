#!/usr/bin/env python3
"""
Script to delete all comments from a specific GitLab merge request.
Useful for local development and testing.

Usage:
    python delete_mr_comments.py <project_id> <mr_iid>

    Or with environment variables:
    PROJECT_ID=123 MR_IID=456 python delete_mr_comments.py

    Or via Makefile:
    make delete-comments PROJECT_ID=123 MR_IID=456
"""

import os
import sys
import requests
from typing import List, Dict, Any


def get_env_or_arg(env_var: str, arg_index: int, description: str) -> str:
    """Get value from environment variable or command line argument"""
    value = os.environ.get(env_var)
    if not value and len(sys.argv) > arg_index:
        value = sys.argv[arg_index]
    if not value:
        raise ValueError(f"Missing {description}. Set {env_var} or pass as argument.")
    return value


def get_project_info(gitlab_url: str, gitlab_token: str, project_id: str) -> Dict[str, Any]:
    """Fetch project information from GitLab"""
    headers = {'PRIVATE-TOKEN': gitlab_token}
    project_url = f"{gitlab_url}/api/v4/projects/{project_id}"

    try:
        response = requests.get(project_url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return {}


def get_mr_info(gitlab_url: str, gitlab_token: str, project_id: str, mr_iid: str) -> Dict[str, Any]:
    """Fetch merge request information from GitLab"""
    headers = {'PRIVATE-TOKEN': gitlab_token}
    mr_url = f"{gitlab_url}/api/v4/projects/{project_id}/merge_requests/{mr_iid}"

    try:
        response = requests.get(mr_url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return {}


def delete_mr_comments(gitlab_url: str, gitlab_token: str, project_id: str, mr_iid: str) -> None:
    """Delete all comments from a merge request"""

    headers = {
        'PRIVATE-TOKEN': gitlab_token
    }

    # Fetch project and MR info for display
    print("\n🔍 Fetching project and MR information...")
    project_info = get_project_info(gitlab_url, gitlab_token, project_id)
    mr_info = get_mr_info(gitlab_url, gitlab_token, project_id, mr_iid)

    project_name = project_info.get('name_with_namespace', project_info.get('name', f'Project {project_id}'))
    mr_title = mr_info.get('title', f'MR !{mr_iid}')

    print(f"\n{'='*60}")
    print(f"🗑️  DELETE MR COMMENTS")
    print(f"{'='*60}")
    print(f"\033[1;33m📦 Project: {project_name}\033[0m")  # Bold yellow
    print(f"\033[1;36m🔀 MR: !{mr_iid} - {mr_title}\033[0m")  # Bold cyan
    print(f"{'='*60}")
    print(f"🌐 GitLab URL: {gitlab_url}")
    print(f"🔢 Project ID: {project_id}")
    print(f"{'='*60}\n")

    # Get all notes/comments for the MR
    notes_url = f"{gitlab_url}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/notes"

    try:
        print("📥 Fetching all comments...")
        response = requests.get(notes_url, headers=headers)
        response.raise_for_status()
        notes = response.json()

        if not notes:
            print("✅ No comments found on this MR.")
            return

        print(f"📋 Found {len(notes)} comment(s)")

        # Ask for confirmation
        print("\n⚠️  WARNING: This will delete ALL comments on this MR!")
        confirmation = input("Type 'yes' to confirm deletion: ")

        if confirmation.lower() != 'yes':
            print("❌ Deletion cancelled.")
            return

        # Delete each note
        deleted_count = 0
        skipped_count = 0
        error_count = 0

        for note in notes:
            note_id = note['id']
            author = note.get('author', {}).get('username', 'unknown')
            body_preview = note.get('body', '')[:50]

            # Skip system notes (GitLab automated messages)
            if note.get('system', False):
                print(f"⏭️  Skipping system note {note_id}")
                skipped_count += 1
                continue

            # Delete the note
            delete_url = f"{gitlab_url}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/notes/{note_id}"

            try:
                print(f"🗑️  Deleting note {note_id} by @{author}: \"{body_preview}...\"")
                delete_response = requests.delete(delete_url, headers=headers)
                delete_response.raise_for_status()
                deleted_count += 1
            except requests.exceptions.RequestException as e:
                print(f"❌ Error deleting note {note_id}: {e}")
                error_count += 1

        print(f"\n{'='*60}")
        print(f"📊 DELETION SUMMARY")
        print(f"{'='*60}")
        print(f"✅ Deleted: {deleted_count}")
        print(f"⏭️  Skipped (system): {skipped_count}")
        print(f"❌ Errors: {error_count}")
        print(f"{'='*60}\n")

    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching comments: {e}")
        sys.exit(1)


def main():
    """Main entry point"""
    try:
        # Get configuration from environment or arguments
        gitlab_url = os.environ.get('GITLAB_URL', 'https://gitlab.com')
        gitlab_token = os.environ.get('GITLAB_TOKEN')

        if not gitlab_token:
            print("❌ Error: GITLAB_TOKEN not set")
            print("Set it in your .env file or as an environment variable")
            sys.exit(1)

        # Get project ID and MR IID
        try:
            project_id = get_env_or_arg('PROJECT_ID', 1, 'Project ID')
            mr_iid = get_env_or_arg('MR_IID', 2, 'MR IID')
        except ValueError as e:
            print(f"❌ {e}")
            print(f"\nUsage: {sys.argv[0]} <project_id> <mr_iid>")
            print(f"   or: PROJECT_ID=123 MR_IID=456 {sys.argv[0]}")
            sys.exit(1)

        # Delete comments
        delete_mr_comments(gitlab_url, gitlab_token, project_id, mr_iid)

    except KeyboardInterrupt:
        print("\n❌ Cancelled by user")
        sys.exit(1)


if __name__ == '__main__':
    main()
