import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

@pytest.mark.asyncio
async def test_kisan_hub_complete_flow(client: AsyncClient, db_session: AsyncSession):
    # 1. Register Farmer/Seller with Gujarati language preference
    farmer_res = await client.post(
        "/api/v1/identity/auth/register?otp_code=123456",
        json={"phone_number": "+919900990099", "full_name": "Ramesh Patel", "preferred_language": "gu"}
    )
    assert farmer_res.status_code == 201
    token_farmer = farmer_res.json()["access_token"]
    headers_farmer = {"Authorization": f"Bearer {token_farmer}"}

    # 2. Get Seeded Categories and find 'Agriculture'
    cat_res = await client.get("/api/v1/marketplace/categories")
    assert cat_res.status_code == 200
    categories = cat_res.json()
    assert len(categories) >= 12
    
    agri_cat = next((c for c in categories if c["name"] == "Agriculture"), None)
    assert agri_cat is not None
    agri_cat_id = agri_cat["id"]

    # 3. Create a Crop Listing via kisan endpoint
    harvest_date_str = datetime.now(timezone.utc).isoformat()
    crop_payload = {
        "category_id": agri_cat_id,
        "title": "Organic Premium Wheat Harvest",
        "description": "High-quality GW-496 wheat grains from organic farm",
        "price": 2400,  # 24 INR in paise
        "listing_type": "sell",
        "quantity": 500,
        "unit": "kg",
        "pillar": "kisan",
        "crop_type": "Wheat",
        "grade": "Grade A",
        "harvest_date": harvest_date_str,
        "mandi_price_reference": 220000  # 2200 INR per quintal reference
    }
    
    crop_res = await client.post(
        "/api/v1/kisan/listings/crop",
        headers=headers_farmer,
        json=crop_payload
    )
    assert crop_res.status_code == 201
    crop_data = crop_res.json()
    assert crop_data["crop_type"] == "Wheat"
    assert crop_data["grade"] == "Grade A"
    assert crop_data["price"] == 2400

    # Retrieve all crop listings
    all_crops = await client.get("/api/v1/kisan/listings/crop")
    assert all_crops.status_code == 200
    assert len(all_crops.json()) >= 1
    assert any(c["title"] == "Organic Premium Wheat Harvest" for c in all_crops.json())

    # 4. Create an Equipment Rental Listing
    rental_payload = {
        "category_id": agri_cat_id,
        "title": "John Deere Tractor for Rental",
        "description": "75 HP Tractor available for field ploughing",
        "price": 120000,  # 1200 INR in paise per hour
        "listing_type": "rent",
        "quantity": 1,
        "unit": "hour",
        "pillar": "kisan",
        "equipment_type": "Tractor",
        "rental_unit": "per_hour",
        "operator_included": True
    }
    
    rental_res = await client.post(
        "/api/v1/kisan/listings/equipment",
        headers=headers_farmer,
        json=rental_payload
    )
    assert rental_res.status_code == 201
    rental_data = rental_res.json()
    assert rental_data["equipment_type"] == "Tractor"
    assert rental_data["rental_unit"] == "per_hour"
    assert rental_data["operator_included"] is True

    # Retrieve all equipment listings
    all_equip = await client.get("/api/v1/kisan/listings/equipment")
    assert all_equip.status_code == 200
    assert len(all_equip.json()) >= 1

    # 5. Fetch Mandi Reference Prices
    mandi_res = await client.get("/api/v1/kisan/mandi-prices?crop_type=Wheat")
    assert mandi_res.status_code == 200
    mandi_data = mandi_res.json()
    assert len(mandi_data) >= 2
    assert any(m["mandi"] == "Ahmedabad Mandi" for m in mandi_data)

    # 6. Apply for a Farmer Micro-Loan
    loan_payload = {
        "amount_requested": 4500000,  # 45,000 INR
        "purpose": "Seed GW-496 purchase and organic compost procurement"
    }
    loan_res = await client.post(
        "/api/v1/kisan/loans/apply",
        headers=headers_farmer,
        json=loan_payload
    )
    assert loan_res.status_code == 201
    loan_data = loan_res.json()
    assert loan_data["status"] == "pending"
    assert loan_data["amount_requested"] == 4500000
    assert loan_data["lender_partner_id"] is not None

    # Get farmer loans
    loans_list = await client.get("/api/v1/kisan/loans", headers=headers_farmer)
    assert loans_list.status_code == 200
    assert len(loans_list.json()) == 1

    # 7. Agricultural Advisory Chatbot (Gujarati response)
    chat_payload = {"query_text": "પાણી ની જરૂરિયાત શું છે?"}
    chat_res = await client.post(
        "/api/v1/kisan/advisory/chat",
        headers=headers_farmer,
        json=chat_payload
    )
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert "સિંચાઈ મહત્વપૂર્ણ છે" in chat_data["response_text"]

    # 8. Register Hindi Farmer to test Hindi advisory responses
    farmer_hi_res = await client.post(
        "/api/v1/identity/auth/register?otp_code=123456",
        json={"phone_number": "+919900990088", "full_name": "Rajesh Kumar", "preferred_language": "hi"}
    )
    assert farmer_hi_res.status_code == 201
    token_farmer_hi = farmer_hi_res.json()["access_token"]
    headers_farmer_hi = {"Authorization": f"Bearer {token_farmer_hi}"}

    chat_hi_res = await client.post(
        "/api/v1/kisan/advisory/chat",
        headers=headers_farmer_hi,
        json={"query_text": "बीज के बारे में जानकारी दें"}
    )
    assert chat_hi_res.status_code == 200
    chat_hi_data = chat_hi_res.json()
    assert "बीज किस्मों का चयन करें" in chat_hi_data["response_text"]
