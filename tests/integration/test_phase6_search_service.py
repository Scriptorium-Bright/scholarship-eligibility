from app.services import ScholarshipSearchService
from tests.support.search_seed import REFERENCE_TIME, seed_phase6_search_data


def test_phase6_search_service_returns_ranked_matches_and_provenance(monkeypatch, tmp_path):
    seed_phase6_search_data(monkeypatch, tmp_path)

    response = ScholarshipSearchService().search(
        "송은장학금 소득분위 8분위",
        reference_time=REFERENCE_TIME,
        limit=10,
    )

    assert response.count >= 1
    assert response.items[0].scholarship_name == "송은장학금"
    assert response.items[0].application_status == "open"
    assert "scholarship_name" in response.items[0].matched_fields
    assert response.items[0].provenance
    assert response.items[0].provenance[0].quote_text


def test_phase6_search_service_filters_closed_results_when_open_only(monkeypatch, tmp_path):
    seed_phase6_search_data(monkeypatch, tmp_path)
    service = ScholarshipSearchService()

    all_results = service.search("장학금", reference_time=REFERENCE_TIME, limit=10)
    open_results = service.search(
        "장학금",
        open_only=True,
        reference_time=REFERENCE_TIME,
        limit=10,
    )
    open_list = service.list_open_scholarships(reference_time=REFERENCE_TIME, limit=10)

    assert [item.scholarship_name for item in all_results.items] == [
        "송은장학금",
        "국가근로장학금",
    ]
    assert [item.scholarship_name for item in open_results.items] == ["송은장학금"]
    assert open_list.count == 1
    assert open_list.items[0].scholarship_name == "송은장학금"
    assert open_list.items[0].application_status == "open"
