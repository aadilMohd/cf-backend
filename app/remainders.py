import logging
from datetime import datetime, timedelta

from app.core.database import SessionLocal
from app.models.models import Cheque, ChequeState, Reminder
from app.push_notifications import send_push

logger = logging.getLogger(__name__)

THRESHOLDS = [1, 0]  # days before the due date: 1 = day before, 0 = due date


def check_and_send_reminders():
    db = SessionLocal()
    try:
        today = datetime.utcnow().date()
        for threshold in THRESHOLDS:
            day_start = datetime.combine(today + timedelta(days=threshold), datetime.min.time())
            day_end = day_start + timedelta(days=1)

            cheques = (
                db.query(Cheque)
                .filter(
                    Cheque.current_state == ChequeState.created,
                    Cheque.payee_id.isnot(None),
                    Cheque.due_date >= day_start,
                    Cheque.due_date < day_end,
                )
                .all()
            )
            for cheque in cheques:
                try:
                    _remind(db, cheque, threshold)
                except Exception:
                    db.rollback()
                    logger.exception("Reminder failed for cheque %s", cheque.id)
    finally:
        db.close()


def _remind(db, cheque, threshold):
    already_sent = (
        db.query(Reminder)
        .filter(Reminder.cheque_id == cheque.id, Reminder.threshold_days == threshold)
        .first()
    )
    if already_sent:
        return

    when = "today" if threshold == 0 else "tomorrow"
    sender = cheque.drawer.name or cheque.drawer.phone_number
    sent = send_push(
        cheque.payee.fcm_token,
        f"Cheque due {when}",
        f"₹{cheque.amount_paise / 100:.2f} from {sender}. Open ChequeFlow to encash it.",
        data={"cheque_id": str(cheque.id)},
    )
    if not sent:
        return  # not recorded, so the next hourly run retries

    db.add(Reminder(cheque_id=cheque.id, recipient_id=cheque.payee_id, threshold_days=threshold))
    db.commit()