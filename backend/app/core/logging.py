import logging
import os
import sys
from typing import Optional

try:
    import structlog
except Exception:  # pragma: no cover
    structlog = None  # type: ignore


def _bool_env(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "y", "on")


def configure_logging(service_name: str = "ai-health-app") -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    json_logs = _bool_env("LOG_JSON", default=False)  # Keep normal logs locally, JSON in prod

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    formatter: logging.Formatter

    if json_logs and structlog is not None:
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.add_log_level,
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        formatter = logging.Formatter("%(message)s")
    else:
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s - %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )

    handler.setFormatter(formatter)
    root.addHandler(handler)

    # Reduce chatty loggers
    logging.getLogger("uvicorn.error").setLevel(level)
    logging.getLogger("uvicorn.access").setLevel(level)
    logging.getLogger("sqlalchemy.engine").setLevel(os.getenv("SQL_LOG_LEVEL", "WARNING").upper())


def get_logger(name: Optional[str] = None):
    if structlog is not None:
        return structlog.get_logger(name or "app")
    return logging.getLogger(name or "app")

