from __future__ import annotations

from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import User
from app.routers import volume_contracts


def test_list_volume_contract_projects_returns_empty_list(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = testing_session()
    try:
        user = User(
            username="hr_admin@test.com",
            hashed_password="hashed",
            full_name="HR Volume Contracts Admin",
            role="HR_ADMIN",
            is_active=True,
        )
        db.add(user)
        db.commit()

        monkeypatch.setattr(volume_contracts, "_require_auth", lambda request, db: user)

        response = volume_contracts.list_volume_contract_projects(
            request=SimpleNamespace(),
            category=None,
            db=db,
        )

        assert response == []
    finally:
        db.close()
