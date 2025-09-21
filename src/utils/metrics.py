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
