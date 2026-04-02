from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Sequence

from app.ai.providers import EmbeddingProvider, build_embedding_provider
from app.core.config import Settings, get_settings
from app.db import session_scope
from app.models import CanonicalDocument, ProvenanceAnchor, ScholarshipNotice, ScholarshipRule
from app.repositories import (
    CanonicalDocumentRepository,
    ScholarshipNoticeRepository,
    ScholarshipRagChunkRepository,
    ScholarshipRuleRepository,
)
from app.schemas import ScholarshipRagChunkUpsert


class ScholarshipRagIndexingService:
    """canonical block와 provenance를 RAG retrieval용 chunk corpus로 적재하는 서비스입니다."""

    def __init__(
        self,
        *,
        embedding_provider: Optional[EmbeddingProvider] = None,
        settings: Optional[Settings] = None,
    ):
        """
        query/document embedding에 사용할 공급자를 주입받아 초기화합니다.
        명시적 공급자가 없으면 설정값을 기준으로 기본 embedding provider를 조립합니다.
        """

        self._settings = settings or get_settings()
        self._embedding_provider = embedding_provider or build_embedding_provider(self._settings)

    def rebuild_notice(self, notice_id: int):
        """notice 하나에 속한 canonical block와 provenance를 다시 읽어 RAG corpus를 재구성합니다."""

        with session_scope() as session:
            notice_repository = ScholarshipNoticeRepository(session)
            document_repository = CanonicalDocumentRepository(session)
            rule_repository = ScholarshipRuleRepository(session)
            rag_chunk_repository = ScholarshipRagChunkRepository(session)

            notice = notice_repository.get_by_id(notice_id)
            if notice is None:
                raise ValueError("Notice does not exist: {0}".format(notice_id))

            canonical_documents = document_repository.list_documents_for_notice_with_anchors(
                notice_id,
                include_provenance_anchors=True,
            )
            if not canonical_documents:
                raise ValueError("Notice does not have canonical documents: {0}".format(notice_id))

            rules = rule_repository.list_rules_for_notice(notice_id)
            chunk_payloads = self._build_rag_chunks(
                notice=notice,
                canonical_documents=canonical_documents,
                rules=rules,
            )
            embedded_payloads = self._embed_chunk_payloads(chunk_payloads)
            rag_chunk_repository.replace_chunks_for_notice(notice.id, embedded_payloads)
            return rag_chunk_repository.list_chunks_for_notice(notice.id)

    def rebuild_published_notices(self):
        """published rule이 있는 notice 전체를 대상으로 RAG corpus를 다시 적재합니다."""

        with session_scope() as session:
            published_rules = ScholarshipRuleRepository(session).list_published_rules(
                include_provenance_anchors=False
            )
            notice_ids = sorted({int(rule.notice_id) for rule in published_rules})

        rebuilt_chunks = []
        for notice_id in notice_ids:
            rebuilt_chunks.extend(self.rebuild_notice(notice_id))
        return rebuilt_chunks

    def _build_rag_chunks(
        self,
        *,
        notice: ScholarshipNotice,
        canonical_documents: Sequence[CanonicalDocument],
        rules: Sequence[ScholarshipRule],
    ) -> List[ScholarshipRagChunkUpsert]:
        """canonical block를 retrieval-friendly chunk payload로 조립합니다."""

        payloads: List[ScholarshipRagChunkUpsert] = []
        rule_hints_by_document_block = self._attach_rule_hints(canonical_documents, rules)

        for document in canonical_documents:
            for block in getattr(document, "blocks_json", []):
                block_id = str(block["block_id"])
                matching_hints = rule_hints_by_document_block.get((document.id, block_id), [])
                if not matching_hints:
                    matching_hints = [
                        {
                            "rule": rules[0],
                            "anchor_keys": [],
                        }
                    ] if len(rules) == 1 else [{"rule": None, "anchor_keys": []}]

                for hint in matching_hints:
                    rule = hint["rule"]
                    anchor_keys = list(hint["anchor_keys"])
                    payloads.append(
                        ScholarshipRagChunkUpsert(
                            notice_id=notice.id,
                            document_id=document.id,
                            rule_id=getattr(rule, "id", None),
                            chunk_key=self._build_chunk_key(
                                notice_id=notice.id,
                                document_id=document.id,
                                block_id=block_id,
                                rule_id=getattr(rule, "id", None),
                            ),
                            block_id=block_id,
                            chunk_text=str(block["text"]),
                            search_text=self._build_search_text(
                                notice=notice,
                                document=document,
                                block=block,
                                rule=rule,
                                anchor_keys=anchor_keys,
                            ),
                            scholarship_name=getattr(rule, "scholarship_name", None),
                            source_label=str(document.source_label),
                            document_kind=document.document_kind,
                            page_number=block.get("page_number"),
                            anchor_keys=anchor_keys,
                            embedding_vector=[],
                            metadata=self._build_metadata(
                                notice=notice,
                                document=document,
                                block=block,
                                rule=rule,
                                anchor_keys=anchor_keys,
                            ),
                        )
                    )

        return payloads

    def _attach_rule_hints(
        self,
        canonical_documents: Sequence[CanonicalDocument],
        rules: Sequence[ScholarshipRule],
    ) -> Dict[tuple[int, str], List[Dict[str, object]]]:
        """anchor key와 rule provenance를 연결해 block별 retrieval 힌트를 계산합니다."""

        rule_by_anchor_key: Dict[str, List[ScholarshipRule]] = defaultdict(list)
        for rule in rules:
            for anchor_key in rule.provenance_keys_json:
                rule_by_anchor_key[str(anchor_key)].append(rule)

        hints: Dict[tuple[int, str], Dict[Optional[int], Dict[str, object]]] = defaultdict(dict)
        for document in canonical_documents:
            for anchor in getattr(document, "provenance_anchors", []):
                matching_rules = rule_by_anchor_key.get(anchor.anchor_key, [])
                for rule in matching_rules:
                    key = (document.id, anchor.block_id)
                    rule_hint = hints[key].setdefault(
                        rule.id,
                        {
                            "rule": rule,
                            "anchor_keys": [],
                        },
                    )
                    rule_hint["anchor_keys"].append(anchor.anchor_key)

        return {
            key: list(grouped_hints.values())
            for key, grouped_hints in hints.items()
        }

    def _embed_chunk_payloads(
        self,
        payloads: Sequence[ScholarshipRagChunkUpsert],
    ) -> List[ScholarshipRagChunkUpsert]:
        """search text를 임베딩해 chunk payload에 vector를 채웁니다."""

        if not payloads:
            return []

        search_texts = [payload.search_text for payload in payloads]
        vectors = self._embedding_provider.embed_documents(texts=search_texts)
        if len(vectors) != len(payloads):
            raise ValueError("Embedding provider returned mismatched vector count")

        return [
            payload.model_copy(update={"embedding_vector": [float(value) for value in vector]})
            for payload, vector in zip(payloads, vectors)
        ]

    def _build_chunk_key(
        self,
        *,
        notice_id: int,
        document_id: int,
        block_id: str,
        rule_id: Optional[int],
    ) -> str:
        """notice/document/block/rule 조합으로 안정적인 chunk key를 만듭니다."""

        base_key = "notice:{0}:document:{1}:block:{2}".format(notice_id, document_id, block_id)
        if rule_id is None:
            return base_key
        return "{0}:rule:{1}".format(base_key, rule_id)

    def _build_search_text(
        self,
        *,
        notice: ScholarshipNotice,
        document: CanonicalDocument,
        block: Dict[str, object],
        rule: Optional[ScholarshipRule],
        anchor_keys: Sequence[str],
    ) -> str:
        """retrieval에 사용할 search text를 notice, block, rule 힌트로 조립합니다."""

        parts = [notice.title]
        if notice.summary:
            parts.append(notice.summary)
        if rule is not None:
            parts.append(rule.scholarship_name)
            if rule.summary_text:
                parts.append(rule.summary_text)
        parts.append(document.source_label)
        if anchor_keys:
            parts.append(" ".join(anchor_keys))
        metadata = block.get("metadata") or {}
        if isinstance(metadata, dict):
            section = metadata.get("section")
            if section:
                parts.append(str(section))
        parts.append(str(block["text"]))
        return " ".join(part for part in parts if part)

    def _build_metadata(
        self,
        *,
        notice: ScholarshipNotice,
        document: CanonicalDocument,
        block: Dict[str, object],
        rule: Optional[ScholarshipRule],
        anchor_keys: Sequence[str],
    ) -> Dict[str, object]:
        """citation hydrate와 디버깅에 쓸 chunk metadata를 구성합니다."""

        metadata = {
            "notice_title": notice.title,
            "notice_url": notice.notice_url,
            "source_label": document.source_label,
            "anchor_keys": list(anchor_keys),
        }
        block_metadata = block.get("metadata") or {}
        if isinstance(block_metadata, dict):
            metadata["block_metadata"] = dict(block_metadata)
        if rule is not None:
            metadata["scholarship_name"] = rule.scholarship_name
            metadata["rule_summary"] = rule.summary_text
        return metadata
