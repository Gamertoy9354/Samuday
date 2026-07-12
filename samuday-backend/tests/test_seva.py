import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.identity.models import User

@pytest.mark.asyncio
async def test_seva_directory_complete_flow(client: AsyncClient, db_session: AsyncSession):
    # 1. Register User 1 (Medical Provider)
    prov1_res = await client.post(
        "/api/v1/identity/auth/register?otp_code=123456",
        json={"phone_number": "+918800112233", "full_name": "Dr. Amit Shah", "preferred_language": "en"}
    )
    assert prov1_res.status_code == 201
    token_prov1 = prov1_res.json()["access_token"]
    headers_prov1 = {"Authorization": f"Bearer {token_prov1}"}

    # 2. Register User 2 (Legal Provider)
    prov2_res = await client.post(
        "/api/v1/identity/auth/register?otp_code=123456",
        json={"phone_number": "+918800112244", "full_name": "Aditya Verma", "preferred_language": "hi"}
    )
    assert prov2_res.status_code == 201
    token_prov2 = prov2_res.json()["access_token"]
    headers_prov2 = {"Authorization": f"Bearer {token_prov2}"}

    # 3. Register User 3 (Reviewer / Seeker)
    seeker_res = await client.post(
        "/api/v1/identity/auth/register?otp_code=123456",
        json={"phone_number": "+918800112255", "full_name": "Rohan Patel", "preferred_language": "gu"}
    )
    assert seeker_res.status_code == 201
    token_seeker = seeker_res.json()["access_token"]
    headers_seeker = {"Authorization": f"Bearer {token_seeker}"}

    # 4. Onboard Medical Provider (Subsidized healthcare clinic)
    med_payload = {
        "name": "Jan Kalyan Clinic",
        "description": "Providing subsidized medical checkups and generic medicines to community members",
        "provider_type": "subsidized",
        "category": "medical",
        "location_geohash": "tsg123"
    }
    med_prov_res = await client.post(
        "/api/v1/seva/providers",
        headers=headers_prov1,
        json=med_payload
    )
    assert med_prov_res.status_code == 201
    med_provider = med_prov_res.json()
    assert med_provider["name"] == "Jan Kalyan Clinic"
    assert med_provider["provider_type"] == "subsidized"
    assert med_provider["is_verified"] is False
    med_provider_id = med_provider["id"]

    # 5. Onboard Legal Provider (Free legal assistance)
    legal_payload = {
        "name": "Community Legal Aid",
        "description": "Free consultation for land disputes and civil matters",
        "provider_type": "free",
        "category": "legal",
        "location_geohash": "tsg124"
    }
    legal_prov_res = await client.post(
        "/api/v1/seva/providers",
        headers=headers_prov2,
        json=legal_payload
    )
    assert legal_prov_res.status_code == 201
    legal_provider = legal_prov_res.json()
    assert legal_provider["provider_type"] == "free"
    legal_provider_id = legal_provider["id"]

    # 6. Submit License Credentials for Medical Provider
    cred_payload = {
        "license_number": "MED-REG-99281-GJ",
        "credential_type": "medical",
        "document_url": "https://storage.samuday.com/docs/med-reg-99281.pdf"
    }
    cred_res = await client.post(
        f"/api/v1/seva/providers/{med_provider_id}/credentials",
        headers=headers_prov1,
        json=cred_payload
    )
    assert cred_res.status_code == 201
    credential = cred_res.json()
    assert credential["license_number"] == "MED-REG-99281-GJ"  # Decrypted response
    assert credential["status"] == "pending"
    credential_id = credential["id"]

    # 7. Admin Approves License Credentials (promote the seeker to admin for this check)
    seeker_me = await client.get("/api/v1/identity/me", headers=headers_seeker)
    seeker_id = seeker_me.json()["id"]
    seeker_result = await db_session.execute(select(User).where(User.id == UUID(seeker_id)))
    admin_user = seeker_result.scalars().first()
    admin_user.is_admin = True
    await db_session.commit()
    admin_headers = headers_seeker
    verify_res = await client.post(
        f"/api/v1/seva/admin/credentials/{credential_id}/verify?admin_action=approved",
        headers=admin_headers
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["status"] == "approved"

    # Confirm medical provider status toggled to is_verified=True
    providers_list = await client.get("/api/v1/seva/providers?category=medical")
    assert providers_list.status_code == 200
    med_prov_updated = next(p for p in providers_list.json() if p["id"] == med_provider_id)
    assert med_prov_updated["is_verified"] is True

    # 8. Log Outcome-Based Review from Seeker
    review_payload = {
        "rating": 5,
        "comment": "Doctor diagnosed my cough and medicines solved it in 3 days!",
        "verified_outcome": True  # Successfully solved the issue!
    }
    review_res = await client.post(
        f"/api/v1/seva/providers/{med_provider_id}/reviews",
        headers=headers_seeker,
        json=review_payload
    )
    assert review_res.status_code == 201
    review = review_res.json()
    assert review["rating"] == 5
    assert review["verified_outcome"] is True

    # Fetch reviews list
    reviews_list = await client.get(f"/api/v1/seva/providers/{med_provider_id}/reviews")
    assert reviews_list.status_code == 200
    assert len(reviews_list.json()) == 1

    # 9. Test Natural-Language Needs Search (multilingual keywords)
    # A. English Search: "I need a doctor in my neighborhood" -> Classifies to category=medical
    search_eng = await client.get("/api/v1/seva/providers?q=I need a doctor in my neighborhood")
    assert search_eng.status_code == 200
    assert len(search_eng.json()) >= 1
    assert any(p["id"] == med_provider_id for p in search_eng.json())

    # B. Gujarati Search: "વકીલ ની મદદ જોઈએ છે" -> Classifies to category=legal
    search_gu = await client.get("/api/v1/seva/providers?q=વકીલ ની મદદ જોઈએ છે")
    assert search_gu.status_code == 200
    assert len(search_gu.json()) >= 1
    assert any(p["id"] == legal_provider_id for p in search_gu.json())

    # C. Hindi Search: "मुफ्त वकील की सलाह" -> Classifies to category=legal, type=free
    search_hi = await client.get("/api/v1/seva/providers?q=मुफ्त वकील की सलाह")
    assert search_hi.status_code == 200
    assert len(search_hi.json()) >= 1
    assert any(p["id"] == legal_provider_id for p in search_hi.json())
