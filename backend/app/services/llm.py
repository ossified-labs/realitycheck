"""Claude wrapper that returns validated structured JSON via forced tool use."""
from __future__ import annotations

from typing import Any, Protocol


class LLMError(RuntimeError):
    pass


class LLM(Protocol):
    def structured(self, *, system: str, prompt: str, tool_name: str,
                   schema: dict[str, Any], max_tokens: int = 2000) -> dict[str, Any]: ...


class ClaudeLLM:
    """Forces Claude to answer by calling a single tool whose input_schema is our JSON schema.

    This gives us machine-readable output without parsing free text.
    """

    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise LLMError("ANTHROPIC_API_KEY is not set")
        import anthropic  # imported lazily so tests run without the SDK

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def structured(self, *, system: str, prompt: str, tool_name: str,
                   schema: dict[str, Any], max_tokens: int = 2000) -> dict[str, Any]:
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            tools=[{"name": tool_name, "description": f"Return the {tool_name} result.",
                    "input_schema": schema}],
            tool_choice={"type": "tool", "name": tool_name},
            messages=[{"role": "user", "content": prompt}],
        )
        for block in resp.content:
            if getattr(block, "type", None) == "tool_use" and block.name == tool_name:
                return dict(block.input)
        raise LLMError(f"Model did not return a {tool_name} tool call")
