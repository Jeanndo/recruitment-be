"""Admin overview endpoint.

The router is protected as a whole, just like the other admin routers, so a
new route cannot accidentally expose application counts without a session.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.api.dependencies import require_staff
from backend.database import get_db
from backend.schemas.dashboard import DashboardResponse
from backend.services import dashboard_service

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["Admin - Dashboard"],
    dependencies=[Depends(require_staff)],
)


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    summary="Get the admin overview",
    description=(
        "Returns job totals, application totals and a per-job breakdown by "
        "review status. Every number is calculated from the database."
    ),
)
def get_dashboard(db: Session = Depends(get_db)) -> DashboardResponse:
    """Return the overview shown on the admin home page."""
    return dashboard_service.get_dashboard(db)
