from pathlib import Path

from app.collectors.sources import DEFAULT_COLLECTOR_SOURCES
from app.db import create_all_tables, session_scope
from app.repositories import ScholarshipNoticeRepository
from app.services import NoticeCollectionService

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "collector"


def _load_fixture(name: str) -> str:
    """Read one collector HTML fixture from disk."""

    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def test_phase3_collection_service_collects_default_sources(monkeypatch, tmp_path):
    database_path = tmp_path / "phase3.sqlite3"
    monkeypatch.setenv("JBNU_DATABASE_URL", "sqlite+pysqlite:///{0}".format(database_path))
    create_all_tables()

    fixture_map = {
        "https://www.jbnu.ac.kr/web/news/notice/sub01.do": _load_fixture("jbnu_main_notice_list.html"),
        "https://www.jbnu.ac.kr/web/news/notice/sub01.do?mode=view&articleNo=402100": _load_fixture(
            "jbnu_main_notice_detail.html"
        ),
        "https://software.jbnu.ac.kr/software/3348/subview.do": _load_fixture("software_notice_list.html"),
        "https://software.jbnu.ac.kr/bbs/software/527/384006/artclView.do": _load_fixture(
            "software_notice_detail.html"
        ),
    }

    def fetch_html(url: str) -> str:
        """Return fixture HTML that matches the requested URL."""

        if url not in fixture_map:
            raise KeyError("Unexpected test URL: {0}".format(url))
        return fixture_map[url]

    service = NoticeCollectionService(fetch_html=fetch_html)
    results = service.collect_default_sources(limit_per_source=10)

    assert [result.source_board for result in results] == ["jbnu-main", "jbnu-software"]
    assert [result.persisted_count for result in results] == [1, 1]
    assert [result.matched_count for result in results] == [1, 1]

    with session_scope() as session:
        notice_repository = ScholarshipNoticeRepository(session)
        main_notice = notice_repository.get_by_source_identity("jbnu-main", "402100")
        software_notice = notice_repository.get_by_source_identity("jbnu-software", "384006")

        assert main_notice is not None
        assert software_notice is not None
        assert main_notice.application_started_at is not None
        assert len(main_notice.attachments) == 1
        assert len(software_notice.attachments) == 2
        assert software_notice.department_name == "소프트웨어공학과"
