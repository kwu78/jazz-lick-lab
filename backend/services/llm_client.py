import json
import logging
import os
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

_API_URL = "https://api.anthropic.com/v1/messages"
_API_VERSION = "2023-06-01"


class AnthropicClient:
    """Minimal Anthropic Messages API client using only stdlib."""

    def __init__(self, api_key: str, model: str, timeout: int = 30):
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    @classmethod
    def from_env(cls) -> "AnthropicClient":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        model = os.getenv("ANTHROPIC_MODEL")
        if not model:
            raise RuntimeError("ANTHROPIC_MODEL is not set")
        timeout = int(os.getenv("ANTHROPIC_TIMEOUT_SEC", "30"))
        return cls(api_key=api_key, model=model, timeout=timeout)

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Send a message to the Anthropic API and return the text response."""
        body = json.dumps({
            "model": self._model,
            "max_tokens": 700,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }).encode()

        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": _API_VERSION,
            "content-type": "application/json",
        }

        req = urllib.request.Request(_API_URL, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode(errors="replace")[:200]
            raise RuntimeError(
                f"Anthropic API error {exc.code}: {err_body}"
            ) from exc

        # Concatenate all text content blocks
        parts = [
            block["text"]
            for block in data.get("content", [])
            if block.get("type") == "text"
        ]
        return "".join(parts)
