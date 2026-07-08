import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.core.security import get_current_user
from app.wallet.models import Wallet, LedgerEntry, PayoutRequest
from app.wallet import service

@pytest.mark.asyncio
async def test_wallet_transactions_and_reconciliation(client: AsyncClient, db_session: AsyncSession):
    # 1. Register a user
    phone = "+919876543230"
    reg_res = await client.post(
        "/api/v1/identity/auth/register?otp_code=123456",
        json={"phone_number": phone, "full_name": "Karan Johar", "preferred_language": "en"}
    )
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Retrieve current user profile to get user ID
    me_res = await client.get("/api/v1/identity/me", headers=headers)
    user_id = me_res.json()["id"]

    # 2. Check initial balance (should be 0)
    bal_res = await client.get("/api/v1/wallet/balance", headers=headers)
    assert bal_res.status_code == 200
    wallet_data = bal_res.json()
    assert wallet_data["balance"] == 0
    wallet_id = wallet_data["id"]

    # 3. Credit wallet via service level (simulate payment gateway deposit)
    # Deposit 500 Rupees = 50000 Paise
    await service.record_transaction(
        db_session,
        wallet_id=UUID(wallet_id),
        amount=50000,
        direction="credit",
        reference_type="deposit"
    )
    await db_session.commit()

    # Verify updated balance via API
    bal_res2 = await client.get("/api/v1/wallet/balance", headers=headers)
    assert bal_res2.json()["balance"] == 50000

    # 4. Debit wallet (simulate listing purchase)
    # Deduct 150 Rupees = 15000 Paise
    await service.record_transaction(
        db_session,
        wallet_id=UUID(wallet_id),
        amount=15000,
        direction="debit",
        reference_type="purchase"
    )
    await db_session.commit()

    # Verify updated balance
    bal_res3 = await client.get("/api/v1/wallet/balance", headers=headers)
    assert bal_res3.json()["balance"] == 35000

    # 5. Overdraft failure path
    with pytest.raises(ValueError) as exc:
        await service.record_transaction(
            db_session,
            wallet_id=UUID(wallet_id),
            amount=40000, # exceeds 35000
            direction="debit",
            reference_type="purchase"
        )
    assert "wallet.insufficient_balance" in str(exc.value) or "Insufficient wallet balance" in str(exc.value)

    # 6. Reconcile ledger
    is_reconciled = await service.reconcile_wallet(db_session, UUID(wallet_id))
    assert is_reconciled is True

    # 7. Request Payout via API
    payout_res = await client.post(
        "/api/v1/wallet/payout",
        headers=headers,
        json={"amount": 10000} # 100 Rupees
    )
    assert payout_res.status_code == 201
    payout_data = payout_res.json()
    assert payout_data["amount"] == 10000
    assert payout_data["status"] == "pending"

    # Verify balance has been debited by 10000 (35000 - 10000 = 25000)
    bal_res4 = await client.get("/api/v1/wallet/balance", headers=headers)
    assert bal_res4.json()["balance"] == 25000

    # 8. Query Ledger Statement via API
    ledger_res = await client.get("/api/v1/wallet/ledger", headers=headers)
    assert ledger_res.status_code == 200
    ledger_entries = ledger_res.json()
    # Should have: deposit (credit), purchase (debit), payout_request (debit)
    assert len(ledger_entries) == 3
    assert ledger_entries[0]["reference_type"] == "payout_request"
    assert ledger_entries[0]["direction"] == "debit"
    assert ledger_entries[0]["balance_after"] == 25000
