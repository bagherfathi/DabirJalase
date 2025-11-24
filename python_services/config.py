"""Configuration helpers for running the service scaffold.

The settings default to values that work in local development but can be
overridden via environment variables to mirror deployment behavior while the
product is built out.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class ServiceSettings:
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    log_level: str = "info"

    @classmethod
    def from_env(cls) -> "ServiceSettings":
        """Load settings from environment variables with safe defaults."""

        def as_bool(value: str, default: bool) -> bool:
            truthy = {"1", "true", "t", "yes", "y"}
            falsy = {"0", "false", "f", "no", "n"}
            if value.lower() in truthy:
                return True
            if value.lower() in falsy:
                return False
            return default

        return cls(
            host=os.getenv("PY_SERVICES_HOST", cls.host),
            port=int(os.getenv("PY_SERVICES_PORT", cls.port)),
            reload=as_bool(os.getenv("PY_SERVICES_RELOAD", str(cls.reload)), cls.reload),
            log_level=os.getenv("PY_SERVICES_LOG_LEVEL", cls.log_level),
        )

