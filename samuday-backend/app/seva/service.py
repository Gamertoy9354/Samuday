import logging
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import encrypt_pii, decrypt_pii
from app.seva.models import ServiceProvider, ProviderCredential, SevaReview
from app.seva.schemas import ServiceProviderCreate, ProviderCredentialCreate, SevaReviewCreate

logger = logging.getLogger(__name__)

# --- Provider Services ---

async def create_service_provider(db: AsyncSession, user_id: UUID, provider_in: ServiceProviderCreate) -> ServiceProvider:
    """Registers a new service provider under the seva directory."""
    provider = ServiceProvider(
        user_id=user_id,
        name=provider_in.name,
        description=provider_in.description,
        provider_type=provider_in.provider_type,
        category=provider_in.category,
        location_geohash=provider_in.location_geohash,
        is_verified=False
    )
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    return provider

async def get_service_providers(
    db: AsyncSession,
    q: Optional[str] = None,
    provider_type: Optional[str] = None,
    category: Optional[str] = None
) -> List[ServiceProvider]:
    """
    Retrieves service providers, supporting standard category filters or 
    natural-language need-based query searches classified by the AI.
    """
    db_query = select(ServiceProvider)

    if q:
        from app.ai.service import classify_seva_query
        ai_classification = await classify_seva_query(q)
        inferred_cat = ai_classification["inferred_category"]
        inferred_type = ai_classification["inferred_provider_type"]

        conditions = []
        if inferred_cat != "general":
            conditions.append(ServiceProvider.category == inferred_cat)
        else:
            # Fallback to direct name/description matches
            conditions.append(
                or_(
                    ServiceProvider.name.ilike(f"%{q}%"),
                    ServiceProvider.description.ilike(f"%{q}%")
                )
            )

        if inferred_type:
            conditions.append(ServiceProvider.provider_type == inferred_type)

        db_query = db_query.where(and_(*conditions))
    else:
        # Standard filter logic
        if provider_type:
            db_query = db_query.where(ServiceProvider.provider_type == provider_type)
        if category:
            db_query = db_query.where(ServiceProvider.category == category)

    result = await db.execute(db_query)
    return list(result.scalars().all())


# --- Credential Verification Workflow ---

async def submit_provider_credentials(
    db: AsyncSession,
    provider_id: UUID,
    cred_in: ProviderCredentialCreate
) -> ProviderCredential:
    """Submits licensing credentials for a provider. Encrypts the license number at rest."""
    encrypted_license = encrypt_pii(cred_in.license_number)
    
    credential = ProviderCredential(
        provider_id=provider_id,
        license_number=encrypted_license,
        credential_type=cred_in.credential_type,
        document_url=cred_in.document_url,
        status="pending"
    )
    db.add(credential)
    await db.commit()
    await db.refresh(credential)
    return credential

async def verify_provider_credential(
    db: AsyncSession,
    credential_id: UUID,
    status: str  # approved, rejected
) -> Optional[ProviderCredential]:
    """Admin workflow: Approves or rejects a credential submission. Approvals toggle is_verified=True on the provider."""
    result = await db.execute(select(ProviderCredential).where(ProviderCredential.id == credential_id))
    credential = result.scalars().first()
    if not credential:
        return None

    credential.status = status
    credential.verified_at = datetime.now(timezone.utc)

    if status == "approved":
        # Toggle provider's verified badge
        prov_result = await db.execute(select(ServiceProvider).where(ServiceProvider.id == credential.provider_id))
        provider = prov_result.scalars().first()
        if provider:
            provider.is_verified = True

    await db.commit()
    await db.refresh(credential)
    return credential


# --- Outcome Reviews ---

async def add_seva_review(
    db: AsyncSession,
    reviewer_id: UUID,
    provider_id: UUID,
    review_in: SevaReviewCreate
) -> SevaReview:
    """Logs a review rating alongside a verified outcome Boolean flag."""
    review = SevaReview(
        provider_id=provider_id,
        reviewer_id=reviewer_id,
        rating=review_in.rating,
        comment=review_in.comment,
        verified_outcome=review_in.verified_outcome
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return review

async def get_provider_reviews(db: AsyncSession, provider_id: UUID) -> List[SevaReview]:
    """Retrieves all reviews logged for a specific provider."""
    result = await db.execute(select(SevaReview).where(SevaReview.provider_id == provider_id))
    return list(result.scalars().all())
