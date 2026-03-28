from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class ExtractionPromptBlock:
    """One canonical block serialized with enough metadata for future evidence mapping."""

    document_id: int
    source_label: str
    document_kind: str
    block_id: str
    page_number: Optional[int]
    text: str


@dataclass(frozen=True)
class NoticeExtractionContext:
    """Prompt payload prepared for one extraction call."""

    prompt_text: str
    selected_blocks: List[ExtractionPromptBlock]
    truncated: bool


class NoticeExtractionPromptBuilder:
    """Build deterministic LLM extraction context from normalized notice documents."""

    def __init__(self, *, max_characters: int = 6000):
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
        """Assemble notice metadata and canonical blocks into one extraction prompt."""

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
        """Serialize one canonical block so the model can cite it back by document and block id."""

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
        """Keep blocks in source order while enforcing a deterministic character budget."""

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
        """Flatten notice and attachment documents into one ordered prompt block list."""

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

