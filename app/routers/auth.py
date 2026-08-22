from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import uuid
import jwt, datetime
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.models import User
from app.state_transition import resolve_pending_cheques_for_user  # confirm filename matches
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

otp_sessions = {}

class OTPRequest(BaseModel):
    phone_number: str

@router.post("/otp/request")
def request_otp(payload: OTPRequest):
    session_token = str(uuid.uuid4())
    # TODO: call MSG91 here once DLT clears — see USE_REAL_OTP flag
    otp_sessions[session_token] = {"phone": payload.phone_number, "code": "123456"}
    return {"session_token": session_token}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class OTPVerify(BaseModel):
    session_token: str
    code: str

@router.post("/otp/verify")
def verify_otp(payload: OTPVerify, db: Session = Depends(get_db)):
    session = otp_sessions.get(payload.session_token)
    if not session or session["code"] != payload.code:
        raise HTTPException(status_code=400, detail="Invalid or expired code")

    user = db.query(User).filter(User.phone_number == session["phone"]).first()
    is_new_user = user is None

    if is_new_user:
        user = User(phone_number=session["phone"])
        db.add(user)
        db.commit()
        db.refresh(user)
        resolve_pending_cheques_for_user(db, user)
        db.commit()

    del otp_sessions[payload.session_token]

    token = jwt.encode(
        {"sub": str(user.id), "exp": datetime.datetime.utcnow() + datetime.timedelta(days=30)},
        settings.jwt_secret,
        algorithm="HS256",
    )
    return {"access_token": token, "user_id": str(user.id), "is_new_user": is_new_user}