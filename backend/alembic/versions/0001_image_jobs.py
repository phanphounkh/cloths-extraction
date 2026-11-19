"""Create image jobs table."""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "image_jobs",
        sa.Column(
            "id",
            sa.String(36),
            primary_key=True,
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
        ),
        sa.Column(
            "garment",
            sa.String(40),
            nullable=False,
        ),
        sa.Column(
            "input_path",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "output_path",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "error",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
    )


def downgrade():
    op.drop_table("image_jobs")