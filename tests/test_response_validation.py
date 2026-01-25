"""
Response Validation Tests - Catch ORM/Schema Mismatches
========================================================

These tests ensure FastAPI response_model validation works correctly.
They catch mismatches between ORM models and Pydantic schemas BEFORE production.

Usage:
    pytest tests/test_response_validation.py -v
"""
import pytest
from fastapi.testclient import TestClient


# ============================================================
# Test Client Setup
# ============================================================

@pytest.fixture(scope="module")
def client():
    """Create test client for API testing."""
    from app.main import app
    return TestClient(app)


# ============================================================
# Response Validation Tests
# ============================================================

class TestBudgetEndpoints:
    """Test budget endpoints return valid schema responses."""
    
    def test_budget_check_returns_valid_or_404(self, client):
        """
        Ensure budget check endpoint doesn't return 500 (schema mismatch).
        
        A 404 is expected if no data exists, but 500 indicates
        a ResponseValidationError from ORM/Schema mismatch.
        """
        response = client.get("/budget/check/1")
        
        # 404 is OK (no data), 500 is BAD (validation error)
        assert response.status_code != 500, \
            f"Response validation error! Got 500: {response.json()}"
        
        if response.status_code == 200:
            data = response.json()
            # Verify required fields from BudgetCheckResponse
            assert "budget_row_id" in data
            assert "remaining_available" in data
            assert "status" in data
    
    def test_budget_list_returns_valid_structure(self, client):
        """Ensure budget list returns proper list structure."""
        response = client.get("/budget/list/1")
        
        # Should return 200 with empty list or populated list
        if response.status_code == 200:
            data = response.json()
            assert "budget_rows" in data
            assert "total_count" in data
            assert isinstance(data["budget_rows"], list)


class TestAuthEndpoints:
    """Test auth endpoints return valid responses."""
    
    def test_login_with_invalid_credentials(self, client):
        """Ensure login returns proper error, not 500 (server error)."""
        response = client.post(
            "/auth/token",
            data={"username": "invalid", "password": "invalid"}
        )
        
        # Should be 401/404/422 (auth errors), not 500 (schema mismatch)
        assert response.status_code != 500, \
            f"Server error - possible schema mismatch: {response.json()}"


# ============================================================
# Pattern: How to add new schema validation tests
# ============================================================

"""
When adding a new endpoint with response_model, add a test like this:

def test_your_endpoint_returns_valid_response(self, client):
    response = client.get("/your/endpoint/1")
    
    # Assert NOT 500 - catches schema mismatches
    assert response.status_code != 500, \
        f"Schema mismatch! {response.json()}"
    
    if response.status_code == 200:
        data = response.json()
        # Verify key fields from your response schema
        assert "required_field" in data
"""
