from sqlalchemy import Column, String, DateTime, Integer, func, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid, enum
from datetime import datetime, date
from app.core.database import Base

# class Party(Base):
#     __tablename__ = "parties"

#     id = Column(UUID(as_uuid=True), primary_key=True, default= uuid.uuid4)
#     name = Column(String, nullable=False)
#     type = Column(String, nullable=False)
#     contact_phone = Column(String, unique=True, nullable=False, index=True)
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
class ChequeState(str, enum.Enum):
    pending_registration = "pending_registration"
    draft = "draft"
    created = "created"
    cancelled = "cancelled"
    encashed = "encashed"

class Cheque(Base):
    __tablename__ = "cheques"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drawer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    payee_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # null until resolved
    payee_phone = Column(String, nullable=False)  # always captured, even before payee_id resolves

    amount_paise = Column(Integer, nullable=False)  # integer paise, never float
    memo = Column(String, nullable=True)
    due_date = Column(DateTime, nullable=False)

    current_state = Column(SQLEnum(ChequeState), nullable=False, default=ChequeState.pending_registration)
    created_at = Column(DateTime, default=datetime.utcnow)

    drawer = relationship("User", foreign_keys=[drawer_id])
    payee = relationship("User", foreign_keys=[payee_id])

class StateTransition(Base):
    __tablename__ = "state_transitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cheque_id = Column(UUID(as_uuid=True), ForeignKey("cheques.id"), nullable=False)
    from_state = Column(String, nullable=True)  # null for the very first transition
    to_state = Column(String, nullable=False)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default= uuid.uuid4)
    name = Column(String, nullable=True)
    phone_number = Column(String,unique=True,nullable=False,index=True)
    # party_id = Column(UUID(as_uuid=True), ForeignKey("parties.id", ondelete="RESTRICT"))
    role = Column(String,nullable=False,default="owner")
    public_key = Column(String,nullable=True)
    created_at = Column(DateTime(timezone=True),server_default=func.now())

class Signature(Base):
    __tablename__ = "signatures"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cheque_id = Column(UUID(as_uuid=True), ForeignKey("cheques.id"), nullable=False, unique=True)
    signer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    signed_hash = Column(String, nullable=False)       # hex-encoded hash of the cheque data at signing time
    signature_value = Column(String, nullable=False)   # hex-encoded signature bytes
    public_key_used = Column(String, nullable=False)   # snapshot of the key at signing time — see note below

    signed_at = Column(DateTime, default=datetime.utcnow)

    cheque = relationship("Cheque")
    signer = relationship("User")

class Invite(Base):
    __tablename__ = "invites"

    id = Column(UUID(as_uuid=True), primary_key = True, default = uuid.uuid4)
    cheque_id = Column(UUID(as_uuid=True), ForeignKey("cheques.id"), nullable=False)
    phone_number = Column(String, nullable=False, index=True)
    sent_at = Column(DateTime, default=datetime.utcnow)
    claimed_at = Column(DateTime, nullable=True)

    cheque = relationship("Cheque")