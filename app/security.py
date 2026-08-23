import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.config import settings
from app.core.database import SessionLocal
from app.models.models import User
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

bearer_scheme = HTTPBearer()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),) -> User:

    token = credentials.credentials
    try:
        payload = jwt.decode(token,settings.jwt_secret,algorithms=["HS256"])
        user_id = payload.get("sub")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401,detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401,detail="Invalid Token")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail = "User not found")
    return user

class ChequeListItem(BaseModel):
    id: UUID
    payee_phone: str
    payee_name: str | None = None
    amount_paise: int
    due_date: datetime
    current_state: str
    memo: str | None

    class Config:
        from_attributes = True