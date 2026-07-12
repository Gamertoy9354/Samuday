import pytest
from app.ai.service import clean_thinking_blocks
from app.core.config import settings

def test_clean_thinking_blocks_xml():
    # 1. Test XML thought tag removal
    assert clean_thinking_blocks("<thought>Thinking process here</thought>Actual response") == "Actual response"
    assert clean_thinking_blocks("<thinking>Thinking process here</thinking>Actual response") == "Actual response"
    assert clean_thinking_blocks("<THOUGHT>Thinking process here\nmulti-line</THOUGHT>\nActual response") == "Actual response"

def test_clean_thinking_blocks_headers():
    # 2. Test headers with Response keyword
    input_text = (
        "Thinking Process:\n"
        "- The user wants shoes.\n"
        "- Show sneakers.\n"
        "Response:\n"
        "Here are the best shoes."
    )
    assert clean_thinking_blocks(input_text) == "Here are the best shoes."

def test_clean_thinking_blocks_non_bullet():
    # 3. Test when thinking process has non-bullet lines
    input_text = (
        "Thought:\n"
        "The user is asking for shoes.\n"
        "I should search for shoes.\n"
        "Response:\n"
        "Here is the response."
    )
    # Let's see what clean_thinking_blocks outputs.
    # Currently it might output:
    # "The user is asking for shoes.\nI should search for shoes.\nResponse:\nHere is the response."
    # Let's run a test to see.
    output = clean_thinking_blocks(input_text)
    print("OUTPUT:", repr(output))
    assert output == "Here is the response."

from httpx import AsyncClient

@pytest.mark.asyncio
async def test_upload_image_endpoint(client: AsyncClient):
    # Register a user to get auth token
    await client.post(
        "/api/v1/identity/auth/register?otp_code=123456",
        json={"phone_number": "+919876543299", "full_name": "Test User", "preferred_language": "en"}
    )
    login_res = await client.post(
        "/api/v1/identity/auth/verify-otp",
        json={"phone_number": "+919876543299", "otp_code": "123456"}
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Upload dummy image
    files = {"file": ("test.png", b"dummy_content", "image/png")}
    response = await client.post("/api/v1/marketplace/upload", files=files, headers=headers)
    assert response.status_code == 200
    assert "url" in response.json()
    assert response.json()["url"].startswith(f"{settings.SUPABASE_URL}/storage/v1/object/public/")
