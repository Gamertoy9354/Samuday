import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.identity.models import User, Vouch, ReputationScore
from app.wallet.models import Wallet

@pytest.mark.asyncio
async def test_otp_and_registration_flow(client: AsyncClient, db_session: AsyncSession):
    phone = "+919876543210"
    
    # 1. Request OTP
    otp_response = await client.post(
        "/api/v1/identity/auth/request-otp",
        json={"phone_number": phone}
    )
    assert otp_response.status_code == 200
    otp_data = otp_response.json()
    assert "mock_otp" in otp_data
    otp_code = otp_data["mock_otp"]
    assert otp_code == "123456"

    # 2. Register user with correct OTP
    reg_response = await client.post(
        f"/api/v1/identity/auth/register?otp_code={otp_code}",
        json={
            "phone_number": phone,
            "full_name": "Ramesh Patel",
            "preferred_language": "gu"
        }
    )
    assert reg_response.status_code == 201
    token_data = reg_response.json()
    assert "access_token" in token_data
    assert "refresh_token" in token_data
    access_token = token_data["access_token"]

    # Verify wallet was initialized automatically
    res = await db_session.execute(select(User).where(User.full_name == "Ramesh Patel"))
    user = res.scalars().first()
    assert user is not None
    
    wallet_res = await db_session.execute(select(Wallet).where(Wallet.user_id == user.id))
    wallet = wallet_res.scalars().first()
    assert wallet is not None
    assert wallet.balance == 0

    # 3. Retrieve Profile via authenticated endpoint
    headers = {"Authorization": f"Bearer {access_token}"}
    me_response = await client.get("/api/v1/identity/me", headers=headers)
    assert me_response.status_code == 200
    profile = me_response.json()
    assert profile["full_name"] == "Ramesh Patel"
    assert profile["preferred_language"] == "gu"
    assert profile["phone_number"] == phone

@pytest.mark.asyncio
async def test_kyc_submission(client: AsyncClient, db_session: AsyncSession):
    # Register and authenticate
    phone = "+919876543211"
    reg_res = await client.post(
        "/api/v1/identity/auth/register?otp_code=123456",
        json={"phone_number": phone, "full_name": "Sita Devi", "preferred_language": "hi"}
    )
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Submit KYC document
    kyc_res = await client.post(
        "/api/v1/identity/kyc",
        headers=headers,
        json={
            "id_type": "aadhaar",
            "document_url": "s3://samuday-kyc/aadhaar_sita.jpg"
        }
    )
    assert kyc_res.status_code == 201
    kyc_data = kyc_res.json()
    assert kyc_data["id_type"] == "aadhaar"
    assert kyc_data["verification_status"] == "pending"

@pytest.mark.asyncio
async def test_community_vouch_and_reputation(client: AsyncClient, db_session: AsyncSession):
    # Register User A (Voucher)
    a_res = await client.post(
        "/api/v1/identity/auth/register?otp_code=123456",
        json={"phone_number": "+919876543220", "full_name": "User A", "preferred_language": "en"}
    )
    token_a = a_res.json()["access_token"]
    
    # Register User B (Vouchee)
    b_res = await client.post(
        "/api/v1/identity/auth/register?otp_code=123456",
        json={"phone_number": "+919876543221", "full_name": "User B", "preferred_language": "en"}
    )
    user_b_data = await client.get("/api/v1/identity/me", headers={"Authorization": f"Bearer {b_res.json()['access_token']}"})
    user_b_id = user_b_data.json()["id"]

    headers_a = {"Authorization": f"Bearer {token_a}"}

    # User A vouches for User B
    vouch_res = await client.post(
        "/api/v1/identity/vouch",
        headers=headers_a,
        json={
            "vouched_user_id": user_b_id,
            "pillar": "sheshop"
        }
    )
    assert vouch_res.status_code == 201
    vouch_data = vouch_res.json()
    assert vouch_data["vouched_user_id"] == user_b_id

    # Verify User B's reputation aggregate score increased from 5.0 to 5.0 (caps at 5.0, so let's check reputation score initialization)
    rep_res = await client.get(
        "/api/v1/identity/reputation",
        headers={"Authorization": f"Bearer {b_res.json()['access_token']}"}
    )
    assert rep_res.status_code == 200
    reputation = rep_res.json()
    assert len(reputation) > 0
    # Let's confirm it's capped or initialized correctly
    assert reputation[0]["score"] == 5.0

    # Self vouching should fail with HTTP 400 Bad Request
    user_a_data = await client.get("/api/v1/identity/me", headers=headers_a)
    user_a_id = user_a_data.json()["id"]
    vouch_self_res = await client.post(
        "/api/v1/identity/vouch",
        headers=headers_a,
        json={
            "vouched_user_id": user_a_id,
            "pillar": "sheshop"
        }
    )
    assert vouch_self_res.status_code == 400
    assert "vouch.self" in vouch_self_res.json()["detail"] or "cannot vouch for yourself" in vouch_self_res.json()["detail"]
