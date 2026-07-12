from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from app.core.config import settings

class Base(DeclarativeBase):
    pass

# Async Database engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800
)

# Async Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db():
    """Dependency injection utility for async database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    """Initializes schemas and registers all SQLAlchemy models before creating tables."""
    async with engine.begin() as conn:
        # Create necessary PostgreSQL schemas for modular boundaries
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS identity;"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS wallet;"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS marketplace;"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS kisan;"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS seva;"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS kutumb;"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS enterprise;"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS promotions;"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS shipping;"))

        # Import models locally inside the initialization function to avoid circular imports
        from app.identity.models import Base as IdentityBase
        from app.wallet.models import Base as WalletBase
        from app.marketplace.models import Base as MarketplaceBase
        from app.kisan.models import Base as KisanBase
        from app.seva.models import Base as SevaBase
        from app.kutumb.models import Base as KutumbBase
        from app.enterprise.models import Base as EnterpriseBase
        from app.promotions.models import Base as PromotionsBase
        from app.cart.models import Base as CartBase
        from app.shipping.models import Base as ShippingBase
        
        # Create all tables registered with the Base
        await conn.run_sync(Base.metadata.create_all)

    # Seed initial industry categories
    async with AsyncSessionLocal() as session:
        from app.marketplace.seed import seed_categories
        await seed_categories(session)
