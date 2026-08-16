from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models import User
from app.schemas import UserSearchResult
from app.security import get_current_user, get_db


class PublicKeyUpload(BaseModel):
    public_key_pem: str


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/search", response_model=UserSearchResult)
def search_user(
    phone: str = Query(..., min_length=10, max_length=15),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Fixed syntax bug: changed '=' to '=='
    user = db.query(User).filter(User.phone_number == phone).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No user found with that number",
        )
    return user


@router.put("/me/public-key")
def upload_public_key(
    payload: PublicKeyUpload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_user.public_key = payload.public_key_pem
    db.commit()
    return {"status": "ok"}