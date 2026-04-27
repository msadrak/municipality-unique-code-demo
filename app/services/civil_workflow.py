"""Civil BPMS services.

The workflow rules here are intentionally data-driven. The service reads the
current step definition, required document type, signature actions, and
financial gate from tables instead of branching on hardcoded step numbers.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.models import (
    ApprovalTask,
    ApprovalTaskStatus,
    CivilProject,
    EntityDocument,
    StepAction,
    WorkflowStep,
    WorkflowStepDefinition,
    WorkflowTransition,
    validate_document_payload,
)
from app.services.civil_financial_bridge import CivilFinancialBridgeService


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

        project.current_step_id = transition.to_step_id
        project.updated_at = datetime.utcnow()
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
        if not definition or not definition.role_required:
            return
        if actor_role in {definition.role_required, "ADMIN"}:
            return
        raise PermissionError(
            f"Role {actor_role} cannot advance step {definition.step_number}; "
            f"{definition.role_required} is required"
        )

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
