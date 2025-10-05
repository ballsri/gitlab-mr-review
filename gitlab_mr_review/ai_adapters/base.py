"""
Base adapter interface for AI models
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Tuple


class AIAdapter(ABC):
    """Base class for AI model adapters"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model_name = "unknown"
        self.model_display_name = "Unknown Model"
        self.pricing = {
            'input_per_million': 0.0,
            'output_per_million': 0.0
        }
    
    @abstractmethod
    def review_code(self, mr_data: Dict[str, Any], 
                   changes: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], Any]:
        """
        Review code and return (review_data, usage_metadata)
        
        Args:
            mr_data: Merge request metadata
            changes: List of file changes
            
        Returns:
            Tuple of (review_data dict, usage_metadata object)
        """
        pass
    
    @abstractmethod
    def build_review_prompt(self, mr_data: Dict[str, Any], 
                           changes: List[Dict[str, Any]]) -> str:
        """Build the review prompt for the AI model"""
        pass
    
    def should_include_file(self, file_path: str, excluded_patterns: List[str]) -> bool:
        """Check if file should be included in review"""
        return not any(pattern in file_path for pattern in excluded_patterns)
    
    def filter_changes(self, changes: List[Dict[str, Any]], 
                      excluded_patterns: List[str], 
                      max_files: int) -> List[Dict[str, Any]]:
        """Filter out excluded files and limit changes"""
        filtered = []
        for change in changes:
            file_path = change.get('new_path', '')
            if self.should_include_file(file_path, excluded_patterns):
                filtered.append(change)
                if len(filtered) >= max_files:
                    break
        return filtered
    
    def parse_review_response(self, response_text: str) -> Dict[str, Any]:
        """Parse AI response into standardized format"""
        import json
        import re
        
        try:
            # Clean control characters that break JSON parsing
            # Remove all control characters except newline, tab, and carriage return
            response_text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', response_text)
            
            # Remove markdown code blocks if present
            if '```json' in response_text:
                json_start = response_text.find('```json') + 7
                json_end = response_text.find('```', json_start)
                response_text = response_text[json_start:json_end].strip()
            elif '```' in response_text:
                json_start = response_text.find('```') + 3
                json_end = response_text.find('```', json_start)
                response_text = response_text[json_start:json_end].strip()
            
            # Parse JSON
            review_data = json.loads(response_text)

            # Normalize top-level structure
            if isinstance(review_data, list):
                review_data = {
                    'summary': 'Review completed',
                    'issues': review_data
                }
            elif not isinstance(review_data, dict):
                review_data = {
                    'summary': str(review_data),
                    'issues': []
                }
            
            # Validate structure
            if 'summary' not in review_data:
                review_data['summary'] = 'Review completed'
            if 'issues' not in review_data:
                review_data['issues'] = []

            severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}

            def normalize_severity(raw: Any) -> str:
                text = str(raw).lower() if raw is not None else 'medium'
                if any(token in text for token in ('critical', 'blocker', 'p0', 'sev0', 'sev-0')):
                    return 'critical'
                if any(token in text for token in ('high', 'p1', 'sev1', 'sev-1')):
                    return 'high'
                if any(token in text for token in ('low', 'p3', 'sev3', 'sev-3')):
                    return 'low'
                return 'medium'

            allowed_categories = {
                'security', 'bug', 'performance', 'refactoring', 'style', 'documentation', 'testing', 'validation'
            }

            def normalize_category(raw: Any) -> str:
                text = str(raw).lower() if raw is not None else 'general'
                for category in allowed_categories:
                    if category in text:
                        return category
                return 'general'

            normalized_issues = []
            for issue in review_data['issues']:
                normalized_issue = dict(issue) if isinstance(issue, dict) else {}
                normalized_issue['severity'] = normalize_severity(normalized_issue.get('severity', 'medium'))
                normalized_issue['category'] = normalize_category(normalized_issue.get('category', 'general'))
                suggestion_raw = str(normalized_issue.get('suggestion_type', 'code')).lower()
                normalized_issue['suggestion_type'] = 'code' if suggestion_raw.startswith('code') else 'conceptual'

                for key in ('start_line', 'end_line'):
                    if key in normalized_issue:
                        try:
                            normalized_issue[key] = int(normalized_issue[key])
                        except (TypeError, ValueError):
                            normalized_issue[key] = 0

                normalized_issues.append(normalized_issue)

            review_data['issues'] = normalized_issues

            # Sort issues by severity (critical first)
            review_data['issues'].sort(
                key=lambda x: severity_order.get(x.get('severity', 'low').lower(), 4)
            )
            
            return review_data
            
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON: {e}")
            print(f"Response text (first 500 chars): {response_text[:500]}")
            
            # Try to salvage partial JSON
            try:
                # Attempt to fix common truncation issues
                # 1. Try to close incomplete strings
                if response_text.rstrip().endswith('"'):
                    fixed_text = response_text
                else:
                    # Find last complete object
                    last_complete = response_text.rfind('}')
                    if last_complete > 0:
                        # Try to close the JSON properly
                        fixed_text = response_text[:last_complete + 1]
                        # Count brackets to balance
                        open_braces = fixed_text.count('{')
                        close_braces = fixed_text.count('}')
                        open_brackets = fixed_text.count('[')
                        close_brackets = fixed_text.count(']')
                        
                        # Add missing closures
                        fixed_text += ']' * (open_brackets - close_brackets)
                        fixed_text += '}' * (open_braces - close_braces)
                        
                        review_data = json.loads(fixed_text)
                        print(f"Successfully salvaged partial response with {len(review_data.get('issues', []))} issues")
                        
                        if 'summary' not in review_data:
                            review_data['summary'] = 'Review completed (response was truncated)'
                        if 'issues' not in review_data:
                            review_data['issues'] = []
                        
                        return review_data
            except Exception as salvage_error:
                print(f"Could not salvage response: {salvage_error}")
            
            # Last resort: return error response
            return {
                "summary": f"Review completed with parsing issues. Raw response (truncated): {response_text[:300]}...",
                "issues": []
            }
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            'name': self.model_name,
            'pricing': self.pricing
        }

    @staticmethod
    def _detect_bracket_side_mismatch(original: str, replacement: str) -> Tuple[bool, str]:
        """
        Detect if replacement removes opening/closing brackets asymmetrically.

        CRITICAL: This prevents partial bracket removal like:
        - Removing '}' without removing '{'
        - Removing '{' without removing '}'

        Returns:
            (has_mismatch, error_message)
        """
        # Count bracket sides in original
        orig_open = {
            'curly': original.count('{'),
            'square': original.count('['),
            'paren': original.count('(')
        }
        orig_close = {
            'curly': original.count('}'),
            'square': original.count(']'),
            'paren': original.count(')')
        }

        # Count bracket sides in replacement
        repl_open = {
            'curly': replacement.count('{'),
            'square': replacement.count('['),
            'paren': replacement.count('(')
        }
        repl_close = {
            'curly': replacement.count('}'),
            'square': replacement.count(']'),
            'paren': replacement.count(')')
        }

        bracket_names = {'curly': '{}', 'square': '[]', 'paren': '()'}

        # Check each bracket type for asymmetric removal
        for btype in ['curly', 'square', 'paren']:
            # If removing closing brackets without removing opening ones
            if repl_close[btype] < orig_close[btype] and repl_open[btype] >= orig_open[btype]:
                removed_count = orig_close[btype] - repl_close[btype]
                return True, f"Removes {removed_count} closing '{bracket_names[btype][1]}' but keeps opening '{bracket_names[btype][0]}' (creates orphan brackets)"

            # If removing opening brackets without removing closing ones
            if repl_open[btype] < orig_open[btype] and repl_close[btype] >= orig_close[btype]:
                removed_count = orig_open[btype] - repl_open[btype]
                return True, f"Removes {removed_count} opening '{bracket_names[btype][0]}' but keeps closing '{bracket_names[btype][1]}' (creates orphan brackets)"

        return False, ""

    @staticmethod
    def _check_statement_boundaries(original_lines: List[str],
                                    start_line: int,
                                    end_line: int) -> Tuple[bool, str]:
        """
        Check if selected lines form complete statements.

        This prevents breaking code in the middle of:
        - Incomplete expressions (ends with operators)
        - Orphaned closing brackets
        - Chain calls

        Returns:
            (is_valid, error_message)
        """
        if not original_lines:
            return True, ""

        first_line = original_lines[0].strip()
        # Check if first line starts with orphaned closing bracket/statement ender
        orphan_starts = [')', '}', ']', ';', ',', ':', 'else', 'catch', 'finally']
        for orphan in orphan_starts:
            if first_line.startswith(orphan):
                return False, f"Line {start_line} starts with '{orphan}' (orphaned - likely part of previous statement)"

        # Check for chain call continuation at start
        if first_line.startswith('?.'):
            return False, f"Line {start_line} starts with method chain continuation (orphaned)"

        return True, ""

    @staticmethod
    def _is_line_count_change_valid(original: str, replacement: str,
                                    original_lines_count: int,
                                    replacement_lines_count: int) -> Tuple[bool, str]:
        """
        Validate if changing line count is structurally sound.

        Allows line count changes IF:
        1. Brackets remain balanced the same way
        2. Not removing closing brackets without opening ones (asymmetric)
        3. Base indentation is preserved

        This allows valid transformations like:
        - Adding validation decorators (2 lines → 4 lines)
        - Extracting constants (1 line → 2 lines)
        - Removing debug code (3 lines → 1 line)

        Returns:
            (is_valid, reason)
        """
        # If line counts match, no need to validate
        if original_lines_count == replacement_lines_count:
            return True, "Line counts match"

        # Check bracket balance
        def count_brackets(text: str) -> Dict[str, int]:
            return {
                'curly': text.count('{') - text.count('}'),
                'square': text.count('[') - text.count(']'),
                'paren': text.count('(') - text.count(')')
            }

        orig_balance = count_brackets(original)
        repl_balance = count_brackets(replacement)

        # Brackets must remain balanced the same way
        if orig_balance != repl_balance:
            return False, f"Bracket balance changed: {orig_balance} → {repl_balance}"

        # Check for asymmetric bracket removal
        orig_open = {'curly': original.count('{'), 'square': original.count('['), 'paren': original.count('(')}
        orig_close = {'curly': original.count('}'), 'square': original.count(']'), 'paren': original.count(')')}
        repl_open = {'curly': replacement.count('{'), 'square': replacement.count('['), 'paren': replacement.count('(')}
        repl_close = {'curly': replacement.count('}'), 'square': replacement.count(']'), 'paren': replacement.count(')')}

        for btype in ['curly', 'square', 'paren']:
            # Removing closing without removing opening
            if repl_close[btype] < orig_close[btype] and repl_open[btype] >= orig_open[btype]:
                return False, f"Removes closing {btype} brackets asymmetrically"
            # Removing opening without removing closing
            if repl_open[btype] < orig_open[btype] and repl_close[btype] >= orig_close[btype]:
                return False, f"Removes opening {btype} brackets asymmetrically"

        # For Python: check indentation level is preserved
        orig_lines = original.split('\n')
        repl_lines = replacement.split('\n')

        if orig_lines and repl_lines:
            # Get first non-empty line's indentation
            def get_indent(lines: List[str]) -> str:
                for line in lines:
                    if line.strip():
                        return line[:len(line) - len(line.lstrip())]
                return ""

            orig_indent = get_indent(orig_lines)
            repl_indent = get_indent(repl_lines)

            # Indentation should match for first significant line
            if orig_indent != repl_indent:
                return False, f"Base indentation changed ('{orig_indent}' → '{repl_indent}')"

        # If all checks pass, line count change is valid
        return True, "Structurally sound line count change"