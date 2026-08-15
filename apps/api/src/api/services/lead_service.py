# Lead persistence helpers
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.lead import Lead
from api.schemas.audit import AuditRequest


async def get_or_create_lead(session: AsyncSession, payload: AuditRequest) -> Lead:
    """Find an existing lead by email, otherwise create one from the audit request."""
    result = await session.execute(select(Lead).where(Lead.email == payload.email))
    lead = result.scalar_one_or_none()

    if lead is not None:
        # Keep the lead's contact info fresh with whatever was just submitted.
        lead.name = payload.name or lead.name
        lead.company = payload.company or lead.company
        lead.phone = payload.phone or lead.phone
        lead.website_url = str(payload.url)
        return lead

    lead = Lead(
        email=payload.email,
        name=payload.name,
        company=payload.company,
        phone=payload.phone,
        website_url=str(payload.url),
    )
    session.add(lead)
    await session.flush()
    return lead
