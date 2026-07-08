import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.identity.models import KYCRecord
from app.kutumb.models import Family, FamilyMember, CommunityGroup, MatrimonialProfile, UserBlock, UserReport

@pytest.mark.asyncio
async def test_kutumb_network_complete_flow(client: AsyncClient, db_session: AsyncSession):
    # 1. Register User A (Family Head)
    res_a = await client.post(
        "/api/v1/identity/auth/register?otp_code=123456",
        json={"phone_number": "+918811881100", "full_name": "Alok Sharma", "preferred_language": "en"}
    )
    assert res_a.status_code == 201
    token_a = res_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    me_a = await client.get("/api/v1/identity/me", headers=headers_a)
    user_a_id = me_a.json()["id"]

    # 2. Register User B (Spouse candidate)
    res_b = await client.post(
        "/api/v1/identity/auth/register?otp_code=123456",
        json={"phone_number": "+918811881111", "full_name": "Priya Sharma", "preferred_language": "en"}
    )
    assert res_b.status_code == 201
    token_b = res_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}
    
    me_b = await client.get("/api/v1/identity/me", headers=headers_b)
    user_b_id = me_b.json()["id"]

    # 3. Register User C (Matrimonial Candidate - Male)
    res_c = await client.post(
        "/api/v1/identity/auth/register?otp_code=123456",
        json={"phone_number": "+918811881122", "full_name": "Candidate C", "preferred_language": "en"}
    )
    assert res_c.status_code == 201
    token_c = res_c.json()["access_token"]
    headers_c = {"Authorization": f"Bearer {token_c}"}
    
    me_c = await client.get("/api/v1/identity/me", headers=headers_c)
    user_c_id = me_c.json()["id"]

    # --- Family Registry Tests ---
    
    # A. User A creates a family
    fam_res = await client.post(
        "/api/v1/kutumb/families",
        headers=headers_a,
        json={"name": "Sharma Family"}
    )
    assert fam_res.status_code == 201
    family = fam_res.json()
    assert family["name"] == "Sharma Family"
    assert family["head_id"] == user_a_id
    family_id = family["id"]

    # B. User A adds User B as a member
    member_payload = {
        "user_id": user_b_id,
        "relationship_type": "spouse",
        "display_name": "Priya Sharma",
        "visible_phone": False,
        "visible_kyc": False
    }
    mem_res = await client.post(
        f"/api/v1/kutumb/families/{family_id}/members",
        headers=headers_a,
        json=member_payload
    )
    assert mem_res.status_code == 201
    member = mem_res.json()
    assert member["family_id"] == family_id
    assert member["relationship_type"] == "spouse"

    # C. User B (not head) attempts to add a member -> fails with 400
    mem_fail = await client.post(
        f"/api/v1/kutumb/families/{family_id}/members",
        headers=headers_b,
        json={
            "user_id": None,
            "relationship_type": "child",
            "display_name": "Baby Sharma",
            "visible_phone": False,
            "visible_kyc": False
        }
    )
    assert mem_fail.status_code == 400
    assert "Only the family head" in mem_fail.json()["detail"]

    # D. Fetch family details
    my_fam_a = await client.get("/api/v1/kutumb/families/me", headers=headers_a)
    assert my_fam_a.status_code == 200
    assert len(my_fam_a.json()["members"]) == 1

    my_fam_b = await client.get("/api/v1/kutumb/families/me", headers=headers_b)
    assert my_fam_b.status_code == 200
    assert my_fam_b.json()["name"] == "Sharma Family"


    # --- Community Groups Tests ---
    
    g1_res = await client.post(
        "/api/v1/kutumb/groups",
        headers=headers_a,
        json={
            "name": "Gokuldham Society",
            "group_type": "society",
            "description": "Housing society in Mumbai",
            "location_geohash": "te7123"
        }
    )
    assert g1_res.status_code == 201

    g2_res = await client.post(
        "/api/v1/kutumb/groups",
        headers=headers_a,
        json={
            "name": "Ram Mandir Ahmedabad",
            "group_type": "temple",
            "description": "Temple community association",
            "location_geohash": "tsg125"
        }
    )
    assert g2_res.status_code == 201

    # Filter groups by geohash prefixes
    list_te7 = await client.get("/api/v1/kutumb/groups?geohash_prefix=te7")
    assert list_te7.status_code == 200
    assert len(list_te7.json()) == 1
    assert list_te7.json()[0]["name"] == "Gokuldham Society"

    list_tsg = await client.get("/api/v1/kutumb/groups?geohash_prefix=tsg")
    assert list_tsg.status_code == 200
    assert len(list_tsg.json()) == 1
    assert list_tsg.json()[0]["name"] == "Ram Mandir Ahmedabad"


    # --- Matrimonial Registry & Gating Tests ---
    
    # A. Register profile with explicit opt-in False -> fails
    mat_fail = await client.post(
        "/api/v1/kutumb/matrimonial/opt-in",
        headers=headers_b,
        json={
            "gender": "female",
            "birth_date": "2000-01-01T00:00:00Z",
            "religion": "Hindu",
            "caste": "Brahmin",
            "occupation": "Engineer",
            "education": "B.Tech",
            "opt_in_confirmed": False
        }
    )
    assert mat_fail.status_code == 400

    # B. Register profile with opt-in True -> passes. Initially family_verified_badge is False.
    mat_payload = {
        "gender": "female",
        "birth_date": "2000-01-01T00:00:00Z",
        "religion": "Hindu",
        "caste": "Brahmin",
        "occupation": "Engineer",
        "education": "B.Tech",
        "opt_in_confirmed": True
    }
    mat_res_b = await client.post(
        "/api/v1/kutumb/matrimonial/opt-in",
        headers=headers_b,
        json=mat_payload
    )
    assert mat_res_b.status_code == 201
    profile_b = mat_res_b.json()
    assert profile_b["family_verified_badge"] is False

    # C. Submit User A's KYC and approve it directly in DB
    kyc_submit = await client.post(
        "/api/v1/identity/kyc",
        headers=headers_a,
        json={"id_type": "aadhaar", "document_url": "s3://docs/aadhaar.jpg"}
    )
    assert kyc_submit.status_code == 201
    
    result = await db_session.execute(select(KYCRecord).where(KYCRecord.user_id == UUID(user_a_id)))
    kyc_rec = result.scalars().first()
    kyc_rec.verification_status = "approved"
    await db_session.commit()

    # D. Register User C (male) matrimonial profile
    mat_res_c = await client.post(
        "/api/v1/kutumb/matrimonial/opt-in",
        headers=headers_c,
        json={
            "gender": "male",
            "birth_date": "1998-05-15T00:00:00Z",
            "religion": "Hindu",
            "caste": "Brahmin",
            "occupation": "Doctor",
            "education": "MBBS",
            "opt_in_confirmed": True
        }
    )
    assert mat_res_c.status_code == 201

    # E. Register User D (linked to Sharma Family). Since User A is now KYC approved, Dev Sharma should automatically have family_verified_badge=True.
    res_d = await client.post(
        "/api/v1/identity/auth/register?otp_code=123456",
        json={"phone_number": "+918811881133", "full_name": "Dev Sharma", "preferred_language": "en"}
    )
    token_d = res_d.json()["access_token"]
    headers_d = {"Authorization": f"Bearer {token_d}"}
    me_d = await client.get("/api/v1/identity/me", headers=headers_d)
    user_d_id = me_d.json()["id"]

    # Link Dev to Sharma Family
    await client.post(
        f"/api/v1/kutumb/families/{family_id}/members",
        headers=headers_a,
        json={
            "user_id": user_d_id,
            "relationship_type": "sibling",
            "display_name": "Dev Sharma",
            "visible_phone": False,
            "visible_kyc": False
        }
    )

    mat_res_d = await client.post(
        "/api/v1/kutumb/matrimonial/opt-in",
        headers=headers_d,
        json={
            "gender": "male",
            "birth_date": "1995-10-10T00:00:00Z",
            "religion": "Hindu",
            "caste": "Brahmin",
            "occupation": "Lawyer",
            "education": "LLB",
            "opt_in_confirmed": True
        }
    )
    assert mat_res_d.status_code == 201
    assert mat_res_d.json()["family_verified_badge"] is True


    # --- Safety Blocking & Reports Tests ---
    
    # A. Search candidates: User C searches for female matches. User B should appear.
    search_1 = await client.get("/api/v1/kutumb/matrimonial/search?gender=female", headers=headers_c)
    assert search_1.status_code == 200
    assert len(search_1.json()) == 1
    assert search_1.json()[0]["user_id"] == user_b_id

    # B. User B blocks User C
    block_res = await client.post(
        "/api/v1/kutumb/blocks",
        headers=headers_b,
        json={"blocked_user_id": user_c_id}
    )
    assert block_res.status_code == 201

    # C. Search candidates again after block:
    # User C searches for female matches -> User B should NOT appear (gated by blockers)
    search_2 = await client.get("/api/v1/kutumb/matrimonial/search?gender=female", headers=headers_c)
    assert search_2.status_code == 200
    assert len(search_2.json()) == 0

    # User B searches for male matches -> User C should NOT appear (gated by blocks)
    search_3 = await client.get("/api/v1/kutumb/matrimonial/search?gender=male", headers=headers_b)
    assert search_3.status_code == 200
    # User D (Dev Sharma) should still appear since User B only blocked User C
    assert len(search_3.json()) == 1
    assert search_3.json()[0]["user_id"] == user_d_id

    # D. File an abuse report
    report_res = await client.post(
        "/api/v1/kutumb/reports",
        headers=headers_b,
        json={
            "reported_user_id": user_c_id,
            "reason": "Harassment in chat communications"
        }
    )
    assert report_res.status_code == 201
    assert report_res.json()["status"] == "pending"
