from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

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


@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Transcribes audio voice record using Groq's Whisper Large V3 API.
    """
    try:
        file_bytes = await file.read()
        transcription = await ai_service.transcribe_audio_groq(file_bytes, file.filename or "recording.webm")
        return {"text": transcription}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-images")
async def generate_images(req: GenerateImagesRequest):
    """
    Generates 3 additional high-resolution AI variant showcase photos from 1 primary image.
    """
    variants = await ai_service.generate_ai_variant_images(
        primary_image_url=req.primary_image_url,
        title=req.title,
        category=req.category or "general"
    )
    return {"primary_image": req.primary_image_url, "generated_variants": variants}


@router.post("/generate-listing")
async def generate_listing(req: GenerateListingRequest):
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
    Interactive AI Seller Diagnostic Agent. Performs diagnostics and runs action tools.
    """
    all_listings = await market_service.get_all_listings(db)
    my_listings = [
        {"id": l.id, "title": l.title, "price": l.price, "quantity": l.quantity}
        for l in all_listings if l.seller_id == current_user.id
    ]
        
    result = await ai_service.run_seller_agent(req.prompt, my_listings)
    return result


@router.get("/seller-insights")
async def get_seller_insights(current_user = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Returns real-time AI Insights & live notifications feed for the seller.
    """
    all_listings = await market_service.get_all_listings(db)
    my_listings = [l for l in all_listings if l.seller_id == current_user.id]
    my_sales = await promo_service.get_seller_sale_events(db, current_user.id)
        
    insights = await ai_service.get_seller_ai_insights(my_listings, my_sales)
    return insights


@router.post("/reviews/auto-reply")
async def auto_reply_review(req: AutoReplyReviewRequest):
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
async def get_review_analytics():
    """
    Returns review sentiment score distribution, top praises, and product flaw summaries.
    """
    analytics = await ai_service.get_review_analytics([])
    return analytics


@router.post("/copilot/chat")
async def customer_copilot_chat(req: CustomerCopilotRequest, db: AsyncSession = Depends(get_db)):
    """
    Multilingual Customer AI Shopping Copilot assistant.
    """
    res = await ai_service.customer_shopping_copilot(req.query, db, req.language or "en")
    return res

