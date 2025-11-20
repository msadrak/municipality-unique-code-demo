from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class OrgUnit(Base):
    __tablename__ = "org_units"

    id = Column(Integer, primary_key=True, index=True)
    area_code = Column(String, index=True)      # نام حوزه/منطقه (مثلاً "منطقه یازده")
    domain_code = Column(String, index=True)    # فعلاً "01"
    dept_code = Column(String, index=True)      # کد اداره
    section_code = Column(String, index=True)   # کد قسمت
    full_code = Column(String, unique=True, index=True)
    title = Column(String)                      # مثلاً "ثبت اسناد و املاک / امور املاک / منطقه ده"

    # روابط
    special_actions = relationship("SpecialAction", back_populates="org_unit")
    continuous_actions = relationship("ContinuousAction", back_populates="org_unit")


class ContinuousAction(Base):
    __tablename__ = "continuous_actions"

    id = Column(Integer, primary_key=True, index=True)
    org_unit_id = Column(Integer, ForeignKey("org_units.id"))
    code = Column(String, index=True)      # مثل "CA001"
    title = Column(String)

    org_unit = relationship("OrgUnit", back_populates="continuous_actions")
    special_actions = relationship("SpecialAction", back_populates="continuous_action")


class ActionType(Base):
    __tablename__ = "action_types"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)   # مثل "ACT017"
    title = Column(String)
    description = Column(String, nullable=True)

    special_actions = relationship("SpecialAction", back_populates="action_type")


class SpecialAction(Base):
    __tablename__ = "special_actions"

    id = Column(Integer, primary_key=True, index=True)
    unique_code = Column(String, unique=True, index=True)

    org_unit_id = Column(Integer, ForeignKey("org_units.id"))
    continuous_action_id = Column(Integer, ForeignKey("continuous_actions.id"))
    action_type_id = Column(Integer, ForeignKey("action_types.id"))

    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    action_date = Column(Date)
    seq_no = Column(Integer)

    org_unit = relationship("OrgUnit", back_populates="special_actions")
    continuous_action = relationship("ContinuousAction", back_populates="special_actions")
    action_type = relationship("ActionType", back_populates="special_actions")
