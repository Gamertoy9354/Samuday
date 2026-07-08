from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional

class WalletResponse(BaseModel):
    id: UUID
    user_id: UUID
    balance: int = Field(..., description="Wallet balance in paise (100 paise = 1 INR)")
    currency: str
    status: str

    class Config:
        from_attributes = True

class LedgerEntryResponse(BaseModel):
    id: UUID
    wallet_id: UUID
    amount: int
    direction: str
    reference_type: str
    reference_id: Optional[UUID]
    balance_after: int
    created_at: datetime

    class Config:
        from_attributes = True

class PayoutRequestCreate(BaseModel):
    amount: int = Field(..., gt=0, description="Amount to pay out in paise")

class PayoutRequestResponse(BaseModel):
    id: UUID
    wallet_id: UUID
    amount: int
    status: str
    requested_at: datetime
    processed_at: Optional[datetime]

    class Config:
        from_attributes = True

class EscrowHoldResponse(BaseModel):
    id: UUID
    transaction_id: UUID
    amount: int
    status: str
    created_at: datetime
    released_at: Optional[datetime]

    class Config:
        from_attributes = True
