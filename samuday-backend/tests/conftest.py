import os
import pytest
import pytest_asyncio
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text

from app.core.database import Base, init_db, get_db
from app.core.config import settings
from app.main import app
from httpx import AsyncClient, ASGITransport

# Use the environment database URL for test suite execution
engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

@pytest.fixture(scope="session")
def event_loop():
    """Custom event loop fixture to run session-scoped async setup blocks."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Initializes schemas and database tables once before executing tests."""
    # This fixture runs `TRUNCATE ... CASCADE` on identity.users (and everything
    # keyed off it: wallets, KYC, orders, listings...) directly against whatever
    # DATABASE_URL points to. There is no separate test database in this project.
    # TRUNCATE is unconditional — it deletes EVERY row, including real accounts
    # created by actually logging into the app (Google Sign-In etc.), not just
    # seeded demo data. This has already happened once and wiped a real user's
    # account with no way to recover it. Require explicit, well-understood opt-in.
    if os.environ.get("ALLOW_TEST_DB_TRUNCATE", "").lower() not in ("1", "true", "yes"):
        pytest.exit(
            "Refusing to run: this test suite deletes ALL rows in identity.users "
            "(and everything cascading from it — wallets, KYC, orders, listings) "
            "on DATABASE_URL. If that's the shared SAMUDAY Supabase project, this "
            "will destroy real user accounts, not just demo data, with no way to "
            "recover them. Only set ALLOW_TEST_DB_TRUNCATE=1 if DATABASE_URL points "
            "at a disposable test database, or if you have explicitly confirmed "
            "with the project owner that destroying all current accounts is fine "
            "right now. Afterwards, re-run `python -m app.seed_demo` to restore "
            "the demo catalog (this does NOT restore any real user accounts).",
            returncode=1
        )

    await init_db()

    # Use a separate temporary engine on the session loop to clean up tables
    # without initializing the module-level engine's connection pool.
    temp_engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async with temp_engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE identity.vouches CASCADE;"))
        await conn.execute(text("TRUNCATE TABLE identity.reputation_scores CASCADE;"))
        await conn.execute(text("TRUNCATE TABLE identity.kyc_records CASCADE;"))
        await conn.execute(text("TRUNCATE TABLE identity.users CASCADE;"))
        await conn.execute(text("TRUNCATE TABLE wallet.wallets CASCADE;"))
        await conn.execute(text("TRUNCATE TABLE wallet.ledger_entries CASCADE;"))
        await conn.execute(text("TRUNCATE TABLE wallet.payout_requests CASCADE;"))
        await conn.execute(text("TRUNCATE TABLE wallet.escrow_holds CASCADE;"))
        await conn.execute(text("TRUNCATE TABLE wallet.payment_orders CASCADE;"))
        await conn.execute(text("TRUNCATE TABLE enterprise.supplier_profiles CASCADE;"))
        await conn.execute(text("TRUNCATE TABLE enterprise.audit_logs CASCADE;"))
        await conn.execute(text("TRUNCATE TABLE kutumb.families CASCADE;"))
        await conn.execute(text("TRUNCATE TABLE kutumb.family_members CASCADE;"))
        await conn.execute(text("TRUNCATE TABLE kutumb.community_groups CASCADE;"))
        await conn.execute(text("TRUNCATE TABLE kutumb.matrimonial_profiles CASCADE;"))
        await conn.execute(text("TRUNCATE TABLE kutumb.user_blocks CASCADE;"))
        await conn.execute(text("TRUNCATE TABLE kutumb.user_reports CASCADE;"))
        await conn.execute(text("TRUNCATE TABLE seva.service_providers CASCADE;"))
        await conn.execute(text("TRUNCATE TABLE seva.provider_credentials CASCADE;"))
        await conn.execute(text("TRUNCATE TABLE seva.seva_reviews CASCADE;"))
        await conn.execute(text("TRUNCATE TABLE kisan.crop_listings CASCADE;"))
        await conn.execute(text("TRUNCATE TABLE kisan.equipment_listings CASCADE;"))
        await conn.execute(text("TRUNCATE TABLE kisan.loan_applications CASCADE;"))
        await conn.execute(text("TRUNCATE TABLE kisan.advisory_sessions CASCADE;"))
        await conn.execute(text("TRUNCATE TABLE marketplace.orders CASCADE;"))
        await conn.execute(text("TRUNCATE TABLE marketplace.listing_media CASCADE;"))
        await conn.execute(text("TRUNCATE TABLE marketplace.listings CASCADE;"))
        await conn.execute(text("TRUNCATE TABLE marketplace.cart_items CASCADE;"))
        await conn.execute(text("TRUNCATE TABLE promotions.sale_events CASCADE;"))
        await conn.execute(text("TRUNCATE TABLE promotions.advertisements CASCADE;"))

        # Bootstrap the platform "house" account that accrues platform/delivery
        # fee revenue on order completion (app/marketplace/fees.py). Without it,
        # release_escrow raises "Platform house wallet not found" for every order
        # test, since the TRUNCATEs above just wiped identity.users/wallet.wallets.
        from app.marketplace.fees import PLATFORM_HOUSE_USER_ID
        await conn.execute(text("""
            INSERT INTO identity.users (id, full_name, email, is_seller, is_admin, preferred_language, status, seller_verification_status, created_at)
            VALUES (:id, 'Samuday Platform (House Account)', 'platform@samuday.internal', false, true, 'en', 'active', 'approved', now())
        """), {"id": str(PLATFORM_HOUSE_USER_ID)})
        await conn.execute(text("""
            INSERT INTO wallet.wallets (id, user_id, balance, currency, status, created_at)
            VALUES (gen_random_uuid(), :id, 0, 'INR', 'active', now())
        """), {"id": str(PLATFORM_HOUSE_USER_ID)})
    await temp_engine.dispose()
    yield
    # Truncate tables for cleanup is handled per test using rolling-back transactions

@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Creates an async database session for a test.
    Wraps the operations inside a transaction block and issues a ROLLBACK on completion
    to guarantee test isolation.
    """
    async with AsyncSessionLocal() as session:
        # Wrap in a transaction
        await session.begin()
        yield session
        await session.rollback()

@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Returns an async HTTP client for API requests, overriding database dependencies."""
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    
    # Configure ASGI transport to route HTTP requests directly to FastAPI
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
        
    app.dependency_overrides.clear()
