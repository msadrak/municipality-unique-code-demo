from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional


class OrgUnitBase(BaseModel):
    id: int
    area_code: str
    domain_code: str
    dept_code: str
    section_code: str
    full_code: str
    title: str

    class Config:
        orm_mode = True


class ActionTypeBase(BaseModel):
    id: int
    code: str
    title: str

    class Config:
        orm_mode = True


class ContinuousActionBase(BaseModel):
    id: int
    code: str
    title: str

    class Config:
        orm_mode = True


class SpecialActionCreate(BaseModel):
    org_unit_id: int
    continuous_action_id: int
    action_type_id: int
    description: str
    action_date: Optional[date] = None   # تاریخ اقدام (اختیاری)


class SpecialActionOut(BaseModel):
    id: int
    unique_code: str
    org_unit: OrgUnitBase
    continuous_action: ContinuousActionBase
    action_type: ActionTypeBase
    description: str
    created_at: datetime

    class Config:
        orm_mode = True
