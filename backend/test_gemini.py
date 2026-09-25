import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

async def test_call():
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key or api_key == 'your_key_here':
        print("Please add your Gemini API key to backend/.env first!")
        return

    from google import genai
    from google.genai import types
    from pydantic import BaseModel
    
    class TestResponse(BaseModel):
        status: str
        message: str

    print("Connecting to Gemini...")
    client = genai.Client(api_key=api_key)
    
    response = await client.aio.models.generate_content(
        model='gemini-3.1-flash-lite',
        contents='Respond with a quick status check indicating everything is working.',
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=TestResponse,
            thinking_config=types.ThinkingConfig(thinking_level="minimal")
        )
    )
    print(f"Success! Response: {response.text}")
    print(f"Usage: {response.usage_metadata}")

if __name__ == '__main__':
    asyncio.run(test_call())
