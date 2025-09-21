import logging
import aiohttp
import asyncio
import json
from typing import Dict, Any

# Assuming these are in the specified paths
from src.config import AppConfig
from src.models import ErrorAnalysis
from src.utils.security import CircuitBreaker, RateLimiter

logger = logging.getLogger(__name__)

class GeminiAnalyzer:
    """Handles the analysis of Oracle errors using the Gemini API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        config: AppConfig,
        circuit_breaker: CircuitBreaker,
        rate_limiter: RateLimiter,
    ):
        self.session = session
        self.config = config.ai
        self.circuit_breaker = circuit_breaker
        self.rate_limiter = rate_limiter
        # Use the user-requested model name, ensuring it's URL-friendly
        self.api_url = f"{self.config.base_url}/models/gemini-1.5-flash:generateContent?key={self.config.api_key}"

    async def analyze_error(self, error_line: str, server_name: str) -> ErrorAnalysis:
        """
        Analyzes a single error line using the Gemini API and returns a structured ErrorAnalysis object.
        """
        logger.info(f"[{server_name}] Analyzing error with Gemini: {error_line[:100]}...")

        # Construct the prompt exactly as specified in req16.py
        prompt = (
            f"You are an expert Oracle DBA. Analyze the following Oracle alert log entry:\n\n"
            f"Error Entry: \"{error_line}\"\n\n"
            "Provide your analysis as a single, minified JSON object with no markdown formatting. "
            "The JSON object must contain these exact keys: 'explanation', 'recommended_action', 'criticality', 'reference'.\n"
            "The 'criticality' value must be one of: 'Critical', 'High', 'Medium', 'Low', 'Informational'.\n"
            "For the 'reference' key, provide an Oracle Doc ID or MOS Note number if known, otherwise use 'N/A'."
        )
        
        headers = {'Content-Type': 'application/json'}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}

        # Use the circuit breaker to wrap the API call
        async with self.circuit_breaker:
            for attempt in range(1, self.config.max_retries + 1):
                try:
                    async with self.session.post(self.api_url, headers=headers, json=payload, timeout=self.config.timeout) as response:
                        if response.status == 429: # Rate limit
                            wait_time = 5 * attempt
                            logger.warning(f"[{server_name}] Rate limit hit (429). Waiting {wait_time}s...")
                            await asyncio.sleep(wait_time)
                            continue

                        response.raise_for_status()
                        raw_response = await response.json()
                        
                        # --- Parse the Gemini Response ---
                        if not raw_response.get('candidates'):
                            block_reason = raw_response.get('promptFeedback', {}).get('blockReason')
                            if block_reason:
                                explanation = f"Error: Gemini blocked the prompt. Reason: {block_reason}"
                            else:
                                explanation = "Error: Gemini returned no candidates in the response."
                            return ErrorAnalysis(error_line=error_line, explanation=explanation, recommended_action="Manual review required.", criticality="Medium", reference="N/A", server=server_name, analysis_success=False)

                        candidate = raw_response['candidates'][0]
                        if candidate.get('content') and candidate['content'].get('parts'):
                            # The response is often wrapped in markdown, so we extract the JSON
                            text_content = candidate['content']['parts'][0].get('text', '{}').strip()
                            json_str = text_content.strip('```json').strip('`').strip()
                            
                            try:
                                data = json.loads(json_str)
                                return ErrorAnalysis(
                                    error_line=error_line,
                                    explanation=data.get('explanation', 'Key "explanation" not found.'),
                                    recommended_action=data.get('recommended_action', 'Key "recommended_action" not found.'),
                                    criticality=data.get('criticality', 'Undefined'),
                                    reference=data.get('reference', 'N/A'),
                                    server=server_name,
                                    analysis_success=True
                                )
                            except json.JSONDecodeError:
                                explanation = f"Error: Failed to decode JSON from Gemini response. Raw text: {text_content[:200]}"
                                return ErrorAnalysis(error_line=error_line, explanation=explanation, recommended_action="Manual review required.", criticality="Medium", reference="N/A", server=server_name, analysis_success=False)
                        
                        return ErrorAnalysis(error_line=error_line, explanation="Error: Incomplete Gemini response structure.", recommended_action="Manual review required.", criticality="Medium", reference="N/A", server=server_name, analysis_success=False)

                except aiohttp.ClientError as e:
                    logger.error(f"[{server_name}] Gemini API network error (attempt {attempt}): {e}")
                    await asyncio.sleep(5 * attempt)
                except asyncio.TimeoutError:
                    logger.error(f"[{server_name}] Gemini API timeout (attempt {attempt}).")
                    await asyncio.sleep(5 * attempt)
        
        # If all retries fail, or the circuit breaker is open
        return ErrorAnalysis(
            error_line=error_line,
            explanation=f"Error: Gemini API failed after {self.config.max_retries} retries or circuit breaker is open.",
            recommended_action="Check network connectivity and API key.",
            criticality="Medium",
            reference="N/A",
            server=server_name,
            analysis_success=False
        )

