#!/bin/bash
#
# update_files.sh
#
# This script populates the necessary Python source files for the Oracle Monitor.
# Run it from the project's root directory (e.g., /u01/genspark/).

echo "🚀 Starting to update project source files..."

# --- Create src/utils/security.py ---
echo "Creating src/utils/security.py..."
cat << 'EOF' > src/utils/security.py
import time
import asyncio
from collections import deque
import logging

logger = logging.getLogger(__name__)

class CircuitBreaker:
    """
    A circuit breaker to prevent repeated calls to a failing service.
    """
    def __init__(self, failure_threshold: int, reset_timeout: int):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # Can be CLOSED, OPEN, or HALF_OPEN

    def record_failure(self):
        """Record a failure and open the circuit if threshold is met."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"Circuit breaker opened. Failing fast for {self.reset_timeout}s.")

    def record_success(self):
        """Reset the circuit on success."""
        self.failure_count = 0
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            logger.info("Circuit breaker closed successfully.")

    async def __aenter__(self):
        """Check the circuit state before allowing an operation."""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.reset_timeout:
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker is now HALF_OPEN. Allowing one test call.")
            else:
                raise ConnectionAbortedError("Circuit breaker is open. Call is blocked.")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Update circuit state based on operation outcome."""
        if exc_type:
            self.record_failure()
        else:
            self.record_success()


class RateLimiter:
    """
    A simple token bucket rate limiter for async operations.
    """
    def __init__(self, rate: int, per: int):
        self.rate = rate
        self.per = per
        self.allowance = rate
        self.last_check = time.monotonic()

    async def acquire(self):
        """Wait until a token is available."""
        while True:
            now = time.monotonic()
            time_passed = now - self.last_check
            self.last_check = now
            self.allowance += time_passed * (self.rate / self.per)

            if self.allowance > self.rate:
                self.allowance = self.rate  # Cap the allowance

            if self.allowance >= 1:
                self.allowance -= 1
                return
            
            # Calculate sleep time to wait for the next token
            sleep_time = (1 - self.allowance) * (self.per / self.rate)
            await asyncio.sleep(sleep_time)
EOF

# --- Create src/utils/metrics.py ---
echo "Creating src/utils/metrics.py..."
cat << 'EOF' > src/utils/metrics.py
import logging
from pathlib import Path

from src.models import MonitoringMetrics

logger = logging.getLogger(__name__)

class MetricsCollector:
    """Collects and persists monitoring metrics."""

    def __init__(self, metrics_file: str = "/var/log/oracle_monitor_metrics.jsonl"):
        self.metrics_file = Path(metrics_file)
        # Ensure the directory for the metrics file exists
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)

    def record_run(self, metrics: MonitoringMetrics):
        """
        Records the metrics of a single monitoring run to a file.
        Appends data as a new line in JSON Lines format.
        """
        try:
            with open(self.metrics_file, 'a') as f:
                f.write(metrics.to_json() + '\n')
            logger.info(f"Metrics successfully recorded to {self.metrics_file}")
        except IOError as e:
            logger.error(f"Failed to write metrics to {self.metrics_file}: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred while recording metrics: {e}", exc_info=True)
EOF

# --- Create src/services/ai_analyzer.py ---
echo "Creating src/services/ai_analyzer.py..."
cat << 'EOF' > src/services/ai_analyzer.py
import logging
import aiohttp
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
        self.api_url = f"{self.config.base_url}/models/{self.config.model}:generateContent?key={self.config.api_key}"

    async def analyze_error(self, error_line: str, server_name: str) -> ErrorAnalysis:
        """
        Analyzes a single error line using the Gemini API.
        
        This is a placeholder implementation. You will need to replace the
        mock response logic with an actual API call and error handling.
        """
        logger.info(f"Analyzing error for {server_name}: {error_line[:100]}...")

        # --- TODO: Implement the actual API call logic here ---
        # This is a mock response for now so the program can run.
        # You should build the real request payload and handle the API response.
        
        # Returning a mock successful analysis for demonstration
        return ErrorAnalysis(
            error_line=error_line,
            explanation="This is a mock explanation from the placeholder analyzer.",
            recommended_action="Check the full implementation of GeminiAnalyzer.",
            criticality="Medium",
            reference="N/A",
            server=server_name,
            analysis_success=True
        )
EOF

# --- Create src/services/email_service.py ---
echo "Creating src/services/email_service.py..."
cat << 'EOF' > src/services/email_service.py
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Any
from datetime import datetime

from src.config import AppConfig
from src.models import ErrorAnalysis

logger = logging.getLogger(__name__)

class EmailService:
    """Handles sending email reports."""

    def __init__(self, config: AppConfig):
        self.config = config.email

    def _format_html_report(self, results_by_server: Dict[str, List[ErrorAnalysis]], timestamp: datetime) -> str:
        """Formats the analysis results into an HTML report."""
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #2c3e50; }}
                h2 {{ color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 5px; }}
                .server-block {{ margin-bottom: 20px; border: 1px solid #ccc; border-radius: 5px; padding: 15px; }}
                .error-item {{ margin-bottom: 15px; padding: 10px; border-left: 5px solid #e74c3c; background-color: #f9f9f9; }}
                .criticality-High {{ border-left-color: #c0392b; }}
                .criticality-Medium {{ border-left-color: #f39c12; }}
                .criticality-Low {{ border-left-color: #27ae60; }}
                strong {{ color: #34495e; }}
            </style>
        </head>
        <body>
            <h1>Oracle Alert Log AI Analysis Report</h1>
            <p><strong>Report Timestamp:</strong> {timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
        """

        for server_name, results in results_by_server.items():
            if not results:
                continue

            html += f"""
            <div class="server-block">
                <h2>Server: {server_name}</h2>
            """
            for analysis in results:
                html += f"""
                <div class="error-item criticality-{analysis.criticality}">
                    <p><strong>Error:</strong> <code>{analysis.error_line}</code></p>
                    <p><strong>Explanation:</strong> {analysis.explanation}</p>
                    <p><strong>Recommended Action:</strong> {analysis.recommended_action}</p>
                    <p><strong>Criticality:</strong> {analysis.criticality}</p>
                </div>
                """
            html += "</div>"

        html += "</body></html>"
        return html

    async def send_comprehensive_report(self, results_by_server: Dict[str, List[ErrorAnalysis]], timestamp: datetime):
        """Sends a comprehensive HTML report via SMTP."""
        if not self.config.to_addresses:
            logger.warning("No recipient addresses configured. Skipping email report.")
            return

        subject = self.config.subject_template.format(company_name="El Sewedy Electric")
        html_body = self._format_html_report(results_by_server, timestamp)

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.config.from_address
        msg['To'] = ", ".join(self.config.to_addresses)
        msg.attach(MIMEText(html_body, 'html'))

        try:
            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                if self.config.use_tls:
                    server.starttls()
                if self.config.username and self.config.password:
                    server.login(self.config.username, self.config.password)
                
                server.sendmail(self.config.from_address, self.config.to_addresses, msg.as_string())
                logger.info(f"Email report sent successfully to {', '.join(self.config.to_addresses)}")

        except Exception as e:
            logger.error(f"Failed to send email: {e}", exc_info=True)
            raise
EOF

# --- Create src/services/file_monitor.py ---
echo "Creating src/services/file_monitor.py..."
cat << 'EOF' > src/services/file_monitor.py
import os
import json
import logging
from pathlib import Path
from typing import Dict, List
import aiofiles

from src.config import AppConfig

logger = logging.getLogger(__name__)

# The path where we'll store the last read position for each log file
STATE_FILE_PATH = Path('/var/tmp/oracle_monitor_state.json')

class LogFileMonitor:
    """Monitors Oracle log files for new error entries."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, int]:
        """Loads the last read position for each file from the state file."""
        if not STATE_FILE_PATH.exists():
            return {}
        try:
            with open(STATE_FILE_PATH, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Could not load state file, starting from scratch: {e}")
            return {}

    def _save_state(self):
        """Saves the current read positions to the state file."""
        try:
            with open(STATE_FILE_PATH, 'w') as f:
                json.dump(self.state, f)
        except IOError as e:
            logger.error(f"Failed to save state file: {e}")

    async def read_new_errors(self, server_name: str) -> List[str]:
        """
        Reads new lines from a log file since the last run.
        For simplicity, this example looks for lines containing 'ORA-'.
        """
        log_filename = self.config.servers.get(server_name)
        if not log_filename:
            logger.error(f"No log file configured for server: {server_name}")
            return []

        base_dir = Path(self.config.monitoring.base_dir)
        
        possible_paths = list(base_dir.rglob(log_filename))
        if not possible_paths:
            logger.error(f"Log file '{log_filename}' not found for server '{server_name}' under '{base_dir}'")
            return []
        
        log_file_path = possible_paths[0]
        logger.info(f"Monitoring log file: {log_file_path}")

        last_position = self.state.get(server_name, 0)
        new_errors = []

        try:
            async with aiofiles.open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                await f.seek(last_position)
                
                async for line in f:
                    if "ORA-" in line:
                        new_errors.append(line.strip())
                
                self.state[server_name] = await f.tell()
                self._save_state()

        except FileNotFoundError:
            logger.error(f"Log file not found at path: {log_file_path}")
        except Exception as e:
            logger.error(f"Error reading log file for {server_name}: {e}", exc_info=True)

        return new_errors
EOF

# --- Create src/services/health_checker.py ---
echo "Creating src/services/health_checker.py..."
cat << 'EOF' > src/services/health_checker.py
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
EOF

echo "✅ All source files have been created/updated successfully!"
echo "➡️ Next steps:"
echo "   1. Make sure config/config.yaml is configured correctly."
echo "   2. Ensure required environment variables (like GEMINI_API_KEY) are set."
echo "   3. Run the application: python3 -m src.oracle_monitor"

