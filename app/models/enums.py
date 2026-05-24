import enum


class UserRole(str, enum.Enum):
    REGION_USER = "REGION_USER"
    SECURITY_AGGREGATOR = "SECURITY_AGGREGATOR"
    CONTRACTOR = "CONTRACTOR"
    SECURITY_DIRECTOR = "SECURITY_DIRECTOR"

    # Civil engineering PLM workflow roles.
    CIVIL_MANAGER = "CIVIL_MANAGER"
    TENDERING_OFFICER = "TENDERING_OFFICER"
    CONTRACTS_OFFICER = "CONTRACTS_OFFICER"
    SUPERVISOR = "SUPERVISOR"
    DELIVERY_COMMISSION = "DELIVERY_COMMISSION"
    FINANCE_MANAGER = "FINANCE_MANAGER"
    FINANCE_OFFICER = "FINANCE_OFFICER"
    YEKTA_ADMIN = "YEKTA_ADMIN"
    OPERATIONAL_MANAGER = "OPERATIONAL_MANAGER"
    TREASURY = "TREASURY"

    # Legacy roles retained for backward compatibility with existing modules.
    ADMIN = "ADMIN"
    GM_HC = "GM_HC"
    VP_PLANNING = "VP_PLANNING"
    VP_FINANCE = "VP_FINANCE"
    WELFARE_DEPT = "WELFARE_DEPT"
    FINANCE_UNIT = "FINANCE_UNIT"
    GM_FINANCE = "GM_FINANCE"
    ISFAHAN_CARD = "ISFAHAN_CARD"
    PAYROLL_MANAGER = "PAYROLL_MANAGER"
    HR_ADMIN = "HR_ADMIN"
    OPERATOR = "OPERATOR"


class AttendanceSheetStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    CREATOR_APPROVED = "CREATOR_APPROVED"
    COMPANY_REP_APPROVED = "COMPANY_REP_APPROVED"
    SECURITY_APPROVED = "SECURITY_APPROVED"
    GM_APPROVED = "GM_APPROVED"
    NEEDS_CORRECTION = "NEEDS_CORRECTION"
    REJECTED = "REJECTED"


class WorkFlowStatus(str, enum.Enum):
    """
    Represents the 4-stage monthly workflow lifecycle:

    1. DRAFT_REGIONS – 33 regions are uploading their 18-column Excel sheets.
    2. PENDING_SECURITY_AGGREGATION – All regions uploaded; waiting for
       the Security Directorate (Mr. Niroumand) to aggregate.
    3. PENDING_CONTRACTOR_STATEMENT – Aggregated; waiting for the Contractor
       (Company) to upload the 6-column invoice statement.
    4. PENDING_SECURITY_AUDIT – Statement uploaded; waiting for the Security
       Director (Mr. Bahadori) to apply contract penalties and approve.
    5. FINAL_APPROVED – Fully reconciled and approved.
    """

    DRAFT_REGIONS = "DRAFT_REGIONS"
    PENDING_SECURITY_AGGREGATION = "PENDING_SECURITY_AGGREGATION"
    PENDING_CONTRACTOR_STATEMENT = "PENDING_CONTRACTOR_STATEMENT"
    PENDING_SECURITY_AUDIT = "PENDING_SECURITY_AUDIT"
    FINAL_APPROVED = "FINAL_APPROVED"
    PENDING_UNIQUE_CODE = "PENDING_UNIQUE_CODE"
    SENT_TO_FINANCE = "SENT_TO_FINANCE"
