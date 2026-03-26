"""Report generation and export API endpoints."""
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.schemas.schemas import ReportOut
from backend.app.services.report_service import (
    generate_summary_report, generate_batch_report,
    export_report_csv, export_report_json,
)

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/summary", response_model=ReportOut)
async def summary_report(
    species: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Overall platform summary report with species distribution, hourly activity, camera counts."""
    report = await generate_summary_report(db, species_filter=species)
    return report


@router.get("/batch/{job_id}")
async def batch_report(job_id: int, db: AsyncSession = Depends(get_db)):
    """Report for a specific batch processing job."""
    report = await generate_batch_report(db, job_id)
    if not report:
        raise HTTPException(status_code=404, detail="Job not found")
    return report


@router.get("/export")
async def export_report(
    format: str = Query("csv", pattern="^(csv|json)$"),
    species: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Export the summary report as CSV or JSON file download."""
    report = await generate_summary_report(db, species_filter=species)

    if format == "csv":
        content = export_report_csv(report)
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=wildlife_report.csv"},
        )
    else:
        content = export_report_json(report)
        return Response(
            content=content,
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=wildlife_report.json"},
        )
