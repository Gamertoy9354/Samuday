import logging
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID, uuid4
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.marketplace.models import Listing
from app.marketplace.service import create_listing
from app.kisan.models import CropListing, EquipmentListing, LoanApplication, AdvisorySession
from app.kisan.schemas import CropListingCreate, EquipmentListingCreate, LoanApplicationCreate

logger = logging.getLogger(__name__)

# --- Listings Creation & Queries ---

async def create_crop_listing(db: AsyncSession, seller_id: UUID, crop_in: CropListingCreate) -> Listing:
    """Creates a standard listing and links crop grading/harvest specifications in one transaction."""
    # 1. Create standard listing
    listing = await create_listing(db, seller_id, crop_in)
    
    # 2. Save crop specifics
    crop_details = CropListing(
        listing_id=listing.id,
        crop_type=crop_in.crop_type,
        grade=crop_in.grade,
        harvest_date=crop_in.harvest_date,
        mandi_price_reference=crop_in.mandi_price_reference
    )
    db.add(crop_details)
    await db.commit()

    # Reload with relationships preloaded
    result = await db.execute(
        select(Listing)
        .options(selectinload(Listing.media), selectinload(Listing.crop_details))
        .where(Listing.id == listing.id)
    )
    return result.scalars().first()

async def create_equipment_listing(db: AsyncSession, seller_id: UUID, equip_in: EquipmentListingCreate) -> Listing:
    """Creates a rental machinery listing and links details transactionally."""
    # 1. Create standard listing
    listing = await create_listing(db, seller_id, equip_in)

    # 2. Save equipment details
    equip_details = EquipmentListing(
        listing_id=listing.id,
        equipment_type=equip_in.equipment_type,
        rental_unit=equip_in.rental_unit,
        operator_included=equip_in.operator_included
    )
    db.add(equip_details)
    await db.commit()

    # Reload with relationships
    result = await db.execute(
        select(Listing)
        .options(selectinload(Listing.media), selectinload(Listing.equipment_details))
        .where(Listing.id == listing.id)
    )
    return result.scalars().first()

async def get_crop_listings(db: AsyncSession) -> List[Listing]:
    """Queries all active crop listings."""
    result = await db.execute(
        select(Listing)
        .options(selectinload(Listing.media), selectinload(Listing.crop_details))
        .join(CropListing, Listing.id == CropListing.listing_id)
        .where(Listing.status == "active")
    )
    return list(result.scalars().all())

async def get_equipment_listings(db: AsyncSession) -> List[Listing]:
    """Queries all active machinery equipment listings."""
    result = await db.execute(
        select(Listing)
        .options(selectinload(Listing.media), selectinload(Listing.equipment_details))
        .join(EquipmentListing, Listing.id == EquipmentListing.listing_id)
        .where(Listing.status == "active")
    )
    return list(result.scalars().all())


# --- Mandi Prices (Mock e-NAM) ---

MOCK_MANDI_PRICES = [
    {"crop_type": "Wheat", "mandi": "Ahmedabad Mandi", "price_per_quintal": 220000, "state": "Gujarat", "updated_at": "2026-07-04"},
    {"crop_type": "Wheat", "mandi": "Indore Mandi", "price_per_quintal": 215000, "state": "Madhya Pradesh", "updated_at": "2026-07-04"},
    {"crop_type": "Cotton", "mandi": "Rajkot Mandi", "price_per_quintal": 720000, "state": "Gujarat", "updated_at": "2026-07-04"},
    {"crop_type": "Rice", "mandi": "Karnal Mandi", "price_per_quintal": 310000, "state": "Haryana", "updated_at": "2026-07-04"},
    {"crop_type": "Bajra", "mandi": "Mehsana Mandi", "price_per_quintal": 195000, "state": "Gujarat", "updated_at": "2026-07-04"},
]

def get_mandi_prices(crop_type: Optional[str] = None) -> List[dict]:
    """Returns mock mandi reference price feeds."""
    if crop_type:
        return [item for item in MOCK_MANDI_PRICES if item["crop_type"].lower() == crop_type.lower()]
    return MOCK_MANDI_PRICES


# --- Farmer Loan Applications ---

async def create_loan_application(db: AsyncSession, farmer_id: UUID, loan_in: LoanApplicationCreate) -> LoanApplication:
    """Submits a farmer micro-credit application, routing it to a mock lending partner."""
    application = LoanApplication(
        farmer_id=farmer_id,
        amount_requested=loan_in.amount_requested,
        purpose=loan_in.purpose,
        lender_partner_id=uuid4(),  # Mock lending partner UUID assignment
        status="pending"
    )
    db.add(application)
    await db.commit()
    await db.refresh(application)
    return application

async def get_loan_applications(db: AsyncSession, farmer_id: UUID) -> List[LoanApplication]:
    """Queries all credit application files filed by a specific farmer."""
    result = await db.execute(select(LoanApplication).where(LoanApplication.farmer_id == farmer_id))
    return list(result.scalars().all())


# --- Crop Advisory Chatbot ---

ADVISORY_RESPONSES = {
    "en": {
        "water": "For crops like wheat, irrigation is critical during the crown root initiation (CRI) stage (approx 21 days after sowing). Maintain moist but not flooded soil.",
        "seeds": "Choose certified high-yield seed varieties like GW-496 or GW-322 for Gujarat dry sowing. Ensure seed treatment with thiram before planting.",
        "pest": "For aphid control in millet/bajra, spray Neem seed kernel extract (NSKE 5%) or apply dimethoate 30 EC if pest threshold exceeds 10 per leaf.",
        "default": "Welcome to Kisan Hub Advisory. Please ask about irrigation (water), seeds, or pest control, and we will guide you."
    },
    "hi": {
        "water": "गेहूं जैसी फसलों के लिए, ताज जड़ दीक्षा (CRI) चरण (बुवाई के लगभग 21 दिन बाद) के दौरान सिंचाई महत्वपूर्ण है। मिट्टी को नम रखें लेकिन पानी का भराव न होने दें।",
        "seeds": "गुजरात की सूखी बुवाई के लिए GW-496 या GW-322 जैसी प्रमाणित उच्च उपज वाली बीज किस्मों का चयन करें। रोपण से पहले थीरम के साथ बीज उपचार सुनिश्चित करें।",
        "pest": "बाजरा में एफिड (माहू) नियंत्रण के लिए, नीम के बीज की गिरी का अर्क (NSKE 5%) स्प्रे करें या डिमेथोएट 30 EC का उपयोग करें।",
        "default": "किसान हब सलाहकार में आपका स्वागत है। कृपया सिंचाई (पानी), बीज या कीट नियंत्रण के बारे में पूछें, और हम आपका मार्गदर्शन करेंगे।"
    },
    "gu": {
        "water": "ઘઉં જેવા પાક માટે, વાવણીના આશરે ૨૧ દિવસ પછી મુગટ મૂળની શરૂઆત (CRI) ના તબક્કા દરમિયાન સિંચાઈ મહત્વપૂર્ણ છે. જમીન ભેજવાળી રાખો, પણ પાણી ભરાવા ન દો.",
        "seeds": "ગુજરાતમાં સૂકી વાવણી માટે GW-496 અથવા GW-322 જેવી પ્રમાણિત બિયારણ જાતો પસંદ કરો. વાવણી પહેલાં થીરામ દવાથી બીજ માવજત કરો.",
        "pest": "બાજરીમાં મોલોમશી (અફિડ) ના નિયંત્રણ માટે, લીમડાના તેલ અથવા લીંબોળીના અર્ક (NSKE 5%) નો છંટકાવ કરવો અથવા ડાયમેથોએટ ૩૦ EC દવાનો ઉપયોગ કરવો.",
        "default": "કિસાન હબ સલાહકારમાં આપનું સ્વાગત છે. કૃપા કરીને સિંચાઈ (પાણી), બિયારણ અથવા જીવાત નિયંત્રણ વિશે પૂછો અને અમે તમને માર્ગદર્શન આપીશું."
    }
}

async def get_crop_advisor_response(db: AsyncSession, farmer_id: UUID, query: str) -> AdvisorySession:
    """
    Context-aware agricultural advisory chatbot.
    Detects user language and answers queries related to water, seeds, or pests.
    Logs the conversation session in the database.
    """
    from app.identity.service import get_user_by_id
    user = await get_user_by_id(db, farmer_id)
    lang = user.preferred_language if user else "en"
    if lang not in ["en", "hi", "gu"]:
        lang = "en"

    # Simple keyword routing
    clean_query = query.lower()
    resp_key = "default"
    if "water" in clean_query or "irrigation" in clean_query or "પાણી" in clean_query or "सिंचाई" in clean_query:
        resp_key = "water"
    elif "seed" in clean_query or "variety" in clean_query or "બીજ" in clean_query or "બિયારણ" in clean_query or "बीज" in clean_query:
        resp_key = "seeds"
    elif "pest" in clean_query or "disease" in clean_query or "insect" in clean_query or "જીવાત" in clean_query or "કીટ" in clean_query or "कीट" in clean_query:
        resp_key = "pest"

    response_text = ADVISORY_RESPONSES[lang][resp_key]

    session = AdvisorySession(
        farmer_id=farmer_id,
        query_text=query,
        response_text=response_text
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session
