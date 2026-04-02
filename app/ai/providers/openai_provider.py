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
    """OpenAI 호환 chat completion 엔드포인트를 호출해 JSON 추출 결과를 파싱합니다."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: Optional[str] = None,
        timeout_seconds: float = 30.0,
        client: Optional[httpx.Client] = None,
    ):
        """
        OpenAI 호환 chat completion 엔드포인트를 호출할 최소 연결 정보를 초기화합니다.
        테스트에서는 외부 네트워크 대신 주입된 httpx client를 그대로 재사용할 수 있게 둡니다.
        """

        self._base_url = base_url.rstrip("/")
        self._model = model
        self._api_key = api_key
        self._client = client or httpx.Client(base_url=self._base_url, timeout=timeout_seconds)
        self._owns_client = client is None

    def extract_rule(self, *, prompt_text: str) -> LLMExtractionResponse:
        """프롬프트를 chat completion 엔드포인트로 보내고 JSON 응답을 검증합니다."""

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
        """공급자가 내부에서 생성한 HTTP 클라이언트가 있으면 정리합니다."""

        if self._owns_client:
            self._client.close()

    def _build_request_payload(self, *, prompt_text: str) -> Dict[str, Any]:
        """JSON 전용 모드의 OpenAI 호환 chat completion 요청 payload를 만듭니다."""

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
        """API key 존재 여부를 반영해 공급자 요청 헤더를 구성합니다."""

        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = "Bearer {0}".format(self._api_key)
        return headers

    def _extract_message_payload(self, response_json: Dict[str, Any]) -> Dict[str, Any]:
        """chat completion 응답의 첫 assistant message에서 JSON 객체를 꺼냅니다."""

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
        """호환 공급자가 배열로 돌려준 텍스트 조각을 하나의 문자열로 합칩니다."""

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
