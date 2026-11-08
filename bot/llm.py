"""LLM provider interface. Swap GeminiModel for another class with the same method
(e.g. a Claude one) to change providers without touching the bot logic."""

import asyncio
import logging
from pathlib import Path
from typing import Protocol

from google import genai
from google.genai import errors, types

logger = logging.getLogger(__name__)

RETRY_DELAY_SECONDS = 10


class DraftModel(Protocol):
    async def generate(self, prompt: str, photos: list[Path]) -> str:
        """Return the model's raw text reply (expected to be JSON)."""


class GeminiModel:
    def __init__(self, api_key: str, model: str):
        self._client = genai.Client(api_key=api_key)
        self._model = model

    async def generate(self, prompt: str, photos: list[Path]) -> str:
        parts = [
            types.Part.from_bytes(data=photo.read_bytes(), mime_type="image/jpeg")
            for photo in photos
        ]
        config = types.GenerateContentConfig(response_mime_type="application/json", temperature=0.7)
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model, contents=[*parts, prompt], config=config
            )
        except errors.ServerError:  # free tier often returns 503 "high demand"; retry once
            logger.warning("Gemini server error, retrying in %ss", RETRY_DELAY_SECONDS)
            await asyncio.sleep(RETRY_DELAY_SECONDS)
            response = await self._client.aio.models.generate_content(
                model=self._model, contents=[*parts, prompt], config=config
            )
        return response.text or ""
