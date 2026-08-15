# Lead model
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base, TimestampMixin, UUIDMixin


class Lead(UUIDMixin, TimestampMixin, Base):
    """A potential customer who requested a site audit."""

    __tablename__ = "leads"

    email: Mapped[str] = mapped_column(String(320), index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    company: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    website_url: Mapped[str] = mapped_column(String(2048), nullable=False)

    # Where the lead came from, e.g. "audit_form"
    source: Mapped[str] = mapped_column(String(100), default="audit_form")

    audits: Mapped[list["Audit"]] = relationship(  # noqa: F821
        back_populates="lead", cascade="all, delete-orphan"
    )
