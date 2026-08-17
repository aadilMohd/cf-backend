from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.security import get_db, get_current_user
from app.models.models import User, Cheque, Invite, ChequeState
from app.schemas import InviteCreate, InviteOut
from app.notifications import send_sms
from datetime import timedelta

router = APIRouter(prefix="/invites", tags=["invites"])

@router.post("", response_model=InviteOut)
def send_invite(
    payload: InviteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cheque = db.query(Cheque).filter(Cheque.id == payload.cheque_id).first()
    if not cheque:
        raise HTTPException(404, "Cheque not found")
    if cheque.drawer_id != current_user.id:
        raise HTTPException(403, "Only the drawer can send an invite for this cheque")
    if cheque.current_state != ChequeState.pending_registration:
        raise HTTPException(400, "This cheque's payee is already registered")

    recent = (
        db.query(Invite)
        .filter(Invite.cheque_id == cheque.id, Invite.sent_at > datetime.utcnow() - timedelta(minutes=5))
        .first()
    )

    if recent:
        raise HTTPException(429, "An invite was already sent recently. Try again in a few minutes.")
    invite = Invite(cheque_id=cheque.id, phone_number=cheque.payee_phone)
    db.add(invite)
    db.commit()
    db.refresh(invite)

    # actual SMS/WhatsApp send happens Day 2 — for today, this just records intent
    return invite

@router.post("", response_model=InviteOut)
async def send_invite(
    payload: InviteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cheque = db.query(Cheque).filter(Cheque.id == payload.cheque_id).first()
    if not cheque:
        raise HTTPException(404, "Cheque not found")
    if cheque.drawer_id != current_user.id:
        raise HTTPException(403, "Only the drawer can send an invite for this cheque")
    if cheque.current_state != ChequeState.pending_registration:
        raise HTTPException(400, "This cheque's payee is already registered")

    invite = Invite(cheque_id=cheque.id, phone_number=cheque.payee_phone)
    db.add(invite)
    db.commit()
    db.refresh(invite)

    deep_link = f"chequeflow://claim?invite_id={invite.id}"
    message = (
        f"{current_user.name or 'Someone'} sent you a cheque on ChequeFlow. "
        f"Get the app to view it: {deep_link}"
    )
    await send_sms(cheque.payee_phone, message)

    return invite