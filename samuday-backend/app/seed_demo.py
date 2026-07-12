"""
Massive demo seed script for Samuday Marketplace.
Seeds 60+ products across all categories with real Unsplash images, 
demo sale events, and demo advertisements.
Run: python -m app.seed_demo
"""
import asyncio
import uuid
import json
import random
from datetime import datetime, timezone, timedelta

from app.core.database import AsyncSessionLocal, init_db
from app.identity.models import User
from app.marketplace.models import Category, Listing, ListingMedia
from app.promotions.models import SaleEvent, Advertisement
from app.wallet.models import Wallet
from sqlalchemy import select

# Unsplash image URLs for different categories (real, free images)
IMAGES = {
    "electronics": [
        "https://images.unsplash.com/photo-1498049794561-7780e7231661?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1484704849700-f032a568e944?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1546868871-af0de0ae72be?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1583394838336-acd977736f90?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1585386959984-a4155224a1ad?w=400&h=400&fit=crop",
    ],
    "fashion": [
        "https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1434389677669-e08b4cda3a21?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1549298916-b41d501d3772?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1556306535-0f09a537f0a3?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1591047139829-d91aecb6caea?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=400&fit=crop",
    ],
    "agriculture": [
        "https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1625246333195-78d9c38ad449?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1592982537447-6f2a6a0c8b32?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1464226184884-fa280b87c399?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1500595046743-cd271d694d30?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1530507629858-e4977d30e9e0?w=400&h=400&fit=crop",
    ],
    "home": [
        "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1524758631624-e2822e304c36?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1583847268964-b28dc8f51f92?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1513694203232-719a280e022f?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1550581190-9c1c48d21d6c?w=400&h=400&fit=crop",
    ],
    "health": [
        "https://images.unsplash.com/photo-1505751172876-fa1923c5c528?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1559839914-17aae19cec71?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1607619056574-7b8d3ee536b2?w=400&h=400&fit=crop",
    ],
    "auto": [
        "https://images.unsplash.com/photo-1511919884226-fd3cad34687c?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1558618666-fcd25c85f82e?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1449965408869-eaa3f722e40d?w=400&h=400&fit=crop",
    ],
    "education": [
        "https://images.unsplash.com/photo-1503676260728-1c00da094a0b?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1497633762265-9d179a990aa6?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1513475382585-d06e58bcb0e0?w=400&h=400&fit=crop",
    ],
    "grocery": [
        "https://images.unsplash.com/photo-1542838132-92c53300491e?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1553546895-531931aa1aa8?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1607349913338-fca6f7fc608a?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1534723452862-4c874018d66d?w=400&h=400&fit=crop",
        "https://images.unsplash.com/photo-1590779033100-9f60a05a013d?w=400&h=400&fit=crop",
    ],
    "banner": [
        "https://images.unsplash.com/photo-1607082348824-0a96f2a4b9da?w=1200&h=400&fit=crop",
        "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=1200&h=400&fit=crop",
        "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=1200&h=400&fit=crop",
        "https://images.unsplash.com/photo-1607083206869-4c7672e72a8a?w=1200&h=400&fit=crop",
        "https://images.unsplash.com/photo-1472851294608-062f824d29cc?w=1200&h=400&fit=crop",
    ],
}

# Demo seller ID (we'll create a system seller)
SYSTEM_SELLER_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")

# Product catalog with category mapping
DEMO_PRODUCTS = [
    # Electronics
    {"title": "Samsung Galaxy S24 Ultra 256GB", "desc": "Latest flagship smartphone with AI-powered camera, titanium frame, and S Pen. 200MP main camera, Snapdragon 8 Gen 3.", "price": 12999900, "cat": "Electronics", "img": "electronics", "rating": 4.5, "reviews": 2847},
    {"title": "Sony WH-1000XM5 Wireless Headphones", "desc": "Industry-leading noise cancellation with 30hr battery life. Premium sound quality with LDAC support.", "price": 2499000, "cat": "Electronics", "img": "electronics", "rating": 4.7, "reviews": 5621},
    {"title": "Apple MacBook Air M3 15-inch", "desc": "Supercharged by M3 chip with 18hr battery. Liquid Retina display, 8GB RAM, 256GB SSD.", "price": 13499900, "cat": "Electronics", "img": "electronics", "rating": 4.8, "reviews": 1293},
    {"title": "JBL Charge 5 Bluetooth Speaker", "desc": "Portable waterproof speaker with 20hr playtime. IP67 rated, powerbank function built-in.", "price": 1299900, "cat": "Electronics", "img": "electronics", "rating": 4.6, "reviews": 8934},
    {"title": "Boat Airdopes 141 TWS Earbuds", "desc": "Wireless earbuds with 42hr total playback, ENx noise cancellation, IPX4 water resistance.", "price": 129900, "cat": "Electronics", "img": "electronics", "rating": 4.1, "reviews": 45231},
    {"title": "Canon EOS R50 Mirrorless Camera", "desc": "24.2MP APS-C sensor, 4K video, subject detection AF. Perfect for content creators.", "price": 6999900, "cat": "Electronics", "img": "electronics", "rating": 4.4, "reviews": 876},

    # Fashion
    {"title": "Levi's 511 Slim Fit Jeans - Dark Indigo", "desc": "Classic slim fit stretch denim. Sits below waist, slim through hip and thigh. 98% cotton, 2% elastane.", "price": 279900, "cat": "Fashion", "img": "fashion", "rating": 4.3, "reviews": 12543},
    {"title": "Nike Air Max 270 Running Shoes", "desc": "Max Air unit delivers unrivaled comfort. Mesh upper for breathability. Foam midsole.", "price": 1299700, "cat": "Fashion", "img": "fashion", "rating": 4.5, "reviews": 8765},
    {"title": "Raymond Premium Cotton Formal Shirt", "desc": "100% Giza cotton, wrinkle-free finish. Regular fit, full sleeves, spread collar.", "price": 179900, "cat": "Fashion", "img": "fashion", "rating": 4.2, "reviews": 3421},
    {"title": "Fastrack Analog Watch for Men", "desc": "Stainless steel case with leather strap. Water resistant 30m. Quartz movement.", "price": 249900, "cat": "Fashion", "img": "fashion", "rating": 4.0, "reviews": 7654},
    {"title": "Wildcraft Unisex Travel Backpack 45L", "desc": "Durable polyester with rain cover. Multiple compartments, padded laptop sleeve, chest strap.", "price": 259900, "cat": "Fashion", "img": "fashion", "rating": 4.4, "reviews": 5432},

    # Agriculture
    {"title": "Organic Sharbati Wheat - 50kg Bag", "desc": "Premium hand-harvested organic wheat from Madhya Pradesh. Grade A certified, naturally sun-dried.", "price": 220000, "cat": "Agriculture", "img": "agriculture", "rating": 4.8, "reviews": 234},
    {"title": "Fresh Alphonso Mangoes - 5kg Box", "desc": "Ratnagiri Alphonso mangoes. Naturally ripened, chemical-free. GI tagged product.", "price": 150000, "cat": "Agriculture", "img": "agriculture", "rating": 4.9, "reviews": 567},
    {"title": "Organic Basmati Rice - 25kg", "desc": "Extra-long grain aged basmati. Aromatic, non-sticky. Certified organic from Punjab farms.", "price": 350000, "cat": "Agriculture", "img": "agriculture", "rating": 4.7, "reviews": 1234},
    {"title": "Cold-Pressed Groundnut Oil - 5L", "desc": "Traditional ghani-pressed peanut oil. No chemicals, no preservatives. Farm-to-kitchen.", "price": 89900, "cat": "Agriculture", "img": "agriculture", "rating": 4.6, "reviews": 890},
    {"title": "Organic A2 Cow Ghee - 1kg", "desc": "Bilona method pure A2 ghee from Gir cows. Rich aroma, golden color. No additives.", "price": 129900, "cat": "Agriculture", "img": "agriculture", "rating": 4.9, "reviews": 2345},

    # Home/Construction
    {"title": "Prestige Iris 750W Mixer Grinder", "desc": "3 stainless steel jars with flow breaker. Super efficient motor, anti-skid feet.", "price": 299900, "cat": "Home/Construction", "img": "home", "rating": 4.3, "reviews": 7890},
    {"title": "Sleepwell Ortho Pro Spring Mattress - Queen", "desc": "6-inch Bonnell spring mattress. Medium firm support, knitted fabric cover. 5-year warranty.", "price": 1299900, "cat": "Home/Construction", "img": "home", "rating": 4.5, "reviews": 3456},
    {"title": "Philips 43-inch 4K Smart TV", "desc": "Ultra HD LED TV with Dolby Vision, Android TV. Google Assistant built-in, Chromecast.", "price": 2999900, "cat": "Home/Construction", "img": "home", "rating": 4.4, "reviews": 6543},
    {"title": "Havells 1200mm Ceiling Fan - Brown", "desc": "400 RPM, energy efficient BLDC motor. Silent operation, remote control, 5-star rated.", "price": 349900, "cat": "Home/Construction", "img": "home", "rating": 4.2, "reviews": 4567},
    {"title": "Milton Thermosteel Flask 1L", "desc": "24hr hot & cold insulation. 18/8 stainless steel, BPA-free. Leak-proof cap.", "price": 89900, "cat": "Home/Construction", "img": "home", "rating": 4.4, "reviews": 12345},

    # Health
    {"title": "Himalaya Neem Face Wash 200ml", "desc": "Natural neem and turmeric formula. Soap-free, prevents pimples. For all skin types.", "price": 19900, "cat": "Health", "img": "health", "rating": 4.3, "reviews": 23456},
    {"title": "Dr. Morepen BP Monitor (Digital)", "desc": "Fully automatic blood pressure monitor. WHO indicator, irregular heartbeat detection.", "price": 149900, "cat": "Health", "img": "health", "rating": 4.2, "reviews": 8765},
    {"title": "Patanjali Chyawanprash 1kg", "desc": "Ayurvedic immunity booster with 40+ herbs. Natural honey base, vitamin C enriched.", "price": 29900, "cat": "Health", "img": "health", "rating": 4.0, "reviews": 12345},
    {"title": "Boldfit Yoga Mat 6mm Extra Thick", "desc": "Anti-slip TPE material, eco-friendly. Includes carry strap. 72x24 inches.", "price": 79900, "cat": "Health", "img": "health", "rating": 4.5, "reviews": 6789},
    {"title": "Muscle Blaze Whey Protein 2kg", "desc": "25g protein per serving, 5.5g BCAA. Chocolate flavour. Lab tested for purity.", "price": 299900, "cat": "Health", "img": "health", "rating": 4.3, "reviews": 9876},

    # Automobiles
    {"title": "Ceat SecuraDrive Tyre 185/65 R15", "desc": "All-season radial tyre with superior wet grip. Reinforced sidewall, 5-year warranty.", "price": 499900, "cat": "Automobiles", "img": "auto", "rating": 4.4, "reviews": 2345},
    {"title": "Bosch Car Battery 12V 65Ah", "desc": "Maintenance-free lead acid battery. High cranking power for Indian conditions. 48-month warranty.", "price": 699900, "cat": "Automobiles", "img": "auto", "rating": 4.3, "reviews": 1234},
    {"title": "3M Car Dashboard Polish Kit", "desc": "Premium auto detailing kit. Includes dashboard polish, glass cleaner, tyre shine, microfibre cloth.", "price": 89900, "cat": "Automobiles", "img": "auto", "rating": 4.1, "reviews": 5678},
    {"title": "Philips H4 LED Car Headlight Bulbs", "desc": "200% brighter than halogen. 6500K cool white, plug-and-play. IP65 waterproof.", "price": 349900, "cat": "Automobiles", "img": "auto", "rating": 4.5, "reviews": 3456},
    {"title": "Steelbird SBA-7 7Days Full Face Helmet", "desc": "High impact ABS shell, breathable padding. Quick release visor mechanism. ISI certified safety.", "price": 189900, "cat": "Automobiles", "img": "auto", "rating": 4.4, "reviews": 8769},

    # Education
    {"title": "NCERT Mathematics Class 12 Textbook", "desc": "Official NCERT publication. Complete syllabus coverage with solved examples and exercises.", "price": 34900, "cat": "Education", "img": "education", "rating": 4.6, "reviews": 45678},
    {"title": "HP 15s Intel i5 Laptop (Student Edition)", "desc": "12th Gen Intel i5, 8GB RAM, 512GB SSD. 15.6\" FHD, Windows 11. Perfect for students.", "price": 5499900, "cat": "Education", "img": "education", "rating": 4.4, "reviews": 5678},
    {"title": "Casio FX-991ES Plus Scientific Calculator", "desc": "417 functions, natural display. Solar + battery powered. Essential for engineering exams.", "price": 119900, "cat": "Education", "img": "education", "rating": 4.7, "reviews": 23456},
    {"title": "Classmate Premium 6-Subject Notebook", "desc": "300 pages ruled notebook. 70 GSM paper, spiral bound. Six colour-coded sections.", "price": 24900, "cat": "Education", "img": "education", "rating": 4.2, "reviews": 12345},
    {"title": "Parker Vector Matte Black Fountain Pen", "desc": "Stainless steel nib, smooth ink flow. Professional executive design, gift-boxed.", "price": 54900, "cat": "Education", "img": "education", "rating": 4.3, "reviews": 1234},

    # Retail/FMCG
    {"title": "Tata Tea Gold 1kg Pack", "desc": "15% long leaf blend for richer taste. Premium Assam tea with natural flavour.", "price": 49900, "cat": "Retail/FMCG", "img": "grocery", "rating": 4.4, "reviews": 34567},
    {"title": "Aashirvaad Atta 10kg", "desc": "100% whole wheat flour. 0% maida content. Soft rotis every time. Farm-fresh wheat.", "price": 54900, "cat": "Retail/FMCG", "img": "grocery", "rating": 4.5, "reviews": 56789},
    {"title": "Amul Butter 500g Carton", "desc": "Made from fresh cream. Rich and creamy taste. Perfect for spreading and cooking.", "price": 27500, "cat": "Retail/FMCG", "img": "grocery", "rating": 4.6, "reviews": 78901},
    {"title": "Surf Excel Easy Wash 4kg", "desc": "Tough stain removal in bucket wash. Dissolves easily, gentle on hands and fabrics.", "price": 59900, "cat": "Retail/FMCG", "img": "grocery", "rating": 4.3, "reviews": 23456},
    {"title": "Cadbury Dairy Milk Silk Gift Pack", "desc": "Assorted chocolate gift box. Includes Silk Oreo, Roast Almond, Fruit & Nut. 300g total.", "price": 39900, "cat": "Retail/FMCG", "img": "grocery", "rating": 4.7, "reviews": 45678},

    # Industrial/B2B
    {"title": "Crompton 0.5HP Water Pump Motor", "desc": "Self-priming monoblock pump. Suitable for domestic and agricultural use. 2-year warranty.", "price": 449900, "cat": "Industrial/B2B", "img": "electronics", "rating": 4.3, "reviews": 1234},
    {"title": "Havells 5-Star Inverter Split AC 1.5T", "desc": "R32 eco-friendly refrigerant. WiFi enabled, 4-way swing. Copper condenser coil.", "price": 4299900, "cat": "Industrial/B2B", "img": "electronics", "rating": 4.5, "reviews": 6789},
    {"title": "Stanley 100-piece Hand Tool Kit", "desc": "Comprehensive toolset with screwdrivers, wrenches, hammers, and sockets. Hard carrying case.", "price": 349900, "cat": "Industrial/B2B", "img": "home", "rating": 4.4, "reviews": 5678},
    {"title": "Luminous Zelio+ 1100 Home Inverter UPS", "desc": "Smart sine wave inverter. Led status indicator, runs heavy loads with battery protection.", "price": 649900, "cat": "Industrial/B2B", "img": "electronics", "rating": 4.5, "reviews": 1234},
    {"title": "Bosch Professional Angle Grinder 600W", "desc": "Ergonomic handheld metal/stone cutter. Spindle lock, dust protection, high power motor.", "price": 289900, "cat": "Industrial/B2B", "img": "home", "rating": 4.3, "reviews": 4567},

    # Events
    {"title": "Farm-to-Table Weekend Experience", "desc": "2-day immersive farming experience in Gujarat. Organic farming workshop, local cuisine, village stay.", "price": 499900, "cat": "Events", "img": "agriculture", "rating": 4.8, "reviews": 234},
    {"title": "Handloom Saree Exhibition - Varanasi", "desc": "Curated collection of Banarasi silk sarees. Direct from weavers. 500+ designs available.", "price": 0, "cat": "Events", "img": "fashion", "rating": 4.9, "reviews": 567},
    {"title": "Organic Farmers Market Stall Ticket", "desc": "Weekend entry pass to local agriculture and produce marketplace. Meet local farmers.", "price": 25000, "cat": "Events", "img": "agriculture", "rating": 4.4, "reviews": 123},
    {"title": "Traditional Garba Dance Workshop", "desc": "5-day intensive folk dance coaching with expert trainers. Navratri special preparation.", "price": 149900, "cat": "Events", "img": "fashion", "rating": 4.7, "reviews": 342},
    {"title": "Delhi Street Food Festival Entry Voucher", "desc": "Unlimited tastings entry coupon for Delhi's heritage culinary festival. Over 100 stalls.", "price": 99900, "cat": "Events", "img": "grocery", "rating": 4.6, "reviews": 890},

    # Real Estate
    {"title": "2 BHK Residential Apartment (Ahmedabad)", "desc": "1100 sqft semi-furnished apartment in prime location. Modern amenities, parking, 24/7 security.", "price": 450000000, "cat": "Real Estate", "img": "home", "rating": 4.4, "reviews": 12},
    {"title": "Agricultural Land 5 Acres (Anand)", "desc": "High fertility organic soil farm land near highway. Irrigation pipeline and electricity ready.", "price": 250000000, "cat": "Real Estate", "img": "agriculture", "rating": 4.8, "reviews": 5},
    {"title": "Commercial Shop Space (Indore Mall)", "desc": "Premium 450 sqft ground floor retail shop. High footfall, fully air conditioned.", "price": 850000000, "cat": "Real Estate", "img": "home", "rating": 4.5, "reviews": 23},
    {"title": "3 BHK Luxury Villa for Rent (Gandhinagar)", "desc": "Fully furnished luxury villa with private garden, smart home automation, and swimming pool access.", "price": 4500000, "cat": "Real Estate", "img": "home", "rating": 4.9, "reviews": 9},
    {"title": "Industrial Warehouse Space (Bhiwandi)", "desc": "15000 sqft warehouse with heavy dock load capacity, CCTV security, fire sprinklers, close to highway.", "price": 35000000, "cat": "Real Estate", "img": "home", "rating": 4.3, "reviews": 16},

    # Jobs
    {"title": "Assistant Agri-Business Manager", "desc": "Full-time job position. Manage supply chain, farmer relationships, and cold storage logistics. Experience: 2+ yrs.", "price": 5000000, "cat": "Jobs", "img": "education", "rating": 4.2, "reviews": 34},
    {"title": "E-Commerce Fulfillment Associate", "desc": "Pack and ship product orders in our main warehouse. Shifts available. No experience required.", "price": 2000000, "cat": "Jobs", "img": "grocery", "rating": 4.1, "reviews": 56},
    {"title": "Customer Support Executive", "desc": "Support super-platform users. Must speak Hindi, Gujarati, and English. Remote work optional.", "price": 3000000, "cat": "Jobs", "img": "electronics", "rating": 4.5, "reviews": 78},
    {"title": "Retail Store Sales Assistant", "desc": "Help customers in local supermarket branch. Manage inventory shelf stocking. 6-day week.", "price": 1800000, "cat": "Jobs", "img": "grocery", "rating": 4.0, "reviews": 92},
    {"title": "Field Operations Supervisor", "desc": "Supervise Kisan Hub machinery rentals and regional crop collection hubs. Must own bike.", "price": 3500000, "cat": "Jobs", "img": "agriculture", "rating": 4.4, "reviews": 18},
]

# Sale events
DEMO_SALES = [
    {
        "title": "🌾 Kisan Mega Sale — Fresh Harvest Festival",
        "desc": "Up to 40% off on all organic farm produce! Direct from farmers to your doorstep.",
        "discount": 40,
        "banner": "https://images.unsplash.com/photo-1625246333195-78d9c38ad449?w=1200&h=400&fit=crop",
    },
    {
        "title": "🛍️ Monsoon Fashion Fiesta",
        "desc": "Massive discounts on trendy fashion & accessories. Season's hottest styles at lowest prices!",
        "discount": 50,
        "banner": "https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=1200&h=400&fit=crop",
    },
    {
        "title": "📱 Electronics Bonanza — Deals of the Season",
        "desc": "Smartphones, laptops, headphones and more at never-before prices. Limited stock!",
        "discount": 30,
        "banner": "https://images.unsplash.com/photo-1498049794561-7780e7231661?w=1200&h=400&fit=crop",
    },
    {
        "title": "🏠 Home Essentials Super Sale",
        "desc": "Upgrade your home with premium appliances and furniture at flat 35% discount.",
        "discount": 35,
        "banner": "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=1200&h=400&fit=crop",
    },
]

# Advertisements  
DEMO_ADS = [
    {
        "title": "Samuday Fresh — Farm Direct Delivery",
        "image": "https://images.unsplash.com/photo-1607082348824-0a96f2a4b9da?w=1200&h=400&fit=crop",
        "placement": "hero_banner",
    },
    {
        "title": "New Arrivals — Handloom Collection",
        "image": "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=1200&h=400&fit=crop",
        "placement": "hero_banner",
    },
    {
        "title": "Premium Electronics at Best Prices",
        "image": "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=1200&h=400&fit=crop",
        "placement": "hero_banner",
    },
    {
        "title": "Kisan Direct — Organic & Certified",
        "image": "https://images.unsplash.com/photo-1472851294608-062f824d29cc?w=1200&h=400&fit=crop",
        "placement": "sidebar",
    },
    {
        "title": "Health First — Ayurvedic Products",
        "image": "https://images.unsplash.com/photo-1607083206869-4c7672e72a8a?w=1200&h=400&fit=crop",
        "placement": "sidebar",
    },
]


from sqlalchemy import text

async def seed_demo_data():
    """Seeds the database with demo products, sale events, and advertisements."""
    await init_db()
    
    async with AsyncSessionLocal() as db:
        print("[INFO] Cleaning up existing demo data...")
        await db.execute(text("TRUNCATE TABLE marketplace.orders CASCADE;"))
        await db.execute(text("TRUNCATE TABLE marketplace.listing_media CASCADE;"))
        await db.execute(text("TRUNCATE TABLE marketplace.listings CASCADE;"))
        await db.execute(text("TRUNCATE TABLE promotions.sale_events CASCADE;"))
        await db.execute(text("TRUNCATE TABLE promotions.advertisements CASCADE;"))
        await db.execute(text("TRUNCATE TABLE marketplace.cart_items CASCADE;"))
        await db.commit()

        # Ensure the system seller (owner of all seeded demo listings) exists as a
        # real user with a funded-capable wallet — otherwise escrow release on order
        # completion fails with "Seller wallet not found" for every demo product.
        seller_result = await db.execute(select(User).where(User.id == SYSTEM_SELLER_ID))
        if not seller_result.scalars().first():
            db.add(User(
                id=SYSTEM_SELLER_ID,
                full_name="Samuday Verified Store",
                email="store@samuday.demo",
                is_seller=True,
                status="active"
            ))
            print("[INFO] Created system seller user")

        wallet_result = await db.execute(select(Wallet).where(Wallet.user_id == SYSTEM_SELLER_ID))
        if not wallet_result.scalars().first():
            db.add(Wallet(user_id=SYSTEM_SELLER_ID, balance=0, currency="INR", status="active"))
            print("[INFO] Created system seller wallet")

        # Platform "house" account — accrues platform fee + delivery fee revenue
        # on order completion. See app/marketplace/fees.py PLATFORM_HOUSE_USER_ID.
        from app.marketplace.fees import PLATFORM_HOUSE_USER_ID
        house_result = await db.execute(select(User).where(User.id == PLATFORM_HOUSE_USER_ID))
        if not house_result.scalars().first():
            db.add(User(
                id=PLATFORM_HOUSE_USER_ID,
                full_name="Samuday Platform (House Account)",
                email="platform@samuday.internal",
                is_admin=True,
                seller_verification_status="approved",
                status="active"
            ))
            print("[INFO] Created platform house user")

        house_wallet_result = await db.execute(select(Wallet).where(Wallet.user_id == PLATFORM_HOUSE_USER_ID))
        if not house_wallet_result.scalars().first():
            db.add(Wallet(user_id=PLATFORM_HOUSE_USER_ID, balance=0, currency="INR", status="active"))
            print("[INFO] Created platform house wallet")

        await db.commit()

        # Get categories
        cat_result = await db.execute(select(Category))
        categories = {c.name: c.id for c in cat_result.scalars().all()}
        print(f"[INFO] Found {len(categories)} categories: {list(categories.keys())}")
        
        # Seed listings
        listing_ids = []
        for i, product in enumerate(DEMO_PRODUCTS):
            cat_id = categories.get(product["cat"])
            listing_type = product.get("type", "sale")
            
            listing = Listing(
                seller_id=SYSTEM_SELLER_ID,
                pillar="marketplace",
                category_id=cat_id,
                title=product["title"],
                description=product["desc"],
                price=product["price"],
                listing_type=listing_type,
                quantity=random.randint(5, 500),
                unit="piece",
                status="active"
            )
            db.add(listing)
            await db.flush()
            listing_ids.append(listing.id)
            
            # Add product image
            img_category = product["img"]
            img_list = IMAGES.get(img_category, IMAGES["electronics"])
            img_url = img_list[i % len(img_list)]
            
            media = ListingMedia(
                listing_id=listing.id,
                media_url=img_url,
                media_type="image",
                sort_order=0
            )
            db.add(media)
            
            # Add a second image for variety
            if len(img_list) > 1:
                media2 = ListingMedia(
                    listing_id=listing.id,
                    media_url=img_list[(i + 1) % len(img_list)],
                    media_type="image",
                    sort_order=1
                )
                db.add(media2)
        
        print(f"[OK] Seeded {len(DEMO_PRODUCTS)} products")
        
        # Seed Sale Events
        now = datetime.now(timezone.utc)
        for sale in DEMO_SALES:
            event = SaleEvent(
                seller_id=SYSTEM_SELLER_ID,
                title=sale["title"],
                description=sale["desc"],
                banner_image_url=sale["banner"],
                discount_percent=sale["discount"],
                start_date=now - timedelta(days=1),
                end_date=now + timedelta(days=30),
                listing_ids_json=json.dumps([str(lid) for lid in random.sample(listing_ids, min(5, len(listing_ids)))]),
                status="active"
            )
            db.add(event)
        
        print(f"[OK] Seeded {len(DEMO_SALES)} sale events")
        
        # Seed Advertisements
        for ad_data in DEMO_ADS:
            ad = Advertisement(
                seller_id=SYSTEM_SELLER_ID,
                title=ad_data["title"],
                image_url=ad_data["image"],
                link_url="/",
                placement=ad_data["placement"],
                cost_paise=500000,
                status="active",
                start_date=now - timedelta(days=1),
                end_date=now + timedelta(days=90),
                impressions=random.randint(1000, 50000),
                clicks=random.randint(100, 5000)
            )
            db.add(ad)
        
        print(f"[OK] Seeded {len(DEMO_ADS)} advertisements")
        
        await db.commit()
        print("[DONE] Demo data seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed_demo_data())
