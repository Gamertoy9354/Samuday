from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin_user, decrypt_pii
from app.identity.models import User
from app.seva.models import ProviderCredential
from app.seva import service
from app.seva.schemas import (
    ServiceProviderCreate, ServiceProviderResponse,
    ProviderCredentialCreate, ProviderCredentialResponse,
    SevaReviewCreate, SevaReviewResponse
)

router = APIRouter(prefix="/seva", tags=["Seva Directory"])

def map_credential_response(credential: ProviderCredential) -> ProviderCredentialResponse:
    """Helper to decrypt and return credential details securely."""
    decrypted_license = decrypt_pii(credential.license_number)
    return ProviderCredentialResponse(
        id=credential.id,
        provider_id=credential.provider_id,
        license_number=decrypted_license,
        credential_type=credential.credential_type,
        document_url=credential.document_url,
        status=credential.status,
        verified_at=credential.verified_at,
        created_at=credential.created_at
    )


# --- Service Provider Endpoints ---

@router.post("/providers", response_model=ServiceProviderResponse, status_code=status.HTTP_201_CREATED)
async def onboard_provider_route(
    payload: ServiceProviderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Onboards the logged-in user as a service provider in the Seva Directory."""
    # Check if provider type is valid
    if payload.provider_type not in ["free", "subsidized", "for_profit"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="provider_type must be one of 'free', 'subsidized', or 'for_profit'"
        )
    provider = await service.create_service_provider(db, current_user.id, payload)
    return provider

@router.get("/providers", response_model=List[ServiceProviderResponse])
async def search_providers_route(
    q: Optional[str] = Query(None, description="Natural language needs query, e.g. 'vakeel madad'"),
    provider_type: Optional[str] = Query(None, description="Filter by free, subsidized, or for_profit"),
    category: Optional[str] = Query(None, description="Filter by medical, legal, food, education, ngo"),
    db: AsyncSession = Depends(get_db)
):
    """Lists and searches service providers, supporting natural-language AI query classification."""
    providers = await service.get_service_providers(db, q, provider_type, category)
    return providers


# --- Credential Verification Endpoints ---

@router.post("/providers/{provider_id}/credentials", response_model=ProviderCredentialResponse, status_code=status.HTTP_201_CREATED)
async def submit_credentials_route(
    provider_id: UUID,
    payload: ProviderCredentialCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Files professional certification credentials for verification. Only the provider owner may submit."""
    try:
        credential = await service.submit_provider_credentials(db, provider_id, payload, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    return map_credential_response(credential)

@router.post("/admin/credentials/{credential_id}/verify", response_model=ProviderCredentialResponse)
async def verify_credential_route(
    credential_id: UUID,
    admin_action: str = Query(..., description="Action to perform: 'approved' or 'rejected'"),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Admin-only endpoint to approve or reject a pending professional credential."""
    if admin_action not in ["approved", "rejected"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="admin_action must be 'approved' or 'rejected'"
        )
    credential = await service.verify_provider_credential(db, credential_id, admin_action)
    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider credential not found"
        )
    return map_credential_response(credential)


# --- Outcome Reviews Endpoints ---

@router.post("/providers/{provider_id}/reviews", response_model=SevaReviewResponse, status_code=status.HTTP_201_CREATED)
async def add_review_route(
    provider_id: UUID,
    payload: SevaReviewCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Submits an outcome-oriented review rating for a service provider."""
    review = await service.add_seva_review(db, current_user.id, provider_id, payload)
    return review

@router.get("/providers/{provider_id}/reviews", response_model=List[SevaReviewResponse])
async def get_reviews_route(
    provider_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Retrieves all reviews logged for a specific service provider."""
    reviews = await service.get_provider_reviews(db, provider_id)
    return reviews
