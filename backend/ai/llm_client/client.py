import json
from mistralai import Mistral
from config import settings

client = Mistral(api_key=settings.mistral_api_key)


async def call_llm_structured(
    system_prompt: str,
    user_message: str,
    temperature: float | None = None,
    model: str | None = None,
) -> dict:
    """
    Call Mistral with JSON-mode output. Returns parsed dict.
    The system prompt must instruct the model to respond only with JSON.

    `model` lets a caller override settings.mistral_model for a single call
    (e.g. if you later want a stronger model for assertion generation and a
    cheaper one for scoring/feedback) without touching every call site.
    """
    temp = temperature if temperature is not None else settings.llm_temperature
    model_name = model or settings.mistral_model

    response = await client.chat.complete_async(
        model=model_name,
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