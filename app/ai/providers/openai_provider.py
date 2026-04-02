from __future__ import annotations

import json
from json import JSONDecodeError
from typing import Any, Dict, List, Optional

import httpx
from pydantic import ValidationError

from app.ai.providers.base import (
    StructuredOutputProviderResponseError,
    StructuredOutputProviderTransportError,
)
from app.schemas import LLMExtractionResponse


class OpenAICompatibleStructuredOutputProvider:
    """Call an OpenAI-compatible chat completion endpoint and parse one JSON extraction payload."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: Optional[str] = None,
        timeout_seconds: float = 30.0,
        client: Optional[httpx.Client] = None,
    ):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._api_key = api_key
        self._client = client or httpx.Client(base_url=self._base_url, timeout=timeout_seconds)
        self._owns_client = client is None

    def extract_rule(self, *, prompt_text: str) -> LLMExtractionResponse:
        """Submit one prompt to a chat completion endpoint and validate the returned JSON payload."""

        try:
            response = self._client.post(
                "/chat/completions",
                headers=self._build_headers(),
                json=self._build_request_payload(prompt_text=prompt_text),
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise StructuredOutputProviderTransportError(
                "Provider returned HTTP error: {0}".format(exc.response.status_code)
            ) from exc
        except httpx.RequestError as exc:
            raise StructuredOutputProviderTransportError(
                "Provider request failed: {0}".format(exc)
            ) from exc

        try:
            response_json = response.json()
            message_payload = self._extract_message_payload(response_json)
            return LLMExtractionResponse.model_validate(message_payload)
        except (KeyError, TypeError, JSONDecodeError, ValidationError) as exc:
            raise StructuredOutputProviderResponseError(
                "Provider returned invalid structured output"
            ) from exc

    def close(self) -> None:
        """Close the owned HTTP client when the provider created it internally."""

        if self._owns_client:
            self._client.close()

    def _build_request_payload(self, *, prompt_text: str) -> Dict[str, Any]:
        """Build one OpenAI-compatible chat completion payload in JSON-only mode."""

        return {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": "Return one JSON object that follows the scholarship extraction schema.",
                },
                {
                    "role": "user",
                    "content": prompt_text,
                },
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        }

    def _build_headers(self) -> Dict[str, str]:
        """Build provider headers, including bearer auth when an API key is available."""

        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = "Bearer {0}".format(self._api_key)
        return headers

    def _extract_message_payload(self, response_json: Dict[str, Any]) -> Dict[str, Any]:
        """Read one JSON object from the first assistant message of a chat completion response."""

        choices = response_json["choices"]
        message = choices[0]["message"]

        parsed = message.get("parsed")
        if isinstance(parsed, dict):
            return parsed

        content = message["content"]
        if isinstance(content, str):
            return json.loads(content)
        if isinstance(content, list):
            text_content = self._join_text_fragments(content)
            return json.loads(text_content)
        if isinstance(content, dict):
            return content

        raise TypeError("Unsupported message content type")

    @staticmethod
    def _join_text_fragments(content: List[Dict[str, Any]]) -> str:
        """Join text fragments from content arrays returned by compatible providers."""

        fragments: List[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            if "text" in item and isinstance(item["text"], str):
                fragments.append(item["text"])
                continue
            if item.get("type") == "text" and isinstance(item.get("text"), str):
                fragments.append(item["text"])
        if not fragments:
            raise TypeError("Structured output content did not include text fragments")
        return "".join(fragments)
