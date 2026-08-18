"""Provider-agnostic errors for shared LLM transport."""

from __future__ import annotations


class LLMError(RuntimeError):
    """Base error for shared LLM transport failures."""


class LLMConfigurationError(LLMError):
    """Raised when provider configuration is incomplete or unsupported."""


class LLMProviderError(LLMError):
    """Raised when a provider request cannot return usable content."""
