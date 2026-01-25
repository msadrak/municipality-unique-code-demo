"""
Accounting Posting Module - FastAPI Router

Provides endpoints for:
- GET /accounting/inbox - List transactions ready for posting
- GET /accounting/tx/{id}/journal-preview - Get frozen journal lines
- POST /accounting/tx/{id}/post - Post a transaction (idempotent)
- POST /accounting/export - Export selected transactions
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import update, and_, or_
from typing import Optional
from datetime import datetime, timedelta
import hashlib
import json
import io
import csv

from app.database import SessionLocal
from app.models import (
    Transaction, User, OrgUnit, AccountingStatus, AccountingEventType,
    JournalSnapshot, JournalLine, AccountingAuditLog
)
from app.schemas.accounting import (
    InboxFilters, InboxItem, InboxResponse,
    JournalPreviewResponse, JournalLineSchema,
    PostRequest, PostResponse, PostErrorResponse,
    BatchPostRequest, BatchPostResponse, BatchPostResult,
    ExportRequest, ValidationStatusEnum
)

router = APIRouter(prefix="/accounting", tags=["Accounting"])


# ============ DATABASE DEPENDENCY ============

def get_db():
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============ DEPENDENCIES ============

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Get current user from session. Must have admin or accountant role."""
    from app.routers.auth import get_current_user as auth_get_user
    user = auth_get_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="احراز هویت الزامی است")
    # Allow admin, ACCOUNTANT, and all admin levels
    allowed_roles = ["admin", "ACCOUNTANT", "ADMIN_L4", "ADMIN_L3", "ADMIN_L2", "ADMIN_L1", "inspector"]
    if user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail=f"دسترسی حسابداری ندارید (نقش: {user.role})")
    return user


# Note: display_id removed per data lineage spec. unique_code is the sole identifier.


# ============ GET /accounting/inbox ============

@router.get("/inbox", response_model=InboxResponse)
def get_inbox(
    request: Request,
    status: Optional[str] = Query("READY_TO_POST"),
    zone_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """List transactions ready for accounting posting."""
    user = get_current_user(request, db)
    
    # Base query: only APPROVED transactions with accounting data
    query = db.query(Transaction).filter(Transaction.status == "APPROVED")
    
    # Filter by accounting status
    if status and status != "ALL":
        if status == "READY_TO_POST":
            query = query.filter(
                or_(
                    Transaction.accounting_status == AccountingStatus.READY_TO_POST,
                    Transaction.accounting_status.is_(None)  # Not yet processed
                )
            )
        elif status == "POSTED":
            query = query.filter(Transaction.accounting_status == AccountingStatus.POSTED)
        elif status == "POST_ERROR":
            query = query.filter(Transaction.accounting_status == AccountingStatus.POST_ERROR)
    
    # Filter by zone
    if zone_id:
        query = query.filter(Transaction.zone_id == zone_id)
    
    # Filter by date range (approved_at via reviewed_at)
    if date_from:
        query = query.filter(Transaction.reviewed_at >= date_from)
    if date_to:
        query = query.filter(Transaction.reviewed_at <= date_to)
    
    # Search
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Transaction.unique_code.ilike(search_pattern),
                Transaction.beneficiary_name.ilike(search_pattern)
            )
        )
    
    # Count total
    total = query.count()
    
    # Paginate and fetch
    transactions = query.order_by(Transaction.reviewed_at.desc()).offset(offset).limit(limit).all()
    
    # Convert to response items
    items = []
    for tx in transactions:
        zone_title = ""
        if tx.zone_id:
            zone = db.query(OrgUnit).filter(OrgUnit.id == tx.zone_id).first()
            zone_title = zone.title if zone else ""
        
        # Determine accounting status
        acc_status = tx.accounting_status.value if tx.accounting_status else "READY_TO_POST"
        
        items.append(InboxItem(
            id=tx.id,
            unique_code=tx.unique_code or "",
            approved_at=tx.reviewed_at,
            beneficiary_name=tx.beneficiary_name or "",
            amount=tx.amount or 0,
            zone_title=zone_title,
            accounting_status=acc_status,
            validation_status=ValidationStatusEnum.VALID,  # TODO: Check journal snapshot
            warning_count=0,
            version=tx.version or 1
        ))
    
    return InboxResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset
    )


# ============ GET /accounting/tx/{id}/journal-preview ============

@router.get("/tx/{tx_id}/journal-preview", response_model=JournalPreviewResponse)
def get_journal_preview(
    tx_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Get frozen journal lines for a transaction."""
    user = get_current_user(request, db)
    
    # Get transaction
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="تراکنش یافت نشد")
    
    # Get or create journal snapshot
    snapshot = db.query(JournalSnapshot).filter(
        JournalSnapshot.transaction_id == tx_id
    ).first()
    
    if not snapshot:
        # Auto-create snapshot for approved transactions
        snapshot = _create_journal_snapshot(tx, db)
    
    # Get lines
    lines = db.query(JournalLine).filter(
        JournalLine.snapshot_id == snapshot.id
    ).order_by(JournalLine.line_sequence).all()
    
    line_schemas = [
        JournalLineSchema(
            sequence=line.line_sequence,
            account_code=line.account_code,
            account_name=line.account_name,
            account_type=line.account_type,
            debit_amount=line.debit_amount,
            credit_amount=line.credit_amount,
            cost_center_code=line.cost_center_code,
            budget_code=line.budget_code,
            line_description=line.line_description
        )
        for line in lines
    ]
    
    # Get section and subsystem names for context
    section_name = tx.section.title if tx.section else None
    subsystem_name = tx.subsystem.name if tx.subsystem else None
    
    return JournalPreviewResponse(
        transaction_id=tx.id,
        unique_code=tx.unique_code or "",
        snapshot_version=snapshot.snapshot_version,
        snapshot_at=snapshot.created_at,
        snapshot_hash=snapshot.snapshot_hash,
        lines=line_schemas,
        total_debit=snapshot.total_debit,
        total_credit=snapshot.total_credit,
        is_balanced=snapshot.is_balanced,
        validation_status=snapshot.validation_status or "VALID",
        validation_errors=snapshot.validation_errors_json or [],
        warnings=[],
        section_name=section_name,
        subsystem_name=subsystem_name
    )


def _create_journal_snapshot(tx: Transaction, db: Session) -> JournalSnapshot:
    """Create a journal snapshot for a transaction.
    
    Data lineage (per account_lineage_audit.md):
    - account_code for expense: tx.budget_item.budget_code
    - account_name for expense: tx.budget_item.description
    - source_budget_item_id: tx.budget_item.id (for audit trail)
    - bank account: hard-coded (TODO: make configurable)
    """
    lines_data = []
    amount_int = int((tx.amount or 0) * 1)  # Already in Rials
    validation_warnings = []
    
    # Validate transaction has budget_item
    has_budget_item = tx.budget_item is not None
    
    if not has_budget_item:
        validation_warnings.append("تراکنش فاقد ردیف بودجه است - از مقادیر پیش‌فرض استفاده شد")
    
    # Debit line (expense) - from BudgetItem
    expense_account_code = tx.budget_item.budget_code if has_budget_item else "00000000"
    expense_account_name = tx.budget_item.description if has_budget_item and tx.budget_item.description else "حساب هزینه (نامشخص)"
    expense_budget_item_id = tx.budget_item.id if has_budget_item else None
    
    if has_budget_item and not tx.budget_item.description:
        validation_warnings.append("شرح ردیف بودجه خالی است")
    
    lines_data.append({
        "sequence": 1,
        "account_code": expense_account_code,
        "account_name": expense_account_name,
        "account_type": "TEMPORARY",
        "debit_amount": amount_int,
        "credit_amount": 0,
        "budget_code": expense_account_code,
        "line_description": tx.description or f"پرداخت به {tx.beneficiary_name}",
        "source_budget_item_id": expense_budget_item_id
    })
    
    # Credit line (bank) - TODO: make configurable
    # Currently hard-coded per audit finding
    lines_data.append({
        "sequence": 2,
        "account_code": "21010100",  # Hard-coded bank account
        "account_name": "حساب بانکی",  # Hard-coded name
        "account_type": "BANK",
        "debit_amount": 0,
        "credit_amount": amount_int,
        "line_description": "واریز از حساب بانکی",
        "source_budget_item_id": None  # No source for bank account
    })
    
    # Calculate totals
    total_debit = sum(l["debit_amount"] for l in lines_data)
    total_credit = sum(l["credit_amount"] for l in lines_data)
    is_balanced = total_debit == total_credit
    
    # Determine validation status
    if not is_balanced:
        validation_status = "BLOCKED"
    elif validation_warnings:
        validation_status = "WARNING"
    else:
        validation_status = "VALID"
    
    # Generate hash
    hash_data = json.dumps(lines_data, sort_keys=True, ensure_ascii=False)
    snapshot_hash = hashlib.sha256(hash_data.encode()).hexdigest()
    
    # Create snapshot
    snapshot = JournalSnapshot(
        transaction_id=tx.id,
        unique_code=tx.unique_code,
        snapshot_version=1,
        snapshot_hash=snapshot_hash,
        total_debit=total_debit,
        total_credit=total_credit,
        is_balanced=is_balanced,
        line_count=len(lines_data),
        validation_status=validation_status,
        validation_errors_json=validation_warnings if validation_warnings else None
    )
    db.add(snapshot)
    db.flush()
    
    # Create lines
    for line_data in lines_data:
        line = JournalLine(
            snapshot_id=snapshot.id,
            line_sequence=line_data["sequence"],
            account_code=line_data["account_code"],
            account_name=line_data["account_name"],
            account_type=line_data["account_type"],
            debit_amount=line_data["debit_amount"],
            credit_amount=line_data["credit_amount"],
            budget_code=line_data.get("budget_code"),
            line_description=line_data.get("line_description"),
            source_budget_item_id=line_data.get("source_budget_item_id")
        )
        db.add(line)
    
    db.commit()
    return snapshot


# ============ POST /accounting/tx/{id}/post ============

@router.post("/tx/{tx_id}/post", response_model=PostResponse)
def post_transaction(
    tx_id: int,
    request: Request,
    post_request: PostRequest,
    db: Session = Depends(get_db)
):
    """Post a transaction (idempotent with optimistic locking)."""
    user = get_current_user(request, db)
    
    # Atomic update with version check
    result = db.execute(
        update(Transaction)
        .where(
            and_(
                Transaction.id == tx_id,
                or_(
                    Transaction.accounting_status == AccountingStatus.READY_TO_POST,
                    Transaction.accounting_status.is_(None)
                ),
                Transaction.version == post_request.version
            )
        )
        .values(
            accounting_status=AccountingStatus.POSTED,
            posted_at=datetime.utcnow(),
            posted_by_id=user.id,
            posting_ref=post_request.posting_ref,
            posting_notes=post_request.notes,
            version=Transaction.version + 1
        )
    )
    
    affected = result.rowcount
    
    if affected == 0:
        # Check why it failed
        tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
        
        if tx is None:
            raise HTTPException(status_code=404, detail="تراکنش یافت نشد")
        
        if tx.accounting_status == AccountingStatus.POSTED:
            if tx.posting_ref == post_request.posting_ref:
                # Idempotent: same ref, return success
                return PostResponse(
                    success=True,
                    transaction_id=tx.id,
                    unique_code=tx.unique_code or "",
                    accounting_status="POSTED",
                    posted_at=tx.posted_at,
                    posted_by=tx.posted_by.username if tx.posted_by else "",
                    posting_ref=tx.posting_ref,
                    new_version=tx.version,
                    message="قبلاً ثبت شده"
                )
            else:
                # Conflict: different ref
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "CONFLICT",
                        "message": "قبلاً با شماره متفاوتی ثبت شده",
                        "existing_ref": tx.posting_ref,
                        "requested_ref": post_request.posting_ref
                    }
                )
        
        if tx.version != post_request.version:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "VERSION_MISMATCH",
                    "message": "تراکنش توسط کاربر دیگری تغییر کرده",
                    "current_version": tx.version
                }
            )
        
        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_STATE",
                "message": f"وضعیت نامعتبر: {tx.accounting_status}"
            }
        )
    
    db.commit()
    
    # Fetch updated transaction
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    
    # Log audit event
    audit_log = AccountingAuditLog(
        event_type=AccountingEventType.POSTED,
        transaction_id=tx.id,
        actor_user_id=user.id,
        actor_username=user.username,
        posting_ref=post_request.posting_ref,
        before_status="READY_TO_POST",
        after_status="POSTED"
    )
    db.add(audit_log)
    db.commit()
    
    return PostResponse(
        success=True,
        transaction_id=tx.id,
        unique_code=tx.unique_code or "",
        accounting_status="POSTED",
        posted_at=tx.posted_at,
        posted_by=user.username,
        posting_ref=tx.posting_ref,
        new_version=tx.version
    )


# ============ POST /accounting/batch-post ============

@router.post("/batch-post", response_model=BatchPostResponse)
def batch_post_transactions(
    request: Request,
    batch_request: BatchPostRequest,
    db: Session = Depends(get_db)
):
    """Post multiple transactions in a batch."""
    user = get_current_user(request, db)
    
    results = []
    succeeded = 0
    failed = 0
    
    for item in batch_request.items:
        try:
            # Use single post logic
            post_req = PostRequest(
                posting_ref=item.posting_ref,
                notes=batch_request.notes,
                version=item.version
            )
            
            result = post_transaction(item.transaction_id, request, post_req, db)
            
            results.append(BatchPostResult(
                transaction_id=item.transaction_id,
                unique_code=result.unique_code,
                success=True,
                posting_ref=item.posting_ref,
                new_version=result.new_version
            ))
            succeeded += 1
            
        except HTTPException as e:
            detail = e.detail if isinstance(e.detail, dict) else {"message": str(e.detail)}
            tx = db.query(Transaction).filter(Transaction.id == item.transaction_id).first()
            
            results.append(BatchPostResult(
                transaction_id=item.transaction_id,
                unique_code=tx.unique_code if tx else "UNKNOWN",
                success=False,
                error=detail.get("error", "UNKNOWN"),
                error_message=detail.get("message", str(e.detail))
            ))
            failed += 1
    
    return BatchPostResponse(
        total_requested=len(batch_request.items),
        succeeded=succeeded,
        failed=failed,
        results=results
    )


# ============ POST /accounting/export ============

@router.post("/export")
def export_transactions(
    request: Request,
    export_request: ExportRequest,
    db: Session = Depends(get_db)
):
    """Export selected transactions as CSV or XLSX (synchronous)."""
    user = get_current_user(request, db)
    
    # Fetch transactions
    transactions = db.query(Transaction).filter(
        Transaction.id.in_(export_request.transaction_ids)
    ).all()
    
    if not transactions:
        raise HTTPException(status_code=404, detail="هیچ تراکنشی یافت نشد")
    
    # Update export tracking
    now = datetime.utcnow()
    for tx in transactions:
        tx.export_count = (tx.export_count or 0) + 1
        tx.last_exported_at = now
        tx.last_exported_by_id = user.id
    db.commit()
    
    # Log audit
    for tx in transactions:
        audit_log = AccountingAuditLog(
            event_type=AccountingEventType.EXPORTED,
            transaction_id=tx.id,
            actor_user_id=user.id,
            actor_username=user.username,
            export_id=f"EXP-{now.strftime('%Y%m%d%H%M%S')}"
        )
        db.add(audit_log)
    db.commit()
    
    # Generate CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    headers = [
        "ID", "Display ID", "Unique Code", "Beneficiary", "Amount",
        "Accounting Status", "Posted At", "Posting Ref", "Zone"
    ]
    if export_request.include_journal_lines:
        headers.extend(["Journal Lines"])
    writer.writerow(headers)
    
    # Data rows
    for tx in transactions:
        zone = db.query(OrgUnit).filter(OrgUnit.id == tx.zone_id).first()
        
        row = [
            tx.id,
            generate_display_id(tx),
            tx.unique_code or "",
            tx.beneficiary_name or "",
            tx.amount or 0,
            tx.accounting_status.value if tx.accounting_status else "",
            tx.posted_at.isoformat() if tx.posted_at else "",
            tx.posting_ref or "",
            zone.title if zone else ""
        ]
        
        if export_request.include_journal_lines:
            snapshot = db.query(JournalSnapshot).filter(
                JournalSnapshot.transaction_id == tx.id
            ).first()
            if snapshot:
                lines = db.query(JournalLine).filter(
                    JournalLine.snapshot_id == snapshot.id
                ).all()
                journal_text = "; ".join([
                    f"{l.account_code}: D{l.debit_amount}/C{l.credit_amount}"
                    for l in lines
                ])
                row.append(journal_text)
            else:
                row.append("")
        
        writer.writerow(row)
    
    # Return as downloadable file
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=accounting-export-{now.strftime('%Y%m%d%H%M%S')}.csv"
        }
    )
