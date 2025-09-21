#!/usr/bin/env python3
"""
Oracle Alert Log Monitor - Enhanced Production Version
Monitors Oracle database alert logs across multiple servers with AI analysis.
"""

import asyncio
import logging
import time
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import ConfigManager, get_config
from src.models import ErrorAnalysis, MonitoringMetrics, HealthStatus
from src.services.ai_analyzer import GeminiAnalyzer
from src.services.email_service import EmailService
from src.services.file_monitor import LogFileMonitor
from src.services.health_checker import HealthChecker
from src.utils.metrics import MetricsCollector
from src.utils.security import CircuitBreaker, RateLimiter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger(__name__)

class OracleMonitor:
    """Main Oracle Alert Log monitoring application."""
    
    def __init__(self):
        self.config = get_config()
        self.metrics_collector = MetricsCollector()
        self.health_checker = HealthChecker(self.config)
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=self.config.ai.circuit_breaker_threshold,
            reset_timeout=self.config.ai.circuit_breaker_reset_timeout
        )
        self.rate_limiter = RateLimiter(
            rate=self.config.ai.rate_limit_requests,
            per=self.config.ai.rate_limit_period
        )
        self.run_history_dir = Path('run_history')

    def _save_run_history(self, results: Dict[str, List[ErrorAnalysis]]):
        """Saves the monitoring results to a timestamped file and keeps the last 20 runs."""
        try:
            self.run_history_dir.mkdir(exist_ok=True)
            
            # --- CHANGED to use local server time instead of UTC ---
            timestamp_str = datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
            file_path = self.run_history_dir / f"run_{timestamp_str}.json"
            
            logger.info(f"Saving results to {file_path} for the web UI.")
            
            serializable_results = {server: [a.to_dict() for a in analyses] for server, analyses in results.items()}

            with open(file_path, 'w') as f:
                json.dump(serializable_results, f, indent=4)
            
            # Clean up old runs, keeping only the 20 most recent
            all_runs = sorted(self.run_history_dir.glob('run_*.json'), reverse=True)
            if len(all_runs) > 20:
                for old_run in all_runs[20:]:
                    logger.info(f"Deleting old run file: {old_run}")
                    os.remove(old_run)

        except Exception as e:
            logger.error(f"Failed to save run history: {e}")
    
    async def run_monitoring_cycle(self) -> MonitoringMetrics:
        """Execute a complete monitoring cycle."""
        start_time = time.time()
        logger.info("Starting Oracle Alert Log monitoring cycle")
        
        health_status = await self.health_checker.check_system_health()
        if health_status['overall_status'] == HealthStatus.UNHEALTHY:
            logger.error("System health check failed, aborting monitoring cycle")
            return self._create_failed_metrics(start_time, "System unhealthy")
        
        all_results: Dict[str, List[ErrorAnalysis]] = {}
        
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.ai.timeout),
            connector=aiohttp.TCPConnector(limit=10, limit_per_host=5)
        ) as session:
            
	   if self.config.ai.engine == "gemini":
    ai_analyzer = GeminiAnalyzer(session=session, config=self.config, circuit_breaker=self.circuit_breaker, rate_limiter=self.rate_limiter)
else:
    ai_analyzer = LMStudioAnalyzer(session=session, model=self.config.ai.model)

	    file_monitor = LogFileMonitor(self.config)
            
            for server_name in self.config.servers.keys():
                logger.info(f"Processing server: {server_name}")
                errors = await file_monitor.read_new_errors(server_name)
                if not errors:
                    all_results[server_name] = []
                    continue
                
                logger.info(f"Found {len(errors)} new errors for {server_name}")
                server_results = []
                for error_line in errors:
                    try:
                        analysis = await ai_analyzer.analyze_error(error_line=error_line, server_name=server_name)
                        server_results.append(analysis)
                    except Exception as e:
                        logger.error(f"Failed to analyze error for {server_name}: {e}")
                        failed_analysis = ErrorAnalysis(error_line=error_line, explanation=f"Analysis failed: {str(e)}", recommended_action="Manual review required", criticality="Medium", server=server_name, timestamp=datetime.utcnow(), analysis_success=False)
                        server_results.append(failed_analysis)
                all_results[server_name] = server_results
        
        self._save_run_history(all_results)

        total_errors = sum(len(res) for res in all_results.values())
        if total_errors > 0:
            summary_data = {
                'total_errors': total_errors,
                'servers_with_errors': len([s for s, res in all_results.items() if res]),
                'total_servers': len(self.config.servers),
                'servers': []
            }
            for server, analyses in all_results.items():
                if analyses:
                    summary_data['servers'].append({
                        'name': server,
                        'error_count': len(analyses),
                        'criticality': {
                            'Critical': sum(1 for a in analyses if a.criticality == 'Critical'),
                            'High': sum(1 for a in analyses if a.criticality == 'High'),
                            'Medium': sum(1 for a in analyses if a.criticality == 'Medium'),
                            'Low': sum(1 for a in analyses if a.criticality == 'Low'),
                        }
                    })
            
            try:
                email_service = EmailService(self.config)
                await email_service.send_comprehensive_report(
                    summary_data=summary_data,
                    timestamp=datetime.utcnow()
                )
                logger.info("Email summary report sent successfully")
            except Exception as e:
                logger.error(f"Failed to send email report: {e}")
        else:
            logger.info("No new errors found across all servers")
        
        processing_time = time.time() - start_time
        metrics = MonitoringMetrics(timestamp=datetime.utcnow(), total_servers=len(self.config.servers), servers_with_errors=len([r for r in all_results.values() if r]), total_errors=total_errors, processing_time=processing_time, api_calls_made=0, api_failures=0, success=True)
        self.metrics_collector.record_run(metrics)
        logger.info(f"Monitoring cycle completed in {processing_time:.2f}s")
        return metrics

    def _create_failed_metrics(self, start_time: float, reason: str) -> MonitoringMetrics:
        return MonitoringMetrics(timestamp=datetime.utcnow(), total_servers=len(self.config.servers), servers_with_errors=0, total_errors=0, processing_time=time.time() - start_time, api_calls_made=0, api_failures=0, success=False, failure_reason=reason)

async def main():
    logger.info("Oracle Alert Log Monitor starting up...")
    try:
        monitor = OracleMonitor()
        metrics = await monitor.run_monitoring_cycle()
        if metrics.success:
            logger.info(f"Monitoring completed successfully: {metrics.total_errors} errors found on {metrics.servers_with_errors}/{metrics.total_servers} servers")
        else:
            logger.error(f"Monitoring failed: {metrics.failure_reason}")
    except KeyboardInterrupt:
        logger.info("Monitoring interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error in main: {e}", exc_info=True)
        raise

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

