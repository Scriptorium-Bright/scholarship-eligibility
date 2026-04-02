from __future__ import annotations

import math
import re
from typing import Iterable, List, Optional, Sequence

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.models import ScholarshipRagChunk
from app.schemas import RagRetrievalCandidate, ScholarshipRagChunkUpsert

TOKEN_PATTERN = re.compile(r"[0-9A-Za-z가-힣]+")


class ScholarshipRagChunkRepository:
    """RAG retrieval에 사용할 chunk corpus를 저장하고 조회하는 repository입니다."""

    def __init__(self, session: Session):
        """
        canonical block 기반 RAG corpus와 retrieval candidate read path를 같은 세션 경계 안에서 다루게 합니다.
        이후 indexing, retrieval, citation hydrate가 같은 repository contract를 재사용할 수 있게 합니다.
        """

        self.session = session

    def _base_statement(self):
        """notice/document/rule 관계를 함께 로드하는 RAG corpus 기본 조회 쿼리입니다."""

        return select(ScholarshipRagChunk).options(
            selectinload(ScholarshipRagChunk.notice),
            selectinload(ScholarshipRagChunk.document),
            selectinload(ScholarshipRagChunk.rule),
        )

    def get_by_chunk_key(self, chunk_key: str) -> Optional[ScholarshipRagChunk]:
        """고유 chunk key를 기준으로 단일 RAG corpus row를 조회합니다."""

        statement = self._base_statement().where(ScholarshipRagChunk.chunk_key == chunk_key)
        return self.session.scalar(statement)

    def upsert_chunks(
        self,
        payloads: Sequence[ScholarshipRagChunkUpsert],
    ) -> List[ScholarshipRagChunk]:
        """
        materialization 단계에서 생성한 chunk payload들을 key 기준으로 삽입 또는 갱신합니다.
        검색용 read model을 멱등적으로 재구성할 수 있게 하는 phase 9.0의 핵심 entrypoint입니다.
        """

        saved_chunks: List[ScholarshipRagChunk] = []
        for payload in payloads:
            chunk = self.get_by_chunk_key(payload.chunk_key)
            payload_data = payload.model_dump()
            payload_data["anchor_keys_json"] = payload_data.pop("anchor_keys")
            payload_data["embedding_vector_json"] = payload_data.pop("embedding_vector")
            payload_data["metadata_json"] = payload_data.pop("metadata")

            if chunk is None:
                chunk = ScholarshipRagChunk(**payload_data)
                self.session.add(chunk)
            else:
                for field_name, value in payload_data.items():
                    setattr(chunk, field_name, value)

            saved_chunks.append(chunk)

        self.session.flush()
        return saved_chunks

    def delete_by_notice_ids(self, notice_ids: Iterable[int]) -> int:
        """지정한 notice들에 속한 RAG corpus row를 일괄 삭제합니다."""

        normalized_notice_ids = [int(notice_id) for notice_id in notice_ids]
        if not normalized_notice_ids:
            return 0

        result = self.session.execute(
            delete(ScholarshipRagChunk).where(ScholarshipRagChunk.notice_id.in_(normalized_notice_ids))
        )
        self.session.flush()
        return int(result.rowcount or 0)

    def list_chunks_for_notice(self, notice_id: int) -> List[ScholarshipRagChunk]:
        """단일 notice에 속한 RAG corpus row를 안정적인 순서로 반환합니다."""

        statement = (
            self._base_statement()
            .where(ScholarshipRagChunk.notice_id == notice_id)
            .order_by(ScholarshipRagChunk.id.asc())
        )
        return list(self.session.scalars(statement))

    def list_chunks_by_ids(self, chunk_ids: Iterable[int]) -> List[ScholarshipRagChunk]:
        """선택된 복수 chunk id에 해당하는 RAG corpus row를 가져옵니다."""

        normalized_chunk_ids = [int(chunk_id) for chunk_id in chunk_ids]
        if not normalized_chunk_ids:
            return []

        statement = (
            self._base_statement()
            .where(ScholarshipRagChunk.id.in_(normalized_chunk_ids))
            .order_by(ScholarshipRagChunk.id.asc())
        )
        return list(self.session.scalars(statement))

    def list_keyword_candidates(
        self,
        query_text: str,
        *,
        limit: int = 10,
    ) -> List[RagRetrievalCandidate]:
        """query text와 chunk text 간 lexical 일치도를 기반으로 retrieval candidate를 구성합니다."""

        normalized_query = self._normalize_text(query_text)
        if not normalized_query:
            return []

        tokens = self._extract_tokens(query_text)
        candidates: List[RagRetrievalCandidate] = []
        for chunk in self.session.scalars(
            self._base_statement().order_by(ScholarshipRagChunk.id.asc())
        ):
            score = self._keyword_score(chunk, normalized_query, tokens)
            if score <= 0:
                continue
            candidates.append(
                self._build_candidate(
                    chunk=chunk,
                    score=score,
                    retrieval_kind="keyword",
                )
            )

        return sorted(candidates, key=self._candidate_sort_key)[:limit]

    def list_vector_candidates(
        self,
        query_embedding: Sequence[float],
        *,
        limit: int = 10,
    ) -> List[RagRetrievalCandidate]:
        """query embedding과 chunk embedding 간 cosine similarity를 계산해 retrieval candidate를 구성합니다."""

        normalized_query_embedding = [float(value) for value in query_embedding]
        if not normalized_query_embedding:
            return []

        candidates: List[RagRetrievalCandidate] = []
        for chunk in self.session.scalars(
            self._base_statement().order_by(ScholarshipRagChunk.id.asc())
        ):
            score = self._cosine_similarity(
                normalized_query_embedding,
                [float(value) for value in chunk.embedding_vector_json],
            )
            if score is None or score <= 0:
                continue
            candidates.append(
                self._build_candidate(
                    chunk=chunk,
                    score=score,
                    retrieval_kind="vector",
                )
            )

        return sorted(candidates, key=self._candidate_sort_key)[:limit]

    def _build_candidate(
        self,
        *,
        chunk: ScholarshipRagChunk,
        score: float,
        retrieval_kind: str,
    ) -> RagRetrievalCandidate:
        """ORM chunk row를 retrieval candidate DTO로 변환합니다."""

        return RagRetrievalCandidate(
            chunk_id=chunk.id,
            chunk_key=chunk.chunk_key,
            notice_id=chunk.notice_id,
            document_id=chunk.document_id,
            rule_id=chunk.rule_id,
            block_id=chunk.block_id,
            chunk_text=chunk.chunk_text,
            search_text=chunk.search_text,
            scholarship_name=chunk.scholarship_name,
            source_label=chunk.source_label,
            document_kind=chunk.document_kind,
            page_number=chunk.page_number,
            anchor_keys=list(chunk.anchor_keys_json),
            metadata=dict(chunk.metadata_json),
            score=round(float(score), 6),
            retrieval_kind=retrieval_kind,
        )

    def _keyword_score(
        self,
        chunk: ScholarshipRagChunk,
        normalized_query: str,
        tokens: Sequence[str],
    ) -> float:
        """질의와 chunk 텍스트의 단순 lexical 유사도를 계산합니다."""

        normalized_chunk_text = self._normalize_text(chunk.chunk_text)
        normalized_search_text = self._normalize_text(chunk.search_text)
        normalized_scholarship_name = self._normalize_text(chunk.scholarship_name or "")

        score = 0.0
        if normalized_query and normalized_query in normalized_scholarship_name:
            score += 5.0
        elif normalized_query and normalized_query in normalized_search_text:
            score += 3.0
        elif normalized_query and normalized_query in normalized_chunk_text:
            score += 2.0

        for token in tokens:
            if token in normalized_scholarship_name:
                score += 2.0
            if token in normalized_chunk_text:
                score += 1.5
            elif token in normalized_search_text:
                score += 1.0

        return score

    def _cosine_similarity(
        self,
        query_embedding: Sequence[float],
        chunk_embedding: Sequence[float],
    ) -> Optional[float]:
        """두 embedding 벡터의 cosine similarity를 계산합니다."""

        if not chunk_embedding or len(query_embedding) != len(chunk_embedding):
            return None

        query_norm = math.sqrt(sum(value * value for value in query_embedding))
        chunk_norm = math.sqrt(sum(value * value for value in chunk_embedding))
        if query_norm == 0 or chunk_norm == 0:
            return None

        dot_product = sum(
            query_value * chunk_value
            for query_value, chunk_value in zip(query_embedding, chunk_embedding)
        )
        return dot_product / (query_norm * chunk_norm)

    def _normalize_text(self, text: str) -> str:
        """비교 연산에 쓸 질의와 문서 텍스트를 소문자 기준으로 정규화합니다."""

        return " ".join(str(text).strip().lower().split())

    def _extract_tokens(self, text: str) -> List[str]:
        """검색 질의를 deterministic token 목록으로 분해합니다."""

        return [match.group(0).lower() for match in TOKEN_PATTERN.finditer(text)]

    def _candidate_sort_key(self, candidate: RagRetrievalCandidate):
        """retrieval candidate를 score 우선으로 안정 정렬합니다."""

        return (-candidate.score, candidate.chunk_id)
