from __future__ import annotations

import uuid
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.models import Activity, ApprovalTask, CivilProject, EntityDocument, User, UserRole, WorkflowStep
from app.models.civil import ApprovalTaskStatus
from app.routers.auth import get_db
from app.routers.civil import (
    ApprovalDecisionRequest,
    DocumentSubmitRequest,
    UploadResponse,
    _create_volume_contract_project,
    _financial_summary,
    _financial_matrix_response,
    _project_budget_line,
    _project_financial_matrix_rows,
    _project_transactions,
    _require_auth,
    _resolve_budget_line,
    _safe_upload_extension,
    _transaction_response,
)
from app.schemas.civil import CivilProjectDetailResponse, CivilProjectListItem
from app.services.civil_workflow import (
    ACCESS_DENIED_MESSAGE,
    CivilWorkflowService,
    DocumentGeneratorService,
)

router = APIRouter(prefix="/api/volume-contracts", tags=["Volume Contracts"])

UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "uploads" / "volume_contracts"


class VolumeContractCreateRequest(BaseModel):
    contract_category: str
    contract_title: str
    contractor_name: str
    contractor_id: int | None = None
    total_amount: int
    start_date: date
    end_date: date
    owning_org_unit_id: int | None = None
    activity_id: int | None = None


class ContractorUserResponse(BaseModel):
    id: int
    username: str
    full_name: str | None = None


def _get_volume_contract_or_404(db: Session, project_id: int) -> CivilProject:
    project = db.query(CivilProject).filter(CivilProject.id == project_id).first()
    if project is None or not project.contract_category:
        raise HTTPException(status_code=404, detail="Volume contract not found")
    return project


@router.post("/attachments", response_model=UploadResponse)
def upload_volume_contract_attachment(
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

    relative_path = f"uploads/volume_contracts/{unique_name}"
    return UploadResponse(
        file_name=file.filename or unique_name,
        file_url=f"/{relative_path}",
        content_type=file.content_type,
        size=size,
    )


@router.post("/projects", response_model=CivilProjectDetailResponse)
def create_volume_contract_project(
    payload: VolumeContractCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user = _require_auth(request, db)
    try:
        return _create_volume_contract_project(
            payload,
            request=request,
            db=db,
            user_id=user.id,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/contractor-users", response_model=list[ContractorUserResponse])
def list_contractor_users(
    request: Request,
    db: Session = Depends(get_db),
):
    _require_auth(request, db)
    users = (
        db.query(User)
        .filter(User.role == UserRole.CONTRACTOR.value)
        .order_by(User.full_name.asc(), User.username.asc())
        .all()
    )
    return [
        ContractorUserResponse(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
        )
        for user in users
    ]


@router.get("/projects", response_model=list[CivilProjectListItem])
def list_volume_contract_projects(
    request: Request,
    category: str | None = Query(None),
    db: Session = Depends(get_db),
):
    user = _require_auth(request, db)

    query = (
        db.query(CivilProject)
        .options(
            joinedload(CivilProject.owning_org_unit),
            joinedload(CivilProject.activity).joinedload(Activity.financial_rules),
            joinedload(CivilProject.current_step),
        )
        .join(WorkflowStep, CivilProject.current_step_id == WorkflowStep.id)
        .filter(CivilProject.contract_category.isnot(None))
    )

    if user.role == "CONTRACTOR":
        query = query.filter(CivilProject.contractor_id == user.id)

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
def get_volume_contract_detail(
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
        .filter(CivilProject.id == project_id, CivilProject.contract_category.isnot(None))
        .first()
    )

    if not project:
        raise HTTPException(status_code=404, detail="Volume contract not found")

    if user.role == "CONTRACTOR" and project.contractor_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied: This contract is not assigned to you.")

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

    total_steps = (
        db.query(WorkflowStep)
        .filter(WorkflowStep.order_index.between(101, 104))
        .count()
    )
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
            "total_steps": total_steps or 4,
            "assigned_role": step_def.role_required if step_def else None,
            "required_form_type": step_def.required_form_type if step_def else None,
            "form_schema": step_def.form_schema if step_def else None,
        },
        "documents": [
            {
                "id": doc.id,
                "document_type": doc.document_type,
                "payload": doc.payload,
                "submitted_by": doc.created_by.username if doc.created_by else None,
                "submitted_at": doc.created_at.isoformat() if doc.created_at else None,
            }
            for doc in project.documents
        ],
        "approval_tasks": [
            {
                "id": task.id,
                "role": task.assigned_role,
                "status": task.status,
                "comments": task.comments,
                "approver_name": task.assigned_user.username if task.assigned_user else None,
            }
            for task in project.approval_tasks
        ],
        "can_advance": can_advance,
        "financial_summary": _financial_summary(db, project),
        "transactions": [_transaction_response(transaction) for transaction in transactions],
        "financial_matrix": [_financial_matrix_response(row) for row in financial_matrix_rows],
    }


@router.post("/projects/{project_id}/documents")
def submit_volume_contract_document(
    project_id: int,
    payload: DocumentSubmitRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user = _require_auth(request, db)
    project = _get_volume_contract_or_404(db, project_id)

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
def approve_volume_contract_task(
    task_id: int,
    decision: ApprovalDecisionRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user = _require_auth(request, db)
    task = (
        db.query(ApprovalTask)
        .join(CivilProject, ApprovalTask.project_id == CivilProject.id)
        .filter(ApprovalTask.id == task_id, CivilProject.contract_category.isnot(None))
        .first()
    )
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
            project = db.query(CivilProject).filter(CivilProject.id == updated_task.project_id).first()
            advance_role = (
                project.current_step.definition.role_required
                if project and project.current_step and project.current_step.definition
                else "ADMIN"
            )
            project = service.advance_project(updated_task.project_id, advance_role or "ADMIN")
            advanced_to_step = project.current_step.order_index if project.current_step else None
        except (PermissionError, ValueError):
            advanced_to_step = None

    return {
        "id": updated_task.id,
        "status": updated_task.status,
        "advanced_to_step": advanced_to_step,
    }


@router.post("/projects/{project_id}/advance")
def advance_volume_contract_project(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = _require_auth(request, db)
    _get_volume_contract_or_404(db, project_id)
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


@router.get("/projects/{project_id}/calculate-statement")
def calculate_volume_contract_statement(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Preview statement events or return generated Step 104 rows."""
    user = _require_auth(request, db)
    _get_volume_contract_or_404(db, project_id)

    try:
        service = CivilWorkflowService(db)
        calculation = service.calculate_volume_contract_statement(project_id)
        return calculation
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/projects/{project_id}/submit-calculation")
def submit_volume_contract_calculation(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Return generated Step 104 matrix rows for compatibility with the old UI."""
    user = _require_auth(request, db)
    project = _get_volume_contract_or_404(db, project_id)

    if user.role not in ("FINANCE_MANAGER", "YEKTA_ADMIN", "ADMIN"):
        raise HTTPException(
            status_code=403,
            detail="Only FINANCE_MANAGER or YEKTA_ADMIN can view generated statement rows",
        )

    try:
        service = CivilWorkflowService(db)
        
        # Calculate the statement
        calculation = service.calculate_volume_contract_statement(project_id)
        
        # Create the document
        doc_service = DocumentGeneratorService()
        document = doc_service.create_document(
            db,
            project_id=project_id,
            step_id=project.current_step_id,
            document_type="AUTO_STATEMENT_CALCULATION",
            payload={
                "gross_amount": calculation["gross_amount"],
                "work_period": calculation["work_period"],
                "statement_number": calculation["statement_number"],
                "statement_document_id": calculation["statement_document_id"],
                "financial_events": calculation["financial_events"],
            },
            created_by_id=user.id,
        )
        
        # Matrix rows are generated when Bahadori submits Step 103. Return them
        # here so finance can see exactly which coded rows are entering the queue.
        financial_matrix_rows = service.update_financial_matrix_with_calculation(
            project_id, calculation
        )
        
        db.commit()
        
        return {
            "document_id": document.id,
            "calculation": calculation,
            "financial_matrix_ids": [row.id for row in financial_matrix_rows],
            "message": "محاسبه خودکار با موفقیت ثبت شد",
        }
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"خطا در ثبت محاسبه: {str(exc)}") from exc


__all__ = ["router"]
