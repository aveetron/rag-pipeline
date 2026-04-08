"""Helpers for OpenAI-compatible LLM endpoints (Ollama, OpenAI, etc.)."""

from urllib.parse import urlparse


def resolve_openai_chat_completions_url(base_url: str) -> str:
    """
    Build the full URL for POST .../chat/completions.

    Ollama expects: http://localhost:11434/v1/chat/completions
    If the user sets a legacy path like /api/generate, we normalize to /v1/chat/completions.
    """
    b = base_url.strip().rstrip("/")
    if b.endswith("/chat/completions"):
        return b
    if b.endswith("/v1"):
        return f"{b}/chat/completions"
    parsed = urlparse(b)
    if not parsed.netloc:
        return f"{b}/v1/chat/completions"
    scheme = parsed.scheme or "http"
    return f"{scheme}://{parsed.netloc}/v1/chat/completions"
