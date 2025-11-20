# app/crud.py
from datetime import date
from typing import Optional, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from . import models, schemas


# ---------- لوکاپ‌ها ----------

def get_org_units(db: Session):
    return db.query(models.OrgUnit).order_by(models.OrgUnit.id).all()


def get_continuous_actions(db: Session):
    return db.query(models.ContinuousAction).order_by(models.ContinuousAction.id).all()


def get_action_types(db: Session):
    return db.query(models.ActionType).order_by(models.ActionType.id).all()


# ---------- لیست اقدامات ویژه ----------

def list_special_actions(
    db: Session,
    org_unit_id: Optional[int] = None,
    continuous_action_id: Optional[int] = None,
    action_type_id: Optional[int] = None,
) -> List[models.SpecialAction]:
    q = db.query(models.SpecialAction)
    if org_unit_id:
        q = q.filter(models.SpecialAction.org_unit_id == org_unit_id)
    if continuous_action_id:
        q = q.filter(models.SpecialAction.continuous_action_id == continuous_action_id)
    if action_type_id:
        q = q.filter(models.SpecialAction.action_type_id == action_type_id)

    return q.order_by(models.SpecialAction.id.desc()).all()


# ---------- تولید کد یونیک ----------

def generate_unique_code(
    db: Session,
    org_unit: models.OrgUnit,
    cont: models.ContinuousAction,
    act: models.ActionType,
    action_date: Optional[date],
):
    """
    ساختن پیشوند کد و پیدا کردن شماره‌ی ترتیبی
    فرمت نهایی:
    FULLCODE-CAxxx-ACTyyy-YYYY-SEQ
    مثل: 12-01-03-02-CA002-ACT021-2025-0001
    """
    if action_date is None:
        year = date.today().year
    else:
        year = action_date.year

    prefix = f"{org_unit.full_code}-{cont.code}-{act.code}-{year}"

    # پیدا کردن بزرگ‌ترین seq_no برای همین prefix
    max_seq = (
        db.query(func.max(models.SpecialAction.seq_no))
        .filter(models.SpecialAction.unique_code.like(f"{prefix}-%"))
        .scalar()
    )

    next_seq = 1 if max_seq is None else int(max_seq) + 1
    seq_str = f"{next_seq:04d}"

    unique_code = f"{prefix}-{seq_str}"
    return unique_code, next_seq


# ---------- ساخت اقدام ویژه ----------

def create_special_action(db: Session, data: schemas.SpecialActionCreate) -> models.SpecialAction:
    """
    این تابع فقط دو آرگومان می‌گیرد: db و data
    بقیه چیزها (کد یونیک، seq_no، ...) اینجا محاسبه می‌شود.
    """

    org = (
        db.query(models.OrgUnit)
        .filter(models.OrgUnit.id == data.org_unit_id)
        .first()
    )
    cont = (
        db.query(models.ContinuousAction)
        .filter(models.ContinuousAction.id == data.continuous_action_id)
        .first()
    )
    act = (
        db.query(models.ActionType)
        .filter(models.ActionType.id == data.action_type_id)
        .first()
    )

    if not org or not cont or not act:
        # اگر دیتای ورودی خراب باشد، بهتر است صریح خطا بدهیم
        raise ValueError("OrgUnit / ContinuousAction / ActionType not found for given IDs")

    unique_code, seq_no = generate_unique_code(
        db=db,
        org_unit=org,
        cont=cont,
        act=act,
        action_date=data.action_date,
    )

    obj = models.SpecialAction(
        unique_code=unique_code,
        seq_no=seq_no,
        org_unit_id=data.org_unit_id,
        continuous_action_id=data.continuous_action_id,
        action_type_id=data.action_type_id,
        description=data.description,
        action_date=data.action_date,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj
