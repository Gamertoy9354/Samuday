import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.marketplace.models import Listing, Order, Category, Chat
from app.wallet import service as wallet_service

@pytest.mark.asyncio
async def test_marketplace_order_escrow_chat_flow(client: AsyncClient, db_session: AsyncSession):
    # 1. Register Seller (Hindi language preference)
    seller_res = await client.post(
        "/api/v1/identity/auth/register?otp_code=123456",
        json={"phone_number": "+919876543240", "full_name": "Suresh Kumar", "preferred_language": "hi"}
    )
    token_seller = seller_res.json()["access_token"]
    headers_seller = {"Authorization": f"Bearer {token_seller}"}
    
    # Retrieve seller profile to get ID
    seller_me = await client.get("/api/v1/identity/me", headers=headers_seller)
    seller_id = seller_me.json()["id"]

    # 2. Register Buyer (Gujarati language preference)
    buyer_res = await client.post(
        "/api/v1/identity/auth/register?otp_code=123456",
        json={"phone_number": "+919876543241", "full_name": "Kirit Bhai", "preferred_language": "gu"}
    )
    token_buyer = buyer_res.json()["access_token"]
    headers_buyer = {"Authorization": f"Bearer {token_buyer}"}
    
    # Retrieve buyer profile to get ID and wallet ID
    buyer_me = await client.get("/api/v1/identity/me", headers=headers_buyer)
    buyer_id = buyer_me.json()["id"]

    # Credit Buyer's Wallet with 100 Rupees (10000 Paise)
    buyer_wallet_res = await client.get("/api/v1/wallet/balance", headers=headers_buyer)
    buyer_wallet_id = buyer_wallet_res.json()["id"]
    await wallet_service.record_transaction(
        db_session,
        wallet_id=UUID(buyer_wallet_id),
        amount=10000,
        direction="credit",
        reference_type="deposit"
    )
    await db_session.commit()

    # 3. Create a Category
    cat_res = await client.post(
        "/api/v1/marketplace/categories",
        headers=headers_seller,
        json={"name": "Agricultural Crops", "pillar": "kisan"}
    )
    assert cat_res.status_code == 201
    category_id = cat_res.json()["id"]

    # 4. Create Listing (Seller uploads crop listing at 20 Rupees/kg = 2000 Paise)
    listing_res = await client.post(
        "/api/v1/marketplace/listings",
        headers=headers_seller,
        json={
            "pillar": "kisan",
            "category_id": category_id,
            "title": "Fresh Bajra",
            "description": "High quality millet harvested last week.",
            "price": 2000,
            "listing_type": "crop",
            "quantity": 100,
            "unit": "kg",
            "media_urls": ["http://s3.bucket/bajra.jpg"]
        }
    )
    assert listing_res.status_code == 201
    listing_id = listing_res.json()["id"]

    # 5. Place Order (Buyer orders 3 kgs of Bajra, total price 6000 Paise)
    order_res = await client.post(
        "/api/v1/marketplace/orders",
        headers=headers_buyer,
        json={
            "listing_id": listing_id,
            "quantity": 3,
            "fulfillment_type": "self_pickup"
        }
    )
    assert order_res.status_code == 201
    order_data = order_res.json()
    # total_amount = product_amount (6000) + 5% platform fee (300) = 6300.
    # Platform fee applies regardless of fulfillment type; only delivery_fee_amount
    # is fulfillment-type-dependent (0 for self_pickup).
    assert order_data["product_amount"] == 6000
    assert order_data["platform_fee_amount"] == 300
    assert order_data["total_amount"] == 6300
    assert order_data["status"] == "paid"  # changes to paid immediately as funds enter escrow
    order_id = order_data["id"]

    # Verify Buyer's Wallet debited (10000 - 6300 = 3700)
    buyer_bal = await client.get("/api/v1/wallet/balance", headers=headers_buyer)
    assert buyer_bal.json()["balance"] == 3700

    # Verify Seller's Wallet balance remains unchanged (still 0)
    seller_bal = await client.get("/api/v1/wallet/balance", headers=headers_seller)
    assert seller_bal.json()["balance"] == 0

    # 6. Complete Order (Buyer confirms collection, releasing escrow)
    comp_res = await client.post(
        f"/api/v1/marketplace/orders/{order_id}/complete",
        headers=headers_buyer
    )
    assert comp_res.status_code == 200
    assert comp_res.json()["status"] == "completed"

    # Verify Seller's Wallet credited with 6000 Paise
    seller_bal2 = await client.get("/api/v1/wallet/balance", headers=headers_seller)
    assert seller_bal2.json()["balance"] == 6000

    # 7. Submit Review
    rev_res = await client.post(
        "/api/v1/marketplace/reviews",
        headers=headers_buyer,
        json={
            "order_id": order_id,
            "rating": 5,
            "comment": "Excellent quality Bajra!"
        }
    )
    assert rev_res.status_code == 201
    assert rev_res.json()["rating"] == 5

    # 8. Start Chat Room & Send Message (Multilingual check)
    chat_init = await client.post(
        "/api/v1/marketplace/chats",
        headers=headers_buyer,
        json={"seller_id": seller_id, "listing_id": listing_id}
    )
    assert chat_init.status_code == 201
    chat_id = chat_init.json()["id"]

    # Send message in Gujarati (buyer language) to Hindi seller
    msg_res = await client.post(
        f"/api/v1/marketplace/chats/{chat_id}/messages",
        headers=headers_buyer,
        json={"content": "Ketla vagye aavu?"} # "What time should I come?" in Gujarati
    )
    assert msg_res.status_code == 201
    msg_data = msg_res.json()
    assert msg_data["content"] == "Ketla vagye aavu?"
    # Verify translated_content is mock-translated to Hindi prefix
    assert "नमस्ते (Hindi Translate)" in msg_data["translated_content"]
