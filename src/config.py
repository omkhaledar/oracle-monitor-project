"""
Configuration management for Oracle Alert Log Monitor.
Supports environment variables, YAML files, and secure defaults.
"""

import os
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml

logger = logging.getLogger(__name__)


@dataclass
class AIConfig:
    """AI service configuration."""
    api_key: str
    model: str = "gemini-1.5-flash"
    timeout: int = 90
    max_retries: int = 3
    rate_limit_requests: int = 10
    rate_limit_period: int = 60  # seconds
    circuit_breaker_threshold: int = 5
    circuit_breaker_reset_timeout: int = 300  # seconds
    base_url: str = "https://generativelanguage.googleapis.com/v1beta"


@dataclass
class EmailConfig:
    """Email service configuration."""
    smtp_server: str
    smtp_port: int = 587
    username: Optional[str] = None
    password: Optional[str] = None
    from_address: str = ""
    to_addresses: List[str] = field(default_factory=list)
    subject_template: str = "Oracle Alert Log - AI Dashboard ({company_name})"
    use_tls: bool = True


@dataclass
class MonitoringConfig:
    """Monitoring and logging configuration."""
    base_dir: str = "/u01"
    log_level: str = "INFO"
    log_file: str = "/var/log/oracle_monitor.log"
    metrics_file: str = "/var/log/oracle_monitor_metrics.jsonl"
    health_check_interval: int = 300  # seconds
    retention_days: int = 30


@dataclass
class SecurityConfig:
    """Security configuration."""
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    allowed_log_extensions: List[str] = field(default_factory=lambda: ['.log'])
    enable_path_validation: bool = True


@dataclass
class AppConfig:
    """Main application configuration."""
    company_name: str = "El Sewedy Electric"
    servers: Dict[str, str] = field(default_factory=dict)
    ai: AIConfig = field(default_factory=lambda: AIConfig(api_key=""))
    email: EmailConfig = field(default_factory=EmailConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)


class ConfigManager:
    """Manages configuration loading and validation."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._find_config_file()
        self._config: Optional[AppConfig] = None
    
    def _find_config_file(self) -> str:
        """Find configuration file in standard locations."""
        possible_paths = [
            os.getenv('ORACLE_MONITOR_CONFIG'),
            './config/config.yaml',
            '/etc/oracle-monitor/config.yaml',
            '~/.config/oracle-monitor/config.yaml'
        ]
        
        for path in possible_paths:
            if path and Path(path).expanduser().exists():
                return str(Path(path).expanduser())
        
        logger.warning("No configuration file found, using defaults")
        return ""
    
    def load_config(self) -> AppConfig:
        """Load configuration from file and environment."""
        if self._config is not None:
            return self._config
        
        # Start with default configuration
        config_data = self._get_default_config()
        
        # Load from YAML file if available
        if self.config_path and Path(self.config_path).exists():
            try:
                with open(self.config_path, 'r') as f:
                    file_config = yaml.safe_load(f)
                    config_data = self._merge_configs(config_data, file_config)
                logger.info(f"Loaded configuration from {self.config_path}")
            except Exception as e:
                logger.error(f"Failed to load config file {self.config_path}: {e}")
        
        # Override with environment variables
        config_data = self._apply_env_overrides(config_data)
        
        # Create and validate configuration
        self._config = self._create_config_object(config_data)
        self._validate_config(self._config)
        
        return self._config
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration values."""
        return {
            'company_name': 'El Sewedy Electric',
            'servers': {
                'EgyplastProd': 'EgyplastProd/db/alert_orcl19.log',
                'EgyTechProd': 'EgyTechProd/db/alert_PROD.log',
                'EPCProd': 'EPCProd/db/alert_PRODEBS.log',
                'HCMProd': 'HCMProd/db/alert_PRODEBS.log',
                'SDMProd': 'SDMProd/db/alert_PROD.log',
                'TransformersProd': 'TransformersProd/db/alert_CPROD.log',
                'UICProd': 'UICProd/db/alert_pcdb.log',
                'UMCProd': 'UMCProd/db/alert_PROD.log',
                'KSAProd_1': 'KSAProd_1/db/alert_PRODCDB1.log',
                'KSAProd_2': 'KSAProd_2/db/alert_PRODCDB2.log',
                'AlgeriaProd': 'AlgeriaProd/db/alert_cprod.log',
                'TZProd': 'TZProd/db/alert_PRODTZ.log',
                'RMEProd': 'RMEProd/db/alert_RMEDB.log'
            },
            'ai': {
                'api_key': '',
                'model': 'gemini-1.5-flash',
                'timeout': 90,
                'max_retries': 3,
                'rate_limit_requests': 10,
                'rate_limit_period': 60
            },
            'email': {
                'smtp_server': '10.0.12.152',
                'smtp_port': 587,
                'from_address': 'omr.khaled@elsewedy.com',
                'to_addresses': ['omr.khaled@elsewedy.com']
            },
            'monitoring': {
                'base_dir': '/u01',
                'log_level': 'INFO'
            }
        }
    
    def _apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides."""
        env_mappings = {
            'GEMINI_API_KEY': ('ai', 'api_key'),
            'SMTP_USER': ('email', 'username'),
            'SMTP_PASS': ('email', 'password'),
            'ORACLE_BASE_DIR': ('monitoring', 'base_dir'),
            'LOG_LEVEL': ('monitoring', 'log_level'),
            'COMPANY_NAME': ('company_name',)
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value:
                self._set_nested_value(config, config_path, value)
        
        return config
    
    def _set_nested_value(self, config: Dict[str, Any], path: tuple, value: str):
        """Set a nested configuration value."""
        current = config
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value
    
    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge configuration dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _create_config_object(self, config_data: Dict[str, Any]) -> AppConfig:
        """Create configuration object from dictionary."""
        ai_config = AIConfig(**config_data.get('ai', {}))
        email_config = EmailConfig(**config_data.get('email', {}))
        monitoring_config = MonitoringConfig(**config_data.get('monitoring', {}))
        security_config = SecurityConfig(**config_data.get('security', {}))
        
        return AppConfig(
            company_name=config_data.get('company_name', 'El Sewedy Electric'),
            servers=config_data.get('servers', {}),
            ai=ai_config,
            email=email_config,
            monitoring=monitoring_config,
            security=security_config
        )
    
    def _validate_config(self, config: AppConfig):
        """Validate configuration values."""
        if not config.ai.api_key:
            raise ValueError("AI API key is required")
        
        if not config.email.from_address:
            raise ValueError("Email from address is required")
        
        if not config.email.to_addresses:
            raise ValueError("Email to addresses are required")
        
        if not config.servers:
            raise ValueError("At least one server must be configured")
        
        logger.info("Configuration validation passed")


# Global configuration instance
_config_manager = ConfigManager()


def get_config() -> AppConfig:
    """Get the global configuration instance."""
    return _config_manager.load_config()


def reload_config():
    """Reload configuration from file."""
    global _config_manager
    _config_manager._config = None
    return _config_manager.load_config()

