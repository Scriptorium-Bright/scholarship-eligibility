from __future__ import annotations

import hashlib
import math
import re
from typing import Dict, List, Optional, Sequence

from app.ai.providers.embedding_base import EmbeddingProvider

TOKEN_PATTERN = re.compile(r"[0-9A-Za-z가-힣]+")


class FakeEmbeddingProvider(EmbeddingProvider):
    """네트워크 호출 없이 결정론적 임베딩 벡터를 생성하는 테스트용 공급자입니다."""

    def __init__(
        self,
        *,
        dimensions: int = 8,
        predefined_vectors: Optional[Dict[str, Sequence[float]]] = None,
    ):
        """
        테스트에서 텍스트별 고정 벡터를 주입하거나, 없으면 해시 기반 벡터를 생성하게 둡니다.
        같은 텍스트는 항상 같은 벡터를 반환하므로 retrieval/indexing 테스트를 재현 가능하게 유지합니다.
        """

        self._dimensions = max(int(dimensions), 1)
        self._predefined_vectors = {
            key: [float(value) for value in vector]
            for key, vector in (predefined_vectors or {}).items()
        }
        self.recorded_document_batches: List[List[str]] = []
        self.recorded_queries: List[str] = []

    def embed_documents(self, *, texts: Sequence[str]) -> List[List[float]]:
        """문서 텍스트 목록을 결정론적 벡터 목록으로 변환하고 기록합니다."""

        normalized_texts = [str(text) for text in texts]
        self.recorded_document_batches.append(normalized_texts)
        return [self._embed_text(text) for text in normalized_texts]

    def embed_query(self, *, text: str) -> List[float]:
        """질의 텍스트 하나를 결정론적 벡터로 변환하고 기록합니다."""

        normalized_text = str(text)
        self.recorded_queries.append(normalized_text)
        return self._embed_text(normalized_text)

    def close(self) -> None:
        """fake provider는 외부 리소스를 소유하지 않으므로 close는 아무 동작도 하지 않습니다."""

    def _embed_text(self, text: str) -> List[float]:
        """사전 정의 벡터가 있으면 사용하고, 없으면 token hash 기반 벡터를 생성합니다."""

        predefined = self._predefined_vectors.get(text)
        if predefined is not None:
            return list(predefined)

        vector = [0.0] * self._dimensions
        for token in self._extract_tokens(text):
            index = self._stable_bucket(token)
            vector[index] += 1.0

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [round(value / norm, 6) for value in vector]

    def _extract_tokens(self, text: str) -> List[str]:
        """텍스트를 임베딩용 deterministic token 목록으로 분해합니다."""

        return [match.group(0).lower() for match in TOKEN_PATTERN.finditer(text)]

    def _stable_bucket(self, token: str) -> int:
        """프로세스 간에도 같은 bucket을 고르도록 안정 해시를 사용합니다."""

        digest = hashlib.sha256(token.encode("utf-8")).digest()
        return int.from_bytes(digest[:4], "big") % self._dimensions
