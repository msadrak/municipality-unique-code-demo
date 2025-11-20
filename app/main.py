# app/main.py
from typing import List

from fastapi import FastAPI, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .database import SessionLocal, engine
from . import models, schemas, crud

models.Base.metadata.create_all(bind=engine)

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------- صفحه اصلی (فرانت) ----------

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# ---------- APIهای lookup ----------

@app.get("/org-units", response_model=List[schemas.OrgUnitBase])
def list_org_units(db: Session = Depends(get_db)):
    return crud.get_org_units(db)


@app.get("/continuous-actions", response_model=List[schemas.ContinuousActionBase])
def list_continuous_actions(db: Session = Depends(get_db)):
    return crud.get_continuous_actions(db)


@app.get("/action-types", response_model=List[schemas.ActionTypeBase])
def list_action_types(db: Session = Depends(get_db)):
    return crud.get_action_types(db)


# ---------- APIهای اقدام ویژه ----------

@app.get("/special-actions", response_model=List[schemas.SpecialActionOut])
def list_special_actions(
    org_unit_id: int | None = None,
    continuous_action_id: int | None = None,
    action_type_id: int | None = None,
    db: Session = Depends(get_db),
):
    return crud.list_special_actions(
        db,
        org_unit_id=org_unit_id,
        continuous_action_id=continuous_action_id,
        action_type_id=action_type_id,
    )


@app.post("/special-actions", response_model=schemas.SpecialActionOut)
def create_special_action_endpoint(
    payload: schemas.SpecialActionCreate,
    db: Session = Depends(get_db),
):
    return crud.create_special_action(db, payload)
