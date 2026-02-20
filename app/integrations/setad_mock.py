"""
Mock Setad Adapter
==================

Returns hardcoded contractor data for Phase 2 demo.
Implements SetadPort protocol without inheritance (structural subtyping).

When the real Setad API becomes available, create setad_adapter.py
implementing the same interface with actual HTTP calls.
"""
from typing import Optional, List
from .ports import ContractorInfo


# Hardcoded test contractors for demo
_MOCK_CONTRACTORS: List[ContractorInfo] = [
    ContractorInfo(
        national_id="10320894567",
        company_name="شرکت عمران سازه ۱",
        registration_number="REG-10001",
        ceo_name="علی احمدی",
        phone="021-88001001",
        address="تهران، خیابان ولیعصر، پلاک ۱۲۰",
        setad_ref_id="SETAD-001",
        is_verified=True,
    ),
    ContractorInfo(
        national_id="10320894568",
        company_name="شرکت فضای سبز ۲",
        registration_number="REG-10002",
        ceo_name="محمد حسینی",
        phone="021-88001002",
        address="تهران، خیابان شریعتی، پلاک ۲۵۰",
        setad_ref_id="SETAD-002",
        is_verified=True,
    ),
    ContractorInfo(
        national_id="10320894569",
        company_name="شرکت خدمات شهری ۳",
        registration_number="REG-10003",
        ceo_name="رضا محمدی",
        phone="021-88001003",
        address="تهران، خیابان آزادی، پلاک ۳۸۰",
        setad_ref_id="SETAD-003",
        is_verified=True,
    ),
    ContractorInfo(
        national_id="10320894570",
        company_name="شرکت ساختمانی نوین ۴",
        registration_number="REG-10004",
        ceo_name="حسین کریمی",
        phone="021-88001004",
        address="تهران، بلوار کشاورز، پلاک ۴۱۰",
        setad_ref_id="SETAD-004",
        is_verified=True,
    ),
    ContractorInfo(
        national_id="10320894571",
        company_name="شرکت مهندسی پارس ۵",
        registration_number="REG-10005",
        ceo_name="مهدی رضایی",
        phone="021-88001005",
        address="تهران، میدان ونک، پلاک ۵۲۰",
        setad_ref_id="SETAD-005",
        is_verified=True,
    ),
]

# Index by national_id for O(1) lookup
_CONTRACTOR_INDEX = {c.national_id: c for c in _MOCK_CONTRACTORS}


class SetadMockAdapter:
    """
    Mock implementation of SetadPort for Phase 2 demo.
    
    Returns test data from an in-memory list.
    Thread-safe (read-only data).
    """
    
    def fetch_auction_winner(self, auction_id: str) -> Optional[ContractorInfo]:
        """Return the first mock contractor as the 'winner' for any auction."""
        if _MOCK_CONTRACTORS:
            return _MOCK_CONTRACTORS[0]
        return None
    
    def verify_contractor(self, national_id: str) -> bool:
        """Check if national_id exists in mock data."""
        return national_id in _CONTRACTOR_INDEX
    
    def search_contractors(self, query: str) -> List[ContractorInfo]:
        """Search mock contractors by company name or national ID (case-insensitive)."""
        query_lower = query.lower()
        results = []
        for contractor in _MOCK_CONTRACTORS:
            if (query_lower in contractor.company_name.lower() or
                query_lower in contractor.national_id):
                results.append(contractor)
        return results
    
    def get_by_national_id(self, national_id: str) -> Optional[ContractorInfo]:
        """Direct lookup by national ID."""
        return _CONTRACTOR_INDEX.get(national_id)
