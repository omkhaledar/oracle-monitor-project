import aiohttp
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class LMStudioClient:
    """Handles interaction with the LM Studio API."""

    def __init__(self, session: aiohttp.ClientSession, base_url: str = "http://swd2504001.elsewedy.home:1234/v1"):
        self.base_url = base_url.rstrip("/")
        self.session = session

    async def list_models(self) -> Dict[str, Any]:
        """GET /v1/models"""
        url = f"{self.base_url}/models"
        async with self.session.get(url) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def chat_completion(self, model: str, messages: List[Dict[str, str]], temperature: float = 0.7) -> Dict[str, Any]:
        """POST /v1/chat/completions"""
        url = f"{self.base_url}/chat/completions"
        payload = {"model": model, "messages": messages, "temperature": temperature}
        async with self.session.post(url, json=payload) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def completion(self, model: str, prompt: str, temperature: float = 0.7) -> Dict[str, Any]:
        """POST /v1/completions"""
        url = f"{self.base_url}/completions"
        payload = {"model": model, "prompt": prompt, "temperature": temperature}
        async with self.session.post(url, json=payload) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def embeddings(self, model: str, input_text: str) -> Dict[str, Any]:
        """POST /v1/embeddings"""
        url = f"{self.base_url}/embeddings"
        payload = {"model": model, "input": input_text}
        async with self.session.post(url, json=payload) as resp:
            resp.raise_for_status()
            return await resp.json()
