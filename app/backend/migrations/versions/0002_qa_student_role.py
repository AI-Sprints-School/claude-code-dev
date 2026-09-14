"""Роль SQL-консоли qa_student: GRANT SELECT на две учебные таблицы (2.7).

Пароль роли берётся из QA_STUDENT_PASSWORD — в репозитории его нет.

Revision ID: 0002
Revises: 0001
"""
from alembic import op

from wallet.config import settings
from wallet.grants import apply_readonly_grants

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    apply_readonly_grants(
        op.get_bind(), settings.qa_student_role, settings.qa_student_password
    )


def downgrade() -> None:
    role = settings.qa_student_role
    op.execute(f'REVOKE ALL ON ALL TABLES IN SCHEMA public FROM "{role}"')
    op.execute(f'REVOKE ALL ON SCHEMA public FROM "{role}"')
