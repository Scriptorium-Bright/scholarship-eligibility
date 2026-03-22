from fastapi import APIRouter, Query

from app.schemas import OpenScholarshipListResponse, ScholarshipSearchResponse
from app.services import ScholarshipSearchService

router = APIRouter(prefix="/scholarships", tags=["scholarships"])


@router.get("/search", response_model=ScholarshipSearchResponse)
def search_scholarships(
    query: str = Query(..., min_length=1, description="Scholarship keyword query"),
    open_only: bool = False,
    limit: int = Query(10, ge=1, le=50),
) -> ScholarshipSearchResponse:
    """Search scholarship rules and return provenance-backed matches."""

    return ScholarshipSearchService().search(query, open_only=open_only, limit=limit)


@router.get("/open", response_model=OpenScholarshipListResponse)
def list_open_scholarships(
    limit: int = Query(10, ge=1, le=50),
) -> OpenScholarshipListResponse:
    """Return scholarships whose application windows are currently open."""

    return ScholarshipSearchService().list_open_scholarships(limit=limit)
