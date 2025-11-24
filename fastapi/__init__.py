"""Lightweight FastAPI shim for offline testing in the scaffold.

The real dependency is declared in requirements.txt; this stub keeps unit tests
runnable in constrained environments without reaching external package indexes.
Only the small surface area used by the scaffold is implemented.
"""
from __future__ import annotations

from typing import Callable, Dict, List


class FastAPI:
    def __init__(self, title: str = ""):
        self.title = title
        self.routes: List[Dict[str, str]] = []

    def get(self, path: str):
        def decorator(func: Callable):
            self.routes.append({"method": "GET", "path": path, "handler": func.__name__})
            return func

        return decorator

    def post(self, path: str):
        def decorator(func: Callable):
            self.routes.append({"method": "POST", "path": path, "handler": func.__name__})
            return func

        return decorator


__all__ = ["FastAPI"]
