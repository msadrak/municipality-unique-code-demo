"""Civil BPMS services.

The workflow rules here are intentionally data-driven. The service reads the
current step definition, required document type, signature actions, and
financial gate from tables instead of branching on hardcoded step numbers.
"""

from __future__ import annotations

import secrets
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models import (
    ApprovalTask,
    ApprovalTaskStatus,
    CivilProject,
    CivilProjectAssignment,
    CivilProjectRole,
    EntityDocument,
    FinancialMatrix,
    StepAction,
    User,
    UserRole,
    WorkflowStep,
    WorkflowStepDefinition,
    WorkflowTransition,
    validate_document_payload,
)
from app.core.security import get_password_hash
from app.services.civil_financial_bridge import CivilFinancialBridgeService
from app.services.yekta_service import STATEMENT_UPLOAD_DOCUMENT_TYPES, YektaService

CONTRACTOR_ASSIGNMENT_FORM = "CONTRACTOR_ASSIGNMENT"
VOLUME_CONTRACT_BASE_FORM = "VOLUME_CONTRACT_BASE"
VOLUME_FINANCIAL_MATRIX_FORM = "FINANCIAL_MATRIX_LINK"
VOLUME_YEKTA_ISSUANCE_FORM = "YEKTA_CODE_ISSUANCE"
VOLUME_TIMESHEET_FORM = "CONTRACTOR_STATEMENT_UPLOAD"
VOLUME_AUTO_CALCULATION_FORM = "AUTO_STATEMENT_CALCULATION"
VOLUME_BASE_STEP_NUMBER = 101
VOLUME_TIMESHEET_STEP_NUMBER = 102
VOLUME_YEKTA_STEP_NUMBER = 103
VOLUME_AUTO_CALCULATION_STEP_NUMBER = 104
VOLUME_STATEMENT_REVIEW_ROLE = "YEKTA_ADMIN"
ACCESS_DENIED_MESSAGE = "Access Denied: You do not have the required role to execute this step."


class DocumentGeneratorService:
    """Validates JSONB form payloads and prepares future PDF render context."""

    def validate_payload(self, document_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        validate_document_payload(document_type, payload)
        return payload

    def create_document(
        self,
        db: Session,
        *,
        project_id: int,
        step_id: int,
        document_type: str,
        payload: dict[str, Any],
        created_by_id: int | None = None,
        file_path: str | None = None,
    ) -> EntityDocument:
        self.validate_payload(document_type, payload)
        document = EntityDocument(
            project_id=project_id,
            step_id=step_id,
            document_type=document_type,
            payload=payload,
            created_by_id=created_by_id,
            file_path=file_path,
        )
        db.add(document)
        db.flush()
        return document

    def prepare_render_context(self, document: EntityDocument) -> dict[str, Any]:
        self.validate_payload(document.document_type, document.payload or {})
        return {
            "document_id": document.id,
            "document_type": document.document_type,
            "project_id": document.project_id,
            "step_id": document.step_id,
            "created_at": document.created_at.isoformat() if document.created_at else None,
            "payload": dict(document.payload or {}),
        }


class CivilWorkflowService:
    """Moves civil projects through DB-defined steps, forms, and approvals."""

    def __init__(self, db: Session):
        self.db = db

    def calculate_volume_contract_statement(self, project_id: int) -> dict[str, Any]:
        """
        Preview the approved contractor statement as standard municipality
        financial events. The actual Yekta issuance happens when Bahadori
        submits Step 103 and the project advances to Step 104.
        """
        return YektaService(self.db).build_volume_statement_preview(project_id)

    def update_financial_matrix_with_calculation(
        self, project_id: int, calculation_result: dict[str, Any]
    ) -> list[FinancialMatrix]:
        """Return statement-level matrix rows generated during Yekta issuance."""
        return YektaService(self.db).statement_rows_for_project(project_id)

    def _to_decimal(self, value: Any) -> Decimal:
        """Convert various numeric types to Decimal for precise calculation."""
        if isinstance(value, Decimal):
            return value
        if isinstance(value, (int, float)):
            return Decimal(str(value))
        if isinstance(value, str):
            # Remove Persian/Arabic digits and separators
            normalized = value.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
            normalized = normalized.replace(",", "").replace("٬", "").strip()
            if not normalized:
                return Decimal("0")
            return Decimal(normalized)
        return Decimal("0")

    def get_workflow_map(self) -> list[dict[str, Any]]:
        definitions = (
            self.db.query(WorkflowStepDefinition)
            .options(joinedload(WorkflowStepDefinition.actions))
            .order_by(WorkflowStepDefinition.step_number.asc())
            .all()
        )
        return [
            {
                "step_number": definition.step_number,
                "name": definition.name,
                "role_required": definition.role_required,
                "required_form_type": definition.required_form_type,
                "financial_gate": definition.financial_gate,
                "required_signatures": [
                    action.assigned_role
                    for action in definition.actions
                    if action.is_required
                ],
            }
            for definition in definitions
        ]

    def print_workflow_map(self) -> str:
        rows = []
        for row in self.get_workflow_map():
            signatures = ", ".join(row["required_signatures"]) or "-"
            rows.append(
                (
                    f"{row['step_number']:02d}. {row['name']} | "
                    f"role={row['role_required'] or '-'} | "
                    f"form={row['required_form_type'] or '-'} | "
                    f"signatures={signatures} | "
                    f"financial_gate={row['financial_gate'] or '-'}"
                )
            )
        output = "\n".join(rows)
        print(output)
        return output

    def enter_current_step(self, project: CivilProject) -> list[ApprovalTask]:
        definition = self._definition_for_step(project.current_step)
        if definition is None:
            return []

        created_tasks: list[ApprovalTask] = []
        for action in definition.actions:
            existing = (
                self.db.query(ApprovalTask)
                .filter(
                    ApprovalTask.project_id == project.id,
                    ApprovalTask.step_id == project.current_step_id,
                    ApprovalTask.step_action_id == action.id,
                )
                .first()
            )
            if existing:
                continue

            task = ApprovalTask(
                project_id=project.id,
                step_id=project.current_step_id,
                step_action_id=action.id,
                assigned_role=action.assigned_role,
                status=ApprovalTaskStatus.PENDING,
                is_required=action.is_required,
            )
            self.db.add(task)
            created_tasks.append(task)

        self.db.flush()
        return created_tasks

    def advance_project(self, project_id: int, actor_role: str) -> CivilProject:
        project = (
            self.db.query(CivilProject)
            .filter(CivilProject.id == project_id)
            .with_for_update()
            .first()
        )
        if project is None:
            raise ValueError(f"Civil project {project_id} was not found")

        self._assert_actor_can_start_step(project, actor_role)
        self.enter_current_step(project)
        self._assert_required_document_submitted(project)
        self._assert_required_approvals_complete(project)

        transition = self._next_transition(project.current_step_id, actor_role)
        if transition is None:
            raise ValueError("No next workflow transition is defined for the current step")

        from_step = project.current_step
        to_step_id = transition.to_step_id
        self._run_pre_transition_hooks(
            project,
            from_step_id=from_step.id if from_step else None,
            to_step_id=to_step_id,
        )
        project.current_step_id = to_step_id
        project.updated_at = datetime.utcnow()
        self.db.flush()
        self._run_post_transition_hooks(project, from_step_id=from_step.id if from_step else None)
        self.db.flush()
        self.db.refresh(project)
        self.enter_current_step(project)
        self.db.commit()
        self.db.refresh(project)
        self._trigger_financial_gate_if_present(project)
        self.db.refresh(project)
        return project

    def approve_task(
        self,
        task_id: int,
        *,
        comments: str | None = None,
        status: ApprovalTaskStatus = ApprovalTaskStatus.APPROVED,
    ) -> ApprovalTask:
        task = (
            self.db.query(ApprovalTask)
            .filter(ApprovalTask.id == task_id)
            .with_for_update()
            .first()
        )
        if task is None:
            raise ValueError(f"Approval task {task_id} was not found")

        task.status = status
        task.comments = comments
        task.resolved_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(task)
        return task

    def ensure_volume_statement_review_task(
        self,
        project: CivilProject,
        document: EntityDocument,
    ) -> None:
        if not project.current_step or project.current_step.order_index != VOLUME_TIMESHEET_STEP_NUMBER:
            return
        if document.document_type not in STATEMENT_UPLOAD_DOCUMENT_TYPES:
            return

        pending_task = (
            self.db.query(ApprovalTask)
            .filter(
                ApprovalTask.project_id == project.id,
                ApprovalTask.step_id == project.current_step_id,
                ApprovalTask.status == ApprovalTaskStatus.PENDING,
            )
            .order_by(ApprovalTask.id.asc())
            .first()
        )
        if pending_task is None:
            pending_task = ApprovalTask(
                project_id=project.id,
                step_id=project.current_step_id,
                assigned_role=VOLUME_STATEMENT_REVIEW_ROLE,
                status=ApprovalTaskStatus.PENDING,
                is_required=True,
            )
            self.db.add(pending_task)

        pending_task.assigned_role = VOLUME_STATEMENT_REVIEW_ROLE
        pending_task.document_id = document.id
        pending_task.is_required = True
        self.db.flush()

    def get_financial_gate_payload(self, project: CivilProject) -> dict[str, Any] | None:
        definition = self._definition_for_step(project.current_step)
        gate_name = self._gate_name_for_definition(definition)
        if definition is None or not gate_name:
            return None
        return {
            "project_id": project.id,
            "project_code": project.project_code,
            "step_definition_id": definition.id,
            "step_number": definition.step_number,
            "financial_gate": gate_name,
        }

    def _trigger_financial_gate_if_present(self, project: CivilProject) -> None:
        definition = self._definition_for_step(project.current_step)
        gate_name = self._gate_name_for_definition(definition)
        if not gate_name:
            return

        CivilFinancialBridgeService().trigger_financial_gate(
            project.id,
            gate_name,
            self.db,
        )

    def user_can_execute_current_step(self, project: CivilProject, actor_role: str | None) -> bool:
        definition = self._definition_for_step(project.current_step)
        return self._role_can_execute_definition(definition, actor_role)

    def _role_can_execute_definition(
        self,
        definition: WorkflowStepDefinition | None,
        actor_role: str | None,
    ) -> bool:
        if not definition or not definition.role_required:
            return True

        normalized_actor_role = self._normalize_role(actor_role)
        if normalized_actor_role == "ADMIN":
            return True
        return normalized_actor_role == self._normalize_role(definition.role_required)

    def _normalize_role(self, role: str | None) -> str:
        return (role or "").strip().upper()

    def _run_post_transition_hooks(
        self,
        project: CivilProject,
        *,
        from_step_id: int | None,
    ) -> None:
        if from_step_id is None:
            return

        assignment_document = self._latest_step_document(
            project.id,
            from_step_id,
            CONTRACTOR_ASSIGNMENT_FORM,
        )

        if assignment_document is not None:
            self._provision_contractor_for_project(project, assignment_document.payload or {})
            return

        volume_base_document = self._latest_step_document(
            project.id,
            from_step_id,
            VOLUME_CONTRACT_BASE_FORM,
        )

        if volume_base_document is not None:
            self._provision_contractor_from_volume_base(project, volume_base_document.payload or {})

    def _run_pre_transition_hooks(
        self,
        project: CivilProject,
        *,
        from_step_id: int | None,
        to_step_id: int | None,
    ) -> None:
        if from_step_id is None:
            return

        self._generate_volume_yekta_if_needed(
            project,
            from_step_id=from_step_id,
            to_step_id=to_step_id,
        )

    def _latest_step_document(
        self,
        project_id: int,
        step_id: int,
        document_type: str,
    ) -> EntityDocument | None:
        return (
            self.db.query(EntityDocument)
            .filter(
                EntityDocument.project_id == project_id,
                EntityDocument.step_id == step_id,
                EntityDocument.document_type == document_type,
            )
            .order_by(EntityDocument.created_at.desc(), EntityDocument.id.desc())
            .first()
        )

    def _latest_step_order_document(
        self,
        project_id: int,
        step_number: int,
        document_type: str,
    ) -> EntityDocument | None:
        return (
            self.db.query(EntityDocument)
            .join(WorkflowStep, EntityDocument.step_id == WorkflowStep.id)
            .filter(
                EntityDocument.project_id == project_id,
                EntityDocument.document_type == document_type,
                WorkflowStep.order_index == step_number,
            )
            .order_by(EntityDocument.created_at.desc(), EntityDocument.id.desc())
            .first()
        )

    def _generate_volume_yekta_if_needed(
        self,
        project: CivilProject,
        from_step_id: int,
        to_step_id: int | None = None,
    ) -> None:
        from_step = (
            self.db.query(WorkflowStep)
            .options(joinedload(WorkflowStep.definition))
            .filter(WorkflowStep.id == from_step_id)
            .first()
        )
        if from_step is None:
            return

        if from_step.order_index != VOLUME_YEKTA_STEP_NUMBER:
            return

        if to_step_id is not None:
            to_step = self.db.query(WorkflowStep).filter(WorkflowStep.id == to_step_id).first()
            if to_step is not None and to_step.order_index <= from_step.order_index:
                return

        YektaService(self.db).issue_for_approved_volume_statement(project.id)

    def _provision_contractor_for_project(
        self,
        project: CivilProject,
        payload: dict[str, Any],
    ) -> None:
        contractor_name = str(payload.get("contractor_name") or "").strip()
        national_id = str(payload.get("national_id") or "").strip()
        phone_number = str(payload.get("phone_number") or "").strip()

        if not national_id:
            raise ValueError("CONTRACTOR_ASSIGNMENT payload is missing national_id")

        contractor = self.db.query(User).filter(User.username == national_id).first()
        generated_password: str | None = None
        account_created = False

        if contractor is None:
            generated_password = secrets.token_urlsafe(12)
            contractor = User(
                username=national_id,
                hashed_password=get_password_hash(generated_password),
                full_name=contractor_name or national_id,
                role=UserRole.CONTRACTOR.value,
                is_active=True,
            )
            self.db.add(contractor)
            self.db.flush()
            account_created = True
        elif contractor.role != UserRole.CONTRACTOR.value:
            contractor.role = UserRole.CONTRACTOR.value
            if contractor_name and not contractor.full_name:
                contractor.full_name = contractor_name
            contractor.is_active = True
            self.db.flush()

        project.contractor_id = contractor.id
        self._ensure_contractor_assignment(project.id, contractor.id)

        if account_created:
            print(
                f"[MOCK SMS] Sent to {phone_number}: Your account is created. "
                f"Username: {national_id}, Password: {generated_password}"
            )
        else:
            print(
                f"[MOCK SMS] Sent to {phone_number}: Your account is linked to project "
                f"{project.project_code}. Username: {national_id}"
            )

    def _provision_contractor_from_volume_base(
        self,
        project: CivilProject,
        payload: dict[str, Any],
    ) -> None:
        contractor_name = str(payload.get("contractor_name") or "").strip()
        if not contractor_name:
            return

        contractor = (
            self.db.query(User)
            .filter(
                User.role == UserRole.CONTRACTOR.value,
                or_(
                    User.full_name == contractor_name,
                    User.username == contractor_name,
                ),
            )
            .order_by(User.id.asc())
            .first()
        )
        if contractor is None:
            return

        project.contractor_id = contractor.id
        self._ensure_contractor_assignment(project.id, contractor.id)

    def _ensure_contractor_assignment(self, project_id: int, contractor_user_id: int) -> None:
        existing = (
            self.db.query(CivilProjectAssignment)
            .filter(
                CivilProjectAssignment.project_id == project_id,
                CivilProjectAssignment.user_id == contractor_user_id,
                CivilProjectAssignment.role == CivilProjectRole.CONTRACTOR,
            )
            .first()
        )
        if existing:
            existing.is_active = True
            return

        self.db.add(
            CivilProjectAssignment(
                project_id=project_id,
                user_id=contractor_user_id,
                role=CivilProjectRole.CONTRACTOR,
                is_active=True,
            )
        )

    def _gate_name_for_definition(
        self,
        definition: WorkflowStepDefinition | None,
    ) -> str | None:
        if definition is None:
            return None
        return (
            getattr(definition, "financial_gate_trigger", None)
            or definition.financial_gate
        )

    def _definition_for_step(self, step: WorkflowStep | None) -> WorkflowStepDefinition | None:
        if step is None:
            return None
        if step.definition is not None:
            return step.definition
        return (
            self.db.query(WorkflowStepDefinition)
            .filter(WorkflowStepDefinition.step_number == step.order_index)
            .first()
        )

    def _assert_actor_can_start_step(self, project: CivilProject, actor_role: str) -> None:
        definition = self._definition_for_step(project.current_step)
        if self._role_can_execute_definition(definition, actor_role):
            return
        raise PermissionError(ACCESS_DENIED_MESSAGE)

    def _assert_required_document_submitted(self, project: CivilProject) -> None:
        definition = self._definition_for_step(project.current_step)
        if not definition or not definition.required_form_type:
            return

        exists = (
            self.db.query(EntityDocument.id)
            .filter(
                EntityDocument.project_id == project.id,
                EntityDocument.step_id == project.current_step_id,
                EntityDocument.document_type == definition.required_form_type,
            )
            .first()
        )
        if not exists:
            raise ValueError(
                f"Step {definition.step_number} requires document "
                f"{definition.required_form_type}"
            )

    def _assert_required_approvals_complete(self, project: CivilProject) -> None:
        pending_required = (
            self.db.query(ApprovalTask)
            .filter(
                ApprovalTask.project_id == project.id,
                ApprovalTask.step_id == project.current_step_id,
                ApprovalTask.is_required.is_(True),
                ApprovalTask.status != ApprovalTaskStatus.APPROVED,
            )
            .all()
        )
        if pending_required:
            roles = ", ".join(sorted(task.assigned_role for task in pending_required))
            raise ValueError(f"Required approvals are still pending: {roles}")

    def _next_transition(self, current_step_id: int, actor_role: str) -> WorkflowTransition | None:
        transitions = (
            self.db.query(WorkflowTransition)
            .join(WorkflowStep, WorkflowTransition.to_step_id == WorkflowStep.id)
            .filter(WorkflowTransition.from_step_id == current_step_id)
            .order_by(WorkflowStep.order_index.asc())
            .all()
        )
        for transition in transitions:
            if transition.required_role in {None, actor_role, "ADMIN"} or actor_role == "ADMIN":
                return transition
        return None
