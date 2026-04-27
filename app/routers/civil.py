from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.models import Activity, ApprovalTask, BudgetItem, CivilProject, EntityDocument, Transaction, WorkflowStep
from app.models.civil import ApprovalTaskStatus
from app.routers.auth import get_current_user, get_db
from app.schemas.civil import CivilProjectListItem, CivilProjectDetailResponse
from app.services.civil_workflow import CivilWorkflowService, DocumentGeneratorService

router = APIRouter(prefix="/api/civil", tags=["Civil"])


class DocumentSubmitRequest(BaseModel):
    document_type: str
    payload: dict[str, Any]


class ApprovalDecisionRequest(BaseModel):
    status: ApprovalTaskStatus
    comments: str | None = None


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


def _project_transactions(db: Session, project: CivilProject) -> list[Transaction]:
    return (
        db.query(Transaction)
        .filter(Transaction.tracking_number.like(f"{_project_tracking_prefix(project)}%"))
        .order_by(Transaction.created_at.desc(), Transaction.id.desc())
        .all()
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


@router.get("/projects", response_model=list[CivilProjectListItem])
def list_civil_projects(
    request: Request,
    db: Session = Depends(get_db),
):
    _require_auth(request, db)

    projects = (
        db.query(CivilProject)
        .options(
            joinedload(CivilProject.owning_org_unit),
            joinedload(CivilProject.activity).joinedload(Activity.financial_rules),
            joinedload(CivilProject.current_step),
        )
        .join(WorkflowStep, CivilProject.current_step)
        .order_by(
            WorkflowStep.phase_number.asc(),
            WorkflowStep.order_index.asc(),
            CivilProject.project_code.asc(),
        )
        .all()
    )

    return [
        CivilProjectListItem(
            id=project.id,
            project_code=project.project_code,
            title=project.title,
            current_phase=project.current_step.phase_number,
            current_step=project.current_step.order_index,
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
    _require_auth(request, db)

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
        
        can_advance = has_form and not has_pending_tasks

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

    return {
        "id": project.id,
        "project_code": project.project_code,
        "title": project.title,
        "budget_line": _project_budget_line(project),
        "current_step_info": {
            "step_name": project.current_step.name,
            "step_number": project.current_step.order_index,
            "total_steps": total_steps or 31,
            "required_form_type": step_def.required_form_type if step_def else None,
            "form_schema": step_def.form_schema if step_def else None,
        },
        "documents": docs_response,
        "approval_tasks": tasks_response,
        "can_advance": can_advance,
        "financial_summary": _financial_summary(db, project),
        "transactions": [
            {
                "id": transaction.id,
                "document_number": transaction.tracking_number,
                "date": transaction.created_at.isoformat() if transaction.created_at else None,
                "amount": transaction.amount,
                "description": transaction.description,
                "status": transaction.status,
            }
            for transaction in transactions
        ],
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

    document = DocumentGeneratorService().create_document(
        db,
        project_id=project.id,
        step_id=project.current_step_id,
        document_type=payload.document_type,
        payload=payload.payload,
        created_by_id=user.id,
    )
    db.query(ApprovalTask).filter(
        ApprovalTask.project_id == project.id,
        ApprovalTask.step_id == project.current_step_id,
        ApprovalTask.document_id.is_(None),
        ApprovalTask.status == ApprovalTaskStatus.PENDING,
    ).update({"document_id": document.id}, synchronize_session=False)
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
    if user_role not in {"ADMIN", task.assigned_role.upper()} and task.assigned_user_id != user.id:
        raise HTTPException(status_code=403, detail="This approval task is not assigned to your role")

    service = CivilWorkflowService(db)
    updated_task = service.approve_task(
        task_id,
        comments=decision.comments,
        status=decision.status,
    )

    advanced_to_step = None
    if decision.status == ApprovalTaskStatus.APPROVED:
        try:
            project = service.advance_project(updated_task.project_id, user.role)
            advanced_to_step = project.current_step.order_index if project.current_step else None
        except ValueError:
            db.rollback()
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
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "id": project.id,
        "current_step": project.current_step.order_index if project.current_step else None,
        "current_step_name": project.current_step.name if project.current_step else None,
    }


__all__ = ["router"]
