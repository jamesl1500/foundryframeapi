# Audit routes: submit a site for audit, fetch results
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.ai.claude_service import generate_recommendations
from api.core.db import get_db
from api.models.audit import Audit, AuditStatus
from api.schemas.audit import AuditRead, AuditRequest
from api.services.audit_service import SiteAuditError, run_audit
from api.services.lead_service import get_or_create_lead

router = APIRouter(prefix="/audits", tags=["audits"])


@router.post("", response_model=AuditRead, status_code=status.HTTP_201_CREATED)
async def create_audit(payload: AuditRequest, db: AsyncSession = Depends(get_db)) -> Audit:
    """Run a full site audit for a lead and persist the lead + audit results."""
    lead = await get_or_create_lead(db, payload)

    audit = Audit(lead_id=lead.id, url=str(payload.url), status=AuditStatus.RUNNING)
    db.add(audit)
    await db.flush()

    try:
        report = await run_audit(str(payload.url))
        ai_result = await generate_recommendations(report, str(payload.url))

        audit.status = AuditStatus.COMPLETED
        audit.overall_score = report.overall_score
        audit.category_scores = report.category_scores
        audit.findings = report.to_dict()
        audit.lighthouse_scores = report.lighthouse_scores
        audit.lighthouse_metrics = report.lighthouse_metrics
        audit.lighthouse_opportunities = report.lighthouse_opportunities
        audit.lighthouse_error = report.lighthouse_error
        audit.ai_summary = ai_result.get("summary")
        audit.ai_recommendations = ai_result
    except SiteAuditError as exc:
        audit.status = AuditStatus.FAILED
        audit.error_message = str(exc)

    await db.commit()
    await db.refresh(audit)
    return audit


@router.get("/{audit_id}", response_model=AuditRead)
async def get_audit(audit_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Audit:
    result = await db.execute(select(Audit).where(Audit.id == audit_id))
    audit = result.scalar_one_or_none()
    if audit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found")
    return audit
