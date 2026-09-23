"""Typed semantic-critic result handling."""

from enum import StrEnum

from pydantic import BaseModel


class SemanticStatus(StrEnum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class SemanticVerdict(BaseModel):
    status: SemanticStatus
    critique: str = ""
