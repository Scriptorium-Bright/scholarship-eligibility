from types import SimpleNamespace

from app.extractors import NoticeExtractionPromptBuilder


def test_phase8_prompt_builder_preserves_block_order_in_context():
    builder = NoticeExtractionPromptBuilder(max_characters=2000)
    canonical_documents = [
        SimpleNamespace(
            id=101,
            source_label="notice-html",
            document_kind="notice_html",
            blocks_json=[
                {"block_id": "block-1", "text": "첫 번째 블록", "page_number": 1},
                {"block_id": "block-2", "text": "두 번째 블록", "page_number": 1},
            ],
        )
    ]

    context = builder.build_notice_context(
        notice_title="송은장학금 안내",
        canonical_documents=canonical_documents,
    )

    assert context.prompt_text.index("block-1") < context.prompt_text.index("block-2")
    assert [block.block_id for block in context.selected_blocks] == ["block-1", "block-2"]


def test_phase8_prompt_builder_serializes_page_numbers():
    builder = NoticeExtractionPromptBuilder(max_characters=2000)
    canonical_documents = [
        SimpleNamespace(
            id=101,
            source_label="attachment-pdf",
            document_kind="attachment_pdf",
            blocks_json=[
                {"block_id": "block-3", "text": "세 번째 블록", "page_number": 2},
            ],
        )
    ]

    context = builder.build_notice_context(
        notice_title="송은장학금 안내",
        canonical_documents=canonical_documents,
    )

    assert "[page_number=2]" in context.prompt_text
    assert "[document_id=101]" in context.prompt_text


def test_phase8_prompt_builder_truncates_to_character_budget():
    builder = NoticeExtractionPromptBuilder(max_characters=120)
    canonical_documents = [
        SimpleNamespace(
            id=101,
            source_label="notice-html",
            document_kind="notice_html",
            blocks_json=[
                {"block_id": "block-1", "text": "가" * 30, "page_number": 1},
                {"block_id": "block-2", "text": "나" * 30, "page_number": 1},
            ],
        )
    ]

    context = builder.build_notice_context(
        notice_title="송은장학금 안내",
        canonical_documents=canonical_documents,
    )

    assert context.truncated is True
    assert [block.block_id for block in context.selected_blocks] == ["block-1"]
    assert "block-2" not in context.prompt_text
