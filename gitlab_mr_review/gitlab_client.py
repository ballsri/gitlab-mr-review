"""
GitLab API Client
"""

import hashlib
import requests
from typing import Dict, Any, Optional


class GitLabClient:
    """Handle GitLab API interactions"""
    
    def __init__(self, gitlab_url: str, token: str, project_id: str):
        self.gitlab_url = gitlab_url
        self.token = token
        self.project_id = project_id
        self.headers = {'PRIVATE-TOKEN': token}
        self.base_url = f"{gitlab_url}/api/v4/projects/{project_id}"
    
    def get_merge_request(self, mr_iid: str) -> Dict[str, Any]:
        """Fetch merge request details"""
        url = f"{self.base_url}/merge_requests/{mr_iid}"
        response = requests.get(url, headers=self.headers, timeout=30)
        response.raise_for_status()
        return response.json()
    
    def get_merge_request_changes(self, mr_iid: str) -> Dict[str, Any]:
        """Fetch merge request changes (diff)"""
        url = f"{self.base_url}/merge_requests/{mr_iid}/changes"
        response = requests.get(url, headers=self.headers, timeout=30)
        response.raise_for_status()
        return response.json()
    
    def post_comment(self, mr_iid: str, comment: str) -> Dict[str, Any]:
        """Post a general comment on the MR"""
        url = f"{self.base_url}/merge_requests/{mr_iid}/notes"
        data = {'body': comment}
        response = requests.post(url, headers=self.headers, json=data, timeout=30)
        response.raise_for_status()
        return response.json()
    
    def post_inline_comment(self, mr_iid: str, mr_data: Dict[str, Any], 
                           file_path: str, line: int, comment: str, 
                           start_line: Optional[int] = None,
                           end_line: Optional[int] = None,
                           start_line_code: Optional[str] = None,
                           end_line_code: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Post an inline comment on specific file/line (or line range for multi-line suggestions)
        
        For multi-line suggestions:
        - start_line: First line of the range
        - end_line: Last line of the range (if different from start_line)
        - GitLab will show the comment spanning from start_line to end_line
        """
        url = f"{self.base_url}/merge_requests/{mr_iid}/discussions"
        
        # Build position based on whether it's single-line or multi-line
        position = {
            'base_sha': mr_data['diff_refs']['base_sha'],
            'start_sha': mr_data['diff_refs']['start_sha'],
            'head_sha': mr_data['diff_refs']['head_sha'],
            'position_type': 'text',
            'new_path': file_path,
            'old_path': file_path,
        }
        
        # For multi-line comments (when start_line != end_line)
        # GitLab API supports line_range for multi-line positions
        if start_line and end_line and start_line != end_line:
            if start_line_code and end_line_code:
                position['line_range'] = {
                    'start': {
                        'line_code': start_line_code,
                        'type': 'new'
                    },
                    'end': {
                        'line_code': end_line_code,
                        'type': 'new'
                    }
                }
                position['new_line'] = end_line
                print(f"  → Multi-line comment: lines {start_line}-{end_line}")
            else:
                print("  → Missing line codes for multi-line comment, falling back to single line")
                position['new_line'] = start_line
        else:
            # Single-line position
            position['new_line'] = start_line if start_line else line
            print(f"  → Single-line comment: line {position['new_line']}")
        
        data = {
            'body': comment,
            'position': position
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=data, timeout=30)
            if response.status_code >= 400:
                print(f"GitLab API response: {response.status_code} {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Failed to post inline comment on {file_path}:{line} - {str(e)}")
            # If line_range fails, try fallback to single line at start_line
            if 'line_range' in position:
                print(f"  → Retrying as single-line comment at line {start_line}")
                position.pop('line_range', None)
                position['new_line'] = start_line
                # Remove line codes to avoid reuse
                start_line_code = None
                end_line_code = None
                data['position'] = position
                try:
                    response = requests.post(url, headers=self.headers, json=data, timeout=30)
                    if response.status_code >= 400:
                        print(f"GitLab API fallback response: {response.status_code} {response.text}")
                    response.raise_for_status()
                    return response.json()
                except:
                    pass
            return None
    
    def _generate_line_code(self, file_path: str, new_line: int, old_line: Optional[int] = None) -> str:
        """Generate line_code in the same way as GitLab::Diff::LineCode.generate."""
        if old_line is None:
            old_line = 0
        base = f"{file_path}_{old_line}_{new_line}"
        digest = hashlib.sha1(base.encode('utf-8')).hexdigest()
        return f"{digest}_{old_line}_{new_line}"