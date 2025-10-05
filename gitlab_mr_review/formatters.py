"""
Comment formatting utilities
"""

from typing import Dict, Any
from .config import CATEGORY_EMOJI, SEVERITY_EMOJI
from .metrics import ReviewMetrics


def format_inline_comment(issue: Dict[str, Any]) -> str:
    """Format inline comment for a specific issue with GitLab suggestion format"""
    severity = issue.get('severity', 'medium').lower()
    category = issue.get('category', 'general')
    
    # Use correct colored emoji based on severity
    severity_emoji = SEVERITY_EMOJI.get(severity, '⚠️')
    category_emoji = CATEGORY_EMOJI.get(category, '💡')
    
    # Build the comment with proper severity case
    severity_display = severity.upper()
    comment = f"""{severity_emoji} **{severity_display}** {category_emoji} *{category.title()}*

**Issue:** {issue.get('issue', 'Issue detected')}

**Why it matters:** {issue.get('explanation', 'This should be addressed')}
"""
    
    # Add code fix in GitLab suggestion format (if provided)
    code_fix = issue.get('code_fix')

    # Handle deletion: code_fix can be empty string or "DELETE" to indicate line deletion
    is_deletion = False
    if code_fix is not None and isinstance(code_fix, str):
        code_fix_stripped = code_fix.strip()
        if code_fix_stripped == '' or code_fix_stripped.upper() == 'DELETE':
            is_deletion = True
            code_fix = ''  # Empty string for deletion
        else:
            code_fix = code_fix.strip('\n')
    else:
        code_fix = None

    suggestion_type = issue.get('suggestion_type', 'code')  # 'code' or 'conceptual'

    if code_fix is not None:  # Changed from 'if code_fix:' to allow empty string for deletion
        if suggestion_type == 'code':
            # Code replacement suggestion with line range
            # GitLab suggestion syntax: ```suggestion:-X+Y
            # -X: Remove X lines AFTER the comment position (not including comment line)
            # +Y: Add Y lines of new content (from code_fix)
            # 
            # Important: The comment must be placed at start_line
            # Then -X tells GitLab how many MORE lines to remove after start_line
            start_line = issue.get('start_line', 0)
            end_line = issue.get('end_line', start_line)
            
            # Validate line range
            if start_line <= 0 or end_line < start_line:
                print(f"Warning: Invalid line range {start_line}-{end_line}, skipping code_fix")
                # Fall through to conceptual approach instead
                comment += f"""
**Suggested approach:**
```
{code_fix}
```
"""
            else:
                # GitLab suggestion format is tricky:
                # ```suggestion:-X+0 means replace current line + X lines after it
                # 
                # The key insight: GitLab ALWAYS replaces AT LEAST the comment line
                # -X means "also remove X MORE lines after the comment line"
                # The replacement is ALWAYS what's in the code block (all lines)
                # 
                # CRITICAL: We should NOT use -X+Y format for line counting!
                # Instead, use -0+0 and let GitLab replace based on content length
                #
                # Actually, after research: GitLab uses the CODE BLOCK CONTENT to determine
                # what gets replaced. The -X just tells it how many ADDITIONAL lines to remove.
                # But if code_fix has fewer lines than (end_line - start_line + 1), we lose code!
                #
                # SOLUTION: Ensure code_fix contains ALL lines being replaced, then use -0+0
                
                lines_to_replace = end_line - start_line + 1  # Total lines being replaced
                lines_in_fix = len(code_fix.split('\n')) if code_fix else 0

                # Handle line deletion: empty code_fix means delete the lines
                if is_deletion:
                    # GitLab suggestion with empty content = delete lines
                    remove_before = 0
                    remove_after = lines_to_replace - 1
                    suggestion_marker = f"```suggestion:-{remove_before}+{remove_after}"

                    # Debug output
                    print(f"🗑️  Deletion suggestion for line {start_line}: deleting {lines_to_replace} line(s)")

                    comment += f"""
**Suggested fix:** Delete {lines_to_replace} line(s)
{suggestion_marker}
```
"""
                # Safety check: If code_fix has fewer lines than what we're replacing,
                # this will DELETE code! Convert to conceptual instead (unless it's intentional deletion).
                elif lines_in_fix < lines_to_replace:
                    print(f"⚠️  DANGER: code_fix ({lines_in_fix} lines) < lines to replace ({lines_to_replace} lines)")
                    print(f"   This would DELETE {lines_to_replace - lines_in_fix} lines of code!")
                    print(f"   Converting to conceptual suggestion to prevent data loss")
                    comment += f"""
**Suggested approach:**
```
{code_fix}
```
"""
                else:
                    # Safe to use suggestion with precise line offsets.
                    # GitLab expects offsets relative to the commented line.
                    # Since we anchor on the first changed line, we never remove lines above it.
                    remove_before = 0
                    remove_after = lines_to_replace - 1
                    suggestion_marker = f"```suggestion:-{remove_before}+{remove_after}"

                    # Debug output
                    print(f"Suggestion for line {start_line}: replacing {lines_to_replace} line(s) with {lines_in_fix} line(s)")

                    comment += f"""
**Suggested fix:**
{suggestion_marker}
{code_fix}
```
"""
        else:
            # Conceptual or design suggestion (no auto-apply)
            # Only show code block if there's actual code content
            if code_fix and code_fix.strip():
                comment += f"""
**Suggested approach:**
```
{code_fix}
```
"""
            else:
                # No code example provided - just show the explanation
                pass
    
    comment += "\n---\n*AI Code Review*"
    
    return comment


def format_summary_comment(review_data: Dict[str, Any], 
                          files_reviewed: int, 
                          metrics: ReviewMetrics,
                          action: str = 'opened') -> str:
    """Format the summary comment for GitLab"""
    issues = review_data.get('issues', [])
    
    # Count by severity
    severity_counts = {
        'critical': 0,
        'high': 0,
        'medium': 0,
        'low': 0
    }
    
    # Count by category
    category_counts = {}
    
    for issue in issues:
        severity = issue.get('severity', 'medium').lower()
        if severity in severity_counts:
            severity_counts[severity] += 1
        
        category = issue.get('category', 'general')
        category_counts[category] = category_counts.get(category, 0) + 1
    
    total_issues = len(issues)
    
    # Different header based on action
    if action == 'opened':
        header = "## 🤖 AI Code Review"
    else:
        header = "## 🔄 AI Code Review Update"
    
    # Parse summary properly - it should be a string, not JSON
    summary_text = review_data.get('summary', 'Review completed')
    if isinstance(summary_text, str):
        # Clean up any JSON artifacts if present
        if summary_text.startswith('{'):
            # Malformed - try to extract just text
            import re
            match = re.search(r'"summary":\s*"([^"]+)"', summary_text)
            if match:
                summary_text = match.group(1)
            else:
                summary_text = "Review completed"
    
    comment = f"""{header}

**Summary:**
{summary_text}

**Files Reviewed:** {files_reviewed}
**Total Suggestions:** {total_issues}
"""
    
    if total_issues > 0:
        comment += "\n### 📊 Issue Breakdown\n\n"
        comment += "**By Severity:**\n"
        if severity_counts['critical'] > 0:
            comment += f"- 🔴 **Critical:** {severity_counts['critical']} (Fix immediately)\n"
        if severity_counts['high'] > 0:
            comment += f"- 🟠 **High:** {severity_counts['high']} (Should fix)\n"
        if severity_counts['medium'] > 0:
            comment += f"- 🟡 **Medium:** {severity_counts['medium']} (Consider fixing)\n"
        if severity_counts['low'] > 0:
            comment += f"- 🔵 **Low:** {severity_counts['low']} (Optional)\n"
        
        comment += "\n**By Category:**\n"
        for category, count in sorted(category_counts.items(), key=lambda x: -x[1]):
            emoji = CATEGORY_EMOJI.get(category, '💡')
            comment += f"- {emoji} {category.title()}: {count}\n"
        
        comment += "\n### 💡 Next Steps\n\n"
        if severity_counts['critical'] > 0:
            comment += f"⚠️ **Action Required:** Fix {severity_counts['critical']} critical issue(s) before merging\n\n"
        
        comment += "Click the **Apply suggestion** button on inline comments to auto-fix issues!\n"
        
    else:
        comment += "\n✅ **No issues detected** - Code looks great!\n"
    
    # Add metrics section
    metrics_dict = metrics.to_dict()
    tokens = metrics_dict.get('tokens', {})
    cost_info = metrics_dict.get('cost', {})
    pricing_info = metrics_dict.get('pricing', {})
    
    comment += f"""
### 📈 Review Metrics

- 🤖 Model: {metrics_dict.get('model', 'Unknown')}
- ⏱️ Duration: {metrics_dict.get('duration_seconds', 0):.2f}s
- 🔄 API Calls: {metrics_dict.get('api_calls', 0)}
- 🎯 Tokens: {tokens.get('total', 0):,} (Input: {tokens.get('input', 0):,}, Output: {tokens.get('output', 0):,})
"""
    
    # Add cost breakdown if available
    if cost_info:
        comment += f"- 💰 Cost: ${cost_info.get('total_cost_usd', 0):.6f} USD (Input: ${cost_info.get('input_cost_usd', 0):.6f}, Output: ${cost_info.get('output_cost_usd', 0):.6f})\n"
    else:
        comment += f"- 💰 Est. Cost: ${metrics_dict.get('estimated_cost_usd', 0):.6f} USD\n"
    
    # Add pricing info if available
    if pricing_info:
        comment += f"- 💵 Pricing: ${pricing_info.get('input_per_million_tokens', 0):.3f}/${pricing_info.get('output_per_million_tokens', 0):.3f} per 1M tokens (in/out)\n"
    
    comment += "\n---\n*Powered by AI Code Review Bot*"
    
    return comment