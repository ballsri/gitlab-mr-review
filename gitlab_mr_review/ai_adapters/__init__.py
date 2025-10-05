"""
AI Adapter Factory
"""

from typing import Optional, Dict, Any

from .base import AIAdapter
from .gemini import GeminiAdapter
from .claude import ClaudeAdapter
from .openai import OpenAIAdapter
from ..ai_models import resolve_model, list_model_choices, normalize_provider


def create_ai_adapter(provider: str, api_key: str, model_name: Optional[str] = None) -> AIAdapter:
    """
    Factory function to create AI adapter based on provider

    Args:
        provider: AI provider name ('gemini', 'anthropic', 'claude', 'openai')
        api_key: API key for the provider
        model_name: Optional specific model name

    Returns:
        AIAdapter instance

    Raises:
        ValueError: If provider is not supported
    """
    provider_key = normalize_provider(provider)

    if provider_key not in ['gemini', 'claude', 'openai']:
        raise ValueError(f"Unsupported AI provider: {provider}. Choose from: gemini, anthropic, claude, openai")

    resolved_name, model_info = resolve_model(provider_key, model_name)
    pricing: Dict[str, float] = model_info.pricing
    adapter_kwargs: Dict[str, Any] = {
        'api_key': api_key,
        'model_name': resolved_name,
        'display_name': model_info.display_name,
    }

    if pricing:
        adapter_kwargs['pricing'] = pricing

    if provider_key == 'gemini':
        adapter = GeminiAdapter(**adapter_kwargs)
    elif provider_key == 'claude':
        adapter = ClaudeAdapter(**adapter_kwargs)
    else:
        adapter = OpenAIAdapter(**adapter_kwargs)

    return adapter


def get_available_models(provider: Optional[str] = None):
    """Return available model choices for UI display."""
    return list_model_choices(provider)


# Export all adapters
__all__ = [
    'AIAdapter',
    'GeminiAdapter',
    'ClaudeAdapter',
    'OpenAIAdapter',
    'create_ai_adapter',
    'get_available_models',
]