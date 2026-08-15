# Lead routes: internal/admin lead listing
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.db import get_db
from api.models.lead import Lead
from api.schemas.lead import LeadRead

router = APIRouter(prefix="/leads", tags=["leads"])


@router.get("", response_model=list[LeadRead])
async def list_leads(db: AsyncSession = Depends(get_db)) -> list[Lead]:
    result = await db.execute(select(Lead).order_by(Lead.created_at.desc()))
    return list(result.scalars().all())
