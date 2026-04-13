from io import BytesIO
from pathlib import Path
from typing import List
from urllib.request import urlopen

import arabic_reshaper
import jdatetime
from bidi.algorithm import get_display
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import FundingRequest, FundingRequestStatus, User
from app.routers.auth import require_auth
from app.schemas.funding import FundingRequestCreate, FundingRequestResponse, FundingRequestUpdate
from app.services import funding as funding_service

router = APIRouter(prefix="/funding", tags=["HR Funding Requests"])

PAGE_WIDTH, PAGE_HEIGHT = A4
PROJECT_ROOT = Path(__file__).resolve().parents[2]
FONT_DIR = PROJECT_ROOT / "assets" / "fonts"
FONT_PATH = FONT_DIR / "Vazirmatn-Regular.ttf"
FONT_DOWNLOAD_URL = "https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/fonts/ttf/Vazirmatn-Regular.ttf"
FONT_NAME = "Vazirmatn"
FONT_BOLD_NAME = FONT_NAME
RTL_RESHAPER = arabic_reshaper.ArabicReshaper({"delete_harakat": False})


def _ensure_vazirmatn_font() -> Path:
    """Download Vazirmatn into the project assets folder if it is not present."""
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    if FONT_PATH.exists():
        return FONT_PATH

    with urlopen(FONT_DOWNLOAD_URL, timeout=30) as response:
        FONT_PATH.write_bytes(response.read())

    return FONT_PATH


def _register_persian_font() -> None:
    """Register the bundled Vazirmatn font for every PDF text draw."""
    if FONT_NAME in pdfmetrics.getRegisteredFontNames():
        return

    font_path = _ensure_vazirmatn_font()
    pdfmetrics.registerFont(TTFont(FONT_NAME, str(font_path)))


_register_persian_font()


def _rtl_text(text: str) -> str:
    return get_display(RTL_RESHAPER.reshape(str(text)))


def _format_amount(amount: int) -> str:
    return f"{int(amount):,}"


def _draw_rtl_line(
    pdf: canvas.Canvas,
    text: str,
    right_x: float,
    y: float,
    font_name: str,
    font_size: int,
) -> None:
    pdf.setFont(font_name, font_size)
    pdf.drawRightString(right_x, y, _rtl_text(text))


def _draw_rtl_paragraph(
    pdf: canvas.Canvas,
    text: str,
    right_x: float,
    y: float,
    width: float,
    font_name: str,
    font_size: int,
    leading: int = 22,
) -> float:
    shaped = _rtl_text(text)
    lines = simpleSplit(shaped, font_name, font_size, width)
    pdf.setFont(font_name, font_size)
    current_y = y
    for line in lines:
        pdf.drawRightString(right_x, current_y, line)
        current_y -= leading
    return current_y


def _build_funding_pdf(request_obj: FundingRequest) -> bytes:
    _register_persian_font()
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setTitle(f"funding-request-{request_obj.id}")
    pdf.setFont(FONT_NAME, 12)

    margin_right = PAGE_WIDTH - 56
    margin_left = 56
    content_width = PAGE_WIDTH - (2 * margin_left)

    today = jdatetime.date.today().strftime("%Y/%m/%d")
    amount_text = _format_amount(request_obj.amount)

    pdf.setLineWidth(1)
    pdf.rect(margin_left, 48, content_width, PAGE_HEIGHT - 96)

    _draw_rtl_line(pdf, "بسمه تعالی", margin_right, PAGE_HEIGHT - 70, FONT_BOLD_NAME, 15)
    _draw_rtl_line(pdf, "نامه درخواست تامین اعتبار", margin_right, PAGE_HEIGHT - 105, FONT_BOLD_NAME, 16)

    y = PAGE_HEIGHT - 145
    _draw_rtl_line(pdf, f"تاریخ: {today}", margin_right, y, FONT_NAME, 11)
    y -= 22
    _draw_rtl_line(pdf, f"شماره پیگیری: {request_obj.tracking_number}", margin_right, y, FONT_NAME, 11)
    y -= 22
    _draw_rtl_line(pdf, f"وضعیت: {request_obj.status.value}", margin_right, y, FONT_NAME, 11)

    y -= 46
    _draw_rtl_line(pdf, "موضوع:", margin_right, y, FONT_BOLD_NAME, 12)
    y -= 24
    y = _draw_rtl_paragraph(pdf, request_obj.title, margin_right, y, content_width - 8, FONT_NAME, 12)

    y -= 24
    _draw_rtl_line(pdf, "شرح درخواست:", margin_right, y, FONT_BOLD_NAME, 12)
    y -= 24
    description = request_obj.description or "توضیحی برای این درخواست ثبت نشده است."
    y = _draw_rtl_paragraph(pdf, description, margin_right, y, content_width - 8, FONT_NAME, 12)

    y -= 24
    _draw_rtl_line(pdf, f"مبلغ درخواستی: {amount_text} ریال", margin_right, y, FONT_BOLD_NAME, 13)

    body = (
        "احتراما، درخواست تامین اعتبار فوق جهت بررسی و اقدام لازم تقدیم می گردد. "
        "خواهشمند است دستور فرمایید مراحل اداری و مالی مربوطه انجام شود."
    )
    y -= 40
    y = _draw_rtl_paragraph(pdf, body, margin_right, y, content_width - 8, FONT_NAME, 12)

    signature_y = max(y - 70, 120)
    _draw_rtl_line(pdf, "امضا و مهر", margin_right - 20, signature_y, FONT_BOLD_NAME, 12)
    pdf.line(margin_right - 170, signature_y - 18, margin_right - 20, signature_y - 18)

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer.getvalue()


@router.post("/", response_model=FundingRequestResponse, status_code=status.HTTP_201_CREATED)
def create_funding_request(
    request_in: FundingRequestCreate,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """
    Ø«Ø¨Øª ÛŒÚ© Ø¯Ø±Ø®ÙˆØ§Ø³Øª ØªØ§Ù…ÛŒÙ† Ø§Ø¹ØªØ¨Ø§Ø± Ø¬Ø¯ÛŒØ¯ (ÙÙ‚Ø· Ù¾Ø±Ø³Ù†Ù„ Ù…Ù†Ø§Ø¨Ø¹ Ø§Ù†Ø³Ø§Ù†ÛŒ ÛŒØ§ Ú©Ø§Ø±Ø¨Ø±Ø§Ù† Ù…Ø¬Ø§Ø²)
    """
    return funding_service.create_funding_request(db=db, request_in=request_in, user_id=current_user.id)


@router.get("/", response_model=List[FundingRequestResponse])
def get_my_funding_requests(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """
    Ø¯Ø±ÛŒØ§ÙØª Ù„ÛŒØ³Øª Ø¯Ø±Ø®ÙˆØ§Ø³Øªâ€ŒÙ‡Ø§ÛŒ Ø§ÛŒØ¬Ø§Ø¯ Ø´Ø¯Ù‡ ØªÙˆØ³Ø· Ú©Ø§Ø±Ø¨Ø± ÙØ¹Ù„ÛŒ
    """
    return funding_service.list_my_funding_requests(db=db, user_id=current_user.id, skip=skip, limit=limit)


@router.get("/all", response_model=List[FundingRequestResponse])
def get_all_funding_requests(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """
    Ø¯Ø±ÛŒØ§ÙØª Ù„ÛŒØ³Øª ØªÙ…Ø§Ù…ÛŒ Ø¯Ø±Ø®ÙˆØ§Ø³Øªâ€ŒÙ‡Ø§ÛŒ ØªØ§Ù…ÛŒÙ† Ø§Ø¹ØªØ¨Ø§Ø± Ù…Ù†Ø§Ø¨Ø¹ Ø§Ù†Ø³Ø§Ù†ÛŒ (Ù†ÛŒØ§Ø² Ø¨Ù‡ Ø³Ø·Ø­ Ø¯Ø³ØªØ±Ø³ÛŒ Ù…Ø¯ÛŒØ±)
    """
    # In a real app we'd check if current_user has manager/admin roles
    return funding_service.list_funding_requests(db=db, skip=skip, limit=limit)


@router.get("/{request_id}/pdf")
def get_funding_request_pdf(
    request_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """
    Generate a formal PDF letter for a funding request.
    """
    db_obj = funding_service.get_funding_request(db=db, request_id=request_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="درخواست یافت نشد")

    pdf_bytes = _build_funding_pdf(db_obj)
    filename = f"funding-request-{request_id}.pdf"
    headers = {"Content-Disposition": f'inline; filename="{filename}"'}
    return StreamingResponse(BytesIO(pdf_bytes), media_type="application/pdf", headers=headers)


@router.get("/{request_id}", response_model=FundingRequestResponse)
def get_funding_request(
    request_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """
    Ø¯Ø±ÛŒØ§ÙØª ÛŒÚ© Ø¯Ø±Ø®ÙˆØ§Ø³Øª Ø®Ø§Øµ Ø¨Ø§ ID
    """
    db_obj = funding_service.get_funding_request(db=db, request_id=request_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="درخواست یافت نشد")
    return db_obj


@router.put("/{request_id}", response_model=FundingRequestResponse)
def update_funding_request(
    request_id: int,
    update_data: FundingRequestUpdate,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """
    ÙˆÛŒØ±Ø§ÛŒØ´ Ø§Ø·Ù„Ø§Ø¹Ø§Øª Ø¯Ø±Ø®ÙˆØ§Ø³Øª (Ù…Ø¹Ù…ÙˆÙ„Ø§Ù‹ Ø¯Ø± Ø­Ø§Ù„Øª DRAFT)
    """
    return funding_service.update_funding_request(
        db=db,
        request_id=request_id,
        update_data=update_data,
        user_id=current_user.id,
    )


@router.patch("/{request_id}/status", response_model=FundingRequestResponse)
def change_request_status(
    request_id: int,
    new_status: FundingRequestStatus,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """
    ØªØºÛŒÛŒØ± ÙˆØ¶Ø¹ÛŒØª Ú¯Ø±Ø§Ù Ú¯Ø±Ø¯Ø´ Ú©Ø§Ø± (Ù…Ø«Ù„Ø§ Ø§Ø² DRAFT Ø¨Ù‡ PENDING_VP_PLANNING)
    """
    # Here we would normally implement strict access controls to ensure e.g.
    # only VP Planning can shift it to PENDING_VP_FINANCE_INITIAL
    return funding_service.transition_status(
        db=db,
        request_id=request_id,
        new_status=new_status,
        user_id=current_user.id,
    )
