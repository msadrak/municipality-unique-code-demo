from __future__ import annotations

import re
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload

from app.models import (
    Activity,
    ApprovalTask,
    BudgetItem,
    CivilProject,
    EntityDocument,
    FinancialMatrix,
    OrgUnit,
    Transaction,
    User,
    UserRole,
    WorkflowStep,
)
from app.models.civil import ApprovalTaskStatus
from app.routers.auth import get_current_user, get_db
from app.schemas.civil import CivilProjectListItem, CivilProjectDetailResponse
from app.services.civil_workflow import (
    ACCESS_DENIED_MESSAGE,
    CivilWorkflowService,
    DocumentGeneratorService,
)

router = APIRouter(prefix="/api/civil", tags=["Civil"])

UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "uploads" / "civil"
ALLOWED_UPLOAD_MIME_TYPES = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/zip": ".zip",
}


class DocumentSubmitRequest(BaseModel):
    document_type: str
    payload: dict[str, Any]


class ApprovalDecisionRequest(BaseModel):
    status: ApprovalTaskStatus
    comments: str | None = None


class UploadResponse(BaseModel):
    file_name: str
    file_url: str
    content_type: str | None = None
    size: int


class CivilProjectCreateRequest(BaseModel):
    contract_category: str | None = None
    contract_title: str
    contractor_name: str
    contractor_id: int | None = None
    total_amount: int
    start_date: date
    end_date: date
    owning_org_unit_id: int | None = None
    activity_id: int | None = None


def _require_auth(request: Request, db: Session):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="احراز هویت الزامی است")
    return user


def _resolve_budget_line(project: CivilProject) -> str | None:
    if not project.activity or not project.activity.financial_rules:
        return None

    active_rule = next(
        (rule for rule in project.activity.financial_rules if rule.is_active),
        project.activity.financial_rules[0],
    )
    return active_rule.budget_line_code


def _project_budget_line(project: CivilProject) -> str | None:
    contract_document = next(
        (
            doc
            for doc in sorted(project.documents, key=lambda item: item.created_at or datetime.min, reverse=True)
            if doc.document_type in {"CONTRACT_SIGNED", "CONTRACT"}
            and (doc.payload or {}).get("budget_line_code")
        ),
        None,
    )
    if contract_document:
        return str((contract_document.payload or {}).get("budget_line_code"))
    return _resolve_budget_line(project)


def _active_budget_item(db: Session, project: CivilProject) -> BudgetItem | None:
    budget_line = _project_budget_line(project)
    if not budget_line:
        return None
    return db.query(BudgetItem).filter(BudgetItem.budget_code == budget_line).first()


def _project_tracking_prefix(project: CivilProject) -> str:
    normalized_project_code = re.sub(r"[^A-Za-z0-9]+", "-", project.project_code).strip("-")
    if not normalized_project_code:
        normalized_project_code = f"PROJECT-{project.id}"
    return f"CIVIL-{normalized_project_code}-DOC-"


def _safe_upload_extension(upload: UploadFile) -> str:
    content_type = upload.content_type or "application/octet-stream"
    if content_type in ALLOWED_UPLOAD_MIME_TYPES:
        return ALLOWED_UPLOAD_MIME_TYPES[content_type]

    suffix = Path(upload.filename or "").suffix.lower()
    if suffix in {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx", ".xls", ".xlsx", ".zip"}:
        return ".jpg" if suffix == ".jpeg" else suffix

    raise HTTPException(
        status_code=400,
        detail="Unsupported attachment type. Use PDF, image, Word, Excel, or ZIP files.",
    )


def _project_transactions(db: Session, project: CivilProject) -> list[Transaction]:
    return (
        db.query(Transaction)
        .filter(Transaction.tracking_number.like(f"{_project_tracking_prefix(project)}%"))
        .order_by(Transaction.created_at.desc(), Transaction.id.desc())
        .all()
    )


def _project_financial_matrix_rows(db: Session, project: CivilProject) -> list[FinancialMatrix]:
    return (
        db.query(FinancialMatrix)
        .filter(FinancialMatrix.project_id == project.id)
        .order_by(
            FinancialMatrix.statement_document_id.desc(),
            FinancialMatrix.event_sequence.asc(),
            FinancialMatrix.id.asc(),
        )
        .all()
    )


def _transaction_response(transaction: Transaction) -> dict[str, Any]:
    form_data = transaction.form_data or {}
    return {
        "id": transaction.id,
        "document_number": transaction.tracking_number,
        "unique_code": transaction.unique_code,
        "date": transaction.created_at.isoformat() if transaction.created_at else None,
        "amount": transaction.amount,
        "description": transaction.description,
        "status": transaction.status,
        "financial_event": form_data.get("financial_event"),
        "financial_event_label": form_data.get("financial_event_label"),
        "financial_matrix_id": form_data.get("financial_matrix_id"),
    }


def _financial_matrix_response(row: FinancialMatrix) -> dict[str, Any]:
    return {
        "id": row.id,
        "transaction_id": row.transaction_id,
        "event_sequence": row.event_sequence,
        "event_code": row.financial_event,
        "event_label": row.financial_event_label,
        "event_group": row.event_group,
        "event_direction": row.event_direction,
        "amount": float(row.amount or 0),
        "yekta_code": row.yekta_code,
        "payment_queue_status": row.payment_queue_status,
        "period_key": row.period_key,
        "source_payload": row.source_payload,
    }


@router.post("/upload", response_model=UploadResponse)
def upload_civil_attachment(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    _require_auth(request, db)

    extension = _safe_upload_extension(file)
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

    unique_name = f"{uuid.uuid4().hex}{extension}"
    destination = UPLOAD_ROOT / unique_name
    size = 0

    with destination.open("wb") as output:
        while chunk := file.file.read(1024 * 1024):
            size += len(chunk)
            output.write(chunk)

    relative_path = f"uploads/civil/{unique_name}"
    return UploadResponse(
        file_name=file.filename or unique_name,
        file_url=f"/{relative_path}",
        content_type=file.content_type,
        size=size,
    )


def _committed_amount(project: CivilProject) -> int | None:
    contract_amounts = [contract.total_amount for contract in project.contracts if contract.total_amount]
    if contract_amounts:
        return int(sum(contract_amounts))

    contract_document = next(
        (
            doc
            for doc in sorted(project.documents, key=lambda item: item.created_at or datetime.min, reverse=True)
            if doc.document_type in {"CONTRACT_SIGNED", "CONTRACT"}
        ),
        None,
    )
    if not contract_document:
        return None

    raw_amount = (contract_document.payload or {}).get("committed_amount")
    try:
        return int(str(raw_amount).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _financial_summary(db: Session, project: CivilProject) -> dict[str, int | None]:
    budget_item = _active_budget_item(db, project)
    transactions = _project_transactions(db, project)
    total_budget = None
    if budget_item:
        total_budget = int(
            budget_item.approved_1403
            or budget_item.allocated_1403
            or 0
        )
    return {
        "total_budget": total_budget,
        "committed_amount": _committed_amount(project),
        "total_paid_net": int(sum(transaction.amount or 0 for transaction in transactions)),
    }


def _next_project_code(db: Session, prefix: str) -> str:
    while True:
        candidate = f"{prefix}-{uuid.uuid4().hex[:8].upper()}"
        exists = db.query(CivilProject.id).filter(CivilProject.project_code == candidate).first()
        if exists is None:
            return candidate


def _volume_category_mapping(db: Session, category: str) -> dict[str, Any] | None:
    row = db.execute(
        text(
            """
            SELECT category_name, workflow_definition_id, initial_step_id, workflow_start_path
            FROM volume_contract_categories
            WHERE category_name = :category AND is_active = TRUE
            """
        ),
        {"category": category},
    ).mappings().first()
    return dict(row) if row else None


def _ensure_volume_contract_defaults(db: Session) -> tuple[OrgUnit, Activity]:
    org = (
        db.query(OrgUnit)
        .filter(OrgUnit.title == "قراردادهای حجمی")
        .first()
    )
    if org is None:
        org = OrgUnit(title="قراردادهای حجمی", code="VOL", org_type="UNIT")
        db.add(org)
        db.flush()

    activity = (
        db.query(Activity)
        .filter(
            Activity.name == "قراردادهای حجمی و کد یکتا",
            Activity.org_unit_id == org.id,
        )
        .first()
    )
    if activity is None:
        activity = Activity(
            name="قراردادهای حجمی و کد یکتا",
            org_unit_id=org.id,
            description="فعالیت پیش‌فرض برای گردش کار قراردادهای حجمی و صدور کد یکتا",
            is_active=True,
        )
        db.add(activity)
        db.flush()

    return org, activity


def _resolve_default_civil_initial_step_id(db: Session) -> int:
    initial_step = (
        db.query(WorkflowStep)
        .filter(WorkflowStep.order_index == 1)
        .first()
    )
    if initial_step is None:
        raise HTTPException(
            status_code=500,
            detail="Default civil workflow step 1 was not found.",
        )
    return int(initial_step.id)


def _resolve_contractor_id_by_name(db: Session, contractor_name: str | None) -> int | None:
    normalized_name = (contractor_name or "").strip()
    if not normalized_name:
        return None

    matches = (
        db.query(User.id)
        .filter(
            User.role == UserRole.CONTRACTOR.value,
            User.full_name == normalized_name,
        )
        .limit(2)
        .all()
    )
    if len(matches) == 1:
        return int(matches[0][0])
    return None


def _create_volume_contract_project(
    payload: CivilProjectCreateRequest,
    *,
    request: Request,
    db: Session,
    user_id: int,
):
    if not payload.contract_category:
        raise HTTPException(status_code=400, detail="contract_category is required for volume contracts.")

    mapping = _volume_category_mapping(db, payload.contract_category)
    if mapping is None:
        raise HTTPException(status_code=400, detail="Unknown or inactive volume contract category.")

    default_org, default_activity = _ensure_volume_contract_defaults(db)
    owning_org_unit_id = payload.owning_org_unit_id or default_org.id
    activity_id = payload.activity_id or default_activity.id
    initial_step_id = int(mapping["initial_step_id"])
    contractor_id = payload.contractor_id
    if contractor_id is not None:
        contractor_exists = (
            db.query(User.id)
            .filter(User.id == contractor_id, User.role == UserRole.CONTRACTOR.value)
            .first()
        )
        if contractor_exists is None:
            raise HTTPException(status_code=400, detail="Selected contractor user was not found.")

    project = CivilProject(
        project_code=_next_project_code(db, "VOL"),
        title=payload.contract_title,
        contract_category=payload.contract_category,
        owning_org_unit_id=owning_org_unit_id,
        activity_id=activity_id,
        created_by_id=user_id,
        contractor_id=contractor_id,
        current_step_id=initial_step_id,
        planned_start_date=payload.start_date,
        planned_end_date=payload.end_date,
        is_active=True,
    )
    db.add(project)
    db.flush()

    DocumentGeneratorService().create_document(
        db,
        project_id=project.id,
        step_id=initial_step_id,
        document_type="VOLUME_CONTRACT_BASE",
        payload={
            "contract_title": payload.contract_title,
            "contractor_name": payload.contractor_name,
            "total_amount": payload.total_amount,
            "start_date": payload.start_date.isoformat(),
            "end_date": payload.end_date.isoformat(),
            "contract_category": payload.contract_category,
        },
        created_by_id=user_id,
    )
    if project.contractor_id is None:
        project.contractor_id = _resolve_contractor_id_by_name(db, payload.contractor_name)
        db.flush()

    if project.contractor_id is not None:
        CivilWorkflowService(db)._ensure_contractor_assignment(project.id, project.contractor_id)

    CivilWorkflowService(db).enter_current_step(project)
    db.commit()
    db.refresh(project)
    return get_civil_project_detail(project.id, request, db)


@router.post("/projects", response_model=CivilProjectDetailResponse)
def create_civil_project(
    payload: CivilProjectCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user = _require_auth(request, db)
    if payload.contract_category:
        return _create_volume_contract_project(
            payload,
            request=request,
            db=db,
            user_id=user.id,
        )

    if payload.owning_org_unit_id is None or payload.activity_id is None:
        raise HTTPException(
            status_code=400,
            detail="Generic civil project initialization requires owning_org_unit_id and activity_id.",
        )

    initial_step_id = _resolve_default_civil_initial_step_id(db)
    project = CivilProject(
        project_code=_next_project_code(db, "CIV"),
        title=payload.contract_title,
        contract_category=None,
        owning_org_unit_id=payload.owning_org_unit_id,
        activity_id=payload.activity_id,
        created_by_id=user.id,
        current_step_id=initial_step_id,
        planned_start_date=payload.start_date,
        planned_end_date=payload.end_date,
        is_active=True,
    )
    db.add(project)
    db.flush()
    CivilWorkflowService(db).enter_current_step(project)
    db.commit()
    db.refresh(project)
    return get_civil_project_detail(project.id, request, db)


@router.post("/volume-contracts/projects", response_model=CivilProjectDetailResponse)
def create_volume_contract_project(
    payload: CivilProjectCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user = _require_auth(request, db)
    return _create_volume_contract_project(
        payload,
        request=request,
        db=db,
        user_id=user.id,
    )


@router.get("/projects", response_model=list[CivilProjectListItem])
def list_civil_projects(
    request: Request,
    category: str | None = Query(None),
    db: Session = Depends(get_db),
):
    _require_auth(request, db)

    query = (
        db.query(CivilProject)
        .options(
            joinedload(CivilProject.owning_org_unit),
            joinedload(CivilProject.activity).joinedload(Activity.financial_rules),
            joinedload(CivilProject.current_step),
        )
        .join(WorkflowStep, CivilProject.current_step)
    )

    if category:
        query = query.filter(CivilProject.contract_category == category)

    projects = query.order_by(
        WorkflowStep.phase_number.asc(),
        WorkflowStep.order_index.asc(),
        CivilProject.project_code.asc(),
    ).all()

    return [
        CivilProjectListItem(
            id=project.id,
            project_code=project.project_code,
            title=project.title,
            current_phase=project.current_step.phase_number,
            current_step=project.current_step.order_index,
            contract_category=project.contract_category,
            yekta_code=project.yekta_code,
            current_step_code=project.current_step.code,
            current_step_name=project.current_step.name,
            activity_name=project.activity.name if project.activity else None,
            budget_line=_resolve_budget_line(project),
            owning_org_unit_name=project.owning_org_unit.title if project.owning_org_unit else None,
        )
        for project in projects
    ]

@router.get("/projects/{project_id}", response_model=CivilProjectDetailResponse)
def get_civil_project_detail(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = _require_auth(request, db)

    project = (
        db.query(CivilProject)
        .options(
            joinedload(CivilProject.owning_org_unit),
            joinedload(CivilProject.activity).joinedload(Activity.financial_rules),
            joinedload(CivilProject.current_step).joinedload(WorkflowStep.definition),
            joinedload(CivilProject.documents).joinedload(EntityDocument.created_by),
            joinedload(CivilProject.approval_tasks).joinedload(ApprovalTask.assigned_user),
        )
        .filter(CivilProject.id == project_id)
        .first()
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    step_def = project.current_step.definition

    workflow_service = CivilWorkflowService(db)
    can_advance = False
    if step_def:
        form_required_type = step_def.required_form_type
        has_form = True
        if form_required_type:
            has_form = any(
                doc.document_type == form_required_type 
                for doc in project.documents 
                if doc.step_id == project.current_step_id
            )
        
        has_pending_tasks = any(
            task.status == ApprovalTaskStatus.PENDING 
            for task in project.approval_tasks 
            if task.step_id == project.current_step_id
        )
        
        can_advance = (
            has_form
            and not has_pending_tasks
            and workflow_service.user_can_execute_current_step(project, user.role)
        )

    total_steps = db.query(WorkflowStep).filter(WorkflowStep.phase_number == project.current_step.phase_number).count()

    docs_response = [
        {
            "id": doc.id,
            "document_type": doc.document_type,
            "payload": doc.payload,
            "submitted_by": doc.created_by.username if doc.created_by else None,
            "submitted_at": doc.created_at.isoformat() if doc.created_at else None,
        }
        for doc in project.documents
    ]

    tasks_response = [
        {
            "id": task.id,
            "role": task.assigned_role,
            "status": task.status,
            "comments": task.comments,
            "approver_name": task.assigned_user.username if task.assigned_user else None,
        }
        for task in project.approval_tasks
    ]
    transactions = _project_transactions(db, project)
    financial_matrix_rows = _project_financial_matrix_rows(db, project)

    return {
        "id": project.id,
        "project_code": project.project_code,
        "title": project.title,
        "contract_category": project.contract_category,
        "yekta_code": project.yekta_code,
        "budget_line": _project_budget_line(project),
        "current_step_info": {
            "step_name": project.current_step.name,
            "step_number": project.current_step.order_index,
            "total_steps": total_steps or 39,
            "assigned_role": step_def.role_required if step_def else None,
            "required_form_type": step_def.required_form_type if step_def else None,
            "form_schema": step_def.form_schema if step_def else None,
        },
        "documents": docs_response,
        "approval_tasks": tasks_response,
        "can_advance": can_advance,
        "financial_summary": _financial_summary(db, project),
        "transactions": [_transaction_response(transaction) for transaction in transactions],
        "financial_matrix": [_financial_matrix_response(row) for row in financial_matrix_rows],
    }


@router.post("/projects/{project_id}/documents")
def submit_project_document(
    project_id: int,
    payload: DocumentSubmitRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user = _require_auth(request, db)
    project = db.query(CivilProject).filter(CivilProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    workflow_service = CivilWorkflowService(db)
    if not workflow_service.user_can_execute_current_step(project, user.role):
        raise HTTPException(status_code=403, detail=ACCESS_DENIED_MESSAGE)

    try:
        document = DocumentGeneratorService().create_document(
            db,
            project_id=project.id,
            step_id=project.current_step_id,
            document_type=payload.document_type,
            payload=payload.payload,
            created_by_id=user.id,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.query(ApprovalTask).filter(
        ApprovalTask.project_id == project.id,
        ApprovalTask.step_id == project.current_step_id,
        ApprovalTask.document_id.is_(None),
        ApprovalTask.status == ApprovalTaskStatus.PENDING,
    ).update({"document_id": document.id}, synchronize_session=False)
    workflow_service.ensure_volume_statement_review_task(project, document)
    db.commit()
    db.refresh(document)
    return {
        "id": document.id,
        "document_type": document.document_type,
        "payload": document.payload,
        "submitted_at": document.created_at.isoformat() if document.created_at else None,
    }


@router.post("/tasks/{task_id}/approve")
def approve_task(
    task_id: int,
    decision: ApprovalDecisionRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user = _require_auth(request, db)
    task = db.query(ApprovalTask).filter(ApprovalTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Approval task not found")

    user_role = (user.role or "").upper()
    task_role = (task.assigned_role or "").upper()
    if user_role != "ADMIN" and user_role != task_role:
        raise HTTPException(status_code=403, detail=ACCESS_DENIED_MESSAGE)

    service = CivilWorkflowService(db)
    updated_task = service.approve_task(
        task_id,
        comments=decision.comments,
        status=decision.status,
    )

    advanced_to_step = None
    if decision.status == ApprovalTaskStatus.APPROVED:
        try:
            # Use ADMIN role for automatic advancement to bypass step-owner checks
            # since all required approvals are being validated by the service anyway.
            project = service.advance_project(updated_task.project_id, "ADMIN")
            advanced_to_step = project.current_step.order_index if project.current_step else None
        except (PermissionError, ValueError):
            # If advancement fails (e.g. pending signatures or role mismatch), 
            # we don't roll back the approval. The project just stays in the current step.
            advanced_to_step = None

    return {
        "id": updated_task.id,
        "status": updated_task.status,
        "advanced_to_step": advanced_to_step,
    }


@router.post("/projects/{project_id}/advance")
def advance_project(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = _require_auth(request, db)
    try:
        project = CivilWorkflowService(db).advance_project(project_id, user.role)
    except PermissionError as exc:
        db.rollback()
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "id": project.id,
        "current_step": project.current_step.order_index if project.current_step else None,
        "current_step_name": project.current_step.name if project.current_step else None,
    }


__all__ = ["router"]
