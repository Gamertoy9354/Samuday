import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from app.core.sms import send_sms_notification
from app.enterprise.models import AuditLog, SupplierProfile
from app.ai.service import parse_voice_to_listing

@pytest.mark.asyncio
async def test_enterprise_scale_and_polish_flow(client: AsyncClient, db_session: AsyncSession):
    # 1. Register Seller (Supplier)
    res_seller = await client.post(
        "/api/v1/identity/auth/register?otp_code=123456",
        json={"phone_number": "+919988776655", "full_name": "Supplier Ramesh", "preferred_language": "en"}
    )
    assert res_seller.status_code == 201
    token_seller = res_seller.json()["access_token"]
    headers_seller = {"Authorization": f"Bearer {token_seller}"}

    me_seller = await client.get("/api/v1/identity/me", headers=headers_seller)
    seller_user_id = me_seller.json()["id"]

    # 2. Register Buyer
    res_buyer = await client.post(
        "/api/v1/identity/auth/register?otp_code=123456",
        json={"phone_number": "+919988776644", "full_name": "Buyer Suresh", "preferred_language": "en"}
    )
    assert res_buyer.status_code == 201
    token_buyer = res_buyer.json()["access_token"]
    headers_buyer = {"Authorization": f"Bearer {token_buyer}"}

    # --- SMS Gateway Verification ---
    sms_sent = send_sms_notification("+919988776655", "Welcome to Samuday Enterprise!")
    assert sms_sent is True


    # --- KYC Audit Log Verification ---
    kyc_res = await client.post(
        "/api/v1/identity/kyc",
        headers=headers_seller,
        json={"id_type": "aadhaar", "document_url": "s3://kyc/supplier-aadhaar.jpg"}
    )
    assert kyc_res.status_code == 201
    
    # Check that an AuditLog entry was automatically generated for kyc_submission
    audit_res = await db_session.execute(select(AuditLog).where(AuditLog.action_type == "kyc_submission"))
    kyc_audit = audit_res.scalars().first()
    assert kyc_audit is not None
    assert str(kyc_audit.actor_id) == kyc_res.json()["user_id"]


    # --- Payment Gateway Integration ---
    # Create checkout session (deposit 10000 paise = 100 INR)
    checkout_res = await client.post(
        "/api/v1/wallet/payment/checkout?amount=10000",
        headers=headers_buyer
    )
    assert checkout_res.status_code == 201
    checkout_data = checkout_res.json()
    assert "checkout_url" in checkout_data
    assert checkout_data["amount"] == 10000
    
    gateway_order_id = checkout_data["gateway_order_id"]
    signature = checkout_data["signature"]

    # Trigger Payment success callback webhook
    callback_res = await client.post(
        f"/api/v1/wallet/payment/callback?gateway_order_id={gateway_order_id}&payment_id=pay_998811&signature={signature}",
        headers=headers_buyer
    )
    assert callback_res.status_code == 200
    assert callback_res.json()["status"] == "success"

    # Confirm buyer's wallet was credited with 10000 paise
    bal_res = await client.get("/api/v1/wallet/balance", headers=headers_buyer)
    assert bal_res.status_code == 200
    assert bal_res.json()["balance"] == 10000

    # Check that an AuditLog entry was generated for wallet_credit
    wallet_audit_res = await db_session.execute(select(AuditLog).where(AuditLog.action_type == "wallet_credit"))
    wallet_audit = wallet_audit_res.scalars().first()
    assert wallet_audit is not None
    assert str(wallet_audit.actor_id) == bal_res.json()["user_id"]


    # --- Supplier Profile & Dashboard Verification ---
    
    # Register Supplier Profile
    supp_profile_res = await client.post(
        "/api/v1/enterprise/supplier/profile",
        headers=headers_seller,
        json={"business_name": "Ramesh Agri Goods Ltd", "gstin": "24ABCDE1234F1Z5"}
    )
    assert supp_profile_res.status_code == 201
    assert supp_profile_res.json()["business_name"] == "Ramesh Agri Goods Ltd"

    # Seed an Agriculture category
    cat_res = await client.post(
        "/api/v1/marketplace/categories",
        headers=headers_seller,
        json={"name": "Agriculture", "pillar": "kisan"}
    )
    assert cat_res.status_code == 201
    category_id = cat_res.json()["id"]

    # Upload Listing (Wheat) via Crop Listing endpoint
    harvest_date_str = datetime.now(timezone.utc).isoformat()
    crop_res = await client.post(
        "/api/v1/kisan/listings/crop",
        headers=headers_seller,
        json={
            "pillar": "kisan",
            "category_id": category_id,
            "title": "Premium Wheat Sharbati",
            "description": "Cleaned, high grade organic wheat.",
            "price": 2000, # 20 INR
            "listing_type": "crop",
            "quantity": 10,
            "unit": "kg",
            "crop_type": "Wheat",
            "grade": "Grade A",
            "harvest_date": harvest_date_str,
            "mandi_price_reference": 220000
        }
    )
    assert crop_res.status_code == 201
    listing_id = crop_res.json()["id"]

    # Place Order (Buyer orders 2 kgs of Wheat, total price = 4000 paise)
    order_res = await client.post(
        "/api/v1/marketplace/orders",
        headers=headers_buyer,
        json={
            "listing_id": listing_id,
            "quantity": 2,
            "fulfillment_type": "seller_delivery"
        }
    )
    assert order_res.status_code == 201
    order_id = order_res.json()["id"]

    # Complete the Order (releasing escrow funds to seller)
    comp_res = await client.post(
        f"/api/v1/marketplace/orders/{order_id}/complete",
        headers=headers_buyer
    )
    assert comp_res.status_code == 200

    # Fetch Supplier Dashboard metrics
    dash_res = await client.get(
        "/api/v1/enterprise/supplier/dashboard",
        headers=headers_seller
    )
    assert dash_res.status_code == 200
    metrics = dash_res.json()
    assert metrics["total_sales_paise"] == 4000
    assert metrics["completed_orders_count"] == 1
    assert metrics["crop_listings_count"] == 1
    assert metrics["active_bookings_count"] == 0


    # --- AI Voice Parser Verification ---
    voice_parse = await parse_voice_to_listing("https://storage.samuday.com/voice/farmer_clip_9.mp3")
    assert voice_parse["crop_type"] == "Wheat"
    assert voice_parse["grade"] == "A"
    assert voice_parse["quantity_kg"] == 500
