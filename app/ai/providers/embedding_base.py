from __future__ import annotations

from typing import List, Protocol, Sequence, runtime_checkable


class EmbeddingProviderError(RuntimeError):
    """임베딩 공급자가 벡터 생성을 완료하지 못했을 때 쓰는 공통 예외입니다."""


class EmbeddingProviderTransportError(EmbeddingProviderError):
    """상위 임베딩 공급자에 연결할 수 없거나 HTTP 오류가 반환될 때 발생합니다."""


class EmbeddingProviderResponseError(EmbeddingProviderError):
    """상위 공급자가 임베딩 응답 형식을 지키지 못했을 때 발생합니다."""


@runtime_checkable
class EmbeddingProvider(Protocol):
    """query/document embedding 공급자가 공통으로 따를 계약입니다."""

    def embed_documents(self, *, texts: Sequence[str]) -> List[List[float]]:
        """여러 문서 텍스트를 같은 길이의 임베딩 벡터 목록으로 변환합니다."""

    def embed_query(self, *, text: str) -> List[float]:
        """단일 query text를 retrieval에 쓸 임베딩 벡터로 변환합니다."""

    def close(self) -> None:
        """공유 HTTP 클라이언트 같은 공급자 리소스를 정리합니다."""
