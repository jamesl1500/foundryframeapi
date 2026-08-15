# Audit model
import enum
import uuid

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base, TimestampMixin, UUIDMixin
from api.models.lead import Lead


class AuditStatus(enum.StrEnum):
    """Lifecycle state of a site audit."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Audit(UUIDMixin, TimestampMixin, Base):
    """A single site audit run for a lead's website."""

    __tablename__ = "audits"

    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    status: Mapped[AuditStatus] = mapped_column(
        String(20), default=AuditStatus.PENDING, nullable=False
    )

    overall_score: Mapped[float | None] = mapped_column(Float)
    # Per-category scores, e.g. {"seo": 82, "performance": 60, ...}
    category_scores: Mapped[dict | None] = mapped_column(JSONB)
    # Raw findings/checks produced by the auditor service
    findings: Mapped[dict | None] = mapped_column(JSONB)

    # Claude-generated summary + recommended package(s)
    ai_summary: Mapped[str | None] = mapped_column(Text)
    ai_recommendations: Mapped[dict | None] = mapped_column(JSONB)

    # Google Lighthouse (via PageSpeed Insights): performance/accessibility/seo/best_practices
    lighthouse_scores: Mapped[dict | None] = mapped_column(JSONB)
    # Core Web Vitals: LCP, CLS, TBT, FCP, Speed Index, TTI
    lighthouse_metrics: Mapped[dict | None] = mapped_column(JSONB)
    lighthouse_opportunities: Mapped[list | None] = mapped_column(JSONB)
    lighthouse_error: Mapped[str | None] = mapped_column(Text)

    error_message: Mapped[str | None] = mapped_column(Text)

    lead: Mapped[Lead] = relationship(back_populates="audits")
