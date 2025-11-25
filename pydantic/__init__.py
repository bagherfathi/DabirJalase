"""Minimal Pydantic shim for offline unit tests.

Provides a BaseModel with basic attribute handling to keep the scaffold runnable
without external downloads. Replace with the real dependency in production.
"""
from __future__ import annotations


class BaseModel:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def model_dump(self):
        return self.__dict__


__all__ = ["BaseModel"]
