"""
Energy Orchestrator Simulation Framework

Production-grade simulation engine for UK residential energy microgrids.
Supports 10-200 homes with solar PV, battery storage, EV charging, and 
optimization via integer linear programming (OR-Tools).
"""

__version__ = "1.0.0"
__author__ = "Richard T. Martin"
__license__ = "MIT"

import logging.config
import yaml
from pathlib import Path

# Configure structured logging
LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        },
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "standard",
            "stream": "ext://sys.stdout"
        },
        "file": {
            "class": "logging.FileHandler",
            "level": "DEBUG",
            "formatter": "detailed",
            "filename": "energy_orchestrator.log"
        }
    },
    "root": {
        "level": "DEBUG",
        "handlers": ["console", "file"]
    }
}

logging.config.dictConfig(LOG_CONFIG)
logger = logging.getLogger(__name__)

logger.info(f"Energy Orchestrator v{__version__} initialized")
