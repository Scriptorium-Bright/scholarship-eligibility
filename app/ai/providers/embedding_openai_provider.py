from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import httpx

from app.ai.providers.embedding_base import (
    EmbeddingProvider,
    EmbeddingProviderResponseError,
    EmbeddingProviderTransportError,
)


class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    """OpenAI 호환 embeddings 엔드포인트를 호출해 임베딩 벡터를 파싱합니다."""

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
        OpenAI 호환 embeddings 엔드포인트를 호출할 최소 연결 정보를 초기화합니다.
        테스트에서는 외부 네트워크 대신 주입된 httpx client를 그대로 재사용할 수 있게 둡니다.
        """

        self._base_url = base_url.rstrip("/")
        self._model = model
        self._api_key = api_key
        self._client = client or httpx.Client(base_url=self._base_url, timeout=timeout_seconds)
        self._owns_client = client is None

    def embed_documents(self, *, texts: Sequence[str]) -> List[List[float]]:
        """문서 텍스트 목록을 embeddings 엔드포인트로 보내고 벡터 목록을 반환합니다."""

        normalized_texts = [str(text) for text in texts]
        if not normalized_texts:
            return []
        response_json = self._post_embeddings(inputs=normalized_texts)
        return self._parse_embeddings(response_json, expected_count=len(normalized_texts))

    def embed_query(self, *, text: str) -> List[float]:
        """단일 query text를 embeddings 엔드포인트로 보내고 벡터 하나를 반환합니다."""

        response_json = self._post_embeddings(inputs=[str(text)])
        vectors = self._parse_embeddings(response_json, expected_count=1)
        return vectors[0]

    def close(self) -> None:
        """공급자가 내부에서 생성한 HTTP 클라이언트가 있으면 정리합니다."""

        if self._owns_client:
            self._client.close()

    def _post_embeddings(self, *, inputs: Sequence[str]) -> Dict[str, Any]:
        """OpenAI 호환 embeddings 엔드포인트를 호출하고 응답 JSON을 반환합니다."""

        try:
            response = self._client.post(
                "/embeddings",
                headers=self._build_headers(),
                json={
                    "model": self._model,
                    "input": list(inputs),
                },
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            raise EmbeddingProviderTransportError(
                "Embedding provider returned HTTP error: {0}".format(exc.response.status_code)
            ) from exc
        except httpx.RequestError as exc:
            raise EmbeddingProviderTransportError(
                "Embedding provider request failed: {0}".format(exc)
            ) from exc
        except ValueError as exc:
            raise EmbeddingProviderResponseError(
                "Embedding provider returned invalid JSON response"
            ) from exc

    def _build_headers(self) -> Dict[str, str]:
        """API key 존재 여부를 반영해 공급자 요청 헤더를 구성합니다."""

        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = "Bearer {0}".format(self._api_key)
        return headers

    def _parse_embeddings(
        self,
        response_json: Dict[str, Any],
        *,
        expected_count: int,
    ) -> List[List[float]]:
        """embeddings 응답의 data 배열을 입력 순서대로 벡터 목록으로 변환합니다."""

        try:
            raw_data = response_json["data"]
            if not isinstance(raw_data, list):
                raise TypeError("Embedding response data is not a list")

            sorted_items = sorted(
                raw_data,
                key=lambda item: int(item.get("index", 0)) if isinstance(item, dict) else 0,
            )
            vectors: List[List[float]] = []
            for item in sorted_items:
                if not isinstance(item, dict):
                    raise TypeError("Embedding response item is not an object")
                embedding = item["embedding"]
                if not isinstance(embedding, list):
                    raise TypeError("Embedding response vector is not a list")
                vectors.append([float(value) for value in embedding])

            if len(vectors) != expected_count:
                raise ValueError("Embedding response count does not match input count")
            return vectors
        except (KeyError, TypeError, ValueError) as exc:
            raise EmbeddingProviderResponseError(
                "Embedding provider returned invalid embedding payload"
            ) from exc
