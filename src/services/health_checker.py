import logging
import shutil
import aiohttp
import asyncio
from typing import Dict, Any

from src.config import AppConfig
from src.models import HealthStatus, HealthCheckResult

logger = logging.getLogger(__name__)

class HealthChecker:
    """Performs health checks on the system and its dependencies."""

    def __init__(self, config: AppConfig):
        self.config = config

    async def check_disk_space(self) -> HealthCheckResult:
        """Checks if there is sufficient disk space."""
        try:
            total, used, free = shutil.disk_usage(self.config.monitoring.base_dir)
            free_percent = (free / total) * 100
            status = HealthStatus.HEALTHY if free_percent > 10 else HealthStatus.DEGRADED
            message = f"{free_percent:.2f}% free space available."
            if status == HealthStatus.DEGRADED:
                message += " Low disk space warning."
            return HealthCheckResult(component="Disk Space", status=status, message=message)
        except Exception as e:
            logger.error(f"Disk space check failed: {e}")
            return HealthCheckResult(component="Disk Space", status=HealthStatus.UNHEALTHY, message=str(e))

    async def check_api_connectivity(self) -> HealthCheckResult:
        """Checks connectivity to the Gemini API endpoint."""
        try:
            # We just need to see if the endpoint is reachable, so a HEAD request is efficient.
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.head(self.config.ai.base_url) as response:
                    if response.status < 500:
                        return HealthCheckResult(component="AI API Connectivity", status=HealthStatus.HEALTHY, message="API endpoint is reachable.")
                    else:
                        return HealthCheckResult(component="AI API Connectivity", status=HealthStatus.UNHEALTHY, message=f"API returned server error: {response.status}")
        except asyncio.TimeoutError:
            return HealthCheckResult(component="AI API Connectivity", status=HealthStatus.UNHEALTHY, message="API connection timed out.")
        except Exception as e:
            logger.error(f"API connectivity check failed: {e}")
            return HealthCheckResult(component="AI API Connectivity", status=HealthStatus.UNHEALTHY, message=str(e))

    async def check_system_health(self) -> Dict[str, Any]:
        """Runs all health checks and returns a summary."""
        logger.info("Performing system health check...")
        results = await asyncio.gather(
            self.check_disk_space(),
            self.check_api_connectivity()
        )

        overall_status = HealthStatus.HEALTHY
        for result in results:
            if result.status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
                break
            if result.status == HealthStatus.DEGRADED:
                overall_status = HealthStatus.DEGRADED

        return {
            "overall_status": overall_status,
            "checks": [res.to_dict() for res in results]
        }
