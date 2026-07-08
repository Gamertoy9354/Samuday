import logging
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.marketplace.models import Category

logger = logging.getLogger(__name__)

# Core industry categories to seed for General Marketplace (Pillar 1)
CATEGORIES_TO_SEED = [
    {"name": "Agriculture", "pillar": "marketplace"},
    {"name": "Retail/FMCG", "pillar": "marketplace"},
    {"name": "Fashion", "pillar": "marketplace"},
    {"name": "Electronics", "pillar": "marketplace"},
    {"name": "Home/Construction", "pillar": "marketplace"},
    {"name": "Automobiles", "pillar": "marketplace"},
    {"name": "Health", "pillar": "marketplace"},
    {"name": "Education", "pillar": "marketplace"},
    {"name": "Industrial/B2B", "pillar": "marketplace"},
    {"name": "Events", "pillar": "marketplace"},
    {"name": "Real Estate", "pillar": "marketplace"},
    {"name": "Jobs", "pillar": "marketplace"},
]

async def seed_categories(db: AsyncSession):
    """Seeds root categories into the database, avoiding duplicates."""
    seeded_count = 0
    for cat in CATEGORIES_TO_SEED:
        result = await db.execute(
            select(Category).where(
                and_(
                    Category.name == cat["name"],
                    Category.pillar == cat["pillar"]
                )
            )
        )
        existing = result.scalars().first()
        if not existing:
            new_cat = Category(
                name=cat["name"],
                pillar=cat["pillar"]
            )
            db.add(new_cat)
            seeded_count += 1
            
    if seeded_count > 0:
        await db.commit()
        logger.info(f"Successfully seeded {seeded_count} industry categories.")
    else:
        logger.info("All industry categories already seeded.")
