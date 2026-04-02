from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List, Optional, Sequence, Tuple

"""
Evidence Mapping
LLM이 뱉은 근거 정보(evidence)를 우리 시스템의 근거 저장 형식(provenance anchor)으로 바꾸는 과정

  - field_name = qualification.gpa_min
  - document_id = 12
  - block_id = notice-block-2
  - quote_text = 직전학기 평점평균 3.20 이상

  이걸 그대로 쓰는 게 아니라, 우리 시스템에서는 이걸

  - 어떤 규정 필드의 근거인지
  - 실제 canonical block과 맞는지
  - 어떤 anchor key로 저장할지
    정리해서 provenance anchor 형태로 바꿔 저장한다.
    
  1. LLM이 evidence 반환
  2. 그 document_id, block_id가 실제 문서 block에 존재하는지 확인
  3. 맞으면 anchor key 생성
  4. ExtractedProvenanceAnchor로 변환
  5. 나중에 DB의 provenance anchor로 저장    

"""

@dataclass(frozen=True)
class ExtractionPromptBlock:
    """향후 evidence 매핑에 필요한 메타데이터를 담은 canonical block 표현입니다."""

    document_id: int
    source_label: str
    document_kind: str
    block_id: str
    page_number: Optional[int]
    text: str


@dataclass(frozen=True)
class NoticeExtractionContext:
    """한 번의 추출 호출에 사용할 프롬프트 payload입니다."""

    prompt_text: str
    selected_blocks: List[ExtractionPromptBlock]
    truncated: bool


class NoticeExtractionPromptBuilder:
    """정규화 문서로부터 결정론적인 LLM 추출 컨텍스트를 만드는 빌더입니다."""

    """LLM이 canonical document 객체를 직접 해석하는 게 아니라, 
    우리가 직렬화한 canonical 문맥을 보고 schema에 맞게 구조화해 반환하는 방식"""

    def __init__(self, *, max_characters: int = 6000):
        """
        한 번의 추출 요청에 포함할 최대 문자 수 예산을 초기화합니다.
        이후 block truncation은 이 값 기준으로 안정적으로 잘리도록 동작합니다.
        """

        self.max_characters = max_characters

    def build_notice_context(
        self,
        *,
        notice_title: str,
        canonical_documents: Iterable[object],
        fallback_summary: Optional[str] = None,
        application_started_at: Optional[datetime] = None,
        application_ended_at: Optional[datetime] = None,
    ) -> NoticeExtractionContext:
        """공지 메타데이터와 canonical block을 하나의 추출 프롬프트로 조립합니다."""

        flattened_blocks = self._flatten_documents(canonical_documents)
        selected_blocks, truncated = self.truncate_blocks(flattened_blocks)
        prompt_lines = [
            "당신은 장학 규정 구조화 추출기다.",
            "추정하지 말고 문서에서 확인 가능한 정보만 JSON schema에 맞춰 반환한다.",
            "근거 evidence에는 반드시 document_id와 block_id를 포함한다.",
            "지원 가능 여부 판정은 하지 말고 규정만 추출한다.",
            "",
            "[notice metadata]",
            "notice_title: {0}".format(notice_title),
        ]
        if fallback_summary:
            prompt_lines.append("fallback_summary: {0}".format(fallback_summary))
        if application_started_at is not None:
            prompt_lines.append("application_started_at: {0}".format(application_started_at.isoformat()))
        if application_ended_at is not None:
            prompt_lines.append("application_ended_at: {0}".format(application_ended_at.isoformat()))

        prompt_lines.extend(
            [
                "",
                "[canonical blocks]",
                *[self.serialize_block(block) for block in selected_blocks],
            ]
        )

        return NoticeExtractionContext(
            prompt_text="\n".join(prompt_lines).strip(),
            selected_blocks=selected_blocks,
            truncated=truncated,
        )

    def serialize_block(self, block: ExtractionPromptBlock) -> str:
        """모델이 document id와 block id로 다시 인용할 수 있게 block을 직렬화합니다."""

        parts = [
            "[document_id={0}]".format(block.document_id),
            "[source_label={0}]".format(block.source_label),
            "[document_kind={0}]".format(block.document_kind),
            "[block_id={0}]".format(block.block_id),
        ]
        if block.page_number is not None:
            parts.append("[page_number={0}]".format(block.page_number))
        return "{0} {1}".format("".join(parts), block.text)

    def truncate_blocks(
        self,
        blocks: Sequence[ExtractionPromptBlock],
    ) -> Tuple[List[ExtractionPromptBlock], bool]:
        """source 순서를 유지한 채 결정론적인 문자 예산 제한을 적용합니다."""

        if not blocks:
            return [], False

        selected: List[ExtractionPromptBlock] = []
        used_characters = 0
        truncated = False

        for block in blocks:
            serialized = self.serialize_block(block)
            block_cost = len(serialized) + 1
            if selected and used_characters + block_cost > self.max_characters:
                truncated = True
                break
            if not selected and block_cost > self.max_characters:
                selected.append(block)
                truncated = True
                break

            selected.append(block)
            used_characters += block_cost

        return selected, truncated

    def _flatten_documents(self, canonical_documents: Iterable[object]) -> List[ExtractionPromptBlock]:
        """notice와 attachment 문서를 하나의 순서 있는 prompt block 목록으로 펼칩니다."""

        flattened_blocks: List[ExtractionPromptBlock] = []
        for document in canonical_documents:
            source_label = getattr(document, "source_label", "unknown-source")
            document_kind = getattr(document, "document_kind", "unknown-kind")
            document_kind_label = getattr(document_kind, "value", str(document_kind))
            for block in getattr(document, "blocks_json", []):
                flattened_blocks.append(
                    ExtractionPromptBlock(
                        document_id=int(getattr(document, "id")),
                        source_label=str(source_label),
                        document_kind=document_kind_label,
                        block_id=str(block["block_id"]),
                        page_number=block.get("page_number"),
                        text=str(block["text"]),
                    )
                )
        return flattened_blocks
