from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import uuid


@dataclass
class BudgetAllocationResult:
    success: bool
    allocation_code: str
    message: str
    timestamp: datetime


class BudgetService:
    @staticmethod
    def check_available_budget(amount: Optional[int], fiscal_year: int) -> bool:
        return (amount or 0) < 50_000_000_000

    @staticmethod
    def reserve_budget(request_id: int, amount: Optional[int], fiscal_year: int) -> BudgetAllocationResult:
        code = f"BDG-{fiscal_year}-{uuid.uuid4().hex[:8].upper()}"
        return BudgetAllocationResult(
            success=True,
            allocation_code=code,
            message="تخصیص بودجه با موفقیت انجام شد",
            timestamp=datetime.utcnow(),
        )

    @staticmethod
    def release_budget(allocation_code: str) -> bool:
        return True
