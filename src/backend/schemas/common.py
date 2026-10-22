"""Shared building blocks for every API schema.

Every schema in `backend.schemas` inherits from `BaseSchema`. Keeping the
common configuration in one place means a rule such as "trim the whitespace a
candidate typed" is applied everywhere instead of being repeated (and
forgotten) in each file.
"""

from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field


class BaseSchema(BaseModel):
    """Base class for all request and response schemas.

    Two settings do the heavy lifting:

    * `from_attributes=True` lets FastAPI build a response straight from an
      ORM object (`Job`) without hand-copying every field. The attribute names
      on the model and the field names on the schema have to match.
    * `str_strip_whitespace=True` trims leading and trailing spaces *before*
      validation. A candidate who types "  Jane Doe  " is stored as
      "Jane Doe", and a title made only of spaces fails the minimum length
      check instead of being saved as invisible whitespace.
    """

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class TimestampSchema(BaseSchema):
    """Columns every table with audit information has."""

    created_at: datetime
    updated_at: datetime


class PaginationParams(BaseSchema):
    """Query parameters shared by every paginated endpoint.

    `ge` / `le` are Pydantic's "greater or equal" / "less or equal" bounds.
    They reject nonsense values such as `page=0` or `page_size=5000` before
    they ever reach the database.
    """

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


# A TypeVar is the placeholder that turns `PaginatedResponse` into a family of
# schemas: `PaginatedResponse[AdminApplicationItem]`,
# `PaginatedResponse[JobListItem]`, ...
T = TypeVar("T")


class PaginatedResponse(BaseSchema, Generic[T]):
    """A page of results plus the information needed to request the next one."""

    items: list[T]
    page: int
    page_size: int
    total: int
