import uuid
from sqlalchemy import Column,String,DateTime,ForeignKey,Enum
from sqlalchemy.dialects.postgresql import uuid
from sqlalchemy.sql import func
from app.core.database import Base

class Party(Base):
    __tablename__ = "parties"

    id = Column(UUID(as_uuid=True), primary_key=True, default= uuid.uuid4)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    contact_phone = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default= uuid.uuid4)
    party_id = Column(UUID(as_uuid=True), ForeignKey("parties.id", ondelete="RESTRICT"))
    role = Column = Column(String,nullable=False,default="owner")
    device_public_key = Column(String,nullable=True)
    created_at = Column(DateTime(timezone=True),server_default=func.now())
    