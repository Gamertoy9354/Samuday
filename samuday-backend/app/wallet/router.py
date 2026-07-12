from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.middleware import t
from app.identity.models import User
from app.wallet import service
from app.wallet.models import LedgerEntry
from app.wallet.schemas import (
    WalletResponse, LedgerEntryResponse, PayoutRequestCreate, PayoutRequestResponse
)

router = APIRouter(prefix="/wallet", tags=["Wallet & Ledger"])

@router.get("/balance", response_model=WalletResponse)
async def get_balance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves current user's wallet profile and balance."""
    wallet = await service.get_wallet_by_user_id(db, current_user.id)
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=t("wallet.not_found")
        )
    return wallet

@router.get("/ledger", response_model=List[LedgerEntryResponse])
async def get_ledger(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves paginated ledger entries (credits and debits) for the caller."""
    wallet = await service.get_wallet_by_user_id(db, current_user.id)
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=t("wallet.not_found")
        )
        
    offset = (page - 1) * page_size
    query = (
        select(LedgerEntry)
        .where(LedgerEntry.wallet_id == wallet.id)
        .order_by(desc(LedgerEntry.created_at))
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(query)
    entries = result.scalars().all()
    return list(entries)

@router.post("/payout", response_model=PayoutRequestResponse, status_code=status.HTTP_201_CREATED)
async def request_payout(
    payload: PayoutRequestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Initiates a payout request, locking and deducting the funds from the wallet balance."""
    try:
        payout = await service.create_payout_request(db, current_user.id, payload.amount)
        return payout
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# --- Payment Gateway Checkout & Webhook Callbacks ---

@router.post("/payment/checkout", status_code=status.HTTP_201_CREATED)
async def create_payment_checkout_endpoint(
    amount: int = Query(..., ge=1, description="Amount to deposit in paise"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generates a payment order and a checkout redirect URL."""
    from app.wallet import payment
    checkout = await payment.create_payment_checkout(db, amount, current_user.id)
    return checkout

@router.post("/payment/callback")
async def verify_payment_callback_endpoint(
    gateway_order_id: str = Query(...),
    payment_id: str = Query(...),
    signature: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Processes successful checkout callbacks and credits the wallet balance.
    The credited amount is always the one fixed at checkout time, never client input."""
    from app.wallet import payment
    credited_amount = await payment.callback_payment_verification(
        db=db,
        gateway_order_id=gateway_order_id,
        payment_id=payment_id,
        signature=signature,
        user_id=current_user.id,
    )
    if credited_amount is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment verification failed"
        )

    # Audit log credit
    try:
        from app.enterprise.service import log_audit_action
        await log_audit_action(
            db=db,
            action_type="wallet_credit",
            actor_id=current_user.id,
            entity_id=current_user.id,
            metadata_dict={"amount_paise": credited_amount}
        )
        await db.commit()
    except Exception as e:
        # Ignore audit log failures to prevent blocking core payment credits
        pass

    return {"status": "success", "message": "Funds successfully credited to wallet balance"}
