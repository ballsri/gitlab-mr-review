"""
Anthropic Claude AI Adapter
"""

import anthropic
from typing import Dict, List, Any, Tuple, Optional
from .base import AIAdapter


# Import config for suggestion limits
try:
    from ..config import MAX_SUGGESTION_LINES, WARN_SUGGESTION_LINES
except ImportError:
    MAX_SUGGESTION_LINES = 10
    WARN_SUGGESTION_LINES = 7


class ClaudeAdapter(AIAdapter):
    """Claude AI adapter"""

    def __init__(
        self,
        api_key: str,
        model_name: str = 'claude-sonnet-4-5-20250929',
        *,
        display_name: Optional[str] = None,
        pricing: Optional[Dict[str, float]] = None,
    ):
        super().__init__(api_key)

        self.client = anthropic.Anthropic(api_key=api_key)

        self.model_name = model_name
        if display_name:
            self.model_display_name = display_name
        else:
            self.model_display_name = model_name

        if pricing:
            self.pricing = pricing.copy()
            return

        # Set pricing based on model version
        # https://www.anthropic.com/pricing
        if '4-5' in model_name or '4.5' in model_name:
            # Claude 4.5 Sonnet
            self.pricing = {
                'input_per_million': 3.0,
                'output_per_million': 15.0
            }
        elif 'sonnet-4' in model_name or '-4-' in model_name:
            # Claude 4 Sonnet
            self.pricing = {
                'input_per_million': 3.0,
                'output_per_million': 15.0
            }
        elif '3-7' in model_name or '3.7' in model_name:
            # Claude 3.7 Sonnet
            self.pricing = {
                'input_per_million': 3.0,
                'output_per_million': 15.0
            }
        elif '3-5' in model_name or '3.5' in model_name:
            # Claude 3.5 Sonnet
            self.pricing = {
                'input_per_million': 3.0,
                'output_per_million': 15.0
            }
        elif 'opus' in model_name.lower():
            # Claude 3 Opus
            self.pricing = {
                'input_per_million': 15.0,
                'output_per_million': 75.0
            }
        else:
            # Default to Sonnet pricing
            self.pricing = {
                'input_per_million': 3.0,
                'output_per_million': 15.0
            }

    def _annotate_diff_with_line_numbers(self, diff: str) -> str:
        """
        Annotate diff with actual line numbers for NEW file.
        Parses @@ headers and adds [LINE XX] markers to show exact line numbers.
        """
        import re

        lines = diff.split('\n')
        annotated = []
        current_new_line = None

        for line in lines:
            # Parse @@ header to get starting line number
            header_match = re.match(r'@@ -(\d+),?\d* \+(\d+),?\d* @@(.*)' , line)
            if header_match:
                current_new_line = int(header_match.group(2))
                annotated.append(line)  # Keep header as-is
                continue

            if current_new_line is None:
                annotated.append(line)
                continue

            # For new/modified lines, show the line number
            if line.startswith('+'):
                # This is an added/modified line - GitLab CAN comment here
                annotated.append(f"[LINE {current_new_line}] {line}")
                current_new_line += 1
            elif line.startswith('-'):
                # Removed line - doesn't exist in new file, don't increment
                annotated.append(f"[REMOVED] {line}")
            else:
                # Context line - exists but wasn't changed, GitLab CANNOT comment here
                annotated.append(f"[CONTEXT] {line}")
                current_new_line += 1

        return '\n'.join(annotated)

    @staticmethod
    def _leading_whitespace(line: str) -> str:
        """Return the leading whitespace (spaces/tabs) for indentation checks."""
        if not line:
            return ''
        stripped = line.lstrip(' \t')
        return line[:len(line) - len(stripped)]

    @staticmethod
    def _count_brackets(text: str) -> Dict[str, int]:
        """Count different types of brackets in text."""
        return {
            'curly': text.count('{') - text.count('}'),
            'square': text.count('[') - text.count(']'),
            'paren': text.count('(') - text.count(')')
        }

    @staticmethod
    def _validate_bracket_balance(original: str, replacement: str) -> Tuple[bool, str]:
        """
        Validate that bracket balance is maintained between original and replacement.
        Returns (is_valid, error_message)
        """
        orig_brackets = ClaudeAdapter._count_brackets(original)
        repl_brackets = ClaudeAdapter._count_brackets(replacement)

        # Check if net change in brackets is the same
        for bracket_type in ['curly', 'square', 'paren']:
            if orig_brackets[bracket_type] != repl_brackets[bracket_type]:
                return False, f"{bracket_type} brackets not balanced (original: {orig_brackets[bracket_type]}, replacement: {repl_brackets[bracket_type]})"

        return True, ""

    def _build_new_file_maps(self, changes: List[Dict[str, Any]]) -> Dict[str, Dict[int, Dict[str, Any]]]:
        """Map each new file line to its content, old line number, and GitLab line_code."""
        import re
        import hashlib

        def generate_line_code(path: str, old_line: int, new_line: int) -> str:
            base = f"{path}_{old_line}_{new_line}"
            digest = hashlib.sha1(base.encode('utf-8')).hexdigest()
            return f"{digest}_{old_line}_{new_line}"

        file_maps: Dict[str, Dict[int, Dict[str, Any]]] = {}

        for change in changes:
            file_path = change.get('new_path') or change.get('old_path')
            if not file_path:
                continue

            diff = change.get('diff', '')
            if not diff:
                continue

            current_new_line: Optional[int] = None
            current_old_line: Optional[int] = None
            removed_old_lines: List[int] = []
            line_map: Dict[int, Dict[str, Any]] = {}

            for line in diff.split('\n'):
                header_match = re.match(r'@@ -(?P<old>\d+),?\d* \+(?P<new>\d+),?\d* @@', line)
                if header_match:
                    current_old_line = int(header_match.group('old'))
                    current_new_line = int(header_match.group('new'))
                    removed_old_lines.clear()
                    continue

                if current_new_line is None or current_old_line is None:
                    continue

                if line.startswith('+'):
                    content = line[1:]
                    if removed_old_lines:
                        old_line_value = removed_old_lines.pop(0)
                    else:
                        old_line_value = 0  # Pure addition
                    line_map[current_new_line] = {
                        'content': content,
                        'old_line': old_line_value,
                        'line_code': generate_line_code(file_path, old_line_value, current_new_line)
                    }
                    current_new_line += 1
                elif line.startswith('-'):
                    removed_old_lines.append(current_old_line)
                    current_old_line += 1
                elif line.startswith(' '):
                    content = line[1:]
                    line_map[current_new_line] = {
                        'content': content,
                        'old_line': current_old_line,
                        'line_code': generate_line_code(file_path, current_old_line, current_new_line)
                    }
                    current_new_line += 1
                    current_old_line += 1
                    removed_old_lines.clear()
                else:
                    # Ignore metadata lines (e.g., \ No newline at end of file)
                    continue

            if line_map:
                file_maps[file_path] = line_map

        return file_maps

    def build_review_prompt(self, mr_data: Dict[str, Any],
                           changes: List[Dict[str, Any]],
                           max_diff_length: int = 3000) -> str:
        """Build prompt for Claude review"""
        prompt = f"""You are an expert code reviewer. Review this GitLab merge request and report only issues you genuinely observe.

SEVERITY GUIDE
🔴 Critical – security exploits, crashes, invalid syntax, broken logic, infinite loops, extreme performance (O(n³)+), data loss, race conditions, deadlocks.
🟠 High – likely bugs, security warnings, O(n²) performance risks, missing critical error handling, resource leaks, incorrect API usage, validation gaps.
🟡 Medium – refactor opportunities, anti-patterns, unclear naming/comments, duplication, style drift, minor performance topics.
🔵 Low – polish, documentation, optional cleanups, organization tweaks.

Review rules:
1. Report only issues you can justify; zero items per band is acceptable.
2. Capture every critical issue; other severities are optional.
3. Use the MR metadata below for context when summarizing.

MR Title: {mr_data.get('title', 'Untitled')}
MR Description: {mr_data.get('description', 'No description provided')[:500]}
Source Branch: {mr_data.get('source_branch', 'unknown')}
Target Branch: {mr_data.get('target_branch', 'unknown')}

Files Changed: {len(changes)}

Changes:
"""

        for change in changes:
            file_path = change.get('new_path', 'unknown')
            diff = change.get('diff', '')[:max_diff_length]

            prompt += f"\n### File: {file_path}\n"
            if change.get('new_file'):
                prompt += "(New file)\n"
            elif change.get('deleted_file'):
                prompt += "(Deleted file)\n"
            elif change.get('renamed_file'):
                prompt += f"(Renamed from: {change.get('old_path')})\n"

            prompt += "\nDiff with NEW line numbers (use these for 'line' field):\n"
            prompt += self._annotate_diff_with_line_numbers(diff)
            prompt += "\n"

        prompt += """
IMPORTANT REMINDERS
- Only [LINE XX] markers in the annotated diff are valid comment targets.
- [CONTEXT] lines are unchanged; [REMOVED] lines no longer exist. Anchor context issues to the nearest [LINE XX].

COMMENT STRUCTURE (4 SECTIONS)
Each issue in GitLab will display as a comment with 4 sections:

1. **Severity Header**: Emoji + severity level (e.g., "🔴 Critical", "🟠 High", "🟡 Medium", "🔵 Low")

2. **Issue Summary**: One-line summary of the problem (this goes in the 'issue' field)
   Example: "SQL injection vulnerability in user query"

3. **Detailed Explanation**: 2-5 lines explaining the code context and why this is an issue (this goes in the 'explanation' field)
   - Reference the specific code being reviewed
   - Explain what's wrong and why it matters
   - Mention potential consequences

4. **Suggestion Fix**: Choose ONE of these three types:

   4.1. **CODE SUGGESTION** (suggestion_type: "code"):
        - Use for simple, localized fixes (1-10 lines)
        - Must specify exact start_line and end_line
        - Replacement code MUST have IDENTICAL line count (unless deleting)
        - Replacement code MUST preserve indentation EXACTLY
        - Replacement MUST be syntactically complete (balanced brackets, proper scope)
        - GitLab will show "Apply suggestion" button
        - Provide only executable code in code_fix (no comments)

        VALIDATION RULES FOR CODE SUGGESTIONS:
        • Count opening/closing brackets: {{, }}, [, ], (, ) must remain balanced
        • Python: Match indentation level precisely (spaces/tabs)
        • TypeScript/JavaScript: Match indentation and bracket depth
        • If replacing lines inside an object/array, keep same indent as surrounding lines
        • If scope changes (adding/removing if/for/function), use conceptual instead
        • Never replace more than 10 lines

        CRITICAL BRACKET PAIRING RULES:
        • NEVER remove a closing bracket (}}, ], )) without removing its opening bracket
        • NEVER remove an opening bracket ({{, [, () without removing its closing bracket
        • If you need to change code inside brackets, replace the CONTENT, keep the brackets
        • Valid: Replace "if (x) {{ doX(); }}" with "if (y) {{ doY(); }}" (same brackets)
        • INVALID: Replace "}}\n}}" with "message: '...'" (removes }} without opening {{)
        • INVALID: Replace "if (!user) {{" with "const valid = check();" (removes {{ without }})

        STATEMENT COMPLETENESS RULES:
        • Replacements must be complete statements/expressions
        • Don't break in the middle of: if/for/while blocks, function calls, object literals
        • Line ranges must start and end at natural boundaries (full statements)
        • First line CANNOT start with: ), }}, ], ;, ,, else, catch, finally, ., ?.
        • Last line CANNOT end with incomplete operators: ,, &&, ||, +, -, *, /, ?, :, .

        STRICT LINE COUNT MATCHING:
        • Replacing lines X to Y requires EXACTLY (Y - X + 1) lines in code_fix
        • Example: Lines 49-51 = 3 lines → code_fix MUST have exactly 3 lines (or use "" to delete all)
        • WRONG: 3 lines → 2 lines (this DELETES a line, breaking code structure)
        • Use empty string "" ONLY to delete ALL selected lines, not to reduce line count

        LINE DELETION SUPPORT:
        • To DELETE lines without replacement, set code_fix to empty string ""
        • Works for single line: start_line=45, end_line=45, code_fix=""
        • Works for multiple lines: start_line=45, end_line=48, code_fix=""
        • DO NOT use placeholder code like "void 0", "// removed", or comments
        • Use empty string to cleanly delete unnecessary code (debug logs, unused imports, dead code)

        Example (Replacement - TypeScript):
        Original (lines 45-46):
        [LINE 45] +    const user = users.find(u => u.id === userId)
        [LINE 46] +    return user.name

        Code fix (must be 2 lines, same indent):
        "    const user = users.find(u => u.id === userId)\n    return user?.name ?? 'Unknown'"

        Example (Deletion - JavaScript):
        Original (lines 38-40):
        [LINE 38] +    console.log('Debug: user =', user)
        [LINE 39] +    console.log('Debug: token =', token)
        [LINE 40] +    debugger;

        Code fix (delete 3 lines):
        ""

   4.2. **CONCEPTUAL EXPLANATION** (suggestion_type: "conceptual"):
        - Use when fix is too large (>10 lines)
        - Use when fix requires changes in multiple non-contiguous locations
        - Use when architecture/structure needs redesign
        - Explain WHAT to do and WHY in the 'explanation' field
        - DO NOT provide code_fix - leave it empty or omit it
        - The explanation should be detailed enough for developers to implement

        Example:
        {{
          "suggestion_type": "conceptual",
          "explanation": "Refactor the authentication logic to separate concerns: move token validation to a middleware, extract user loading to a service class, and handle errors at the controller level. This will improve testability and make the code more maintainable."
        }}
        (Note: no code_fix field)

   4.3. **EXPLANATION WITH CODE EXAMPLE** (suggestion_type: "example"):
        - Use when conceptual explanation benefits from showing example implementation
        - Provide illustrative code in the 'code_fix' field (not direct replacements)
        - Code is shown as example only (not for "Apply suggestion" button)
        - MUST include actual code in code_fix field

        Example:
        {{
          "suggestion_type": "example",
          "explanation": "Extract the validation logic into a separate function to improve reusability. See example implementation below:",
          "code_fix": "function validateUserInput(input: UserInput): ValidationResult {{\n  if (!input.email || !input.email.includes('@')) {{\n    return {{ valid: false, error: 'Invalid email' }};\n  }}\n  return {{ valid: true }};\n}}\n\n// Then call this function:\nconst result = validateUserInput(userInput);"
        }}
        (Note: code_fix contains example code, not empty)

SUGGESTION TYPE DECISION TREE:
- Fix is 1-10 contiguous lines + preserves structure → "code"
- Fix is >10 lines OR multiple locations OR structural change → "conceptual"
- Conceptual fix would benefit from example code → "example"

IMPORTANT: PROVIDE VARIETY IN SUGGESTION TYPES
Do NOT make all suggestions the same type. A good review typically includes:
- Some CODE suggestions (for simple, direct fixes)
- Some CONCEPTUAL explanations (for larger refactorings)
- Some EXAMPLE suggestions (when showing implementation helps)

Review quality examples:

GOOD REVIEW (varied types):
- Issue 1: Missing null check → suggestion_type: "code" with 2-line fix
- Issue 2: Poor error handling architecture → suggestion_type: "conceptual" explaining the approach
- Issue 3: Complex validation logic → suggestion_type: "example" showing how to extract to function
- Issue 4: Typo in variable name → suggestion_type: "code" with 1-line fix

BAD REVIEW (all same type):
- Issue 1: Missing null check → suggestion_type: "conceptual"
- Issue 2: Typo → suggestion_type: "conceptual"
- Issue 3: Simple logic error → suggestion_type: "conceptual"
(This is BAD because simple fixes should use "code", not "conceptual")

WHEN TO USE EACH TYPE:

Use "code" for:
✅ Simple bugs (off-by-one, null checks, typos)
✅ Missing validation (add length check, type check)
✅ Security fixes (sanitize input, use parameterized query)
✅ Quick refactors (rename variable, extract constant)
✅ Style fixes (fix indentation, remove console.log)

Use "conceptual" for:
✅ Architectural changes (split monolithic function, separate concerns)
✅ Design pattern suggestions (use Factory, Strategy pattern)
✅ Multi-file changes (move logic to new service class)
✅ Large refactorings (>10 lines or multiple locations)

Use "example" for:
✅ Complex patterns that benefit from code demonstration
✅ New utility functions developers should create
✅ Alternative implementations to consider
✅ When showing HOW to implement helps understanding

OUTPUT FORMAT
CRITICAL: You MUST respond with ONLY valid JSON. No markdown, no explanations, no preamble, no code blocks - just raw JSON.

CRITICAL RULES FOR ALL ISSUES:
1. EVERY issue MUST have a "file" field (the file path where the issue is located)
2. EVERY issue MUST have "start_line" field (even for conceptual suggestions - pick the most relevant line)
3. For multi-line issues, also provide "end_line"
4. If an issue is architectural/conceptual spanning multiple files, pick the PRIMARY file and line where it's most evident
5. NEVER omit "file" or "start_line" - GitLab requires these to post comments

Your response must be a JSON object with this exact structure:
{{
  "summary": "string (overall review summary)",
  "issues": [
    {{
      "file": "string (REQUIRED - file path, e.g., 'src/auth/auth.service.ts')",
      "start_line": number (REQUIRED - line number, even for conceptual issues),
      "end_line": number (optional - only if issue spans multiple lines),
      "severity": "critical|high|medium|low",
      "category": "security|bug|performance|refactoring|style|documentation|testing",
      "issue": "string (one-line summary)",
      "explanation": "string (2-5 lines detailed explanation)",
      "suggestion_type": "code|conceptual|example",
      "code_fix": "string (ONLY for suggestion_type='code', exact replacement code)"
    }}
  ]
}}

IMPORTANT: If you identify an issue but it doesn't map to a specific line:
- For architectural issues: Pick the main file/class where the pattern is most evident
- For missing features: Point to where the feature SHOULD be added
- For general concerns: Point to the configuration file or main entry point
- DO NOT create issues without file/line - they will be skipped!

Start your response with {{ and end with }}. Do NOT wrap in markdown code blocks.

🚨 CRITICAL: LINE NUMBER ACCURACY
You MUST use the EXACT line numbers from [LINE XX] markers in the diff!

Example showing CORRECT line number usage:
@@ -40,5 +40,8 @@
[CONTEXT]    const query = 'SELECT * FROM users'
[LINE 40] +  const newQuery = `SELECT * FROM users WHERE username='${{username}}'`
[LINE 41] +  console.log(newQuery)
[LINE 42] +  const user = this.users.find(u => u.id === userId)

CORRECT line numbers:
✅ To comment on console.log: use start_line=41, end_line=41
✅ To replace lines 40-42: use start_line=40, end_line=42, code_fix must be exactly 3 lines

WRONG line numbers (NEVER DO THIS):
❌ Using lines 57-62 when actual [LINE XX] markers show 52-57
❌ Counting lines from diff header instead of [LINE XX] markers
❌ Off-by-one errors (line 53 when marker shows [LINE 52])

VALIDATION CHECKLIST before submitting each issue:
1. Find the [LINE XX] marker for the first line → that's your start_line
2. Find the [LINE XX] marker for the last line → that's your end_line
3. Count replacement lines → must match (end_line - start_line + 1) unless deleting
4. Double-check: Does start_line match the first [LINE XX] you see? YES/NO

Remember: GitLab will highlight lines based on YOUR line numbers. Wrong numbers = suggestion appears in wrong place!
"""

        return prompt

    def _refine_code_fixes(self, issues: List[Dict[str, Any]],
                          changes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Phase 2: Refine code fixes to ensure minimal, precise replacements.
        Validates that code_fix only replaces the EXACT lines that need changing.
        """
        refined_issues = []
        conceptual_conversions = 0
        file_line_maps = self._build_new_file_maps(changes)

        for issue in issues:
            file_path = issue.get('file')
            start_line = issue.get('start_line', 0)
            end_line = issue.get('end_line', start_line)
            line_map = file_line_maps.get(file_path, {}) if file_path else {}

            if line_map and start_line:
                start_meta = line_map.get(start_line)
                end_meta = line_map.get(end_line)
                if start_meta and start_meta.get('line_code'):
                    issue['line_code_start'] = start_meta['line_code']
                if end_meta and end_meta.get('line_code'):
                    issue['line_code_end'] = end_meta['line_code']
                elif start_meta and start_meta.get('line_code'):
                    issue['line_code_end'] = start_meta['line_code']

            # Skip if not a code suggestion
            if issue.get('suggestion_type') != 'code':
                refined_issues.append(issue)
                continue

            # Validate code_fix exists for code suggestions
            code_fix = issue.get('code_fix')
            if not code_fix or not isinstance(code_fix, str):
                print(f"⚠️  Missing code_fix for code suggestion, converting to conceptual")
                print(f"   File: {issue.get('file')}:{issue.get('start_line', 0)}")
                print(f"   Issue: {issue.get('issue', 'Unknown')[:60]}")
                issue['suggestion_type'] = 'conceptual'
                issue['code_fix'] = None  # Clear invalid code_fix
                refined_issues.append(issue)
                conceptual_conversions += 1
                continue

            start_line = issue.get('start_line', 0)
            end_line = issue.get('end_line', start_line)
            lines_to_replace = end_line - start_line + 1
            code_fix_lines = len(code_fix.split('\n'))

            # Rule 0: CRITICAL - code_fix must have enough lines to replace the range
            # If we're replacing 2 lines but code_fix only has 1 line, we'll DELETE a line!
            if code_fix_lines < lines_to_replace:
                print(f"🚨 CRITICAL: code_fix has {code_fix_lines} line(s) but replacing {lines_to_replace} line(s)")
                print(f"   File: {issue.get('file')}:{start_line}-{end_line}")
                print(f"   This would DELETE {lines_to_replace - code_fix_lines} line(s) of code!")
                print(f"   Converting to conceptual to prevent data loss")
                issue['suggestion_type'] = 'conceptual'
                conceptual_conversions += 1
                refined_issues.append(issue)
                continue

            # Rule 0b: Validate line count changes with smart bracket/indent checking
            if code_fix_lines != lines_to_replace:
                # Extract original code from line_map
                original_lines = []
                for line_num in range(start_line, end_line + 1):
                    line_meta = line_map.get(line_num)
                    if line_meta:
                        original_lines.append(line_meta.get('content', ''))

                if original_lines:
                    original_code = '\n'.join(original_lines)

                    # Use smart validation to check if line count change is valid
                    is_valid, reason = self._is_line_count_change_valid(
                        original_code, code_fix, lines_to_replace, code_fix_lines
                    )

                    if not is_valid:
                        print(f"⚠️  REJECTED: Line count mismatch ({lines_to_replace} → {code_fix_lines})")
                        print(f"   File: {issue.get('file')}:{start_line}-{end_line}")
                        print(f"   Reason: {reason}")
                        issue['suggestion_type'] = 'conceptual'
                        conceptual_conversions += 1
                        refined_issues.append(issue)
                        continue
                    else:
                        print(f"✅ ALLOWED: Line count change ({lines_to_replace} → {code_fix_lines})")
                        print(f"   File: {issue.get('file')}:{start_line}-{end_line}")
                        print(f"   Reason: {reason}")
                else:
                    # Can't validate without original code, reject to be safe
                    print(f"⚠️  REJECTED: Line count mismatch, no original code to validate")
                    print(f"   File: {issue.get('file')}:{start_line}-{end_line}")
                    issue['suggestion_type'] = 'conceptual'
                    conceptual_conversions += 1
                    refined_issues.append(issue)
                    continue

            # Rule 1: Hard limit - reject suggestions that replace too many lines
            if lines_to_replace > MAX_SUGGESTION_LINES:
                print(f"⚠️  REJECTED: Replacing {lines_to_replace} lines (max: {MAX_SUGGESTION_LINES})")
                print(f"   File: {issue.get('file')}:{start_line}-{end_line}")
                print(f"   Issue: {issue.get('issue', 'Unknown')[:60]}")
                issue['suggestion_type'] = 'conceptual'
                conceptual_conversions += 1

            # Rule 2: Warning threshold - flag suspicious replacements
            elif lines_to_replace > WARN_SUGGESTION_LINES:
                print(f"⚠️  WARNING: Large replacement ({lines_to_replace} lines)")
                print(f"   File: {issue.get('file')}:{start_line}-{end_line}")
                print(f"   Keeping as code suggestion, but verify accuracy")

            # Rule 3: Detect function-level replacements (likely over-replacement)
            # If replacing 15+ lines with similar line count, probably replacing entire function
            if lines_to_replace >= 15 and code_fix_lines >= 10:
                print(f"⚠️  REJECTED: Function-level replacement detected")
                print(f"   Replacing {lines_to_replace} lines with {code_fix_lines} lines")
                print(f"   This looks like entire function replacement, converting to conceptual")
                issue['suggestion_type'] = 'conceptual'
                conceptual_conversions += 1

            # Rule 4: Sanity check - code_fix shouldn't be dramatically longer
            if code_fix_lines > lines_to_replace * 3:
                print(f"⚠️  WARNING: Replacement is {code_fix_lines}x longer than original ({lines_to_replace} → {code_fix_lines})")
                print(f"   File: {issue.get('file')}:{start_line}-{end_line}")

            # Rule 5: Ensure indentation matches original lines when possible
            line_map = file_line_maps.get(file_path, {}) if file_path else {}
            if line_map:
                code_fix_split = code_fix.split('\n')
                indentation_mismatch = False
                for idx, fix_line in enumerate(code_fix_split):
                    line_meta = line_map.get(start_line + idx)
                    if not line_meta:
                        continue
                    original_content = line_meta.get('content', '')
                    original_indent = self._leading_whitespace(original_content)
                    fix_indent = self._leading_whitespace(fix_line)
                    if original_indent != fix_indent:
                        indentation_mismatch = True
                        print(f"⚠️  REJECTED: Indentation mismatch at line {start_line + idx}")
                        print(f"   Original indent '{original_indent}' vs fix indent '{fix_indent}'")
                        break
                if indentation_mismatch:
                    issue['suggestion_type'] = 'conceptual'
                    conceptual_conversions += 1
                    refined_issues.append(issue)
                    continue

            # Rule 6: Validate bracket balance
            # Extract original code from line_map
            if line_map:
                original_lines = []
                for line_num in range(start_line, end_line + 1):
                    line_meta = line_map.get(line_num)
                    if line_meta:
                        original_lines.append(line_meta.get('content', ''))

                if original_lines:
                    original_code = '\n'.join(original_lines)
                    is_valid, error_msg = self._validate_bracket_balance(original_code, code_fix)

                    if not is_valid:
                        print(f"⚠️  REJECTED: Bracket balance mismatch")
                        print(f"   File: {issue.get('file')}:{start_line}-{end_line}")
                        print(f"   {error_msg}")
                        issue['suggestion_type'] = 'conceptual'
                        conceptual_conversions += 1
                        refined_issues.append(issue)
                        continue

                    # Rule 7: Check for bracket side mismatch (asymmetric removal)
                    has_mismatch, mismatch_msg = self._detect_bracket_side_mismatch(original_code, code_fix)
                    if has_mismatch:
                        print(f"⚠️  REJECTED: Bracket side mismatch")
                        print(f"   File: {issue.get('file')}:{start_line}-{end_line}")
                        print(f"   {mismatch_msg}")
                        issue['suggestion_type'] = 'conceptual'
                        conceptual_conversions += 1
                        refined_issues.append(issue)
                        continue

                    # Rule 8: Check statement boundaries
                    is_valid_boundary, boundary_msg = self._check_statement_boundaries(
                        original_lines, start_line, end_line
                    )
                    if not is_valid_boundary:
                        print(f"⚠️  REJECTED: Invalid statement boundaries")
                        print(f"   File: {issue.get('file')}:{start_line}-{end_line}")
                        print(f"   {boundary_msg}")
                        issue['suggestion_type'] = 'conceptual'
                        conceptual_conversions += 1
                        refined_issues.append(issue)
                        continue

            refined_issues.append(issue)

        if conceptual_conversions > 0:
            print(f"✅ Converted {conceptual_conversions} over-broad suggestions to conceptual")

        return refined_issues

    def review_code(self, mr_data: Dict[str, Any],
                   changes: List[Dict[str, Any]],
                   excluded_patterns: Optional[List[str]] = None,
                   max_files: int = 10,
                   max_diff_length: int = 3000) -> Tuple[Dict[str, Any], Any]:
        """Send code to Claude for review"""

        if excluded_patterns is None:
            excluded_patterns = []

        filtered_changes = self.filter_changes(changes, excluded_patterns, max_files)

        if not filtered_changes:
            return {
                "summary": "No reviewable code changes found (only binary/generated files)",
                "issues": []
            }, None

        prompt = self.build_review_prompt(mr_data, filtered_changes, max_diff_length)

        try:
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=16384,
                temperature=0.1,
                system="You are a code review assistant. You MUST respond with ONLY valid JSON. Never use markdown formatting, code blocks, or any text outside the JSON structure. Your entire response must be parseable as JSON.",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Extract response text
            response_text = ""
            for block in response.content:
                if block.type == "text":
                    response_text += block.text

            if not response_text:
                print("Claude response was empty")
                return {
                    "summary": "Review completed (empty response)",
                    "issues": []
                }, None

            # Clean response text - remove any potential preamble/postamble
            response_text = response_text.strip()

            # If response starts with text before JSON, try to extract just the JSON
            if not response_text.startswith('{'):
                # Look for first { and last }
                first_brace = response_text.find('{')
                last_brace = response_text.rfind('}')
                if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                    print(f"⚠️  Response had preamble/postamble, extracting JSON...")
                    response_text = response_text[first_brace:last_brace + 1]

            # Extract usage metadata - return the actual usage object, not a dict
            usage_metadata = response.usage

            # Debug: Print actual token usage
            print(f"Token usage - Input: {usage_metadata.input_tokens}, Output: {usage_metadata.output_tokens}, Total: {usage_metadata.input_tokens + usage_metadata.output_tokens}")

            # Parse and validate response
            parsed_response = self.parse_review_response(response_text)

            # If parsing failed but we have some text, try to salvage it
            if not parsed_response.get('issues') and 'summary' in parsed_response and len(parsed_response['summary']) > 400:
                print("Warning: Response may have been truncated, but continuing with available data")

            # Phase 2: Refine code fixes to prevent over-replacement
            print(f"\n🔍 Validating {len(parsed_response.get('issues', []))} code suggestions...")
            parsed_response['issues'] = self._refine_code_fixes(
                parsed_response.get('issues', []),
                filtered_changes
            )

            return parsed_response, usage_metadata

        except Exception as e:
            print(f"Claude API error: {str(e)}")
            return {
                "summary": f"Review failed: {str(e)}",
                "issues": []
            }, None
