import logging
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.middleware import t
from app.wallet.models import Wallet, LedgerEntry, PayoutRequest, EscrowHold

logger = logging.getLogger(__name__)

async def create_wallet(db: AsyncSession, user_id: UUID) -> Wallet:
    """Creates a new INR wallet with zero balance for a registered user."""
    # Ensure wallet does not already exist
    existing = await get_wallet_by_user_id(db, user_id)
    if existing:
        return existing
        
    wallet = Wallet(user_id=user_id, balance=0, currency="INR", status="active")
    db.add(wallet)
    await db.flush()
    return wallet

async def get_wallet_by_user_id(db: AsyncSession, user_id: UUID) -> Optional[Wallet]:
    """Retrieves a user's wallet profile."""
    result = await db.execute(select(Wallet).where(Wallet.user_id == user_id))
    return result.scalars().first()

async def record_transaction(
    db: AsyncSession,
    wallet_id: UUID,
    amount: int,
    direction: str,
    reference_type: str,
    reference_id: Optional[UUID] = None
) -> LedgerEntry:
    """
    Creates a ledger row and updates the wallet balance transactionally.
    Locks the wallet row using SELECT FOR UPDATE to prevent race conditions.
    """
    if amount <= 0:
        raise ValueError("Transaction amount must be greater than zero.")
        
    if direction not in ["credit", "debit"]:
        raise ValueError("Invalid transaction direction.")

    # Acquire write lock on the target wallet row
    result = await db.execute(
        select(Wallet).where(Wallet.id == wallet_id).with_for_update()
    )
    wallet = result.scalars().first()
    if not wallet:
        raise ValueError(t("wallet.not_found"))
        
    if wallet.status != "active":
        raise ValueError("Wallet is suspended or locked.")

    # Check balance and compute new state
    if direction == "debit":
        if wallet.balance < amount:
            raise ValueError(t("wallet.insufficient_balance"))
        wallet.balance -= amount
    else:
        wallet.balance += amount

    # Write audit log to ledger entries
    entry = LedgerEntry(
        wallet_id=wallet_id,
        amount=amount,
        direction=direction,
        reference_type=reference_type,
        reference_id=reference_id,
        balance_after=wallet.balance
    )
    db.add(entry)
    await db.flush()
    return entry

async def transfer_funds(
    db: AsyncSession,
    sender_user_id: UUID,
    receiver_user_id: UUID,
    amount: int,
    reference_type: str,
    reference_id: Optional[UUID] = None
):
    """
    Transfers funds from sender to receiver.
    Locks the wallets in alphabetical UUID order to prevent deadlocks.
    """
    sender_wallet = await get_wallet_by_user_id(db, sender_user_id)
    receiver_wallet = await get_wallet_by_user_id(db, receiver_user_id)
    
    if not sender_wallet or not receiver_wallet:
        raise ValueError("One or both wallets not found.")

    # Sort to avoid deadlock issues when locking multiple rows
    wallet_ids = sorted([sender_wallet.id, receiver_wallet.id])
    
    # Acquire write locks in sorted order
    for w_id in wallet_ids:
        await db.execute(select(Wallet).where(Wallet.id == w_id).with_for_update())

    # Perform debit/credit mutations
    await record_transaction(
        db, sender_wallet.id, amount, "debit", reference_type, reference_id
    )
    await record_transaction(
        db, receiver_wallet.id, amount, "credit", reference_type, reference_id
    )

async def reconcile_wallet(db: AsyncSession, wallet_id: UUID) -> bool:
    """
    Audits the wallet by summing up the credits and debits of all ledger rows.
    Compares the calculated sum with the cached balance.
    """
    # Fetch credits sum
    credit_res = await db.execute(
        select(func.sum(LedgerEntry.amount)).where(
            and_(LedgerEntry.wallet_id == wallet_id, LedgerEntry.direction == "credit")
        )
    )
    credits = credit_res.scalar() or 0
    
    # Fetch debits sum
    debit_res = await db.execute(
        select(func.sum(LedgerEntry.amount)).where(
            and_(LedgerEntry.wallet_id == wallet_id, LedgerEntry.direction == "debit")
        )
    )
    debits = debit_res.scalar() or 0

    computed_balance = credits - debits
    
    # Fetch current balance
    wallet_res = await db.execute(select(Wallet).where(Wallet.id == wallet_id))
    wallet = wallet_res.scalars().first()
    
    if not wallet:
        return False
        
    is_reconciled = (wallet.balance == computed_balance)
    if not is_reconciled:
        logger.critical(
            f"RECONCILIATION FAILURE on Wallet {wallet_id}. "
            f"Cached Balance: {wallet.balance}, Calculated Ledger Sum: {computed_balance}"
        )
    return is_reconciled

async def create_payout_request(db: AsyncSession, user_id: UUID, amount: int) -> PayoutRequest:
    """Deducts requested payout from wallet and places in pending payout batch queue."""
    wallet = await get_wallet_by_user_id(db, user_id)
    if not wallet:
        raise ValueError(t("wallet.not_found"))
        
    # Debit amount immediately to hold funds
    await record_transaction(
        db, wallet.id, amount, "debit", "payout_request"
    )
    
    payout = PayoutRequest(
        wallet_id=wallet.id,
        amount=amount,
        status="pending"
    )
    db.add(payout)
    await db.commit()
    await db.refresh(payout)
    return payout

async def hold_escrow(db: AsyncSession, buyer_id: UUID, amount: int, transaction_id: UUID) -> EscrowHold:
    """Locks buyer's funds by moving them out of their balance into an escrow hold ledger row."""
    buyer_wallet = await get_wallet_by_user_id(db, buyer_id)
    if not buyer_wallet:
         raise ValueError("Buyer wallet not found.")

    # Debit buyer wallet
    await record_transaction(
        db, buyer_wallet.id, amount, "debit", "escrow_hold", transaction_id
    )

    # Record the hold status
    hold = EscrowHold(
        transaction_id=transaction_id,
        amount=amount,
        status="held"
    )
    db.add(hold)
    await db.flush()
    return hold

async def release_escrow(
    db: AsyncSession,
    transaction_id: UUID,
    seller_id: UUID,
    platform_fee_amount: int = 0,
    delivery_fee_amount: int = 0,
) -> EscrowHold:
    """
    Releases the locked escrow amount on order completion, split three ways:
    - seller gets the product amount (hold.amount minus the two fee amounts below)
    - the platform house wallet gets platform_fee_amount (real Samuday revenue)
    - the platform house wallet also gets delivery_fee_amount, tracked under a
      separate reference_type since it's a pass-through liability owed to the
      courier, not platform profit, once real Delhivery billing is connected.
    """
    from app.marketplace.fees import PLATFORM_HOUSE_USER_ID

    res = await db.execute(
        select(EscrowHold).where(
            and_(EscrowHold.transaction_id == transaction_id, EscrowHold.status == "held")
        ).with_for_update()
    )
    hold = res.scalars().first()
    if not hold:
        raise ValueError("No active escrow hold found for this transaction.")

    seller_wallet = await get_wallet_by_user_id(db, seller_id)
    if not seller_wallet:
        raise ValueError("Seller wallet not found.")

    seller_amount = hold.amount - platform_fee_amount - delivery_fee_amount
    if seller_amount < 0:
        raise ValueError("Fee amounts exceed the escrowed total.")

    if seller_amount > 0:
        await record_transaction(
            db, seller_wallet.id, seller_amount, "credit", "escrow_release", transaction_id
        )

    if platform_fee_amount > 0 or delivery_fee_amount > 0:
        house_wallet = await get_wallet_by_user_id(db, PLATFORM_HOUSE_USER_ID)
        if not house_wallet:
            raise ValueError("Platform house wallet not found.")
        if platform_fee_amount > 0:
            await record_transaction(
                db, house_wallet.id, platform_fee_amount, "credit", "platform_fee", transaction_id
            )
        if delivery_fee_amount > 0:
            await record_transaction(
                db, house_wallet.id, delivery_fee_amount, "credit", "delivery_fee_collected", transaction_id
            )

    hold.status = "released"
    hold.released_at = datetime.now(timezone.utc)
    return hold

async def refund_escrow(db: AsyncSession, transaction_id: UUID, buyer_id: UUID) -> EscrowHold:
    """Refunds the locked escrow amount back to the buyer."""
    res = await db.execute(
        select(EscrowHold).where(
            and_(EscrowHold.transaction_id == transaction_id, EscrowHold.status == "held")
        ).with_for_update()
    )
    hold = res.scalars().first()
    if not hold:
        raise ValueError("No active escrow hold found for this transaction.")

    buyer_wallet = await get_wallet_by_user_id(db, buyer_id)
    if not buyer_wallet:
        raise ValueError("Buyer wallet not found.")

    # Credit buyer's wallet back
    await record_transaction(
        db, buyer_wallet.id, hold.amount, "credit", "escrow_refund", transaction_id
    )

    hold.status = "refunded"
    hold.released_at = datetime.now(timezone.utc)
    return hold
