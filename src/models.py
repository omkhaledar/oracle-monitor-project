"""
Data models for Oracle Alert Log Monitor.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
import json


class HealthStatus(Enum):
    """System health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"  
    UNHEALTHY = "unhealthy"


class CriticalityLevel(Enum):
    """Error criticality levels."""
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    INFORMATIONAL = "Informational"


@dataclass
class ErrorAnalysis:
    """Represents the AI analysis of an Oracle error."""
    error_line: str
    explanation: str
    recommended_action: str
    criticality: str
    reference: str
    server: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    analysis_success: bool = True
    processing_time: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'error_line': self.error_line,
            'explanation': self.explanation,
            'recommended_action': self.recommended_action,
            'criticality': self.criticality,
            'reference': self.reference,
            'server': self.server,
            'timestamp': self.timestamp.isoformat(),
            'analysis_success': self.analysis_success,
            'processing_time': self.processing_time
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ErrorAnalysis':
        """Create instance from dictionary."""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass  
class MonitoringMetrics:
    """Metrics for a monitoring cycle."""
    timestamp: datetime
    total_servers: int
    servers_with_errors: int
    total_errors: int
    processing_time: float
    api_calls_made: int
    api_failures: int
    success: bool = True
    failure_reason: Optional[str] = None
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps({
            'timestamp': self.timestamp.isoformat(),
            'total_servers': self.total_servers,
            'servers_with_errors': self.servers_with_errors,
            'total_errors': self.total_errors,
            'processing_time': self.processing_time,
            'api_calls_made': self.api_calls_made,
            'api_failures': self.api_failures,
            'success': self.success,
            'failure_reason': self.failure_reason
        })


@dataclass
class HealthCheckResult:
    """Result of a health check operation."""
    component: str
    status: HealthStatus
    message: str
    response_time: Optional[float] = None
    details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'component': self.component,
            'status': self.status.value,
            'message': self.message,
            'response_time': self.response_time,
            'details': self.details or {}
        }


@dataclass
class ServerStatus:
    """Status of an individual server."""
    name: str
    log_file_path: str
    accessible: bool
    last_check: datetime
    error_count: int = 0
    last_error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'log_file_path': self.log_file_path,
            'accessible': self.accessible,
            'last_check': self.last_check.isoformat(),
            'error_count': self.error_count,
            'last_error': self.last_error
        }

