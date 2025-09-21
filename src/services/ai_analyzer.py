import logging
import aiohttp
import asyncio
import json
from typing import Dict, Any

from src.config import AppConfig
from src.models import ErrorAnalysis
from src.utils.security import CircuitBreaker, RateLimiter
from src.services.lmstudio_client import LMStudioClient

logger = logging.getLogger(__name__)

class GeminiAnalyzer:
    """Handles the analysis of Oracle errors using the Gemini API."""

    def __init__(self, session: aiohttp.ClientSession, config: AppConfig, circuit_breaker: CircuitBreaker, rate_limiter: RateLimiter):
        self.session = session
        self.config = config.ai
        self.circuit_breaker = circuit_breaker
        self.rate_limiter = rate_limiter
        self.api_url = f"{self.config.base_url}/models/gemini-1.5-flash:generateContent?key={self.config.api_key}"

    async def analyze_error(self, error_line: str, server_name: str) -> ErrorAnalysis:
        # (your existing Gemini code unchanged)
        ...
        

class LMStudioAnalyzer:
    """Handles the analysis of Oracle errors using LM Studio API."""

    def __init__(self, session: aiohttp.ClientSession, model: str = "TheBloke/Mistral-7B-Instruct-v0.2-GGUF"):
        self.session = session
        self.model = model
        self.client = LMStudioClient(session)

    async def analyze_error(self, error_line: str, server_name: str) -> ErrorAnalysis:
        """
        Analyzes a single error line using LM Studio and returns a structured ErrorAnalysis object.
        """
        logger.info(f"[{server_name}] Analyzing error with LM Studio: {error_line[:100]}...")

        try:
            response = await self.client.chat_completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert Oracle DBA."},
                    {"role": "user", "content": (
                        f"Analyze the following Oracle alert log entry:\n\n"
                        f"Error Entry: \"{error_line}\"\n\n"
                        "Respond as a single JSON object with these keys: "
                        "'explanation', 'recommended_action', 'criticality', 'reference'. "
                        "Criticality must be one of: Critical, High, Medium, Low, Informational."
                    )}
                ]
            )

            if "choices" not in response or not response["choices"]:
                return ErrorAnalysis(error_line=error_line, explanation="LM Studio returned no choices.", recommended_action="Manual review required", criticality="Medium", reference="N/A", server=server_name, analysis_success=False)

            text_content = response["choices"][0]["message"]["content"].strip()
            json_str = text_content.strip("```json").strip("```").strip()

            try:
                data = json.loads(json_str)
                return ErrorAnalysis(
                    error_line=error_line,
                    explanation=data.get("explanation", "Missing explanation."),
                    recommended_action=data.get("recommended_action", "Missing recommended_action."),
                    criticality=data.get("criticality", "Undefined"),
                    reference=data.get("reference", "N/A"),
                    server=server_name,
                    analysis_success=True
                )
            except json.JSONDecodeError:
                return ErrorAnalysis(error_line=error_line, explanation=f"Failed to parse JSON. Raw: {text_content[:200]}", recommended_action="Manual review required", criticality="Medium", reference="N/A", server=server_name, analysis_success=False)

        except Exception as e:
            logger.error(f"[{server_name}] LM Studio API error: {e}")
            return ErrorAnalysis(error_line=error_line, explanation=f"LM Studio API error: {str(e)}", recommended_action="Manual review required", criticality="Medium", reference="N/A", server=server_name, analysis_success=False)

