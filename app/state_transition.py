from sqlalchemy.orm import Session
from app.models.models import Cheque, ChequeState, Invite, User
from datetime import datetime

def resolve_pending_cheques_for_user(db: Session, user: User):
    """Called once, right after a new user is created. Finds any cheques
    waiting on this phone number and links them to the new account."""
    pending = (
        db.query(Cheque)
        .filter(
            Cheque.payee_phone == user.phone_number,
            Cheque.payee_id.is_(None),
            Cheque.current_state == ChequeState.pending_registration,
        )
        .all()
    )

    for cheque in pending:
        cheque.payee_id = user.id
        apply_transition(
            db, cheque, ChequeState.draft,
            actor_id=user.id,  # the resolving event is triggered by the payee joining
            reason="Payee registered",
        )

        matching_invite = (
            db.query(Invite)
            .filter(Invite.cheque_id == cheque.id, Invite.claimed_at.is_(None))
            .order_by(Invite.sent_at.desc())
            .first()
        )
        if matching_invite:
            matching_invite.claimed_at = datetime.utcnow()

    return pending  # useful for the caller to know how many resolved