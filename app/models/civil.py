"""Civil engineering project orchestration models."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import relationship, validates

from app.database import Base
from app.models.enums import UserRole


class CivilProjectRole(str, enum.Enum):
    CIVIL_MANAGER = UserRole.CIVIL_MANAGER.value
    TENDERING_OFFICER = UserRole.TENDERING_OFFICER.value
    CONTRACTS_OFFICER = UserRole.CONTRACTS_OFFICER.value
    SUPERVISOR = UserRole.SUPERVISOR.value
    DELIVERY_COMMISSION = UserRole.DELIVERY_COMMISSION.value
    CONTRACTOR = UserRole.CONTRACTOR.value
    FINANCE_MANAGER = UserRole.FINANCE_MANAGER.value


class ApprovalTaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


DOCUMENT_PAYLOAD_REQUIREMENTS: dict[str, set[str]] = {
    "LAND_HANDOVER": {
        "delivery_date",
        "initial_amount",
        "project_code",
        "contractor_name",
        "handover_location",
        "land_area",
        "municipality_representative",
        "contractor_representative",
    },
    "COMMISSION_MINUTES": {
        "meeting_date",
        "commission_members",
        "agenda",
        "decisions",
    },
}


def validate_document_payload(document_type: str | None, payload: dict | None) -> dict | None:
    if not document_type or payload is None:
        return payload

    required_fields = DOCUMENT_PAYLOAD_REQUIREMENTS.get(document_type)
    if not required_fields:
        return payload

    missing_fields = sorted(field for field in required_fields if field not in payload)
    if missing_fields:
        missing_csv = ", ".join(missing_fields)
        raise ValueError(f"{document_type} payload is missing required fields: {missing_csv}")
    return payload


class WorkflowStepDefinition(Base):
    __tablename__ = "workflow_step_definitions"
    __table_args__ = (
        CheckConstraint("step_number >= 1", name="ck_workflow_step_definitions_step_number_positive"),
        UniqueConstraint("step_number", name="uq_workflow_step_definitions_step_number"),
    )

    id = Column(Integer, primary_key=True, index=True)
    step_number = Column(Integer, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    role_required = Column(String(64), nullable=True, index=True)
    required_form_type = Column(String(128), nullable=True, index=True)
    form_schema = Column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    financial_gate = Column(String(128), nullable=True, index=True)

    workflow_steps = relationship("WorkflowStep", back_populates="definition")
    actions = relationship(
        "StepAction",
        back_populates="step_definition",
        cascade="all, delete-orphan",
        order_by="StepAction.order_index",
    )


class StepAction(Base):
    __tablename__ = "step_actions"
    __table_args__ = (
        UniqueConstraint(
            "step_definition_id",
            "assigned_role",
            name="uq_step_actions_definition_role",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    step_definition_id = Column(
        Integer,
        ForeignKey("workflow_step_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assigned_role = Column(String(64), nullable=False, index=True)
    is_required = Column(Boolean, nullable=False, default=True)
    order_index = Column(Integer, nullable=False, default=0)

    step_definition = relationship("WorkflowStepDefinition", back_populates="actions")
    approval_tasks = relationship("ApprovalTask", back_populates="step_action")


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"
    __table_args__ = (
        CheckConstraint("phase_number BETWEEN 1 AND 4", name="ck_workflow_steps_phase_range"),
        UniqueConstraint("code", name="uq_workflow_steps_code"),
        UniqueConstraint("order_index", name="uq_workflow_steps_order_index"),
    )

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(64), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    phase_number = Column(Integer, nullable=False, index=True)
    order_index = Column(Integer, nullable=False, index=True)
    step_definition_id = Column(
        Integer,
        ForeignKey("workflow_step_definitions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    definition = relationship("WorkflowStepDefinition", back_populates="workflow_steps")
    current_projects = relationship(
        "CivilProject",
        back_populates="current_step",
        foreign_keys="CivilProject.current_step_id",
    )
    outgoing_transitions = relationship(
        "WorkflowTransition",
        back_populates="from_step",
        foreign_keys="WorkflowTransition.from_step_id",
        cascade="all, delete-orphan",
    )
    incoming_transitions = relationship(
        "WorkflowTransition",
        back_populates="to_step",
        foreign_keys="WorkflowTransition.to_step_id",
        cascade="all, delete-orphan",
    )
    documents = relationship("EntityDocument", back_populates="step")
    approval_tasks = relationship("ApprovalTask", back_populates="step")


class WorkflowTransition(Base):
    __tablename__ = "workflow_transitions"
    __table_args__ = (
        UniqueConstraint(
            "from_step_id",
            "to_step_id",
            "required_role",
            name="uq_workflow_transitions_route",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    from_step_id = Column(
        Integer,
        ForeignKey("workflow_steps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    to_step_id = Column(
        Integer,
        ForeignKey("workflow_steps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    required_role = Column(String(64), nullable=True, index=True)
    is_automatic = Column(Boolean, nullable=False, default=False)

    from_step = relationship(
        "WorkflowStep",
        back_populates="outgoing_transitions",
        foreign_keys=[from_step_id],
    )
    to_step = relationship(
        "WorkflowStep",
        back_populates="incoming_transitions",
        foreign_keys=[to_step_id],
    )


class CivilProject(Base):
    __tablename__ = "civil_projects"
    __table_args__ = (
        UniqueConstraint("project_code", name="civil_projects_project_code_key"),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_code = Column(String(64), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False, index=True)

    owning_org_unit_id = Column(
        Integer,
        ForeignKey("org_units.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    activity_id = Column(
        Integer,
        ForeignKey("activities.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    created_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    current_step_id = Column(
        Integer,
        ForeignKey("workflow_steps.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    planned_start_date = Column(Date, nullable=True)
    planned_end_date = Column(Date, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    owning_org_unit = relationship("OrgUnit", foreign_keys=[owning_org_unit_id], backref="civil_projects")
    activity = relationship("Activity", foreign_keys=[activity_id], backref="civil_projects")
    created_by = relationship("User", foreign_keys=[created_by_id], backref="civil_projects_created")
    current_step = relationship(
        "WorkflowStep",
        back_populates="current_projects",
        foreign_keys=[current_step_id],
    )
    assignments = relationship(
        "CivilProjectAssignment",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    contracts = relationship("Contract", back_populates="civil_project")
    credit_requests = relationship("CreditRequest", back_populates="civil_project")
    documents = relationship(
        "EntityDocument",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    approval_tasks = relationship(
        "ApprovalTask",
        back_populates="project",
        cascade="all, delete-orphan",
    )


class CivilProjectAssignment(Base):
    __tablename__ = "civil_project_assignments"
    __table_args__ = (
        CheckConstraint(
            "assigned_at IS NOT NULL",
            name="ck_civil_project_assignments_assigned_at_not_null",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("civil_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(
        SAEnum(CivilProjectRole, name="civil_project_role"),
        nullable=False,
        index=True,
    )
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    project = relationship("CivilProject", back_populates="assignments")
    user = relationship("User", backref="civil_project_assignments")


class EntityDocument(Base):
    __tablename__ = "entity_documents"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("civil_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_id = Column(
        Integer,
        ForeignKey("workflow_steps.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    document_type = Column(String(128), nullable=False, index=True)
    payload = Column(
        MutableDict.as_mutable(JSONB().with_variant(JSON(), "sqlite")),
        nullable=False,
        default=dict,
    )
    file_path = Column(String(1024), nullable=True)
    created_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    @validates("document_type")
    def validate_document_type(self, _key: str, value: str) -> str:
        validate_document_payload(value, self.payload)
        return value

    @validates("payload")
    def validate_payload(self, _key: str, value: dict) -> dict:
        validate_document_payload(self.document_type, value)
        return value

    project = relationship("CivilProject", back_populates="documents")
    step = relationship("WorkflowStep", back_populates="documents")
    created_by = relationship("User", foreign_keys=[created_by_id], backref="entity_documents_created")
    approval_tasks = relationship("ApprovalTask", back_populates="document")


class ApprovalTask(Base):
    __tablename__ = "approval_tasks"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("civil_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_id = Column(
        Integer,
        ForeignKey("workflow_steps.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    document_id = Column(
        Integer,
        ForeignKey("entity_documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    step_action_id = Column(
        Integer,
        ForeignKey("step_actions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    assigned_role = Column(String(64), nullable=False, index=True)
    assigned_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status = Column(
        SAEnum(ApprovalTaskStatus, name="approval_task_status"),
        nullable=False,
        default=ApprovalTaskStatus.PENDING,
        index=True,
    )
    is_required = Column(Boolean, nullable=False, default=True)
    comments = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    project = relationship("CivilProject", back_populates="approval_tasks")
    step = relationship("WorkflowStep", back_populates="approval_tasks")
    document = relationship("EntityDocument", back_populates="approval_tasks")
    step_action = relationship("StepAction", back_populates="approval_tasks")
    assigned_user = relationship("User", foreign_keys=[assigned_user_id], backref="approval_tasks")


__all__ = [
    "ApprovalTask",
    "ApprovalTaskStatus",
    "CivilProject",
    "CivilProjectAssignment",
    "CivilProjectRole",
    "DOCUMENT_PAYLOAD_REQUIREMENTS",
    "EntityDocument",
    "StepAction",
    "WorkflowStep",
    "WorkflowStepDefinition",
    "WorkflowTransition",
    "validate_document_payload",
]
