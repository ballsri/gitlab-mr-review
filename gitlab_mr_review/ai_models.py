"""Central registry of AI models, display names, and pricing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class ModelInfo:
    """Metadata for an AI model."""

    provider: str
    name: str
    display_name: str
    pricing: Dict[str, float]
    aliases: Tuple[str, ...] = field(default_factory=tuple)
    description: str = ""
    is_default: bool = False


# Pricing references gathered from each provider's public pricing pages (2025-09).
AI_MODEL_REGISTRY: Dict[str, List[ModelInfo]] = {
    "gemini": [
        ModelInfo(
            provider="gemini",
            name="gemini-2.5-flash",
            display_name="Gemini 2.5 Flash",
            pricing={
                "input_per_million": 0.3,
                "output_per_million": 2.5,
            },
            aliases=(
                "gemini-2-5-flash",
                "gemini-flash",
                "flash-2.5",
            ),
            description="Fast review-focused Gemini 2.5 Flash model",
            is_default=True,
        ),
         ModelInfo(
            provider="gemini",
            name="gemini-2.5-pro",
            display_name="Gemini 2.5 Pro",
            pricing={
                "input_per_million": 1.25,
                "output_per_million": 10.0,
            },
            aliases=(
                "gemini-2-5-pro",
                "gemini-pro",
                "pro-2.5",
            ),
            description="Review-focused Gemini 2.5 Pro model",
        ),
    ],
    "claude": [
        ModelInfo(
            provider="claude",
            name="claude-sonnet-4-5-20250929",
            display_name="Claude 4.5 Sonnet",
            pricing={
                "input_per_million": 3.0,
                "output_per_million": 15.0,
            },
            aliases=(
                "claude-sonnet-4.5",
                "claude-sonnet-4-5",
                "sonnet-4.5",
                "sonnet-4-5",
            ),
            description="Balanced Claude Sonnet tier suitable for reviews",
            is_default=True,
        ),
        ModelInfo(
            provider="claude",
            name="claude-sonnet-4-20250514",
            display_name="Claude Sonnet 4",
            pricing={
                "input_per_million": 3.0,
                "output_per_million": 15.0,
            },
            aliases=("claude-sonnet-4", "sonnet-4"),
            description="Claude Sonnet 4 tier for fast reviews",
        ),
    ],
    "openai": [
        ModelInfo(
            provider="openai",
            name="gpt-5-2025-08-07",
            display_name="GPT-5 (Aug 2025)",
            pricing={
                "input_per_million": 1.25,
                "output_per_million": 10.0,
            },
            aliases=("gpt-5", "gpt5"),
            description="OpenAI GPT-5 tuned for code review",
            is_default=True,
        ),
        ModelInfo(
            provider="openai",
            name="gpt-5-mini-2025-08-07",
            display_name="GPT-5 Mini (Aug 2025)",
            pricing={
                "input_per_million": 0.25,
                "output_per_million": 2.0,
            },
            aliases=("gpt-5-mini", "gpt5-mini", "gpt-5m", "gpt5m"),
            description="OpenAI GPT-5 Mini tuned for code review",
        ),
    ],
}

PROVIDER_ALIASES: Dict[str, str] = {
    "anthropic": "claude",
    "claude": "claude",
    "gemini": "gemini",
    "google": "gemini",
    "openai": "openai",
}


def normalize_provider(provider: str) -> str:
    """Normalize provider identifiers to canonical registry keys."""

    provider_key = provider.lower()
    return PROVIDER_ALIASES.get(provider_key, provider_key)


def get_supported_providers() -> List[str]:
    """Return a sorted list of supported provider identifiers."""

    return sorted(AI_MODEL_REGISTRY.keys())


def get_models_for_provider(provider: str) -> List[ModelInfo]:
    """Return all models available for a provider."""

    provider_key = normalize_provider(provider)
    if provider_key not in AI_MODEL_REGISTRY:
        raise ValueError(f"Unsupported AI provider: {provider}")
    return AI_MODEL_REGISTRY[provider_key]


def get_default_model(provider: str) -> ModelInfo:
    """Return the default model configuration for a provider."""

    models = get_models_for_provider(provider)
    for model in models:
        if model.is_default:
            return model
    return models[0]


def resolve_model(provider: str, requested_model: Optional[str] = None) -> Tuple[str, ModelInfo]:
    """Resolve a model request to a concrete model name and metadata.

    Args:
        provider: Provider identifier (e.g., "gemini", "openai", "claude").
        requested_model: Optional model name supplied by the user.

    Returns:
        Tuple of (resolved model name, ModelInfo).

    Raises:
        ValueError: If the provider or model is not recognised.
    """

    models = get_models_for_provider(provider)

    if requested_model:
        requested_lower = requested_model.lower()
        # Direct match first
        for model in models:
            if requested_lower == model.name.lower():
                return model.name, model
        # Alias or fuzzy match
        for model in models:
            for alias in model.aliases:
                alias_lower = alias.lower()
                if (
                    requested_lower == alias_lower
                    or alias_lower == requested_lower
                    or alias_lower in requested_lower
                    or requested_lower in alias_lower
                ):
                    return model.name, model
        raise ValueError(
            f"Unknown model '{requested_model}' for provider '{provider}'. "
            "Run list_model_choices() to see supported options."
        )

    default_model = get_default_model(provider)
    return default_model.name, default_model


def get_default_model_name(provider: str) -> str:
    """Return the default model name for a provider."""

    return get_default_model(provider).name


def get_model_display_name(provider: str, model_name: Optional[str] = None) -> str:
    """Return a human-friendly display name for the given model."""

    _, model_info = resolve_model(provider, model_name)
    return model_info.display_name


def get_model_pricing(provider: str, model_name: Optional[str] = None) -> Dict[str, float]:
    """Return the pricing dictionary for the given model."""

    _, model_info = resolve_model(provider, model_name)
    return model_info.pricing


def list_model_choices(provider: Optional[str] = None) -> List[Dict[str, str]]:
    """Return model choices suitable for dropdowns/UI configuration."""

    choices: List[Dict[str, str]] = []

    providers = [normalize_provider(provider)] if provider else get_supported_providers()
    for provider_key in providers:
        for model in get_models_for_provider(provider_key):
            choices.append(
                {
                    "provider": provider_key,
                    "model": model.name,
                    "display_name": model.display_name,
                    "is_default": "true" if model.is_default else "false",
                }
            )

    return choices


__all__ = [
    "ModelInfo",
    "AI_MODEL_REGISTRY",
    "PROVIDER_ALIASES",
    "get_supported_providers",
    "get_models_for_provider",
    "normalize_provider",
    "get_default_model",
    "get_default_model_name",
    "get_model_display_name",
    "get_model_pricing",
    "resolve_model",
    "list_model_choices",
]
