from pydantic import BaseModel, field_validator
from uuid import UUID 
from datetime import datetime

class UserSearchResult(BaseModel):
    id: UUID
    name : str | None

    class Config:
        from_attributes = True

class ChequeCreate(BaseModel):
    payee_phone: str
    amount_paise: int
    memo: str | None = None
    due_date: datetime

    @field_validator("amount_paise")
    @classmethod
    def amount_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("amount_paise must be positive")
        return v
        
class ChequeOut(BaseModel):
    id: UUID
    drawer_id: UUID
    payee_id: UUID | None
    payee_phone: str
    amount_paise: int
    memo: str | None
    due_date: datetime
    current_state: str
    created_at: datetime

    class Config:
        from_attributes = True

class StateTransitionOut(BaseModel):
    from_state: str | None
    to_state: str
    actor_id: UUID
    reason: str | None
    created_at: datetime

    class Config:
        from_attributes = True

class ChequeDetail(BaseModel):
    id: UUID
    drawer_id: UUID
    drawer_name: str | None
    payee_id: UUID | None
    payee_phone: str
    payee_name: str | None
    amount_paise: int
    memo: str | None
    due_date: datetime
    current_state: str
    created_at: datetime
    transitions: list[StateTransitionOut]

    class Config:
        from_attributes = True

class InviteCreate(BaseModel):
    cheque_id: UUID

class InviteOut(BaseModel):
    id: UUID
    cheque_id: UUID
    phone_number: str
    sent_at: datetime
    claimed_at: datetime | None

    class Config:
        from_attributes = True