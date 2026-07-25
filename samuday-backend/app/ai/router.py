from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from uuid import UUID

from app.ai import service as ai_service
from app.marketplace import service as market_service
from app.promotions import service as promo_service
from app.core.security import get_current_user
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/ai", tags=["AI Suite"])

# Request / Response Schemas
class GenerateImagesRequest(BaseModel):
    primary_image_url: str
    title: str
    category: Optional[str] = "general"

class GenerateListingRequest(BaseModel):
    short_summary: str
    audio_url: Optional[str] = None
    language: Optional[str] = "en"

class SellerAgentRequest(BaseModel):
    prompt: str

class AutoReplyReviewRequest(BaseModel):
    buyer_name: str
    rating: int
    review_text: str
    product_title: str

class CustomerCopilotRequest(BaseModel):
    query: str
    language: Optional[str] = "en"

class GenerateAdRequest(BaseModel):
    listing_id: UUID


MAX_AUDIO_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Transcribes audio voice record using Groq's Whisper Large V3 API.
    """
    try:
        file_bytes = await file.read()
        if len(file_bytes) > MAX_AUDIO_UPLOAD_BYTES:
            raise HTTPException(status_code=400, detail="Audio file too large (max 10MB).")
        transcription = await ai_service.transcribe_audio_groq(file_bytes, file.filename or "recording.webm")
        return {"text": transcription}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-images")
async def generate_images(req: GenerateImagesRequest, current_user = Depends(get_current_user)):
    """
    Generates 2 additional high-resolution AI variant showcase photos from 1 primary image.
    """
    variants = await ai_service.generate_ai_variant_images(
        primary_image_url=req.primary_image_url,
        title=req.title,
        category=req.category or "general"
    )
    return {"primary_image": req.primary_image_url, "generated_variants": variants}


@router.post("/generate-listing")
async def generate_listing(req: GenerateListingRequest, current_user = Depends(get_current_user)):
    """
    Converts short voice audio or text input (EN, HI, GU) into a full SEO-optimized listing object.
    """
    if not req.short_summary.strip():
        raise HTTPException(status_code=400, detail="Please provide a summary or speak about your product.")

    listing_data = await ai_service.generate_full_seo_listing(
        short_summary=req.short_summary,
        audio_url=req.audio_url,
        lang=req.language or "en"
    )
    return listing_data


@router.post("/seller-agent")
async def seller_agent(req: SellerAgentRequest, current_user = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Interactive AI Seller Diagnostic Agent. Performs diagnostics and runs action tools,
    grounded in the seller's real listings, orders/engagement, and buyer reviews —
    not just listing titles/prices.
    """
    seller_listings = await market_service.get_my_listings(db, current_user.id)
    my_listings = [
        {"id": l.id, "title": l.title, "price": l.price, "quantity": l.quantity, "status": l.status}
        for l in seller_listings
    ]
    reviews = await market_service.get_seller_reviews(db, current_user.id)
    review_analytics = await ai_service.get_review_analytics(reviews)
    orders = await market_service.get_orders_for_user(db, current_user.id, role="seller")

    result = await ai_service.run_seller_agent(req.prompt, my_listings, reviews, review_analytics, orders)
    return result


@router.get("/seller-insights")
async def get_seller_insights(current_user = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Returns real-time AI Insights & live notifications feed for the seller, computed from
    their real listings, orders, sale events, and reviews.
    """
    seller_listings = await market_service.get_my_listings(db, current_user.id)
    my_listings = [
        {"id": l.id, "title": l.title, "price": l.price, "quantity": l.quantity, "status": l.status}
        for l in seller_listings
    ]
    my_sales_orm = await promo_service.get_seller_sale_events(db, current_user.id)
    my_sales = [
        {"id": str(s.id), "title": s.title, "status": s.status, "end_date": s.end_date.isoformat()}
        for s in my_sales_orm
    ]
    orders = await market_service.get_orders_for_user(db, current_user.id, role="seller")
    reviews = await market_service.get_seller_reviews(db, current_user.id)
    review_analytics = await ai_service.get_review_analytics(reviews)

    insights = await ai_service.get_seller_ai_insights(my_listings, my_sales, orders, review_analytics)
    return insights


@router.post("/reviews/auto-reply")
async def auto_reply_review(req: AutoReplyReviewRequest, current_user = Depends(get_current_user)):
    """
    Generates a polite, context-aware AI response to a buyer review.
    """
    reply = await ai_service.auto_reply_buyer_review(
        buyer_name=req.buyer_name,
        rating=req.rating,
        review_text=req.review_text,
        product_title=req.product_title
    )
    return {"ai_reply": reply}


@router.get("/reviews/analytics")
async def get_review_analytics(current_user = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Returns review sentiment score distribution, top praises, and product flaw summaries,
    computed from the current seller's real buyer reviews.
    """
    reviews = await market_service.get_seller_reviews(db, current_user.id)
    analytics = await ai_service.get_review_analytics(reviews)
    return analytics


@router.post("/generate-ad")
async def generate_ad_endpoint(
    req: GenerateAdRequest,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generates a complete ad creative (headline + AI banner image) for one of the
    seller's own listings, so sellers only pick a listing rather than write copy
    or source an image themselves.
    """
    listing = await market_service.get_listing_by_id(db, req.listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only advertise your own listings.")

    primary_image = listing.media[0].media_url if listing.media else None
    creative = await ai_service.generate_ad_creative(listing.title, listing.description, primary_image)
    return {
        "listing_id": str(listing.id),
        "listing_title": listing.title,
        "headline": creative["headline"],
        "image_url": creative["image_url"],
    }


@router.post("/copilot/chat")
async def customer_copilot_chat(req: CustomerCopilotRequest, db: AsyncSession = Depends(get_db)):
    """
    Multilingual Customer AI Shopping Copilot assistant.
    """
    res = await ai_service.customer_shopping_copilot(req.query, db, req.language or "en")
    return res

