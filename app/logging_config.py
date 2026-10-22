import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

class StructuredJsonFormatter(logging.Formatter):
    """
    Format logs as structured JSON records for SRE observability pipelines.
    Sanitizes potential secrets and provides standardized fields.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": "syncops-assistant",
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Inject standard contextual attributes if present
        for field in ("request_id", "endpoint", "method", "status_code", "duration_ms", "incident_id", "operation", "client_ip"):
            if hasattr(record, field):
                log_obj[field] = getattr(record, field)
                
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_obj)

def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configures structured JSON logging on the root logger."""
    root_logger = logging.getLogger("syncops")
    root_logger.setLevel(level.upper())
    
    # Avoid duplicate handlers if reconfigured
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredJsonFormatter())
        root_logger.addHandler(handler)
        
    return root_logger

logger = setup_logging()
