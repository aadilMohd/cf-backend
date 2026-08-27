from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from uuid import UUID
from typing import Literal

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.exceptions import InvalidSignature

from app.security import get_db, get_current_user
from app.models.models import User, Cheque, StateTransition, ChequeState, Signature
from app.schemas import ChequeCreate, ChequeOut, ChequeDetail, ChequeListItem
from app.crypto_utils import compute_cheque_hash

router = APIRouter(prefix="/cheques", tags=["cheques"])

class SignRequest(BaseModel):
    signature_hex: str

@router.post("", response_model=ChequeOut)
def create_cheque(
    payload: ChequeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    payee = db.query(User).filter(User.phone_number == payload.payee_phone).first()

    cheque = Cheque(
        drawer_id=current_user.id,
        payee_id=payee.id if payee else None,
        payee_phone=payload.payee_phone,
        amount_paise=payload.amount_paise,
        memo=payload.memo,
        due_date=payload.due_date,
        current_state=ChequeState.draft if payee else ChequeState.pending_registration,
    )
    db.add(cheque)
    db.flush()  # gets cheque.id without committing yet

    transition = StateTransition(
        cheque_id=cheque.id,
        from_state=None,
        to_state=cheque.current_state.value,
        actor_id=current_user.id,
        reason="Cheque created",
    )
    db.add(transition)
    db.commit()
    db.refresh(cheque)
    return cheque

@router.post("/{cheque_id}/sign", response_model=ChequeOut)
def sign_cheque(
    cheque_id: UUID,
    payload: SignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cheque = db.query(Cheque).filter(Cheque.id == cheque_id).first()
    if not cheque:
        raise HTTPException(404, "Cheque not found")
    if cheque.drawer_id != current_user.id:
        raise HTTPException(403, "Only the drawer can sign this cheque")
    if cheque.current_state != ChequeState.draft:
        raise HTTPException(400, f"Cannot sign a cheque in state {cheque.current_state}")
    if not current_user.public_key:
        raise HTTPException(400, "No public key on file for this user")

    expected_hash = compute_cheque_hash(cheque)
    public_key = serialization.load_pem_public_key(current_user.public_key.encode())
    signature_bytes = bytes.fromhex(payload.signature_hex)

    try:
        public_key.verify(signature_bytes, expected_hash, ec.ECDSA(hashes.SHA256()))
    except InvalidSignature:
        raise HTTPException(400, "Signature verification failed")
    
    sig_row = Signature(
        cheque_id=cheque.id,
        signer_id=current_user.id,
        signed_hash=expected_hash.hex(),
        signature_value=payload.signature_hex,
        public_key_used=current_user.public_key,
    )
    db.add(sig_row)

    old_state = cheque.current_state
    cheque.current_state = ChequeState.created
    db.add(StateTransition(
        cheque_id=cheque.id, from_state=old_state.value, to_state="created",
        actor_id=current_user.id, reason="Signed",
    ))
    db.commit()
    db.refresh(cheque)
    return cheque

@router.get("", response_model=list[ChequeListItem])
def list_cheques(
    role: Literal["issued", "received"] = Query(...),
    status: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Cheque)
    if role == "issued":
        query = query.filter(Cheque.drawer_id == current_user.id)
    else:
        query = query.filter(Cheque.payee_id == current_user.id)

    if status:
        query = query.filter(Cheque.current_state == status)

    cheques = query.order_by(Cheque.due_date.asc()).all()

    results = []
    for c in cheques:
        results.append(ChequeListItem(
            id=c.id,
            payee_phone=c.payee_phone,
            payee_name=c.payee.name if c.payee else None,
            amount_paise=c.amount_paise,
            due_date=c.due_date,
            current_state=c.current_state.value,
            memo=c.memo,
        ))
    return results

class CancelRequest(BaseModel):
    reason: str | None = None

@router.post("/{cheque_id}/cancel", response_model=ChequeOut)
def cancel_cheque(
    cheque_id: UUID,
    payload: CancelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cheque = db.query(Cheque).filter(Cheque.id == cheque_id).first()
    if not cheque:
        raise HTTPException(404, "Cheque not found")
    if cheque.drawer_id != current_user.id:
        raise HTTPException(403, "Only the drawer can cancel this cheque")
    if cheque.current_state not in (ChequeState.draft, ChequeState.created,ChequeState.pending_registration):
        raise HTTPException(
            400, f"Cannot cancel a cheque in state {cheque.current_state.value}"
        )
    
    old_state = cheque.current_state
    cheque.current_state = ChequeState.cancelled
    db.add(StateTransition(
        cheque_id=cheque.id,
        from_state=old_state.value,
        to_state="cancelled",
        actor_id=current_user.id,
        reason=payload.reason,
    ))
    db.commit()
    db.refresh(cheque)
    return cheque

@router.get("/{cheque_id}", response_model=ChequeDetail)
def get_cheque_detail(
    cheque_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cheque = db.query(Cheque).filter(Cheque.id == cheque_id).first()
    if not cheque:
        raise HTTPException(404, "Cheque not found")

    if current_user.id not in (cheque.drawer_id, cheque.payee_id):
        raise HTTPException(403, "You don't have access to this cheque")

    transitions = (
        db.query(StateTransition)
        .filter(StateTransition.cheque_id == cheque.id)
        .order_by(StateTransition.created_at.asc())
        .all()
    )

    return ChequeDetail(
        id=cheque.id,
        drawer_id=cheque.drawer_id,
        drawer_name=cheque.drawer.name if cheque.drawer else None,
        payee_id=cheque.payee_id,
        payee_phone=cheque.payee_phone,
        payee_name=cheque.payee.name if cheque.payee else None,
        amount_paise=cheque.amount_paise,
        memo=cheque.memo,
        due_date=cheque.due_date,
        current_state=cheque.current_state.value,
        created_at=cheque.created_at,
        transitions=transitions,
    )