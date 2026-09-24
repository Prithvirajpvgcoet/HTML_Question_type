import json
from openai import AsyncOpenAI
from config import settings

client = AsyncOpenAI(api_key=settings.openai_api_key)


async def call_llm_structured(
    system_prompt: str,
    user_message: str,
    temperature: float | None = None,
) -> dict:
    """
    Call GPT-4o with JSON-mode output. Returns parsed dict.
    The system prompt must instruct the model to respond only with JSON.
    """
    temp = temperature if temperature is not None else settings.llm_temperature

    response = await client.chat.completions.create(
        model=settings.openai_model,
        temperature=temp,
        max_tokens=settings.llm_max_tokens,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )

    raw = response.choices[0].message.content
    return json.loads(raw)