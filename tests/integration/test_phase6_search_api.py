from fastapi.testclient import TestClient

from app.main import create_app
from tests.support.search_seed import REFERENCE_TIME, seed_phase6_search_data


def test_phase6_search_api_returns_open_matches(monkeypatch, tmp_path):
    seed_phase6_search_data(monkeypatch, tmp_path)
    monkeypatch.setattr("app.services.search.now_in_seoul", lambda: REFERENCE_TIME)
    client = TestClient(create_app())

    response = client.get(
        "/api/v1/scholarships/search",
        params={"query": "장학금", "open_only": "true", "limit": 10},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "장학금"
    assert body["count"] == 1
    assert body["items"][0]["scholarship_name"] == "송은장학금"
    assert body["items"][0]["application_status"] == "open"
    assert body["items"][0]["provenance"]


def test_phase6_open_scholarship_api_lists_current_notices(monkeypatch, tmp_path):
    seed_phase6_search_data(monkeypatch, tmp_path)
    monkeypatch.setattr("app.services.search.now_in_seoul", lambda: REFERENCE_TIME)
    client = TestClient(create_app())

    response = client.get("/api/v1/scholarships/open", params={"limit": 10})

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["items"][0]["scholarship_name"] == "송은장학금"
    assert body["items"][0]["application_status"] == "open"
