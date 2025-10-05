"""
Configuration for GitLab MR Review Bot
"""

import os

# Review settings
MAX_FILES = 10
MAX_DIFF_LENGTH = 3000

# Code suggestion limits (prevent over-replacement)
MAX_SUGGESTION_LINES = 10  # Maximum lines a code suggestion can replace
WARN_SUGGESTION_LINES = 7  # Warn if suggestion replaces more than this

# Excluded file patterns
EXCLUDED_FILE_PATTERNS = [
    'package-lock.json',
    'yarn.lock',
    'Gemfile.lock',
    'composer.lock',
    'Pipfile.lock',
    'poetry.lock',
    '.min.js',
    '.min.css',
    'dist/',
    'build/',
    'node_modules/',
    'vendor/',
    '.svg',
    '.png',
    '.jpg',
    '.jpeg',
    '.gif',
    '.ico',
    '.woff',
    '.woff2',
    '.ttf',
    '.eot'
]

# AI Model configuration
DEFAULT_AI_MODEL = os.environ.get('AI_MODEL', 'gemini')  # gemini, claude, openai

# API Keys
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

# Severity configuration
SEVERITY_LIMITS = {
    'critical': None,  # Report all critical issues
    'high': 3,         # Report top 3 high issues
    'medium': 3,       # Report top 3 medium issues
    'low': 3          # Report top 3 low issues
}

# Category emoji mapping
CATEGORY_EMOJI = {
    'security': '🔒',
    'bug': '🐛',
    'performance': '⚡',
    'refactoring': '🔨',
    'style': '💅',
    'documentation': '📝',
    'testing': '🧪'
}

# Severity emoji mapping
SEVERITY_EMOJI = {
    'critical': '🔴',
    'high': '🟠',
    'medium': '🟡',
    'low': '🔵'
}