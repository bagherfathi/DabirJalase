"""Module entrypoint to run the FastAPI scaffold with uvicorn.

Example:
    PY_SERVICES_PORT=8080 python -m python_services
"""

from __future__ import annotations

import sys
from pathlib import Path
import site

# Ensure installed packages (from site-packages) are found before local stubs
# This prevents the local fastapi/pydantic directories from being imported
project_root = Path(__file__).parent.parent
site_packages = [p for p in site.getsitepackages() if p]
# Move site-packages to the front of sys.path
for sp in reversed(site_packages):
    if sp in sys.path:
        sys.path.remove(sp)
    sys.path.insert(0, sp)

import uvicorn
from uvicorn.config import Config

from python_services.api.server import app
from python_services.config import ServiceSettings, configure_logging


def main() -> None:
    settings = ServiceSettings.from_env()
    configure_logging(settings.log_level)
    config = Config(
        app=app,
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level,
    )
    server = uvicorn.Server(config)
    server.run()


if __name__ == "__main__":
    main()

