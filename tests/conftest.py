import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, SessionLocal, engine
from app.models import User
import jwt
from app.config import settings

@pytest.fixture
def client():
    Base.metadata.create_all(bind=engine)  # spin up test schema
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)    # tear down after each test

@pytest.fixture
def test_user():
    db = SessionLocal()
    user = User(phone_number="+919999999999", name="Test User")
    db.add(user)
    db.commit()
    db.refresh(user)
    yield user
    db.close()

@pytest.fixture
def auth_headers(test_user):
    token = jwt.encode(
        {"sub": str(test_user.id)},
        settings.jwt_secret,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def pending_cheque(test_user):
    db = SessionLocal()
    cheque = Cheque(
        drawer_id=test_user.id,
        payee_id=None,
        payee_phone="+919888888888",  # a number no test_user fixture uses
        amount_paise=10000,
        due_date=datetime.utcnow() + timedelta(days=7),
        current_state=ChequeState.pending_registration,
    )
    db.add(cheque)
    db.commit()
    db.refresh(cheque)
    yield cheque
    db.close()