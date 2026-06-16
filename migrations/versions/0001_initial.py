"""Начальная схема: таблица bookings.

Revision ID: 0001
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

service_type = postgresql.ENUM("consultation", "haircut", "massage", name="service_type")
booking_status = postgresql.ENUM("pending", "confirmed", "failed", name="booking_status")


def upgrade() -> None:
    """Создаёт таблицу bookings и enum-типы."""
    op.create_table(
        "bookings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("service_type", service_type, nullable=False),
        sa.Column("status", booking_status, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Удаляет таблицу bookings и enum-типы."""
    op.drop_table("bookings")
    booking_status.drop(op.get_bind())
    service_type.drop(op.get_bind())
