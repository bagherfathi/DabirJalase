"""Lightweight FastAPI shim for offline testing in the scaffold.

The real dependency is declared in requirements.txt; this stub keeps unit tests
runnable in constrained environments without reaching external package indexes.
Only the small surface area used by the scaffold is implemented.
"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional


class HTTPException(Exception):
    def __init__(self, status_code: int, detail: str | None = None):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail or ""


class Request:
    def __init__(self, headers: Optional[Dict[str, str]] = None, url: Optional[str] = None):
        self.headers = {k.lower(): v for k, v in (headers or {}).items()}
        self.url = SimpleNamespace(path=url or "")


class Response:
    def __init__(self, content: Any, status_code: int = 200, headers: Optional[Dict[str, str]] = None):
        self.content = content
        self.status_code = status_code
        self.headers: Dict[str, str] = headers or {}

    def json(self) -> Any:
        return self.content


class FastAPI:
    def __init__(self, title: str = ""):
        self.title = title
        self.routes: List[Dict[str, Any]] = []
        self.middlewares: List[Callable] = []

    def get(self, path: str):
        def decorator(func: Callable):
            self.routes.append({"method": "GET", "path": path, "handler": func})
            return func

        return decorator

    def post(self, path: str):
        def decorator(func: Callable):
            self.routes.append({"method": "POST", "path": path, "handler": func})
            return func

        return decorator

    def middleware(self, _type: str):
        def decorator(func: Callable):
            self.middlewares.append(func)
            return func

        return decorator

    def _find_route(self, method: str, path: str) -> Dict[str, Any]:
        for route in self.routes:
            if route["method"] == method and route["path"] == path:
                return route
        raise ValueError(f"Route not found: {method} {path}")

    async def _dispatch(self, method: str, path: str, headers: Dict[str, str], body: Any = None) -> Response:
        route = self._find_route(method, path)
        request = Request(headers=headers, url=path)

        async def endpoint(_: Request) -> Response:
            handler = route["handler"]
            result = handler(body) if body is not None else handler()
            return result if isinstance(result, Response) else Response(result)

        call_next = endpoint
        for middleware in reversed(self.middlewares):
            previous = call_next

            async def wrapper(req: Request, middleware=middleware, nxt=previous):
                return await middleware(req, nxt)

            call_next = wrapper

        return await call_next(request)


class TestClient:
    def __init__(self, app: FastAPI):
        self.app = app

    def request(self, method: str, path: str, headers: Optional[Dict[str, str]] = None, json: Any = None) -> Response:
        try:
            return asyncio.run(self.app._dispatch(method, path, headers or {}, json))
        except HTTPException as exc:  # pragma: no cover - mirrors FastAPI behavior
            return Response({"detail": exc.detail}, status_code=exc.status_code)

    def get(self, path: str, headers: Optional[Dict[str, str]] = None) -> Response:
        return self.request("GET", path, headers=headers)

    def post(self, path: str, headers: Optional[Dict[str, str]] = None, json: Any = None) -> Response:
        return self.request("POST", path, headers=headers, json=json)


status = SimpleNamespace(HTTP_401_UNAUTHORIZED=401)


__all__ = ["FastAPI", "HTTPException", "Request", "Response", "TestClient", "status"]
