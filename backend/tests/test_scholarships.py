"""
Scholarship endpoints unit and search tests.
Tests the 5 required scholarship endpoints and validation rules.
"""
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.scholarship import ScholarshipResponse, ScholarshipSummaryResponse
from app.utils.errors import NotFoundException, ValidationException

client = TestClient(app)

MOCK_SCHOLARSHIPS = [
    ScholarshipResponse(
        scholarship_id="TRB-SCH-000001",
        name="Pre-Matric Scholarship for ST Students",
        short_name="PRE_MATRIC",
        description="Financial assistance for ST students studying in classes IX and X.",
        scholarship_type="PRE_MATRIC",
        provider="Ministry of Tribal Affairs",
        is_active=True,
    ),
    ScholarshipResponse(
        scholarship_id="TRB-SCH-000002",
        name="Post-Matric Scholarship for ST Students",
        short_name="POST_MATRIC",
        description="Financial assistance for ST students pursuing post-matriculation or post-secondary education.",
        scholarship_type="POST_MATRIC",
        provider="Ministry of Tribal Affairs",
        is_active=True,
    ),
    ScholarshipResponse(
        scholarship_id="TRB-SCH-000003",
        name="National Fellowship and Scholarship for Higher Education of ST Students",
        short_name="NFST",
        description="Fellowship support for ST students pursuing M.Phil and Ph.D. courses.",
        scholarship_type="HIGHER_EDUCATION",
        provider="Ministry of Tribal Affairs",
        is_active=True,
    ),
    ScholarshipResponse(
        scholarship_id="TRB-SCH-000004",
        name="National Overseas Scholarship for ST Candidates",
        short_name="NOS",
        description="Financial assistance to selected ST candidates for pursuing Master level courses and Ph.D abroad.",
        scholarship_type="OVERSEAS",
        provider="Ministry of Tribal Affairs",
        is_active=True,
    ),
    ScholarshipResponse(
        scholarship_id="TRB-SCH-000005",
        name="Top Class Education Scheme for ST Students",
        short_name="TOP_CLASS",
        description="Encourages meritorious ST students to pursue studies in premier identified institutions.",
        scholarship_type="TOP_CLASS",
        provider="Ministry of Tribal Affairs",
        is_active=True,
    ),
]


# =====================================================================
# 1. Get All Active Scholarships (GET /api/v1/scholarships)
# =====================================================================

def test_get_all_active_scholarships():
    """Test retrieving all active scholarship schemes (no auth required)."""
    with patch("app.services.scholarship_service.scholarship_service.get_all_active_scholarships") as mock_get_all:
        mock_get_all.return_value = MOCK_SCHOLARSHIPS

        response = client.get("/api/v1/scholarships")
        assert response.status_code == 200
        data = response.json()
        assert "scholarships" in data
        assert "count" in data
        assert data["count"] == 5
        assert len(data["scholarships"]) == 5
        assert data["scholarships"][0]["scholarship_id"] == "TRB-SCH-000001"
        assert data["scholarships"][0]["short_name"] == "PRE_MATRIC"
        # Ensure database UUIDs or internal tables are not leaked
        assert "id" not in data["scholarships"][0]


# =====================================================================
# 2. Get Scholarship By ID (GET /api/v1/scholarships/{scholarship_id})
# =====================================================================

def test_get_scholarship_by_id_success():
    """Test retrieving scholarship details by business identifier."""
    with patch("app.services.scholarship_service.scholarship_service.get_scholarship_by_business_id") as mock_get_id:
        mock_get_id.return_value = MOCK_SCHOLARSHIPS[0]

        response = client.get("/api/v1/scholarships/TRB-SCH-000001")
        assert response.status_code == 200
        data = response.json()
        assert data["scholarship_id"] == "TRB-SCH-000001"
        assert data["name"] == "Pre-Matric Scholarship for ST Students"
        assert data["provider"] == "Ministry of Tribal Affairs"
        assert data["is_active"] is True


def test_get_scholarship_by_id_not_found():
    """Test retrieving non-existent scholarship returns 404."""
    with patch("app.services.scholarship_service.scholarship_service.get_scholarship_by_business_id") as mock_get_id:
        mock_get_id.side_effect = NotFoundException(
            message="Scholarship 'TRB-SCH-999999' not found.",
            code="SCHOLARSHIP_NOT_FOUND"
        )

        response = client.get("/api/v1/scholarships/TRB-SCH-999999")
        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "SCHOLARSHIP_NOT_FOUND"


# =====================================================================
# 3. Get Scholarship By Short Name (GET /api/v1/scholarships/code/{short_name})
# =====================================================================

def test_get_scholarship_by_short_name_success():
    """Test retrieving scholarship by code (e.g. POST_MATRIC)."""
    with patch("app.services.scholarship_service.scholarship_service.get_scholarship_by_short_name") as mock_get_code:
        mock_get_code.return_value = MOCK_SCHOLARSHIPS[1]

        response = client.get("/api/v1/scholarships/code/POST_MATRIC")
        assert response.status_code == 200
        data = response.json()
        assert data["scholarship_id"] == "TRB-SCH-000002"
        assert data["short_name"] == "POST_MATRIC"


def test_get_scholarship_by_short_name_not_found():
    """Test retrieving unknown short name returns 404."""
    with patch("app.services.scholarship_service.scholarship_service.get_scholarship_by_short_name") as mock_get_code:
        mock_get_code.side_effect = NotFoundException(
            message="Scholarship with code 'UNKNOWN_CODE' not found.",
            code="SCHOLARSHIP_NOT_FOUND"
        )

        response = client.get("/api/v1/scholarships/code/UNKNOWN_CODE")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "SCHOLARSHIP_NOT_FOUND"


# =====================================================================
# 4. Search Scholarships (GET /api/v1/scholarships/search?q=...)
# =====================================================================

def test_search_scholarships_success():
    """Test searching active scholarships with matching keyword."""
    with patch("app.services.scholarship_service.scholarship_service.search_scholarships") as mock_search:
        mock_search.return_value = [MOCK_SCHOLARSHIPS[1]]

        response = client.get("/api/v1/scholarships/search?q=post")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["scholarships"][0]["short_name"] == "POST_MATRIC"


def test_search_scholarships_empty_query():
    """Test searching with whitespace/empty query returns validation error."""
    response = client.get("/api/v1/scholarships/search?q=")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_search_scholarships_missing_query():
    """Test searching without q parameter returns validation error."""
    response = client.get("/api/v1/scholarships/search")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_search_scholarships_excessively_long_query():
    """Test query exceeding 100 characters is rejected."""
    long_query = "a" * 105
    response = client.get(f"/api/v1/scholarships/search?q={long_query}")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


# =====================================================================
# 5. Get Scholarship Summary (GET /api/v1/scholarships/summary)
# =====================================================================

def test_get_scholarship_summary():
    """Test retrieving scholarship counts summary."""
    with patch("app.services.scholarship_service.scholarship_service.get_scholarship_summary") as mock_summary:
        mock_summary.return_value = ScholarshipSummaryResponse(
            total_scholarships=5,
            active_scholarships=5
        )

        response = client.get("/api/v1/scholarships/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["total_scholarships"] == 5
        assert data["active_scholarships"] == 5
