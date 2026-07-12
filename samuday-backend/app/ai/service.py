import logging
import random
import re
import asyncio
from datetime import datetime, timezone, timedelta
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
    Generates 3 distinct, high-quality visual variations of the uploaded primary image
    using Pillow, uploading each to Supabase Storage. Each variant simulates a
    professional photography angle/style:
      1. Top-Down Studio View — rotated perspective with clean white padding
      2. Side-Angle Dramatic — perspective warp with high contrast dark background
      3. Warm Golden Hour Lifestyle — saturated warm tones with soft vignette
    """
    import io
    import uuid
    from PIL import Image, ImageEnhance, ImageFilter, ImageDraw
    from app.core.storage import upload_bytes

    generated_urls = []

    source = await _load_image_bytes(primary_image_url)
    if not source:
        return []
    source_bytes, _ = source

    try:
        with Image.open(io.BytesIO(source_bytes)) as img:
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
            buf1 = io.BytesIO()
            bg1.save(buf1, "JPEG", quality=92)
            generated_urls.append(await upload_bytes(buf1.getvalue(), v1_filename, "image/jpeg"))
            
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
            buf2 = io.BytesIO()
            detail_rgb.save(buf2, "JPEG", quality=92)
            generated_urls.append(await upload_bytes(buf2.getvalue(), v2_filename, "image/jpeg"))
            
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
            buf3 = io.BytesIO()
            lifestyle.save(buf3, "JPEG", quality=92)
            generated_urls.append(await upload_bytes(buf3.getvalue(), v3_filename, "image/jpeg"))
            
    except Exception as e:
        logger.error(f"Error during PIL local variant generation: {e}")
        
    return generated_urls

GEMINI_IMAGE_MODEL = "gemini-2.5-flash-image"  # "Nano Banana" — free-tier image generation/editing


async def _load_image_bytes(image_url: str) -> Optional[tuple]:
    """Fetches a primary_image_url (a Supabase Storage public URL) to (bytes, mime_type)."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(image_url, timeout=10.0)
            if resp.status_code == 200:
                mime_type = resp.headers.get("content-type", "image/jpeg").split(";")[0]
                return resp.content, mime_type
    except Exception as e:
        logger.error(f"Failed to fetch primary image for AI editing: {e}")
    return None


async def _gemini_edit_image(source_bytes: bytes, source_mime: str, prompt: str) -> Optional[bytes]:
    """Sends one image + edit instruction to Gemini 2.5 Flash Image, returns the edited image bytes or None."""
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        return None
    source_b64 = base64.b64encode(source_bytes).decode("utf-8")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_IMAGE_MODEL}:generateContent"
    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inlineData": {"mimeType": source_mime, "data": source_b64}}
            ]
        }],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=30.0)
            if response.status_code == 200:
                res_data = response.json()
                parts = res_data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                image_part = next((p for p in parts if "inlineData" in p), None)
                if image_part:
                    return base64.b64decode(image_part["inlineData"]["data"])
            logger.warning(f"Gemini Nano Banana image edit failed with code {response.status_code}: {response.text[:300]}")
    except Exception as e:
        logger.error(f"Error during Gemini Nano Banana image edit: {e}")
    return None


async def _cloudflare_edit_image(source_bytes: bytes, source_mime: str, prompt: str) -> Optional[bytes]:
    """
    Free image-to-image fallback via Cloudflare Workers AI's flux-2-klein-4b model, which
    unifies generation and editing in one model. Takes the source image bytes directly
    (multipart upload — no public URL needed). Free tier: 10,000 Neurons/day, no card required.
    """
    account_id = settings.CLOUDFLARE_ACCOUNT_ID
    api_token = settings.CLOUDFLARE_API_TOKEN
    if not account_id or not api_token:
        return None
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/black-forest-labs/flux-2-klein-4b"
    headers = {"Authorization": f"Bearer {api_token}"}
    files = {"input_image_0": ("source.jpg", source_bytes, source_mime or "image/jpeg")}
    data = {"prompt": prompt}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, files=files, data=data, timeout=60.0)
            if response.status_code == 200:
                res_data = response.json()
                img_b64 = res_data.get("result", {}).get("image")
                if img_b64:
                    return base64.b64decode(img_b64)
            logger.warning(f"Cloudflare Workers AI image edit failed with code {response.status_code}: {response.text[:300]}")
    except Exception as e:
        logger.error(f"Error during Cloudflare Workers AI image edit: {e}")
    return None


async def _edit_image_with_fallback(source_bytes: bytes, source_mime: str, prompt: str) -> Optional[bytes]:
    """
    Edits an image via Gemini Nano Banana first (primary — generally higher quality, no
    rate-limit surprises). If that's unavailable (no API key, quota exhausted, transient
    failure), falls back to Cloudflare Workers AI so the feature still returns an image
    instead of erroring out.
    """
    edited = await _gemini_edit_image(source_bytes, source_mime, prompt)
    if edited:
        return edited
    logger.info("Gemini image edit unavailable — falling back to Cloudflare Workers AI")
    return await _cloudflare_edit_image(source_bytes, source_mime, prompt)


async def generate_ad_creative(listing_title: str, listing_description: str, primary_image_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Generates a complete ad creative for a seller's "Advertise" tab: a punchy headline
    (via NVIDIA LLM) and an eye-catching promotional banner image derived from the
    listing's own photo (via Gemini Nano Banana image editing, falling back to the
    original photo untouched if image editing isn't available).
    """
    system_prompt = (
        "You are an expert e-commerce advertisement copywriter for the Indian market. "
        "Given a product's title and description, write ONE punchy advertisement headline "
        "suitable for a homepage banner (under 60 characters). "
        "Respond with ONLY the headline text itself — no quotes, no explanation, no markdown, "
        "no restating these instructions.\n\n"
        "Example:\n"
        "Product: boAt Airdopes 141 TWS Bluetooth Earbuds - Black\n"
        "Headline: Big Bass, Bigger Savings — boAt Airdopes 141\n\n"
        "Example:\n"
        "Product: Premium Organic Basmati Rice 25kg - Grade A Punjab Origin\n"
        "Headline: Farm-Fresh Basmati Rice, Delivered to Your Door"
    )
    user_prompt = f"Product: {listing_title}\nDescription: {(listing_description or '')[:400]}\nHeadline:"
    raw_headline = await call_nvidia_llm(user_prompt, system_prompt, temperature=0.7, max_tokens=40)
    headline = (raw_headline or "").strip().strip('"').strip("*").split("\n")[0].strip()
    # Small/instruction-following-weak models sometimes echo the prompt instead of
    # producing a headline — detect that failure mode and fall back to the title.
    if not headline or len(headline) > 90 or re.search(r'\b(the user|you are|respond with|instructions?)\b', headline, re.IGNORECASE):
        headline = listing_title
    headline = headline[:80]

    ad_image_url = primary_image_url
    if primary_image_url:
        source = await _load_image_bytes(primary_image_url)
        if source:
            source_bytes, source_mime = source
            prompt = (
                f"Edit this product photo of '{listing_title}' into an eye-catching e-commerce "
                f"advertisement banner: wide promotional composition, bold vivid colors, professional "
                f"marketing look, with clean negative space on one side reserved for text overlay. "
                f"Keep the product itself recognizable and unchanged."
            )
            edited_bytes = await _edit_image_with_fallback(source_bytes, source_mime, prompt)
            if edited_bytes:
                import uuid
                from app.core.storage import upload_bytes
                try:
                    ad_image_url = await upload_bytes(edited_bytes, f"ad_{uuid.uuid4().hex}.jpg", "image/jpeg")
                except Exception as e:
                    logger.error(f"Failed to upload AI ad creative image: {e}")

    return {"headline": headline, "image_url": ad_image_url}


async def generate_ai_variant_images(primary_image_url: str, title: str, category: str = "general") -> List[str]:
    """
    Generates 3 additional high-quality AI variant product showcase photos from the primary image.
    Uses Gemini 2.5 Flash Image ("Nano Banana") to edit the seller's actual uploaded photo into
    professional showcase variants — it's available on the Gemini API free tier (500 req/day),
    unlike the Imagen predict endpoint, which requires a paid plan. Falls back to Cloudflare
    Workers AI per-image if Gemini is unavailable, then to local Pillow-based variants, then
    themed stock photos, if neither AI provider comes through.
    """
    import uuid
    from app.core.storage import upload_bytes
    logger.info(f"Generating AI variant images for '{title}' (Category: {category})")

    prompts = [
        f"Edit this product photo of '{title}' into a professional e-commerce studio shot: clean pure-white background, "
        f"soft even studio lighting, sharp focus, centered composition. Keep the product itself unchanged.",
        f"Edit this product photo of '{title}' into a vibrant lifestyle shot: place it in a realistic, warmly-lit "
        f"in-use context that suits the product, high resolution. Keep the product itself recognizable and unchanged.",
        f"Edit this product photo of '{title}' into a detailed macro close-up that highlights its material and build "
        f"quality, shallow depth of field, premium editorial look. Keep the product itself unchanged."
    ]

    generated_urls = []
    source = await _load_image_bytes(primary_image_url)

    if source:
        source_bytes, source_mime = source
        for prompt in prompts:
            edited_bytes = await _edit_image_with_fallback(source_bytes, source_mime, prompt)
            if edited_bytes:
                filename = f"gen_{uuid.uuid4().hex}.jpg"
                try:
                    generated_urls.append(await upload_bytes(edited_bytes, filename, "image/jpeg"))
                except Exception as e:
                    logger.error(f"Failed to upload AI variant image to storage: {e}")

    # Fallback to local image variations if neither AI provider comes through
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

5. WEIGHT: Estimate the shipping weight of ONE unit of the product in grams (integer), including reasonable packaging. Use real-world knowledge (e.g. earbuds ~150g, a ceiling fan ~2500g, a 25kg rice bag ~25500g, a smartphone ~250g). This is used for courier rate calculation, so it matters — never omit it.

EXAMPLES:

Input: "boat airdopes 141 earbuds bluetooth TWS price 1299"
Output:
{
  "title": "boAt Airdopes 141 TWS Bluetooth Earbuds - Black",
  "description": "### boAt Airdopes 141 TWS Bluetooth Earbuds\\n\\n**Product Overview**\\nExperience true wireless freedom with the boAt Airdopes 141. These lightweight TWS earbuds deliver immersive audio with powerful bass, crystal-clear calls, and an ergonomic in-ear design perfect for daily commutes and workouts.\\n\\n**Key Features**\\n- 🎵 8mm Drivers with boAt Signature Sound\\n- 🔋 Up to 42 hours total playback with charging case\\n- 📱 Bluetooth v5.1 with instant pairing and low latency\\n- 💧 IPX4 water and sweat resistance\\n- 🎤 Built-in microphone with ENx noise cancellation\\n\\n**What's in the Box**\\n- 1x boAt Airdopes 141 (L+R earbuds)\\n- 1x Charging case\\n- 1x USB-C charging cable\\n- 3x Ear tip sizes (S/M/L)\\n\\n**Warranty & Support**\\n- 1 Year Manufacturer Warranty\\n- Dedicated boAt customer support",
  "category": "Electronics",
  "price_inr": 1299,
  "weight_grams": 150
}

Input: "i want to sell organic basmati rice 25kg bag for 1800 rupees premium quality from Punjab"
Output:
{
  "title": "Premium Organic Basmati Rice 25kg - Grade A Punjab Origin",
  "description": "### Premium Organic Basmati Rice — 25kg Pack\\n\\n**Product Overview**\\nSourced directly from the fertile lands of Punjab, this premium organic basmati rice is 100% natural and free from pesticides. Each grain is extra-long, aromatic, and cooks into fluffy, separated grains perfect for biryani, pulao, and everyday meals.\\n\\n**Key Features**\\n- 🌾 100% Certified Organic — No pesticides or chemicals\\n- 📏 Extra-long grain basmati (8mm+ after cooking)\\n- 🏆 Grade A quality with strict quality control\\n- 🚛 Farm-fresh, directly sourced from Punjab farmers\\n- 📦 Airtight 25kg packaging for long shelf life\\n\\n**What's in the Box**\\n- 1x 25kg bag of Premium Organic Basmati Rice\\n- Quality certification card\\n\\n**Warranty & Support**\\n- 30-day freshness guarantee\\n- Easy returns if quality does not meet expectations",
  "category": "Agriculture",
  "price_inr": 1800,
  "weight_grams": 25500
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
    weight_grams = 500

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

        # ── Weight (for Delhivery shipping rate calculation) ──
        if parsed_json.get("weight_grams") is not None:
            try:
                weight_grams = max(int(float(parsed_json["weight_grams"])), 10)
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
        "weight_grams": weight_grams,
        "seo_tags": seo_tags,
        "specifications": specs,
        "target_audience": "General Consumers, Local Businesses & Farmers",
        "competitive_pricing_advice": f"Recommended selling price: Rs.{(estimated_price_paise / 100):,.2f}. Competitor range: Rs.{((estimated_price_paise * 0.95)/100):,.2f} - Rs.{((estimated_price_paise * 1.1)/100):,.2f}."
    }


LOW_STOCK_THRESHOLD = 20

async def run_seller_agent(
    prompt: str,
    seller_listings: List[Dict[str, Any]],
    reviews: List[Dict[str, Any]],
    review_analytics: Dict[str, Any],
    orders: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Interactive AI Seller Diagnostic Agent powered by NVIDIA AI LLM. Every "tool" below
    is computed from the seller's real listings/orders/reviews (passed in by the caller),
    not invented — this replaces an earlier version that returned hardcoded canned stats
    (e.g. "boost sales by 35%") regardless of what the seller actually asked or owned.
    """
    logger.info(f"AI Seller Agent query: '{prompt}' on {len(seller_listings)} listings, {len(orders)} orders, {len(reviews)} reviews")
    lower = prompt.lower()

    completed_orders = [o for o in orders if o.get("status") == "completed"]
    cancelled_orders = [o for o in orders if o.get("status") == "cancelled"]
    total_orders = len(orders)
    completion_rate = round(len(completed_orders) / total_orders * 100) if total_orders else 0
    total_revenue_paise = sum(o.get("product_amount", 0) for o in completed_orders)

    low_stock_items = [l for l in seller_listings if l.get("status") == "active" and (l.get("quantity") or 0) < LOW_STOCK_THRESHOLD]

    # Diagnostic tool executions — each grounded in real computed data
    executed_tools = []
    response_text = ""

    if any(k in lower for k in ["review", "rating", "feedback", "customer opinion", "સમીક્ષા", "રેટિંગ"]):
        ra = review_analytics
        if ra["total_reviews"] == 0:
            executed_tools.append({"tool": "analyze_reviews", "status": "info", "output": "No buyer reviews yet."})
            response_text = "📝 **AI Review Analysis Tool**: You don't have any buyer reviews yet. Once buyers rate their completed orders, I'll be able to analyze sentiment trends and flag recurring product issues here."
        else:
            executed_tools.append({
                "tool": "analyze_reviews",
                "status": "success",
                "output": f"Analyzed {ra['total_reviews']} real review(s): {ra['average_rating']}/5 avg, {ra['sentiment_breakdown']['positive_percent']}% positive."
            })
            flaw_note = f" Flagged concerns from buyer comments: {'; '.join(ra['flaw_reports'])}." if ra["flaw_reports"] else " No recurring complaints detected in buyer comments."
            response_text = (
                f"📝 **AI Review Analysis Tool**: Based on your **{ra['total_reviews']} real buyer review(s)**, "
                f"your average rating is **{ra['average_rating']}/5** "
                f"({ra['sentiment_breakdown']['positive_percent']}% positive, {ra['sentiment_breakdown']['neutral_percent']}% neutral, {ra['sentiment_breakdown']['negative_percent']}% negative)."
                f"{flaw_note} {ra['ai_improvement_suggestions'][0]}"
            )

    elif any(k in lower for k in ["engagement", "orders", "sales", "revenue", "performance", "how am i doing", "business", "વેચાણ", "ઓર્ડર"]):
        executed_tools.append({
            "tool": "analyze_engagement",
            "status": "success",
            "output": f"{total_orders} total order(s), {completion_rate}% completion rate, ₹{total_revenue_paise / 100:,.2f} revenue from completed orders."
        })
        if total_orders == 0:
            response_text = "📊 **AI Engagement Analysis Tool**: You haven't received any orders yet. Once buyers start ordering, I'll track your completion rate and revenue here."
        else:
            response_text = (
                f"📊 **AI Engagement Analysis Tool**: You've received **{total_orders} order(s)** total — "
                f"**{len(completed_orders)} completed**, **{len(cancelled_orders)} cancelled**, "
                f"a **{completion_rate}% completion rate**. Completed orders have earned you **₹{total_revenue_paise / 100:,.2f}** so far."
            )

    elif any(k in lower for k in ["stock", "inventory", "quantities", "માલ", "જથ્થો", "સ્ટોક", "સામાન"]):
        if low_stock_items:
            names = ", ".join(l.get("title", "") for l in low_stock_items[:5])
            executed_tools.append({
                "tool": "alert_low_stock",
                "status": "warning",
                "output": f"{len(low_stock_items)} item(s) have under {LOW_STOCK_THRESHOLD} units remaining."
            })
            response_text = f"⚠️ **AI Stock Alert Tool**: {len(low_stock_items)} of your active listings have under {LOW_STOCK_THRESHOLD} units remaining: {names}. Replenish soon to avoid running out."
        else:
            executed_tools.append({"tool": "alert_low_stock", "status": "success", "output": "All active listings have healthy stock levels."})
            response_text = f"✅ **AI Stock Alert Tool**: All of your active listings currently have {LOW_STOCK_THRESHOLD}+ units in stock."

    elif any(k in lower for k in ["price", "discount", "cost", "competitor", "ભાવ", "કિંમત", "દામ", "કીમત"]):
        executed_tools.append({
            "tool": "review_pricing",
            "status": "info",
            "output": f"Reviewed pricing across {len(seller_listings)} listing(s)."
        })
        response_text = (
            f"💡 **AI Price Review Tool**: You currently have **{len(seller_listings)} listing(s)**. "
            "I don't have live competitor pricing data connected yet, so I can't quantify a specific price-drop impact — "
            "but you can ask me to analyze which of your listings has the lowest ratings or highest cancellation rate, "
            "which is a data-backed way to prioritize where a price or quality fix would help most."
        )

    else:
        executed_tools.append({
            "tool": "seller_summary",
            "status": "info",
            "output": f"{len(seller_listings)} listings, {total_orders} orders, {review_analytics['total_reviews']} reviews on file."
        })
        response_text = (
            f"✨ **AI Seller Assistant**: You currently have **{len(seller_listings)} listing(s)**, "
            f"**{total_orders} order(s)** ({completion_rate}% completion rate), and "
            f"**{review_analytics['total_reviews']} buyer review(s)** "
            f"(avg {review_analytics['average_rating']}/5). Ask me to analyze your reviews, engagement, pricing, or stock for specifics."
        )

    # Try NVIDIA LLM enhancement — grounded strictly in the real data computed above
    recent_comments = [r["review_text"] for r in reviews[:5] if r.get("review_text")]
    llm_prompt = (
        f"Seller query: '{prompt}'\n\n"
        f"Seller's listings ({len(seller_listings)} items):\n" + "\n".join([
            f"- {l.get('title')} @ ₹{l.get('price', 0)/100:.2f} (Qty: {l.get('quantity')}, status: {l.get('status')})"
            for l in seller_listings[:5]
        ]) +
        f"\n\nReal engagement data: {total_orders} total orders, {len(completed_orders)} completed, "
        f"{len(cancelled_orders)} cancelled, {completion_rate}% completion rate, "
        f"₹{total_revenue_paise / 100:.2f} total revenue from completed orders.\n"
        f"\nReal review data: {review_analytics['total_reviews']} review(s), "
        f"{review_analytics['average_rating']}/5 average rating, "
        f"{review_analytics['sentiment_breakdown']['positive_percent']}% positive sentiment."
        + (f" Recent review comments: {'; '.join(recent_comments)}" if recent_comments else " No review comments yet.") +
        "\n\nProvide helpful, structured e-commerce advice using Markdown: bullet points for lists, "
        "and a Markdown pipe table (| Column | Column |\\n|---|---|\\n| ... |) whenever comparing "
        "multiple listings, prices, or metrics side by side. Base your analysis strictly on the real data "
        "given above — if the data needed to answer isn't provided (e.g. no reviews yet, no orders yet), say so "
        "plainly instead of inventing numbers, percentages, or trends."
    )
    llm_reply = await call_nvidia_llm(
        llm_prompt,
        "You are an expert AI seller business coach and diagnostic agent for an e-commerce platform. "
        "Only use the real data provided in the prompt; never fabricate statistics, percentages, or results."
    )
    if llm_reply:
        response_text = llm_reply

    suggested_actions = []
    if low_stock_items:
        suggested_actions.append("Replenish Low Stock Items")
    if review_analytics["total_reviews"] > 0 and review_analytics["sentiment_breakdown"]["negative_percent"] > 0:
        suggested_actions.append("Review Flagged Customer Feedback")
    if total_orders == 0:
        suggested_actions.append("Promote Your First Listing")
    if not suggested_actions:
        suggested_actions.append("Ask Me to Analyze Reviews or Engagement")

    return {
        "reply": response_text,
        "tools_executed": executed_tools,
        "timestamp": "Just now",
        "suggested_actions": suggested_actions
    }


def _parse_iso(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


async def get_seller_ai_insights(
    seller_listings: List[Dict[str, Any]],
    sales: List[Dict[str, Any]],
    orders: List[Dict[str, Any]],
    review_analytics: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Generates the seller dashboard's "Live AI Insight" banner and notification feed from the
    seller's real listings/orders/reviews — replaces an earlier version that returned the same
    hardcoded fake stats (28% page-view spike, 94% health score, etc.) to every seller regardless
    of their actual data.
    """
    now = datetime.now(timezone.utc)
    total_listings = len(seller_listings)
    active_listings = [l for l in seller_listings if l.get("status") == "active"]
    low_stock_items = [l for l in active_listings if (l.get("quantity") or 0) < LOW_STOCK_THRESHOLD]

    completed_orders = [o for o in orders if o.get("status") == "completed"]
    completion_rate = round(len(completed_orders) / len(orders) * 100) if orders else None
    recent_orders = [o for o in orders if (dt := _parse_iso(o.get("created_at"))) and dt >= now - timedelta(hours=48)]

    expiring_sales = [
        s for s in sales
        if s.get("status") == "active" and (dt := _parse_iso(s.get("end_date"))) and now <= dt <= now + timedelta(days=3)
    ]

    notifications = []

    if recent_orders:
        notifications.append({
            "id": "orders-48h",
            "type": "success",
            "title": "📈 New Orders",
            "message": f"You received {len(recent_orders)} order(s) in the last 48 hours.",
            "time": "Live"
        })

    if review_analytics.get("total_reviews", 0) > 0 and review_analytics["sentiment_breakdown"]["negative_percent"] > 0:
        notifications.append({
            "id": "negative-reviews",
            "type": "warning",
            "title": "⚠️ Reviews Need Attention",
            "message": f"{review_analytics['sentiment_breakdown']['negative_percent']}% of your {review_analytics['total_reviews']} review(s) are negative. Check the Reviews tab for details.",
            "time": "Live"
        })

    if low_stock_items:
        names = ", ".join(l.get("title", "") for l in low_stock_items[:3])
        notifications.append({
            "id": "low-stock",
            "type": "warning",
            "title": "⚡ Low Stock Warning",
            "message": f"{len(low_stock_items)} listing(s) have under {LOW_STOCK_THRESHOLD} units remaining: {names}.",
            "time": "Live"
        })

    if expiring_sales:
        names = ", ".join(s.get("title", "") for s in expiring_sales[:3])
        notifications.append({
            "id": "sales-expiring",
            "type": "info",
            "title": "⏳ Sale Event(s) Ending Soon",
            "message": f"{len(expiring_sales)} sale event(s) end within 3 days: {names}.",
            "time": "Live"
        })

    if total_listings == 0:
        notifications.append({
            "id": "no-listings",
            "type": "info",
            "title": "🚀 Get Started",
            "message": "You haven't published any listings yet. Add your first product to start selling.",
            "time": "Live"
        })

    if not notifications:
        notifications.append({
            "id": "all-clear",
            "type": "success",
            "title": "✅ All Clear",
            "message": "No urgent issues right now — stock levels, orders, and reviews all look healthy.",
            "time": "Live"
        })

    # Health score: a real composite of completion rate, review rating, and stock health —
    # only includes components that have actual data behind them (no data = not averaged in,
    # rather than assuming a default).
    health_components = []
    if completion_rate is not None:
        health_components.append(completion_rate)
    if review_analytics.get("total_reviews", 0) > 0:
        health_components.append(review_analytics["average_rating"] / 5 * 100)
    if active_listings:
        stock_health = max(0, 100 - len(low_stock_items) / len(active_listings) * 100)
        health_components.append(stock_health)
    health_score = round(sum(health_components) / len(health_components)) if health_components else None

    if low_stock_items:
        recommendation = f"Restock {low_stock_items[0].get('title')} — it's running low and could go out of stock."
    elif review_analytics.get("total_reviews", 0) > 0 and review_analytics["sentiment_breakdown"]["negative_percent"] > 0:
        recommendation = "Some buyers left negative reviews recently — review them and consider replying personally."
    elif total_listings == 0:
        recommendation = "Publish your first listing to start appearing in search and category pages."
    elif not sales:
        recommendation = "You don't have any active sale events — consider launching one to boost visibility."
    else:
        recommendation = "Your shop is running smoothly — keep listings updated and respond to buyer messages promptly."

    summary = {
        "health_score": health_score,
        "total_listings": total_listings,
        "active_sales_count": len(sales),
        "ai_recommendation": recommendation,
    }

    return {
        "summary": summary,
        "notifications": notifications
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
    Summarizes real review sentiment distribution from the seller's actual reviews.
    Returns a "no data yet" shape (not invented numbers) when there are none.
    """
    total = len(reviews_list)
    if total == 0:
        return {
            "total_reviews": 0,
            "average_rating": 0,
            "sentiment_breakdown": {"positive_percent": 0, "neutral_percent": 0, "negative_percent": 0},
            "top_praises": [],
            "flaw_reports": [],
            "ai_improvement_suggestions": ["No reviews yet — insights will appear here once buyers start rating completed orders."]
        }

    ratings = [r.get("rating", 0) for r in reviews_list]
    average_rating = round(sum(ratings) / total, 1)
    positive = sum(1 for r in ratings if r >= 4)
    neutral = sum(1 for r in ratings if r == 3)
    negative = sum(1 for r in ratings if r <= 2)

    comments = [r.get("review_text", "") for r in reviews_list if r.get("review_text")]
    suggestions = []
    if negative > 0:
        suggestions.append("Review your lower-rated orders below and consider reaching out to those buyers directly.")
    if not suggestions:
        suggestions.append("Keep it up — your reviews are trending positive!")

    return {
        "total_reviews": total,
        "average_rating": average_rating,
        "sentiment_breakdown": {
            "positive_percent": round(positive / total * 100),
            "neutral_percent": round(neutral / total * 100),
            "negative_percent": round(negative / total * 100),
        },
        "top_praises": comments[:4],
        "flaw_reports": [c for c in comments if any(k in c.lower() for k in ["bad", "poor", "late", "delay", "broken", "damaged", "issue"])][:4],
        "ai_improvement_suggestions": suggestions
    }


# Category inference keywords for the shopping copilot's retrieval — deliberately
# separate from ai/service.py's own listing-generator cat_keywords dict since the
# vocabularies buyers search with (plurals, colloquialisms) differ from what sellers
# title their listings with.
COPILOT_CATEGORY_KEYWORDS = {
    "Agriculture": ["wheat", "rice", "mango", "gehu", "ghee", "kheti", "kisan", "basmati", "crop", "seed",
                    "seeds", "fertilizer", "organic", "harvest", "farm", "grain", "grains", "vegetable",
                    "vegetables", "dal", "atta", "flour"],
    "Fashion": ["shirt", "shirts", "jeans", "saree", "kurti", "wear", "cloth", "clothing", "shoes", "shoe",
                "dress", "jacket", "watch", "watches", "footwear", "apparel"],
    "Electronics": ["tv", "television", "phone", "phones", "mobile", "mobiles", "smartphone", "smartphones",
                     "headphone", "headphones", "laptop", "laptops", "speaker", "speakers", "camera", "cameras",
                     "earbuds", "earphone", "earphones", "tablet", "charger", "smartwatch", "monitor",
                     "electronics", "gadget", "gadgets"],
    "Home/Construction": ["fan", "fans", "mattress", "cookware", "flask", "furniture", "sofa", "bed",
                           "light", "bulb", "paint", "cement", "pipe", "inverter", "ups"],
    "Health": ["face wash", "protein", "medicine", "medicines", "supplement", "vitamin", "ayurvedic",
               "health", "gym", "yoga"],
    "Automobiles": ["car", "cars", "bike", "bikes", "tyre", "tyres", "tire", "helmet", "scooter",
                     "vehicle", "motor"],
    "Retail/FMCG": ["soap", "shampoo", "detergent", "snack", "snacks", "biscuit", "tea", "coffee", "grocery"],
    "Education": ["book", "books", "course", "tuition", "coaching", "study", "exam", "notebook"],
    "Jobs": ["job", "jobs", "vacancy", "hiring", "career", "employment", "recruit", "recruiter"],
}

_PRICE_NUM = r'(?:rs\.?|₹|inr)?\s*(\d[\d,]*(?:\.\d+)?\s*k?)\b'


def _parse_price_token(token: str) -> int:
    """Converts a matched price fragment like '20,000' or '20k' into paise."""
    t = token.strip().lower().replace(",", "").replace("₹", "").replace("rs.", "").replace("rs", "").replace("inr", "").strip()
    if t.endswith("k"):
        value = float(t[:-1]) * 1000
    else:
        value = float(t)
    return int(value * 100)


def extract_price_range_paise(query: str):
    """
    Parses natural-language price constraints ('under 20,000', 'between 500 and 1000',
    '20000 से कम', '500 થી ઓછું') into (price_min_paise, price_max_paise).
    Kept independent of the LLM extraction step so price filtering works even when
    the LLM is unavailable or ignores instructions to drop price phrases.
    """
    t = query.lower()

    m = re.search(rf'between\s*{_PRICE_NUM}\s*(?:and|to|-)\s*{_PRICE_NUM}', t)
    if m:
        a, b = _parse_price_token(m.group(1)), _parse_price_token(m.group(2))
        return min(a, b), max(a, b)

    price_max = None
    m = re.search(rf'(?:under|below|less than|upto|up to|within|max(?:imum)?)\s*{_PRICE_NUM}', t)
    if m:
        price_max = _parse_price_token(m.group(1))
    else:
        m = re.search(rf'{_PRICE_NUM}\s*(?:से\s*कम|थी\s*ઓછું|se\s*kam)', t)
        if m:
            price_max = _parse_price_token(m.group(1))

    price_min = None
    m = re.search(rf'(?:over|above|more than|min(?:imum)?)\s*{_PRICE_NUM}', t)
    if m:
        price_min = _parse_price_token(m.group(1))
    else:
        m = re.search(rf'{_PRICE_NUM}\s*(?:से\s*(?:ज़्यादा|ज्यादा|अधिक)|થી\s*(?:વધારે|વધુ))', t)
        if m:
            price_min = _parse_price_token(m.group(1))

    if price_min is None and price_max is None:
        m = re.search(rf'(?:around|near|approx(?:imately)?)\s*{_PRICE_NUM}', t)
        if m:
            mid = _parse_price_token(m.group(1))
            price_min, price_max = int(mid * 0.7), int(mid * 1.3)

    return price_min, price_max


def infer_category_from_text(text: str) -> Optional[str]:
    """Best-effort category guess from free text, used to bias/restrict catalog retrieval."""
    low = text.lower()
    best_cat, best_hits = None, 0
    for cat, keywords in COPILOT_CATEGORY_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in low)
        if hits > best_hits:
            best_cat, best_hits = cat, hits
    return best_cat


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
        "You are an assistant that extracts the single best English PRODUCT search term (1-3 words) "
        "for an e-commerce catalog from a user query, translating it to English if it is in another language. "
        "Respond only with the English product words (nothing else). "
        "Do not write sentences or punctuation. "
        "CRITICAL: Never include price, budget, quantity, or currency information (e.g. 'under 20000', "
        "'below 500', 'for 2000 rupees') in your answer -- return only the product name/type. "
        "Examples:\n"
        "User: 'Show me some nice cotton formal shirts' -> 'cotton formal shirt'\n"
        "User: 'મને બૂટ ખરીદવા છે' -> 'shoes'\n"
        "User: 'I want to buy a smartphone' -> 'smartphone'\n"
        "User: 'Best smartphones under 20,000' -> 'smartphone'\n"
        "User: 'wheat between 500 and 1000 rupees' -> 'wheat'"
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

    # Always strip fillers and bare numbers/prices from whichever source produced the
    # tokens — the LLM extractor is instructed to drop price phrases but small models
    # don't reliably follow that, and a literal token like "20000" or "under" almost
    # never appears verbatim in a title/description, silently starving the search.
    search_tokens = [
        t for t in search_tokens
        if t not in conversational_fillers and not re.fullmatch(r'[\d,]+k?', t)
    ]

    # Map cross-lingual tokens
    mapped_tokens = []
    for token in search_tokens:
        if token in cross_lingual_dict:
            mapped_tokens.append(cross_lingual_dict[token])
    search_tokens.extend(mapped_tokens)

    # Remove duplicates while preserving order
    search_tokens = list(dict.fromkeys(search_tokens))

    # Price and category intent are parsed independently of the keyword tokens above,
    # so "under 20,000" constrains price rather than being searched for as literal text.
    price_min_paise, price_max_paise = extract_price_range_paise(query)
    inferred_category = infer_category_from_text(query) or infer_category_from_text(" ".join(search_tokens))

    logger.info(
        f"AI Copilot parsed query -> tokens={search_tokens}, category={inferred_category}, "
        f"price_min_paise={price_min_paise}, price_max_paise={price_max_paise}"
    )

    # 2. Database search query execution (RAG), tried from most to least specific so a
    # confident category/price match is never displaced by an unrelated keyword fallback.
    async def _query_tier(category: Optional[str], use_price: bool, use_keywords: bool) -> List[Listing]:
        q = (
            select(Listing)
            .options(selectinload(Listing.media), selectinload(Listing.category))
            .where(Listing.status == "active")
        )
        if category:
            q = q.where(Listing.category.has(Category.name == category))
        if use_price:
            if price_min_paise is not None:
                q = q.where(Listing.price >= price_min_paise)
            if price_max_paise is not None:
                q = q.where(Listing.price <= price_max_paise)
        if use_keywords and search_tokens:
            kw_conditions = []
            for token in search_tokens:
                kw_conditions.append(Listing.title.ilike(f"%{token}%"))
                kw_conditions.append(Listing.description.ilike(f"%{token}%"))
                kw_conditions.append(Listing.category.has(Category.name.ilike(f"%{token}%")))
            q = q.where(or_(*kw_conditions))
        # Newest-first: a stable tiebreaker for the Python relevance-score sort below,
        # and otherwise Postgres's undefined row order skews toward older rows.
        q = q.order_by(Listing.created_at.desc())
        res = await db.execute(q)
        return list(res.scalars().all())

    has_price = price_min_paise is not None or price_max_paise is not None
    tier_specs = []
    if inferred_category and search_tokens:
        tier_specs.append((inferred_category, True, True))
        tier_specs.append((inferred_category, False, True))
    if inferred_category:
        tier_specs.append((inferred_category, True, False))
        tier_specs.append((inferred_category, False, False))
    if search_tokens:
        tier_specs.append((None, True, True))
        tier_specs.append((None, False, True))
    if has_price:
        tier_specs.append((None, True, False))

    db_listings: List[Listing] = []
    for category, use_price, use_keywords in tier_specs:
        try:
            db_listings = await _query_tier(category, use_price, use_keywords)
        except Exception as e:
            logger.error(f"AI Catalog tiered search failed (category={category}, price={use_price}, kw={use_keywords}): {e}")
            db_listings = []
        if db_listings:
            break

    # Fallback to most recently published listings if nothing above matched at all.
    # Ordering by created_at is essential here: without it Postgres returns rows in
    # arbitrary physical order under LIMIT, which tends to favor older rows and can
    # permanently hide newly-added products from this fallback.
    if not db_listings:
        try:
            res = await db.execute(
                select(Listing)
                .options(selectinload(Listing.media), selectinload(Listing.category))
                .where(Listing.status == "active")
                .order_by(Listing.created_at.desc())
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
            "image": l.media[0].media_url if l.media else "",
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
