import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, BigInteger, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base

class Wallet(Base):
    __tablename__ = "wallets"
    __table_args__ = {"schema": "wallet"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    balance = Column(BigInteger, default=0, nullable=False)  # stored in paise
    currency = Column(String, default="INR", nullable=False)
    status = Column(String, default="active", nullable=False)  # active, locked
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    entries = relationship("LedgerEntry", back_populates="wallet", cascade="all, delete-orphan")

class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    __table_args__ = {"schema": "wallet"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_id = Column(UUID(as_uuid=True), ForeignKey("wallet.wallets.id", ondelete="CASCADE"), nullable=False)
    amount = Column(BigInteger, nullable=False)  # absolute amount in paise (must be positive)
    direction = Column(String, nullable=False)  # credit or debit
    reference_type = Column(String, nullable=False)  # order, payout, vouch, escrow_hold, etc.
    reference_id = Column(UUID(as_uuid=True), nullable=True)  # polymorphic link to orders/payouts
    balance_after = Column(BigInteger, nullable=False)  # balance snapshot for audit tracing
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    wallet = relationship("Wallet", back_populates="entries")

class PayoutRequest(Base):
    __tablename__ = "payout_requests"
    __table_args__ = {"schema": "wallet"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_id = Column(UUID(as_uuid=True), ForeignKey("wallet.wallets.id", ondelete="CASCADE"), nullable=False)
    amount = Column(BigInteger, nullable=False)
    status = Column(String, default="pending", nullable=False)  # pending, processed, failed
    requested_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    payout_batch_id = Column(UUID(as_uuid=True), nullable=True)

class EscrowHold(Base):
    __tablename__ = "escrow_holds"
    __table_args__ = {"schema": "wallet"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Linked order/transaction UUID (no hard FK to ease future microservice isolation)
    transaction_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    amount = Column(BigInteger, nullable=False)
    status = Column(String, default="held", nullable=False)  # held, released, refunded
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    released_at = Column(DateTime(timezone=True), nullable=True)
