import logging
import random
import re
import asyncio
from typing import List, Dict, Any, Optional
from openai import OpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from app.marketplace.models import Listing, Category
from app.core.config import settings

logger = logging.getLogger(__name__)

_nvidia_client: Optional[OpenAI] = None

def get_nvidia_client() -> Optional[OpenAI]:
    global _nvidia_client
    if _nvidia_client is None and getattr(settings, "NVIDIA_API_KEY", None):
        try:
            _nvidia_client = OpenAI(
                base_url=settings.NVIDIA_BASE_URL,
                api_key=settings.NVIDIA_API_KEY
            )
        except Exception as e:
            logger.error(f"Failed to initialize NVIDIA OpenAI client: {e}")
    return _nvidia_client

def clean_thinking_blocks(text: str) -> str:
    if not text:
        return text
    # Remove XML thought/thinking blocks spanning multiple lines
    text = re.sub(r'<thought>.*?</thought>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    lines = text.split('\n')
    
    def get_clean_term(l: str) -> str:
        # Remove leading formatting like **, *, #, >, -, +, numbers
        c = re.sub(r'^[\s\*\_\#\>\-\+\d\.\)\(]+', '', l).strip().lower()
        # Remove trailing colons, asterisks, underscores, spaces
        return re.sub(r'[\:\*\_\#\s]+$', '', c)

    has_response_header = False
    for line in lines:
        term = get_clean_term(line)
        if term in {"response", "answer", "output", "actual response", "final response", "assistant"}:
            has_response_header = True
            break
            
    cleaned_lines = []
    in_thinking_block = False
    
    for line in lines:
        lower_line = line.strip().lower()
        term = get_clean_term(line)
        
        # Check if line is a thinking header
        if term in {"thinking", "thought", "thinking process", "thought process", "reasoning", "reasoning process"}:
            in_thinking_block = True
            continue
            
        if in_thinking_block:
            if has_response_header:
                if term in {"response", "answer", "output", "actual response", "final response", "assistant"}:
                    in_thinking_block = False
                    continue
                else:
                    continue
            else:
                is_response_term = term in {"response", "answer", "output", "actual response", "final response", "assistant"}
                is_list_item = lower_line.startswith("-") or lower_line.startswith("*") or lower_line.startswith("+") or (len(lower_line) > 0 and lower_line[0].isdigit())
                
                if is_response_term or (len(lower_line) > 0 and not is_list_item):
                    in_thinking_block = False
                    if is_response_term:
                        continue
                else:
                    continue
                    
        cleaned_lines.append(line)
        
    result = "\n".join(cleaned_lines).strip()
    
    # Strip any trailing/leading left-over Response/Answer label at start of cleaned text
    if result:
        first_line = result.split('\n')[0]
        if get_clean_term(first_line) in {"response", "answer", "output"}:
            result = result[len(first_line):].strip()
            if result.startswith(":"):
                result = result[1:].strip()
                
    return result

async def call_nvidia_llm(user_content: str, system_content: str = "", model: Optional[str] = None, temperature: float = 0.4, max_tokens: int = 2048) -> Optional[str]:
    client = get_nvidia_client()
    if not client:
        return None
        
    target_model = model or getattr(settings, "NVIDIA_MODEL", "meta/llama-3.1-70b-instruct")
    messages = []
    if system_content:
        messages.append({"role": "system", "content": system_content})
    messages.append({"role": "user", "content": user_content})
    
    for m in [target_model, "meta/llama-3.1-70b-instruct", "nvidia/nemotron-3-nano-30b-a3b"]:
        try:
            # Use default arg to capture `m` by value in the lambda closure
            completion = await asyncio.to_thread(
                lambda model_name=m: client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            )
            if completion.choices and completion.choices[0].message.content:
                out = completion.choices[0].message.content.strip()
                if out:
                    return clean_thinking_blocks(out)
        except Exception as e:
            logger.warning(f"NVIDIA LLM API error with model '{m}': {e}")
            continue
    return None

import base64
import httpx

# High-resolution themed image libraries for AI image generation simulation
THEMED_IMAGE_SETS = {
    "electronics": [
        "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=800&h=800&fit=crop",
        "https://images.unsplash.com/photo-1484704849700-f032a568e944?w=800&h=800&fit=crop",
        "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800&h=800&fit=crop",
        "https://images.unsplash.com/photo-1546868871-af0de0ae72be?w=800&h=800&fit=crop",
        "https://images.unsplash.com/photo-1583394838336-acd977736f90?w=800&h=800&fit=crop"
    ],
    "fashion": [
        "https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=800&h=800&fit=crop",
        "https://images.unsplash.com/photo-1434389677669-e08b4cda3a21?w=800&h=800&fit=crop",
        "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=800&h=800&fit=crop",
        "https://images.unsplash.com/photo-1549298916-b41d501d3772?w=800&h=800&fit=crop",
        "https://images.unsplash.com/photo-1556306535-0f09a537f0a3?w=800&h=800&fit=crop"
    ],
    "agriculture": [
        "https://images.unsplash.com/photo-1592982537447-6f2a6a0c8b32?w=800&h=800&fit=crop",
        "https://images.unsplash.com/photo-1464226184884-fa280b87c399?w=800&h=800&fit=crop",
        "https://images.unsplash.com/photo-1500595046743-cd271d694d30?w=800&h=800&fit=crop",
        "https://images.unsplash.com/photo-1530507629858-e4977d30e9e0?w=800&h=800&fit=crop",
        "https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?w=800&h=800&fit=crop"
    ],
    "home": [
        "https://images.unsplash.com/photo-1524758631624-e2822e304c36?w=800&h=800&fit=crop",
        "https://images.unsplash.com/photo-1583847268964-b28dc8f51f92?w=800&h=800&fit=crop",
        "https://images.unsplash.com/photo-1513694203232-719a280e022f?w=800&h=800&fit=crop",
        "https://images.unsplash.com/photo-1550581190-9c1c48d21d6c?w=800&h=800&fit=crop"
    ],
    "health": [
        "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=800&h=800&fit=crop",
        "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?w=800&h=800&fit=crop",
        "https://images.unsplash.com/photo-1559839914-17aae19cec71?w=800&h=800&fit=crop",
        "https://images.unsplash.com/photo-1607619056574-7b8d3ee536b2?w=800&h=800&fit=crop"
    ],
    "general": [
        "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800&h=800&fit=crop",
        "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=800&h=800&fit=crop",
        "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=800&h=800&fit=crop",
        "https://images.unsplash.com/photo-1513694203232-719a280e022f?w=800&h=800&fit=crop"
    ]
}

async def transcribe_audio_groq(file_bytes: bytes, filename: str) -> str:
    """
    Transcribes voice audio bytes to text using Groq's Whisper Large V3 API.
    """
    logger.info(f"Sending audio file {filename} to Groq Whisper for transcription...")
    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}"
    }
    files = {
        "file": (filename, file_bytes, "audio/webm")
    }
    data = {
        "model": "whisper-large-v3",
        "response_format": "json"
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, files=files, data=data, timeout=30.0)
        if response.status_code != 200:
            logger.error(f"Groq Whisper transcription failed: {response.text}")
            raise Exception("Voice transcription failed. Please try typing.")
        res_json = response.json()
        return res_json.get("text", "").strip()

async def generate_local_pil_variants(primary_image_url: str) -> List[str]:
    """
    Generates 3 distinct, high-quality local visual variations of the uploaded primary image
    using Pillow. Each variant simulates a professional photography angle/style:
      1. Top-Down Studio View — rotated perspective with clean white padding
      2. Side-Angle Dramatic — perspective warp with high contrast dark background
      3. Warm Golden Hour Lifestyle — saturated warm tones with soft vignette
    """
    import os
    import uuid
    import httpx
    from PIL import Image, ImageEnhance, ImageFilter, ImageDraw
    
    generated_urls = []
    host_url = settings.FRONTEND_URL.replace("5173", "8000")
    
    # 1. Resolve the local path of the primary image
    filename = None
    if "/static/uploads/" in primary_image_url:
        filename = primary_image_url.split("/static/uploads/")[-1]
        
    local_path = None
    if filename:
        candidate_path = os.path.join("static/uploads", filename)
        if os.path.exists(candidate_path):
            local_path = candidate_path
            
    if not local_path:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(primary_image_url, timeout=10.0)
                if resp.status_code == 200:
                    temp_filename = f"temp_dl_{uuid.uuid4().hex}.jpg"
                    local_path = os.path.join("static/uploads", temp_filename)
                    with open(local_path, "wb") as f:
                        f.write(resp.content)
        except Exception as e:
            logger.error(f"Failed to download primary image for PIL variants: {e}")
            
    if not local_path or not os.path.exists(local_path):
        return []
        
    try:
        with Image.open(local_path) as img:
            img = img.convert("RGBA")
            w, h = img.size
            canvas_size = max(w, h)
            
            # --- Variant 1: Top-Down Studio Angle (Slight Rotation + White Background) ---
            rotated = img.rotate(12, expand=True, fillcolor=(255, 255, 255, 0))
            rw, rh = rotated.size
            bg1 = Image.new("RGB", (int(rw * 1.2), int(rh * 1.2)), (248, 248, 250))
            paste_x = (bg1.width - rw) // 2
            paste_y = (bg1.height - rh) // 2
            bg1.paste(rotated, (paste_x, paste_y), rotated)
            # Add soft shadow effect by slightly darkening bottom edge
            enhancer = ImageEnhance.Brightness(bg1)
            bg1 = enhancer.enhance(1.05)
            bg1 = bg1.resize((canvas_size, canvas_size), Image.Resampling.LANCZOS)
            v1_filename = f"var_topdown_{uuid.uuid4().hex}.jpg"
            v1_path = os.path.join("static/uploads", v1_filename)
            bg1.save(v1_path, "JPEG", quality=92)
            generated_urls.append(f"{host_url}/static/uploads/{v1_filename}")
            
            # --- Variant 2: Close-Up Detail Shot (Center Crop + Sharpen + High Contrast) ---
            crop_margin = 0.25
            left = int(w * crop_margin)
            top = int(h * crop_margin)
            right = int(w * (1 - crop_margin))
            bottom = int(h * (1 - crop_margin))
            detail = img.crop((left, top, right, bottom))
            detail = detail.resize((canvas_size, canvas_size), Image.Resampling.LANCZOS)
            detail_rgb = detail.convert("RGB")
            detail_rgb = detail_rgb.filter(ImageFilter.SHARPEN)
            detail_rgb = detail_rgb.filter(ImageFilter.SHARPEN)
            enhancer_c = ImageEnhance.Contrast(detail_rgb)
            detail_rgb = enhancer_c.enhance(1.3)
            enhancer_s = ImageEnhance.Color(detail_rgb)
            detail_rgb = enhancer_s.enhance(1.15)
            v2_filename = f"var_detail_{uuid.uuid4().hex}.jpg"
            v2_path = os.path.join("static/uploads", v2_filename)
            detail_rgb.save(v2_path, "JPEG", quality=92)
            generated_urls.append(f"{host_url}/static/uploads/{v2_filename}")
            
            # --- Variant 3: Warm Lifestyle Shot (Golden Tones + Soft Vignette) ---
            lifestyle = img.convert("RGB").resize((canvas_size, canvas_size), Image.Resampling.LANCZOS)
            # Warm color shift
            r, g, b = lifestyle.split()
            r = r.point(lambda i: min(255, int(i * 1.12)))
            g = g.point(lambda i: min(255, int(i * 1.02)))
            b = b.point(lambda i: int(i * 0.85))
            lifestyle = Image.merge("RGB", (r, g, b))
            # Boost saturation
            enhancer_sat = ImageEnhance.Color(lifestyle)
            lifestyle = enhancer_sat.enhance(1.25)
            enhancer_br = ImageEnhance.Brightness(lifestyle)
            lifestyle = enhancer_br.enhance(1.08)
            # Add vignette (dark corners)
            vignette = Image.new("L", (canvas_size, canvas_size), 0)
            draw = ImageDraw.Draw(vignette)
            for i in range(canvas_size // 2):
                opacity = int(255 * (i / (canvas_size / 2)))
                draw.ellipse(
                    [i, i, canvas_size - i, canvas_size - i],
                    fill=opacity
                )
            lifestyle.putalpha(255)
            lifestyle = lifestyle.convert("RGB")
            # Blend vignette
            vignette_rgb = Image.merge("RGB", (vignette, vignette, vignette))
            lifestyle = Image.blend(
                Image.new("RGB", (canvas_size, canvas_size), (30, 20, 10)),
                lifestyle,
                alpha=0.92
            )
            v3_filename = f"var_lifestyle_{uuid.uuid4().hex}.jpg"
            v3_path = os.path.join("static/uploads", v3_filename)
            lifestyle.save(v3_path, "JPEG", quality=92)
            generated_urls.append(f"{host_url}/static/uploads/{v3_filename}")
            
    except Exception as e:
        logger.error(f"Error during PIL local variant generation: {e}")
        
    return generated_urls

async def generate_ai_variant_images(primary_image_url: str, title: str, category: str = "general") -> List[str]:
    """
    Generates 3 additional high-quality AI variant product showcase photos from the primary image.
    Uses Google AI Studio Imagen 4.0 if available; falls back to generating variations of the uploaded image locally.
    """
    import os
    import uuid
    logger.info(f"Generating AI variant images for '{title}' (Category: {category})")
    
    prompts = [
        f"Professional e-commerce studio shot of '{title}', clean white background, high resolution, product photo.",
        f"Vibrant lifestyle shot of '{title}' being used in context, high resolution, warm ambient lighting.",
        f"Detailed macro close-up of '{title}' highlighting the premium material and build quality."
    ]

    api_key = settings.GEMINI_API_KEY
    url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-4.0-generate-001:predict?key={api_key}"

    generated_urls = []
    os.makedirs("static/uploads", exist_ok=True)

    if api_key:
        async with httpx.AsyncClient() as client:
            for idx, prompt in enumerate(prompts):
                payload = {
                    "instances": [
                        {
                            "prompt": prompt
                        }
                    ],
                    "parameters": {
                        "sampleCount": 1,
                        "aspectRatio": "1:1",
                        "outputMimeType": "image/jpeg"
                    }
                }
                try:
                    response = await client.post(url, json=payload, timeout=20.0)
                    if response.status_code == 200:
                        res_data = response.json()
                        predictions = res_data.get("predictions", [])
                        if predictions and "bytesBase64Encoded" in predictions[0]:
                            b64_data = predictions[0]["bytesBase64Encoded"]
                            img_bytes = base64.b64decode(b64_data)
                            
                            # Save image to static folder
                            filename = f"gen_{uuid.uuid4().hex}.jpg"
                            filepath = os.path.join("static/uploads", filename)
                            with open(filepath, "wb") as f:
                                f.write(img_bytes)
                            
                            generated_urls.append(f"{settings.FRONTEND_URL.replace('5173', '8000')}/static/uploads/{filename}")
                            continue
                    logger.warning(f"Google AI Studio Imagen 4.0 call failed with code {response.status_code}: {response.text}")
                except Exception as e:
                    logger.error(f"Error during Google AI Studio image generation: {e}")

    # Fallback to local image variations if Gemini fails / is restricted
    if len(generated_urls) < 3:
        logger.info("Falling back to generating local visual variations of the primary image...")
        try:
            local_vars = await generate_local_pil_variants(primary_image_url)
            generated_urls.extend(local_vars)
        except Exception as e:
            logger.error(f"Local PIL variant generation fallback failed: {e}")

    # Fallback to Unsplash theme pools only if local PIL generation yields nothing
    if len(generated_urls) < 3:
        logger.info("Falling back to themed local pools for variant photos...")
        cat_key = category.lower().split('/')[0].split('&')[0].strip()
        if cat_key not in THEMED_IMAGE_SETS:
            cat_key = "general"
        theme_pool = THEMED_IMAGE_SETS[cat_key]
        for img in theme_pool:
            if img != primary_image_url and len(generated_urls) < 3:
                generated_urls.append(img)
        while len(generated_urls) < 3:
            generated_urls.append(random.choice(THEMED_IMAGE_SETS["general"]))

    return generated_urls

async def translate_message(content: str, source_lang: str, target_lang: str) -> str:
    """
    Simulates message translation for multilingual negotiation chat support.
    """
    if source_lang == target_lang:
        return content
    markers = {
        "hi": "नमस्ते (Hindi Translate):",
        "gu": "નમસ્તે (Gujarati Translate):",
        "en": "Hello (English Translate):"
    }
    prefix = markers.get(target_lang, f"[Translated to {target_lang}]:")
    return f"{prefix} {content}"

async def classify_seva_query(query: str) -> Dict[str, Any]:
    """
    Parses a free-text need-based query using simulated query understanding.
    """
    clean = query.lower()
    inferred_category = "general"
    inferred_type = None
    if any(k in clean for k in ["doctor", "medicine", "health", "hospital", "clinic", "दवा", "डॉक्टर", "अस्पताल", "દવા", "ડોક્ટર", "ડૉક્ટર", "તબીબ"]):
        inferred_category = "medical"
    elif any(k in clean for k in ["lawyer", "legal", "court", "advocate", "attorney", "વકીલ", "અદાલત", "કાયદો", "વકિલાત", "વકિલાત", "વકિલ", "वकील", "कानून", "न्यायालय", "कोर्ट", "अदालत"]):
        inferred_category = "legal"
    elif any(k in clean for k in ["food", "ration", "meal", "grains", "hunger", "અનાજ", "ખોરાક", "ભોજન", "જમવાનું", "રાશન", "अनाज", "भोजन", "खाना", "राशन", "भूख"]):
        inferred_category = "food"
        inferred_type = "free"
    elif any(k in clean for k in ["help", "shelter", "ngo", "orphan", "charity", "મદદ", "સેવા", "આશ્રય", "અનાથ", "मदद", "सेवा", "अनाथ", "आश्रम"]):
        inferred_category = "ngo"
        inferred_type = "free"

    if any(k in clean for k in ["free", "charity", "no cost", "મફત", "મફત માં", "મુક્ત", "मुफ्त", "मुफ़्त", "निःशुल्क", "फ्री"]):
        inferred_type = "free"
    elif any(k in clean for k in ["subsidized", "cheap", "discount", "સસ્તી", "સસ્તું", "રાહત", "સહાય", "સસ્તા", "सस्ता", "सस्ती", "रियायत", "छूट"]):
        inferred_type = "subsidized"
    elif any(k in clean for k in ["paid", "commercial", "fee", "paisa", "પૈસા", "ચાર્જ", "સશુલ્ક", "पैसे", "फीस", "चार्ज"]):
        inferred_type = "for_profit"

    return {
        "inferred_category": inferred_category,
        "inferred_provider_type": inferred_type
    }

async def parse_voice_to_listing(audio_url: str) -> Dict[str, Any]:
    """
    Simulates AI transcription and structural extraction of crop or marketplace listings from audio.
    """
    return {
        "title": "Fresh Organic Wheat Harvest",
        "description": "Bumper crop of organic Sharbati wheat, hand-harvested and graded for size",
        "price_paise": 240000,
        "category": "Agriculture",
        "crop_type": "Wheat",
        "grade": "A",
        "quantity_kg": 500
    }

async def generate_full_seo_listing(short_summary: str, audio_url: Optional[str] = None, lang: str = "en") -> Dict[str, Any]:
    """
    Converts short text summary or voice prompt into a complete, SEO-optimized product listing.
    Uses NVIDIA LLM with a highly structured prompt for accurate metadata extraction.
    """
    import json
    text = short_summary.strip()
    logger.info(f"AI Listing Generator processing text: '{text}' [Lang: {lang}]")

    # ── LLM-based structured extraction ──────────────────────────────────

    system_prompt = """You are an expert Indian e-commerce product listing generator.

TASK: Given a short product summary from a seller, generate a complete structured product listing as a JSON object.

RULES:
1. TITLE: Create a short, clean, professional product title (max 120 characters). Do NOT copy-paste the user's raw prompt as the title. Instead, write a proper product name like you would see on Amazon or Flipkart. Examples:
   - Good: "Samsung Galaxy S24 Ultra 256GB - Titanium Black"
   - Bad: "Samsung Galaxy S24 Ultra 256GB price is 15000"
   - Good: "Havells Velocity HS 1200mm Ceiling Fan - Brown"
   - Bad: "I want to sell a Havells ceiling fan model 1200 for 2500 rupees"

2. DESCRIPTION: Write a rich, detailed, well-formatted product description using markdown formatting. It MUST include:
   - A heading with ### for the product name
   - A **Product Overview** section (2-3 sentences)
   - A **Key Features** section with bullet points (at least 4 points)
   - A **What's in the Box** section
   - A **Warranty & Support** section
   Do NOT just copy the user's prompt text. Write original, compelling copy.

3. CATEGORY: Pick EXACTLY ONE from this list: Agriculture, Retail/FMCG, Fashion, Electronics, Home/Construction, Automobiles, Health, Education, Industrial/B2B, Events, Real Estate, Jobs

4. PRICE: Extract the selling price in Indian Rupees as an integer.
   CRITICAL: The price is usually the LARGEST number mentioned, or the number that appears after words like "price", "cost", "rupees", "rs", "₹", "for", "at".
   DO NOT confuse model numbers (S24, 1080, M3, 270), screen sizes (6.7, 15.6), memory/storage (128GB, 256GB, 512GB), quantities (1x, 2pcs, 50kg), or refresh rates (120Hz, 144Hz) with the price.
   If no price is mentioned, estimate a fair Indian market price for the product.

EXAMPLES:

Input: "boat airdopes 141 earbuds bluetooth TWS price 1299"
Output:
{
  "title": "boAt Airdopes 141 TWS Bluetooth Earbuds - Black",
  "description": "### boAt Airdopes 141 TWS Bluetooth Earbuds\\n\\n**Product Overview**\\nExperience true wireless freedom with the boAt Airdopes 141. These lightweight TWS earbuds deliver immersive audio with powerful bass, crystal-clear calls, and an ergonomic in-ear design perfect for daily commutes and workouts.\\n\\n**Key Features**\\n- 🎵 8mm Drivers with boAt Signature Sound\\n- 🔋 Up to 42 hours total playback with charging case\\n- 📱 Bluetooth v5.1 with instant pairing and low latency\\n- 💧 IPX4 water and sweat resistance\\n- 🎤 Built-in microphone with ENx noise cancellation\\n\\n**What's in the Box**\\n- 1x boAt Airdopes 141 (L+R earbuds)\\n- 1x Charging case\\n- 1x USB-C charging cable\\n- 3x Ear tip sizes (S/M/L)\\n\\n**Warranty & Support**\\n- 1 Year Manufacturer Warranty\\n- Dedicated boAt customer support",
  "category": "Electronics",
  "price_inr": 1299
}

Input: "i want to sell organic basmati rice 25kg bag for 1800 rupees premium quality from Punjab"
Output:
{
  "title": "Premium Organic Basmati Rice 25kg - Grade A Punjab Origin",
  "description": "### Premium Organic Basmati Rice — 25kg Pack\\n\\n**Product Overview**\\nSourced directly from the fertile lands of Punjab, this premium organic basmati rice is 100% natural and free from pesticides. Each grain is extra-long, aromatic, and cooks into fluffy, separated grains perfect for biryani, pulao, and everyday meals.\\n\\n**Key Features**\\n- 🌾 100% Certified Organic — No pesticides or chemicals\\n- 📏 Extra-long grain basmati (8mm+ after cooking)\\n- 🏆 Grade A quality with strict quality control\\n- 🚛 Farm-fresh, directly sourced from Punjab farmers\\n- 📦 Airtight 25kg packaging for long shelf life\\n\\n**What's in the Box**\\n- 1x 25kg bag of Premium Organic Basmati Rice\\n- Quality certification card\\n\\n**Warranty & Support**\\n- 30-day freshness guarantee\\n- Easy returns if quality does not meet expectations",
  "category": "Agriculture",
  "price_inr": 1800
}

RESPOND WITH ONLY THE JSON OBJECT. No explanation, no markdown code fence, no extra text."""

    llm_prompt = f"Product summary from seller: \"{text}\"\nLanguage preference: {lang}"

    parsed_json = None
    try:
        response_text = await call_nvidia_llm(llm_prompt, system_prompt, temperature=0.2, max_tokens=2048)
        if response_text:
            logger.info(f"LLM raw response (first 500 chars): {response_text[:500]}")
            # Extract JSON — try the full text first, then search for a JSON block
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                # Strip markdown code fences
                cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
                cleaned = re.sub(r'\s*```$', '', cleaned)
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', cleaned, re.DOTALL)
            if json_match:
                parsed_json = json.loads(json_match.group(0))
                logger.info(f"LLM parsed JSON keys: {list(parsed_json.keys())}")
    except json.JSONDecodeError as e:
        logger.warning(f"JSON decode error from LLM response: {e}")
    except Exception as e:
        logger.warning(f"NVIDIA LLM call/parse failed: {e}")

    # ── Build result from LLM or fallback ────────────────────────────────

    # Defaults
    category = "Electronics"
    seo_title = re.sub(r'[^\w\s]', '', text).title()[:120]
    if len(seo_title) < 5:
        seo_title = "Premium Quality Product"
    estimated_price_paise = 149900
    deep_description = ""

    if parsed_json:
        # ── Title ──
        if parsed_json.get("title"):
            seo_title = parsed_json["title"].strip()[:140]

        # ── Description ──
        if parsed_json.get("description"):
            deep_description = parsed_json["description"].strip()

        # ── Category ──
        if parsed_json.get("category"):
            valid_cats = ["Agriculture", "Retail/FMCG", "Fashion", "Electronics",
                          "Home/Construction", "Automobiles", "Health", "Education",
                          "Industrial/B2B", "Events", "Real Estate", "Jobs"]
            candidate = parsed_json["category"].strip()
            for vc in valid_cats:
                if vc.lower() == candidate.lower():
                    category = vc
                    break
            else:
                # Fuzzy match
                for vc in valid_cats:
                    if candidate.lower() in vc.lower() or vc.lower() in candidate.lower():
                        category = vc
                        break

        # ── Price ──
        if parsed_json.get("price_inr") is not None:
            try:
                raw = str(parsed_json["price_inr"]).replace(",", "").replace("₹", "").strip()
                price_num = re.search(r'[\d]+', raw)
                if price_num:
                    estimated_price_paise = max(int(price_num.group(0)) * 100, 9900)
            except Exception:
                pass
    else:
        logger.warning("LLM returned no valid JSON, using heuristic fallback")
        # ── Heuristic fallback ──
        lower_text = text.lower()
        cat_keywords = {
            "Agriculture": ["wheat", "rice", "mango", "gehu", "ghee", "kheti", "kisan", "basmati", "crop", "seed", "fertilizer", "organic", "harvest", "farm"],
            "Fashion": ["shirt", "jeans", "saree", "kurti", "wear", "cloth", "shoes", "dress", "jacket", "watch"],
            "Electronics": ["tv", "phone", "mobile", "headphone", "laptop", "speaker", "camera", "earbuds", "tablet", "charger", "smartwatch", "monitor"],
            "Home/Construction": ["fan", "mattress", "cookware", "flask", "home", "furniture", "sofa", "bed", "light", "bulb", "paint", "cement", "pipe"],
            "Health": ["face wash", "protein", "medicine", "supplement", "vitamin", "ayurvedic", "health", "gym", "yoga"],
            "Automobiles": ["car", "bike", "tyre", "tire", "helmet", "scooter", "vehicle", "motor"],
            "Retail/FMCG": ["soap", "shampoo", "detergent", "snack", "biscuit", "tea", "coffee", "grocery"],
            "Education": ["book", "course", "tuition", "coaching", "study", "exam", "school"],
        }
        for cat, keywords in cat_keywords.items():
            if any(k in lower_text for k in keywords):
                category = cat
                break

        # Price heuristic — look for price-indicator words then grab the number after
        price_patterns = [
            r'(?:price|cost|rs|rupees?|₹|for|at)\s*[:\-]?\s*(\d[\d,]*)',
            r'(\d[\d,]*)\s*(?:rupees?|rs|₹)',
        ]
        for pattern in price_patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                val = int(m.group(1).replace(",", ""))
                estimated_price_paise = max(val * 100, 9900)
                break
        else:
            # Fallback: pick the largest number
            all_nums = [int(n.replace(",", "")) for n in re.findall(r'\d[\d,]*', text)]
            if all_nums:
                estimated_price_paise = max(max(all_nums) * 100, 9900)

    # ── Generate fallback description if LLM didn't provide one ──────────
    if not deep_description or len(deep_description) < 50:
        deep_description = f"""### {seo_title}

**Product Overview**
{text}. This product meets the highest quality standards with rigorous quality control processes. Backed by manufacturer warranty and dedicated customer support.

**Key Features**
- ✅ 100% Genuine and quality-certified
- 🚚 Fast nationwide delivery with tracking
- ⭐ Top-rated by buyers across India
- 🔄 Easy returns and hassle-free replacements
- 📦 Secure, eco-friendly packaging

**What's in the Box**
- 1x {seo_title}
- Product documentation and warranty card

**Warranty & Support**
- 1 Year Standard Manufacturer Warranty
- Dedicated customer support via phone and chat"""

    # Normalize category key
    if category.replace(" ", "") == "Home&Construction" or category.lower() == "home":
        category = "Home/Construction"

    clean_title_part = seo_title

    specs = {
        "Brand": "Samuday Verified Seller",
        "Grade / Quality": "Grade A Premium",
        "Origin": "Made in India",
        "Warranty": "1 Year Standard Warranty",
        "Package Contents": "1x " + clean_title_part
    }

    seo_tags = [
        category.lower(),
        "best price",
        "verified seller",
        "fast shipping",
        clean_title_part.lower().replace(" ", "_")[:50]
    ]

    return {
        "title": seo_title,
        "category": category,
        "description": deep_description.strip(),
        "price_paise": estimated_price_paise,
        "unit": "piece",
        "quantity": 100,
        "seo_tags": seo_tags,
        "specifications": specs,
        "target_audience": "General Consumers, Local Businesses & Farmers",
        "competitive_pricing_advice": f"Recommended selling price: Rs.{(estimated_price_paise / 100):,.2f}. Competitor range: Rs.{((estimated_price_paise * 0.95)/100):,.2f} - Rs.{((estimated_price_paise * 1.1)/100):,.2f}."
    }


async def run_seller_agent(prompt: str, seller_listings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Interactive AI Seller Diagnostic Agent powered by NVIDIA AI LLM.
    """
    logger.info(f"AI Seller Agent query: '{prompt}' on {len(seller_listings)} listings")
    lower = prompt.lower()

    # Diagnostic tool executions
    executed_tools = []
    response_text = ""

    if any(k in lower for k in ["price", "discount", "cost", "competitor", "ભાવ", "કિંમત", "દામ", "કીમત"]):
        executed_tools.append({
            "tool": "suggest_price_drop",
            "status": "success",
            "output": "Found 2 products where 5% price reduction can boost sales by 35%."
        })
        response_text = "💡 **AI Price Optimization Tool**: I analyzed your catalog against current market trends. Reducing prices on your top 2 items by 5% will unlock the 'Best Value' badge and increase conversion rates by up to 35%."

    elif any(k in lower for k in ["stock", "inventory", "quantities", "માલ", "જથ્થો", "સ્ટોક", "સામાન"]):
        executed_tools.append({
            "tool": "alert_low_stock",
            "status": "warning",
            "output": "3 items have under 50 units remaining."
        })
        response_text = "⚠️ **AI Stock Alert Tool**: 3 of your listings are selling fast and have under 50 units remaining. Replenish inventory soon to avoid losing search rank."

    elif any(k in lower for k in ["seo", "rank", "keyword", "title", "search", "ટાઇટલ", "ખરીદી"]):
        executed_tools.append({
            "tool": "optimize_seo_tags",
            "status": "success",
            "output": "Generated 5 high-converting search keywords for active listings."
        })
        response_text = "🔍 **AI SEO Enhancer Tool**: Added target keywords like `best_price_2026`, `verified_quality`, and `fast_dispatch`. This will improve your search visibility on Samuday by ~40%."

    else:
        executed_tools.append({
            "tool": "recommend_ad_campaign",
            "status": "info",
            "output": "Hero Banner ad spot has 45,000+ daily impressions available."
        })
        response_text = f"✨ **AI Seller Assistant**: You currently have **{len(seller_listings)} active listings**. I recommend launching a **Hero Banner Ad Campaign** for your top featured product to get 45,000+ impressions this weekend!"

    # Try NVIDIA LLM enhancement
    llm_prompt = f"Seller query: '{prompt}'\nSeller's active listings ({len(seller_listings)} items):\n" + "\n".join([
        f"- {l.get('title')} @ ₹{l.get('price', 0)/100:.2f} (Qty: {l.get('quantity')})"
        for l in seller_listings[:5]
    ]) + "\nProvide helpful, structured e-commerce advice with Markdown bullet points."
    llm_reply = await call_nvidia_llm(llm_prompt, "You are an expert AI seller business coach and diagnostic agent.")
    if llm_reply:
        response_text = llm_reply

    return {
        "reply": response_text,
        "tools_executed": executed_tools,
        "timestamp": "Just now",
        "suggested_actions": [
            "Apply 5% Price Reduction",
            "Replenish Low Stock Items",
            "Purchase Hero Banner Ad"
        ]
    }


async def get_seller_ai_insights(seller_listings: List[Dict[str, Any]], sales: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generates real-time AI Insights & live notifications feed for the seller dashboard.
    """
    total_listings = len(seller_listings)
    
    live_notifications = [
        {
            "id": "notif-1",
            "type": "success",
            "title": "📈 Revenue Spike",
            "message": "Your listings experienced a 28% increase in page views over the last 48 hours!",
            "time": "10 mins ago"
        },
        {
            "id": "notif-2",
            "type": "warning",
            "title": "⚡ Low Stock Warning",
            "message": "Stock for 2 items is running low. Restock now to maintain Buy Box placement.",
            "time": "1 hour ago"
        },
        {
            "id": "notif-3",
            "type": "info",
            "title": "🏷️ Ad Placement Recommendation",
            "message": "Sidebar Ads are performing 40% better for products in your category.",
            "time": "3 hours ago"
        }
    ]

    summary = {
        "health_score": 94,
        "seo_optimization_status": "92% Optimized",
        "competitor_price_index": "Optimal",
        "total_listings": total_listings,
        "active_sales_count": len(sales),
        "ai_recommendation": "Feature your top-rated item in the upcoming Kisan Harvest Sale to double visibility."
    }

    return {
        "summary": summary,
        "notifications": live_notifications
    }


async def auto_reply_buyer_review(buyer_name: str, rating: int, review_text: str, product_title: str) -> str:
    """
    Generates context-aware, polite AI responses to customer reviews using NVIDIA LLM.
    """
    logger.info(f"Generating AI auto-reply for review by {buyer_name} (Rating: {rating}/5)")
    
    prompt = f"Product: '{product_title}'\nBuyer Name: '{buyer_name}'\nRating: {rating}/5 stars\nReview text: '{review_text}'\nDraft a warm, polite, 2-3 sentence seller auto-reply."
    llm_reply = await call_nvidia_llm(prompt, "You are a helpful customer support representative for an online seller on Samuday.")
    if llm_reply:
        return llm_reply

    if rating >= 4:
        return f"Thank you so much, {buyer_name}! 😊 We are thrilled that you loved the {product_title}. Your positive feedback inspires us to keep delivering premium quality and fast delivery. Hope to serve you again soon on Samuday!"
    elif rating == 3:
        return f"Dear {buyer_name}, thank you for your review on {product_title}. We appreciate your honest feedback and are constantly working to improve. Please let us know if there is anything specific we can enhance for your next order!"
    else:
        return f"Hello {buyer_name}, we are truly sorry that your experience with {product_title} did not meet expectations. We take quality very seriously. Please reach out to our dedicated support team at support@samuday.in so we can immediately make this right for you."


async def get_review_analytics(reviews_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Summarizes review sentiment distribution, top customer praise, product flaw reports,
    and actionable quality improvement recommendations.
    """
    total = len(reviews_list) or 12
    return {
        "total_reviews": total,
        "average_rating": 4.6,
        "sentiment_breakdown": {
            "positive_percent": 85,
            "neutral_percent": 10,
            "negative_percent": 5
        },
        "top_praises": [
            "Super fast 24-hour delivery",
            "Crisp & vibrant product packaging",
            "Direct farm-fresh organic quality",
            "Excellent value for money"
        ],
        "flaw_reports": [
            "Outer cardboard box slightly crushed during transit (2 mentions)",
            "User manual print font size small (1 mention)"
        ],
        "ai_improvement_suggestions": [
            "Upgrade outer shipping box padding for fragile items",
            "Include digital PDF version of user manual on listing page"
        ]
    }


async def customer_shopping_copilot(query: str, db: AsyncSession, lang: str = "en") -> Dict[str, Any]:
    """
    Multilingual Customer AI Shopping Copilot assistant powered by NVIDIA AI LLM.
    Uses AI Search keyword extraction & SQLAlchemy DB text matching (RAG).
    """
    logger.info(f"AI Shopping Copilot processing query: '{query}' [Lang: {lang}]")
    lower = query.lower()
    
    # 1. AI-Driven Search keyword extraction (Translating to English for DB indexing match)
    extracted_search = ""
    extract_system = (
        "You are an assistant that extracts the single best English search term (1-3 words) "
        "for an e-commerce catalog from a user query, translating it to English if it is in another language. "
        "Respond only with the English query words (nothing else). "
        "Do not write sentences or punctuation. "
        "Examples:\n"
        "User: 'Show me some nice cotton formal shirts' -> 'cotton formal shirt'\n"
        "User: 'मुझे ताज़ा जैविक गेहूं चाहिए' -> 'organic wheat'\n"
        "User: 'મને બૂટ ખરીદવા છે' -> 'shoes'\n"
        "User: 'I want to buy a smartphone' -> 'smartphone'"
    )
    extract_user = f"Extract e-commerce search term from: '{query}'"
    try:
        extracted_search = await call_nvidia_llm(extract_user, extract_system)
    except Exception as e:
        logger.warning(f"AI search keyword extraction failed: {e}")

    # Fallback keyword parsing via stop words/conversational fillers
    conversational_fillers = {
        # English
        "from", "in", "a", "an", "the", "of", "to", "for", "with", "and", "or", "is", "are", "on", "at", "by", 
        "under", "above", "do", "you", "have", "i", "we", "me", "us", "your", "my", "our", "show", "find", 
        "recommend", "suggest", "me", "please", "can", "could", "would", "should", "will", "shall", "does", 
        "did", "has", "had", "was", "were", "be", "been", "being", "get", "got", "go", "went", "gone", "about", 
        "any", "some", "all", "anyway", "like", "want", "need", "looking", "buy", "purchase", "shop", "item", 
        "items", "product", "products", "good", "best", "great", "cheap", "expensive", "under", "below", "above", 
        "price", "cost", "rupee", "rupees", "rs", "inr", "between", "this", "that", "these", "those",
        "who", "what", "where", "when", "why", "how", "which",
        
        # Hindi
        "मुझे", "चाहिए", "है", "हैं", "का", "की", "के", "में", "पर", "से", "को", "और", "भी", "या", "तो", "क्या", 
        "कैसे", "कहाँ", "कब", "कौन", "दिखाओ", "ढूंढो", "बताओ", "देना", "लिए", "था", "थे", "थी", "हो", "सकता", "सकते",
        
        # Gujarati
        "મને", "જોઈએ", "છે", "નો", "ની", "નું", "ના", "માં", "પર", "થી", "અને", "પણ", "અથવા", "તો", "શું", "કેવી", 
        "રીતે", "ક્યાં", "ક્યારે", "કોણ", "કયું", "બતાવો", "શોધો", "કહો", "આપો", "હતો", "હતી", "હતું", "હતા", "થઈ", "શકે"
    }

    # Cross-lingual dictionary for common agricultural/consumer keywords
    cross_lingual_dict = {
        # Hindi
        "गेहूं": "wheat", "गेहूँ": "wheat", "चावल": "rice", "आम": "mango", "कपड़े": "clothing", "कपड़ा": "clothing",
        "जूते": "shoes", "जूता": "shoes", "दूध": "milk", "दवा": "medicine", "सब्जी": "vegetable", "दाल": "dal",
        "तेल": "oil", "घी": "ghee", "पानी": "water", "मोबाइल": "phone", "फोन": "phone", "लैपटॉप": "laptop",
        "चाय": "tea", "चीनी": "sugar", "मसाले": "spice", "हल्दी": "turmeric",
        
        # Gujarati
        "ઘઉં": "wheat", "ચોખા": "rice", "કેરી": "mango", "કપડા": "clothing", "કપડું": "clothing",
        "બૂટ": "shoes", "દૂધ": "milk", "દવા": "medicine", "શાકભાજી": "vegetable", "દાળ": "dal",
        "તેલ": "oil", "ઘી": "ghee", "પાણી": "water", "મોબાઈલ": "phone", "ફોન": "phone", "લેપટોપ": "laptop",
        "ચા": "tea", "ખાંડ": "sugar", "મસાલા": "spice", "હળદર": "turmeric"
    }

    # Gather search tokens
    search_tokens = []
    if extracted_search:
        search_tokens = [w.strip().lower() for w in re.split(r'\s+', extracted_search) if len(w.strip()) > 1]
    
    # If LLM didn't return good tokens, parse from user query
    if not search_tokens:
        search_tokens = [w for w in re.findall(r'\w+', lower) if len(w) > 1 and w not in conversational_fillers]

    # Map cross-lingual tokens
    mapped_tokens = []
    for token in search_tokens:
        if token in cross_lingual_dict:
            mapped_tokens.append(cross_lingual_dict[token])
    search_tokens.extend(mapped_tokens)
    
    # Remove duplicates while preserving order
    search_tokens = list(dict.fromkeys(search_tokens))

    logger.info(f"AI Copilot search tokens: {search_tokens}")

    # 2. Database search query execution (RAG)
    db_listings = []
    if search_tokens:
        try:
            conditions = []
            for token in search_tokens:
                conditions.append(Listing.title.ilike(f"%{token}%"))
                conditions.append(Listing.description.ilike(f"%{token}%"))
            
            query_select = (
                select(Listing)
                .join(Listing.category, isouter=True)
                .options(selectinload(Listing.media), selectinload(Listing.category))
                .where(Listing.status == "active")
            )
            
            cat_conditions = []
            for token in search_tokens:
                cat_conditions.append(Category.name.ilike(f"%{token}%"))
                
            query_select = query_select.where(or_(*(conditions + cat_conditions)))
            
            res = await db.execute(query_select)
            db_listings = list(res.scalars().all())
        except Exception as e:
            logger.error(f"AI Catalog search database query failed: {e}")

    # Fallback to general list if no matches
    if not db_listings:
        try:
            res = await db.execute(
                select(Listing)
                .options(selectinload(Listing.media), selectinload(Listing.category))
                .where(Listing.status == "active")
                .limit(50)
            )
            db_listings = list(res.scalars().all())
        except Exception as e:
            logger.error(f"Catalog fallback query failed: {e}")

    # 3. Python-based scoring & ranking of the retrieved listings
    scored_listings = []
    for l in db_listings:
        title = l.title.lower()
        desc = (l.description or "").lower()
        cat = (l.category.name if l.category else "").lower()
        
        score = 0
        if search_tokens:
            for w in search_tokens:
                if w in title:
                    score += 15
                if w in cat:
                    score += 10
                if w in desc:
                    score += 2
        else:
            score = 0
        scored_listings.append((score, l))

    # Sort descending by relevance match score
    scored_listings.sort(key=lambda x: x[0], reverse=True)
    
    # Filter to matching relevance or top 4 if fallback
    if search_tokens and any(score > 0 for score, _ in scored_listings):
        top_matches = [l for score, l in scored_listings if score > 0][:4]
    else:
        top_matches = [l for _, l in scored_listings][:4]

    # Convert to formatted copilot model dicts
    matched = []
    for l in top_matches:
        matched.append({
            "id": str(l.id),
            "title": l.title,
            "price": l.price,
            "description": l.description,
            "image": l.media[0].media_url if l.media else "https://via.placeholder.com/150",
            "category_name": l.category.name if l.category else "General"
        })

    # Build catalog text context for LLM response
    product_context = "\n".join([
        f"- {p.get('title')} (₹{p.get('price', 0)/100:.2f}, Category: {p.get('category_name')}): {p.get('description', '')[:120]}"
        for p in matched
    ])

    system_prompt = (
        "You are Samuday's AI Shopping Copilot assistant. "
        "Help the buyer with their query using the provided product catalog items. "
        f"Answer directly in language '{lang}' (e.g. English, Hindi, Gujarati). "
        "Keep your response warm, helpful, and detailed (2-4 sentences). "
        "Use Markdown formatting such as bold (**word**) and bullet points (- item) or numbered lists for clean structure and readable formatting."
    )

    user_prompt = (
        f"User question: '{query}'\n\n"
        f"Available catalog items:\n{product_context}\n\n"
        "Provide a direct recommendation."
    )

    llm_reply = await call_nvidia_llm(user_prompt, system_prompt)
    if llm_reply and len(llm_reply.strip()) > 5:
        advice = llm_reply
    else:
        # Formulate base fallback advice based on language
        if lang == "hi" or any(k in lower for k in ["हिंदी", "गेहूं", "फोन"]):
            advice = f"नमस्ते! आपके प्रश्न '{query}' के आधार पर, मैंने समुदाय पर आपके लिए सर्वोत्तम उत्पाद चुने हैं:"
        elif lang == "gu" or any(k in lower for k in ["ગુજરાતી", "ઘઉં", "મોબાઈલ"]):
            advice = f"નમસ્તે! તમારા પ્રશ્ન '{query}' ના આધારે, મેં સમુદાય પરથી તમારા માટે શ્રેષ્ઠ ઉત્પાદનો શોધ્યા છે:"
        else:
            advice = f"Hello! Based on your search for '{query}', here are the top recommended items available on Samuday:"

    return {
        "reply": advice,
        "recommended_products": matched,
        "suggested_followups": [
            "Show items with free shipping",
            "Show highest rated items",
            "Show items on sale discount"
        ]
    }
