from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    Activity,
    ApprovalTask,
    ApprovalTaskStatus,
    BudgetItem,
    CivilProjectAssignment,
    CivilProject,
    EntityDocument,
    FinancialMatrix,
    FinancialRule,
    OrgUnit,
    Transaction,
    User,
    WorkflowStep,
    WorkflowStepDefinition,
    WorkflowTransition,
)
from app.core.security import verify_password
from app.services.civil_financial_bridge import CivilFinancialBridgeService
from app.services.civil_workflow import CivilWorkflowService, DocumentGeneratorService
from app.services.yekta_codes import build_yekta_segments


def _session():
    engine = create_engine("sqlite:///:memory:")
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def test_transaction_created_gate_creates_pending_treasury_transaction():
    db = _session()
    try:
        org_unit = OrgUnit(title="Civil Unit", code="CIV", org_type="UNIT")
        db.add(org_unit)
        db.flush()

        activity = Activity(name="Civil execution", org_unit_id=org_unit.id)
        budget_item = BudgetItem(budget_code="BL-100", description="Civil budget")
        db.add_all([activity, budget_item])
        db.flush()

        db.add(
            FinancialRule(
                activity_id=activity.id,
                cost_center_code="CC-100",
                budget_line_code=budget_item.budget_code,
                financial_event_type="CIVIL_PROGRESS_PAYMENT",
                is_active=True,
            )
        )

        step33 = WorkflowStep(
            code="STEP_33",
            name="Progress Statement",
            phase_number=3,
            order_index=33,
        )
        db.add(step33)
        db.flush()

        project = CivilProject(
            project_code="CIV-001",
            title="Demo civil project",
            owning_org_unit_id=org_unit.id,
            activity_id=activity.id,
            current_step_id=step33.id,
        )
        db.add(project)
        db.flush()

        db.add(
            EntityDocument(
                project_id=project.id,
                step_id=step33.id,
                document_type="PROGRESS_STATEMENT",
                payload={
                    "gross_amount": "1,000",
                    "contractor_name": "Demo Contractor",
                    "contract_number": "CON-001",
                },
            )
        )
        db.commit()

        transaction = CivilFinancialBridgeService().trigger_financial_gate(
            project.id,
            "TRANSACTION_CREATED",
            db,
        )

        assert transaction.status == "PENDING_TREASURY"
        assert transaction.amount == 850
        assert transaction.activity_id == activity.id
        assert transaction.zone_id == org_unit.id
        assert transaction.budget_item_id == budget_item.id
        assert transaction.beneficiary_name == "Demo Contractor"
        assert transaction.unique_code is None
        assert transaction.form_data["financial_gate"] == "TRANSACTION_CREATED"
    finally:
        db.close()


def test_advance_project_triggers_transaction_created_gate_once():
    db = _session()
    try:
        org_unit = OrgUnit(title="Civil Unit", code="CIV", org_type="UNIT")
        db.add(org_unit)
        db.flush()

        activity = Activity(name="Civil execution", org_unit_id=org_unit.id)
        db.add(activity)
        db.flush()

        step32_definition = WorkflowStepDefinition(
            step_number=32,
            name="Regional Financial Data",
            role_required="FINANCE_MANAGER",
            required_form_type=None,
        )
        step33_definition = WorkflowStepDefinition(
            step_number=33,
            name="Progress Statement",
            role_required="FINANCE_MANAGER",
            required_form_type="PROGRESS_STATEMENT",
            financial_gate="TRANSACTION_CREATED",
        )
        db.add_all([step32_definition, step33_definition])
        db.flush()

        step32 = WorkflowStep(
            code="STEP_32",
            name=step32_definition.name,
            phase_number=3,
            order_index=32,
            step_definition_id=step32_definition.id,
        )
        step33 = WorkflowStep(
            code="STEP_33",
            name=step33_definition.name,
            phase_number=3,
            order_index=33,
            step_definition_id=step33_definition.id,
        )
        db.add_all([step32, step33])
        db.flush()

        db.add(
            WorkflowTransition(
                from_step_id=step32.id,
                to_step_id=step33.id,
                required_role="FINANCE_MANAGER",
            )
        )

        project = CivilProject(
            project_code="CIV-002",
            title="Demo civil project",
            owning_org_unit_id=org_unit.id,
            activity_id=activity.id,
            current_step_id=step32.id,
        )
        db.add(project)
        db.flush()

        db.add(
            EntityDocument(
                project_id=project.id,
                step_id=step33.id,
                document_type="PROGRESS_STATEMENT",
                payload={"gross_amount": 2000},
            )
        )
        db.commit()

        CivilWorkflowService(db).advance_project(project.id, "FINANCE_MANAGER")
        CivilFinancialBridgeService().trigger_financial_gate(
            project.id,
            "TRANSACTION_CREATED",
            db,
        )

        transactions = db.query(Transaction).all()
        assert len(transactions) == 1
        assert transactions[0].amount == 1700
        assert transactions[0].status == "PENDING_TREASURY"
    finally:
        db.close()


def test_contractor_assignment_transition_provisions_user_and_links_project(capsys):
    db = _session()
    try:
        org_unit = OrgUnit(title="Civil Unit", code="CIV", org_type="UNIT")
        db.add(org_unit)
        db.flush()

        activity = Activity(name="Civil execution", org_unit_id=org_unit.id)
        db.add(activity)
        db.flush()

        step15_definition = WorkflowStepDefinition(
            step_number=15,
            name="Commission winner selection",
            role_required="TENDERING_OFFICER",
            required_form_type="CONTRACTOR_ASSIGNMENT",
        )
        step16_definition = WorkflowStepDefinition(
            step_number=16,
            name="Winning contractor invitation",
            role_required="CONTRACTS_OFFICER",
            required_form_type=None,
        )
        db.add_all([step15_definition, step16_definition])
        db.flush()

        step15 = WorkflowStep(
            code="STEP_15",
            name=step15_definition.name,
            phase_number=2,
            order_index=15,
            step_definition_id=step15_definition.id,
        )
        step16 = WorkflowStep(
            code="STEP_16",
            name=step16_definition.name,
            phase_number=2,
            order_index=16,
            step_definition_id=step16_definition.id,
        )
        db.add_all([step15, step16])
        db.flush()

        db.add(
            WorkflowTransition(
                from_step_id=step15.id,
                to_step_id=step16.id,
                required_role="TENDERING_OFFICER",
            )
        )

        project = CivilProject(
            project_code="CIV-003",
            title="Contractor assignment demo",
            owning_org_unit_id=org_unit.id,
            activity_id=activity.id,
            current_step_id=step15.id,
        )
        db.add(project)
        db.flush()

        db.add(
            EntityDocument(
                project_id=project.id,
                step_id=step15.id,
                document_type="CONTRACTOR_ASSIGNMENT",
                payload={
                    "contractor_name": "Demo Contractor",
                    "national_id": "1234567890",
                    "phone_number": "09120000000",
                    "winning_bid": 100000000,
                    "contract_coefficient": 1.12,
                },
            )
        )
        db.commit()

        CivilWorkflowService(db).advance_project(project.id, "TENDERING_OFFICER")

        contractor = db.query(User).filter(User.username == "1234567890").one()
        db.refresh(project)
        assignment = (
            db.query(CivilProjectAssignment)
            .filter(
                CivilProjectAssignment.project_id == project.id,
                CivilProjectAssignment.user_id == contractor.id,
            )
            .one()
        )

        assert contractor.role == "CONTRACTOR"
        assert contractor.full_name == "Demo Contractor"
        assert verify_password(
            capsys.readouterr().out.split("Password: ", 1)[1].strip(),
            contractor.hashed_password,
        )
        assert project.contractor_id == contractor.id
        assert assignment.is_active is True
    finally:
        db.close()


@pytest.mark.skip(reason="legacy pre-restoration 10-step volume-contract flow")
def test_volume_contract_step_105_approval_generates_multi_event_yekta_matrix():
    db = _session()
    try:
        org_unit = OrgUnit(title="Volume Contracts Unit", code="VOL", org_type="UNIT")
        db.add(org_unit)
        db.flush()

        activity = Activity(name="Cleaning Services", org_unit_id=org_unit.id)
        db.add(activity)
        db.flush()

        step101_definition = WorkflowStepDefinition(
            step_number=101,
            name="Volume Contract Base",
            role_required="HR_ADMIN",
            required_form_type="VOLUME_CONTRACT_BASE",
        )
        step103_definition = WorkflowStepDefinition(
            step_number=103,
            name="Financial Matrix Link",
            role_required="FINANCE_MANAGER",
            required_form_type="FINANCIAL_MATRIX_LINK",
        )
        step104_definition = WorkflowStepDefinition(
            step_number=104,
            name="Financial Matrix Confirmation",
            role_required="YEKTA_ADMIN",
            required_form_type="YEKTA_CODE_ISSUANCE",
        )
        step105_definition = WorkflowStepDefinition(
            step_number=105,
            name="Contractor Statement Upload",
            role_required="CONTRACTOR",
            required_form_type="APPENDIX_5_TIMESHEET",
        )
        step106_definition = WorkflowStepDefinition(
            step_number=106,
            name="Auto Statement Calculation",
            role_required="FINANCE_OFFICER",
            required_form_type="AUTO_STATEMENT_CALCULATION",
        )
        db.add_all([
            step101_definition,
            step103_definition,
            step104_definition,
            step105_definition,
            step106_definition,
        ])
        db.flush()

        step101 = WorkflowStep(
            code="VOL_STEP_101",
            name=step101_definition.name,
            phase_number=1,
            order_index=101,
            step_definition_id=step101_definition.id,
        )
        step103 = WorkflowStep(
            code="VOL_STEP_103",
            name=step103_definition.name,
            phase_number=1,
            order_index=103,
            step_definition_id=step103_definition.id,
        )
        step104 = WorkflowStep(
            code="VOL_STEP_104",
            name=step104_definition.name,
            phase_number=2,
            order_index=104,
            step_definition_id=step104_definition.id,
        )
        step105 = WorkflowStep(
            code="VOL_STEP_105",
            name=step105_definition.name,
            phase_number=2,
            order_index=105,
            step_definition_id=step105_definition.id,
        )
        step106 = WorkflowStep(
            code="VOL_STEP_106",
            name=step106_definition.name,
            phase_number=2,
            order_index=106,
            step_definition_id=step106_definition.id,
        )
        db.add_all([step101, step103, step104, step105, step106])
        db.flush()

        db.add_all(
            [
                WorkflowTransition(
                    from_step_id=step104.id,
                    to_step_id=step105.id,
                    required_role="YEKTA_ADMIN",
                ),
                WorkflowTransition(
                    from_step_id=step105.id,
                    to_step_id=step106.id,
                    required_role="CONTRACTOR",
                ),
            ]
        )

        project = CivilProject(
            project_code="VOL-001",
            title="Cleaning Services",
            contract_category="نظافت و پذیرایی",
            owning_org_unit_id=org_unit.id,
            activity_id=activity.id,
            current_step_id=step105.id,
        )
        db.add(project)
        db.flush()

        db.add_all(
            [
                EntityDocument(
                    project_id=project.id,
                    step_id=step101.id,
                    document_type="VOLUME_CONTRACT_BASE",
                    payload={
                        "contract_title": "Cleaning Services",
                        "contractor_name": "Demo Contractor",
                        "total_amount": 1000000,
                        "start_date": "2026-01-01",
                        "end_date": "2026-12-31",
                    },
                ),
                EntityDocument(
                    project_id=project.id,
                    step_id=step103.id,
                    document_type="FINANCIAL_MATRIX_LINK",
                    payload={
                        "budget_line_level_5": "BL5-001",
                        "cost_center": "CC-001",
                    },
                ),
                EntityDocument(
                    project_id=project.id,
                    step_id=step105.id,
                    document_type="APPENDIX_5_TIMESHEET",
                    payload={
                        "statement_number": "ST-1405-02-001",
                        "work_period": "1405-02",
                        "gross_amount": 1000000,
                        "statement_file": {
                            "file_name": "statement.pdf",
                            "file_url": "/uploads/volume_contracts/statement.pdf",
                        },
                        "attendance_18_column_file": {
                            "file_name": "attendance.xlsx",
                            "file_url": "/uploads/volume_contracts/attendance.xlsx",
                        },
                        "statement_6_column_file": {
                            "file_name": "statement6.xlsx",
                            "file_url": "/uploads/volume_contracts/statement6.xlsx",
                        },
                    },
                ),
            ]
        )
        db.commit()

        statement_document = (
            db.query(EntityDocument)
            .filter(
                EntityDocument.project_id == project.id,
                EntityDocument.document_type == "APPENDIX_5_TIMESHEET",
            )
            .one()
        )
        db.add(
            ApprovalTask(
                project_id=project.id,
                step_id=step105.id,
                document_id=statement_document.id,
                assigned_role="YEKTA_ADMIN",
                status=ApprovalTaskStatus.APPROVED,
                is_required=True,
            )
        )
        db.commit()

        CivilWorkflowService(db).advance_project(project.id, "ADMIN")

        db.refresh(project)
        matrix_rows = (
            db.query(FinancialMatrix)
            .order_by(FinancialMatrix.event_sequence.asc())
            .all()
        )
        transactions = db.query(Transaction).order_by(Transaction.tracking_number.asc()).all()
        expected_gross_yekta_code = generate_financial_matrix_yekta_code(
            budget_line_level_5="BL5-001",
            cost_center="CC-001",
            financial_event="GROSS_STATEMENT",
            activity_name="Cleaning Services",
            sequence=1,
        )
        db.refresh(statement_document)

        assert project.current_step_id == step106.id
        assert project.yekta_code is None
        assert len(matrix_rows) == 10
        assert len(transactions) == 10
        assert matrix_rows[0].budget_line_level_5 == "BL5-001"
        assert matrix_rows[0].cost_center == "CC-001"
        assert matrix_rows[0].financial_event == "GROSS_STATEMENT"
        assert matrix_rows[0].activity_name == "Cleaning Services"
        assert int(matrix_rows[0].amount) == 1000000
        assert matrix_rows[0].yekta_code == expected_gross_yekta_code
        assert matrix_rows[-1].financial_event == "NET_PAYABLE"
        assert int(matrix_rows[-1].amount) == 800000
        assert all(row.yekta_code for row in matrix_rows)
        assert all(row.payment_queue_status == "READY_FOR_PAYMENT_QUEUE" for row in matrix_rows)
        assert {transaction.unique_code for transaction in transactions} == {
            row.yekta_code for row in matrix_rows
        }
        assert len(statement_document.payload["financial_matrix_rows"]) == 10
    finally:
        db.close()


def test_appendix_5_salary_analysis_requires_numeric_values():
    db = _session()
    try:
        org_unit = OrgUnit(title="Volume Contracts Unit", code="VOL", org_type="UNIT")
        db.add(org_unit)
        db.flush()

        activity = Activity(name="Cleaning Services", org_unit_id=org_unit.id)
        db.add(activity)
        db.flush()

        step102 = WorkflowStep(
            code="VOL_STEP_102",
            name="Appendix 5 Salary Analysis",
            phase_number=1,
            order_index=102,
        )
        db.add(step102)
        db.flush()

        project = CivilProject(
            project_code="VOL-APP-005",
            title="Appendix 5 validation",
            contract_category="نظافت و پذیرایی",
            owning_org_unit_id=org_unit.id,
            activity_id=activity.id,
            current_step_id=step102.id,
        )
        db.add(project)
        db.flush()

        with pytest.raises(ValueError, match="APPENDIX_5_SALARY_ANALYSIS fields must be numeric"):
            DocumentGeneratorService().create_document(
                db,
                project_id=project.id,
                step_id=step102.id,
                document_type="APPENDIX_5_SALARY_ANALYSIS",
                payload={
                    "base_salary": "1000000",
                    "housing_allowance": 100000,
                    "grocery_allowance": 100000,
                    "child_family_allowance": 100000,
                    "overtime_rate": 100000,
                    "employer_insurance_premium": 100000,
                },
            )
    finally:
        db.close()


def _volume_yekta_payload(org_unit: OrgUnit, **overrides) -> dict:
    payload = {
        "zone_id": org_unit.id,
        "department_id": org_unit.id,
        "section_id": org_unit.id,
        "budget_item_id": None,
        "budget_code": "21030501",
        "cost_center_code": "501",
        "continuous_activity_code": "12",
        "special_activity": "Cleaning Services",
        "beneficiary_name": "Demo Contractor",
        "financial_event_defaults": {
            "GROSS_STATEMENT": "104",
            "VALUE_ADDED_TAX": "110",
            "TAX_WITHHOLDING": "120",
            "EMPLOYEE_INSURANCE": "130",
            "EMPLOYER_INSURANCE": "131",
            "SOCIAL_SECURITY_DEPOSIT": "132",
            "RETENTION_GUARANTEE": "140",
            "PERFORMANCE_GUARANTEE": "141",
            "OTHER_DEDUCTIONS": "199",
            "NET_PAYABLE": "150",
        },
        "event_overrides": [],
        "fiscal_year": "1405",
    }
    payload.update(overrides)
    return payload


def _volume_four_step_fixture(db):
    org_unit = OrgUnit(title="Volume Contracts Unit", code="05", org_type="UNIT")
    db.add(org_unit)
    db.flush()

    activity = Activity(name="Cleaning Services", org_unit_id=org_unit.id)
    budget_item = BudgetItem(budget_code="21030501", description="Cleaning budget")
    db.add_all([activity, budget_item])
    db.flush()

    definitions = [
        WorkflowStepDefinition(
            step_number=101,
            name="HR Initialization",
            role_required="HR_ADMIN",
            required_form_type="VOLUME_CONTRACT_BASE",
        ),
        WorkflowStepDefinition(
            step_number=102,
            name="Contractor Upload",
            role_required="CONTRACTOR",
            required_form_type="CONTRACTOR_STATEMENT_UPLOAD",
        ),
        WorkflowStepDefinition(
            step_number=103,
            name="Bahadori Yekta Sub-Process",
            role_required="YEKTA_ADMIN",
            required_form_type="YEKTA_CODE_ISSUANCE",
        ),
        WorkflowStepDefinition(
            step_number=104,
            name="Automated Matrix/Yekta Generation",
            role_required="FINANCE_MANAGER",
            required_form_type="AUTO_STATEMENT_CALCULATION",
        ),
    ]
    db.add_all(definitions)
    db.flush()

    steps = [
        WorkflowStep(
            code="VOL_NEW_STEP_101",
            name=definitions[0].name,
            phase_number=1,
            order_index=101,
            step_definition_id=definitions[0].id,
        ),
        WorkflowStep(
            code="VOL_NEW_STEP_102",
            name=definitions[1].name,
            phase_number=2,
            order_index=102,
            step_definition_id=definitions[1].id,
        ),
        WorkflowStep(
            code="VOL_NEW_STEP_103",
            name=definitions[2].name,
            phase_number=3,
            order_index=103,
            step_definition_id=definitions[2].id,
        ),
        WorkflowStep(
            code="VOL_NEW_STEP_104",
            name=definitions[3].name,
            phase_number=4,
            order_index=104,
            step_definition_id=definitions[3].id,
        ),
    ]
    db.add_all(steps)
    db.flush()

    db.add_all(
        [
            WorkflowTransition(from_step_id=steps[1].id, to_step_id=steps[2].id, required_role="CONTRACTOR"),
            WorkflowTransition(from_step_id=steps[2].id, to_step_id=steps[3].id, required_role="YEKTA_ADMIN"),
        ]
    )

    project = CivilProject(
        project_code="VOL-RESTORED-001",
        title="Cleaning Services",
        contract_category="Cleaning",
        owning_org_unit_id=org_unit.id,
        activity_id=activity.id,
        current_step_id=steps[2].id,
    )
    db.add(project)
    db.flush()

    statement_document = EntityDocument(
        project_id=project.id,
        step_id=steps[1].id,
        document_type="CONTRACTOR_STATEMENT_UPLOAD",
        payload={
            "statement_number": "ST-1405-02-001",
            "work_period": "1405-02",
            "statement_total_amount": 1000000,
            "statement_file": {
                "file_name": "statement.pdf",
                "file_url": "/uploads/volume_contracts/statement.pdf",
            },
            "statement_6_column_file": {
                "file_name": "statement6.xlsx",
                "file_url": "/uploads/volume_contracts/statement6.xlsx",
            },
            "vat_invoice_files": [
                {"file_name": "vat.pdf", "file_url": "/uploads/volume_contracts/vat.pdf"}
            ],
        },
    )
    db.add_all(
        [
            EntityDocument(
                project_id=project.id,
                step_id=steps[0].id,
                document_type="VOLUME_CONTRACT_BASE",
                payload={
                    "contract_title": "Cleaning Services",
                    "contractor_name": "Demo Contractor",
                    "total_amount": 1000000,
                    "start_date": "2026-01-01",
                    "end_date": "2026-12-31",
                },
            ),
            statement_document,
        ]
    )
    db.commit()
    return org_unit, project, statement_document, steps[2], steps[3]


def test_volume_contract_step_103_yekta_payload_generates_multi_event_yekta_matrix():
    db = _session()
    try:
        org_unit, project, statement_document, step103, step104 = _volume_four_step_fixture(db)
        db.add(
            EntityDocument(
                project_id=project.id,
                step_id=step103.id,
                document_type="YEKTA_CODE_ISSUANCE",
                payload=_volume_yekta_payload(org_unit),
            )
        )
        db.commit()

        CivilWorkflowService(db).advance_project(project.id, "YEKTA_ADMIN")

        db.refresh(project)
        matrix_rows = db.query(FinancialMatrix).order_by(FinancialMatrix.event_sequence.asc()).all()
        transactions = db.query(Transaction).order_by(Transaction.tracking_number.asc()).all()
        expected_gross_yekta_code = build_yekta_segments(
            zone_code="05",
            department_code="05",
            section_code="05",
            budget_code="21030501",
            cost_center_code="501",
            continuous_action_code="12",
            special_activity="Cleaning Services",
            beneficiary_name="Demo Contractor",
            financial_event_code="104",
            fiscal_year="1405",
            sequence=1,
        ).code()
        db.refresh(statement_document)

        assert project.current_step_id == step104.id
        assert project.yekta_code is None
        assert len(matrix_rows) == 10
        assert len(transactions) == 10
        assert matrix_rows[0].budget_line_level_5 == "21030501"
        assert matrix_rows[0].cost_center == "501"
        assert matrix_rows[0].financial_event == "GROSS_STATEMENT"
        assert matrix_rows[0].activity_name == "Cleaning Services"
        assert int(matrix_rows[0].amount) == 1000000
        assert matrix_rows[0].yekta_code == expected_gross_yekta_code
        assert matrix_rows[-1].financial_event == "NET_PAYABLE"
        assert int(matrix_rows[-1].amount) == 800000
        assert all(row.yekta_code for row in matrix_rows)
        assert all(row.payment_queue_status == "READY_FOR_PAYMENT_QUEUE" for row in matrix_rows)
        assert all(transaction.status == "READY_FOR_PAYMENT_QUEUE" for transaction in transactions)
        assert {transaction.unique_code for transaction in transactions} == {row.yekta_code for row in matrix_rows}
        assert matrix_rows[0].source_payload["yekta_payload"]["financial_event_code"] == "104"
        assert transactions[0].form_data["yekta_payload"]["budget_code"] == "21030501"
        assert len(statement_document.payload["financial_matrix_rows"]) == 10
    finally:
        db.close()


def test_volume_contract_step_103_requires_submitted_yekta_payload():
    db = _session()
    try:
        _org_unit, project, _statement_document, _step103, _step104 = _volume_four_step_fixture(db)
        with pytest.raises(ValueError, match="Step 103 Yekta sub-process payload is required"):
            CivilWorkflowService(db).advance_project(project.id, "YEKTA_ADMIN")
    finally:
        db.close()


def test_volume_contract_yekta_event_override_changes_only_one_event_segment():
    db = _session()
    try:
        org_unit, project, _statement_document, step103, _step104 = _volume_four_step_fixture(db)
        payload = _volume_yekta_payload(
            org_unit,
            event_overrides=[
                {"event_code": "VALUE_ADDED_TAX", "financial_event_code": "777"}
            ],
        )
        db.add(
            EntityDocument(
                project_id=project.id,
                step_id=step103.id,
                document_type="YEKTA_CODE_ISSUANCE",
                payload=payload,
            )
        )
        db.commit()

        CivilWorkflowService(db).advance_project(project.id, "YEKTA_ADMIN")
        rows = {row.financial_event: row for row in db.query(FinancialMatrix).all()}

        assert rows["VALUE_ADDED_TAX"].yekta_code.split("-")[8] == "777"
        assert rows["GROSS_STATEMENT"].yekta_code.split("-")[8] == "104"
        assert rows["NET_PAYABLE"].yekta_code.split("-")[8] == "150"
    finally:
        db.close()


def test_yekta_issuance_rejects_ui_supplied_sequence():
    db = _session()
    try:
        org_unit, project, _statement_document, step103, _step104 = _volume_four_step_fixture(db)
        with pytest.raises(ValueError, match="system-generated sequence"):
            DocumentGeneratorService().create_document(
                db,
                project_id=project.id,
                step_id=step103.id,
                document_type="YEKTA_CODE_ISSUANCE",
                payload=_volume_yekta_payload(org_unit, sequence="999"),
            )
    finally:
        db.close()


def test_volume_contract_statement_upload_does_not_require_18_column_attendance():
    db = _session()
    try:
        org_unit = OrgUnit(title="Volume Contracts Unit", code="05", org_type="UNIT")
        db.add(org_unit)
        db.flush()
        activity = Activity(name="Cleaning Services", org_unit_id=org_unit.id)
        db.add(activity)
        db.flush()
        step102 = WorkflowStep(code="VOL_UPLOAD_STEP_102", name="Contractor Upload", phase_number=2, order_index=102)
        db.add(step102)
        db.flush()
        project = CivilProject(
            project_code="VOL-UPLOAD-001",
            title="Upload validation",
            contract_category="Cleaning",
            owning_org_unit_id=org_unit.id,
            activity_id=activity.id,
            current_step_id=step102.id,
        )
        db.add(project)
        db.flush()

        document = DocumentGeneratorService().create_document(
            db,
            project_id=project.id,
            step_id=step102.id,
            document_type="CONTRACTOR_STATEMENT_UPLOAD",
            payload={
                "statement_number": "ST-1",
                "work_period": "1405-02",
                "statement_file": {"file_name": "statement.pdf", "file_url": "/uploads/statement.pdf"},
                "statement_6_column_file": {"file_name": "statement.xlsx", "file_url": "/uploads/statement.xlsx"},
                "vat_invoice_files": [{"file_name": "vat.pdf", "file_url": "/uploads/vat.pdf"}],
            },
        )

        assert document.document_type == "CONTRACTOR_STATEMENT_UPLOAD"
        assert "attendance_18_column_file" not in document.payload
    finally:
        db.close()


def test_volume_contract_statement_yekta_generation_requires_yekta_payload_data():
    db = _session()
    try:
        org_unit, project, _statement_document, step103, _step104 = _volume_four_step_fixture(db)
        payload = _volume_yekta_payload(org_unit, cost_center_code="")
        DocumentGeneratorService().create_document(
            db,
            project_id=project.id,
            step_id=step103.id,
            document_type="YEKTA_CODE_ISSUANCE",
            payload=payload,
        )
        db.commit()
        with pytest.raises(ValueError, match="missing required fields: cost_center_code"):
            CivilWorkflowService(db).advance_project(project.id, "YEKTA_ADMIN")
    finally:
        db.close()


@pytest.mark.skip(reason="legacy pre-restoration FINANCIAL_MATRIX_LINK flow")
def test_volume_contract_statement_yekta_generation_requires_matrix_data():
    db = _session()
    try:
        org_unit = OrgUnit(title="Volume Contracts Unit", code="VOL", org_type="UNIT")
        db.add(org_unit)
        db.flush()

        activity = Activity(name="Cleaning Services", org_unit_id=org_unit.id)
        db.add(activity)
        db.flush()

        step101_definition = WorkflowStepDefinition(
            step_number=101,
            name="Volume Contract Base",
            role_required="HR_ADMIN",
            required_form_type="VOLUME_CONTRACT_BASE",
        )
        step103_definition = WorkflowStepDefinition(
            step_number=103,
            name="Financial Matrix Link",
            role_required="FINANCE_MANAGER",
            required_form_type="FINANCIAL_MATRIX_LINK",
        )
        step104_definition = WorkflowStepDefinition(
            step_number=104,
            name="Financial Matrix Confirmation",
            role_required="YEKTA_ADMIN",
            required_form_type="YEKTA_CODE_ISSUANCE",
        )
        step105_definition = WorkflowStepDefinition(
            step_number=105,
            name="Contractor Statement Upload",
            role_required="CONTRACTOR",
            required_form_type="APPENDIX_5_TIMESHEET",
        )
        step106_definition = WorkflowStepDefinition(
            step_number=106,
            name="Auto Statement Calculation",
            role_required="FINANCE_OFFICER",
            required_form_type="AUTO_STATEMENT_CALCULATION",
        )
        db.add_all([
            step101_definition,
            step103_definition,
            step104_definition,
            step105_definition,
            step106_definition,
        ])
        db.flush()

        step101 = WorkflowStep(
            code="VOL_MISSING_STEP_101",
            name=step101_definition.name,
            phase_number=1,
            order_index=101,
            step_definition_id=step101_definition.id,
        )
        step103 = WorkflowStep(
            code="VOL_MISSING_STEP_103",
            name=step103_definition.name,
            phase_number=1,
            order_index=103,
            step_definition_id=step103_definition.id,
        )
        step104 = WorkflowStep(
            code="VOL_MISSING_STEP_104",
            name=step104_definition.name,
            phase_number=2,
            order_index=104,
            step_definition_id=step104_definition.id,
        )
        step105 = WorkflowStep(
            code="VOL_MISSING_STEP_105",
            name=step105_definition.name,
            phase_number=2,
            order_index=105,
            step_definition_id=step105_definition.id,
        )
        step106 = WorkflowStep(
            code="VOL_MISSING_STEP_106",
            name=step106_definition.name,
            phase_number=2,
            order_index=106,
            step_definition_id=step106_definition.id,
        )
        db.add_all([step101, step103, step104, step105, step106])
        db.flush()

        db.add_all(
            [
                WorkflowTransition(
                    from_step_id=step104.id,
                    to_step_id=step105.id,
                    required_role="YEKTA_ADMIN",
                ),
                WorkflowTransition(
                    from_step_id=step105.id,
                    to_step_id=step106.id,
                    required_role="CONTRACTOR",
                ),
            ]
        )

        project = CivilProject(
            project_code="VOL-MISSING-001",
            title="Missing matrix data",
            contract_category="نظافت و پذیرایی",
            owning_org_unit_id=org_unit.id,
            activity_id=activity.id,
            current_step_id=step105.id,
        )
        db.add(project)
        db.flush()

        db.add_all(
            [
                EntityDocument(
                    project_id=project.id,
                    step_id=step101.id,
                    document_type="VOLUME_CONTRACT_BASE",
                    payload={
                        "contract_title": "Missing matrix data",
                        "contractor_name": "Demo Contractor",
                        "total_amount": 1000000,
                        "start_date": "2026-01-01",
                        "end_date": "2026-12-31",
                    },
                ),
                EntityDocument(
                    project_id=project.id,
                    step_id=step103.id,
                    document_type="FINANCIAL_MATRIX_LINK",
                    payload={
                        "budget_line_level_5": "BL5-001",
                        "cost_center": "",
                    },
                ),
                EntityDocument(
                    project_id=project.id,
                    step_id=step105.id,
                    document_type="APPENDIX_5_TIMESHEET",
                    payload={
                        "statement_number": "ST-1405-02-002",
                        "work_period": "1405-02",
                        "gross_amount": 1000000,
                        "statement_file": {
                            "file_name": "statement.pdf",
                            "file_url": "/uploads/volume_contracts/statement.pdf",
                        },
                        "attendance_18_column_file": {
                            "file_name": "attendance.xlsx",
                            "file_url": "/uploads/volume_contracts/attendance.xlsx",
                        },
                        "statement_6_column_file": {
                            "file_name": "statement6.xlsx",
                            "file_url": "/uploads/volume_contracts/statement6.xlsx",
                        },
                    },
                ),
            ]
        )
        db.commit()

        statement_document = (
            db.query(EntityDocument)
            .filter(
                EntityDocument.project_id == project.id,
                EntityDocument.document_type == "APPENDIX_5_TIMESHEET",
            )
            .one()
        )
        db.add(
            ApprovalTask(
                project_id=project.id,
                step_id=step105.id,
                document_id=statement_document.id,
                assigned_role="YEKTA_ADMIN",
                status=ApprovalTaskStatus.APPROVED,
                is_required=True,
            )
        )
        db.commit()

        with pytest.raises(ValueError, match="budget_line_level_5, cost_center, and contract title are required"):
            CivilWorkflowService(db).advance_project(project.id, "ADMIN")
    finally:
        db.close()


def test_advance_project_rejects_wrong_step_role():
    db = _session()
    try:
        org_unit = OrgUnit(title="Civil Unit", code="CIV", org_type="UNIT")
        db.add(org_unit)
        db.flush()

        activity = Activity(name="Civil execution", org_unit_id=org_unit.id)
        db.add(activity)
        db.flush()

        current_definition = WorkflowStepDefinition(
            step_number=2,
            name="Finance controlled step",
            role_required="FINANCE_MANAGER",
            required_form_type=None,
        )
        next_definition = WorkflowStepDefinition(
            step_number=3,
            name="Next step",
            role_required="CIVIL_MANAGER",
            required_form_type=None,
        )
        db.add_all([current_definition, next_definition])
        db.flush()

        current_step = WorkflowStep(
            code="STEP_02",
            name=current_definition.name,
            phase_number=1,
            order_index=2,
            step_definition_id=current_definition.id,
        )
        next_step = WorkflowStep(
            code="STEP_03",
            name=next_definition.name,
            phase_number=1,
            order_index=3,
            step_definition_id=next_definition.id,
        )
        db.add_all([current_step, next_step])
        db.flush()

        db.add(
            WorkflowTransition(
                from_step_id=current_step.id,
                to_step_id=next_step.id,
                required_role="FINANCE_MANAGER",
            )
        )

        project = CivilProject(
            project_code="CIV-004",
            title="RBAC demo",
            owning_org_unit_id=org_unit.id,
            activity_id=activity.id,
            current_step_id=current_step.id,
        )
        db.add(project)
        db.commit()

        service = CivilWorkflowService(db)
        assert service.user_can_execute_current_step(project, "CIVIL_MANAGER") is False
        assert service.user_can_execute_current_step(project, "FINANCE_MANAGER") is True

        with pytest.raises(PermissionError) as exc:
            service.advance_project(project.id, "CIVIL_MANAGER")

        assert str(exc.value) == "Access Denied: You do not have the required role to execute this step."
    finally:
        db.close()
