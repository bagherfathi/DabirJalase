"""Module entrypoint to run the FastAPI scaffold with uvicorn.

Example:
    PY_SERVICES_PORT=8080 python -m python_services
"""

from __future__ import annotations

import uvicorn

from python_services.api.server import app
from python_services.config import ServiceSettings, configure_logging


def main() -> None:
    settings = ServiceSettings.from_env()
    configure_logging(settings.log_level)
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level,
    )


if __name__ == "__main__":
    main()

