from alembic import op
import sqlalchemy as sa

revision = "0001_init_tables"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'departments',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(120), nullable=False, unique=True)
    )

    op.create_table(
        'jobs',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('title', sa.String(120), nullable=False, unique=True)
    )

    op.create_table(
        'employees',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(80), nullable=False),
        sa.Column('department_id', sa.Integer, sa.ForeignKey('departments.id'), nullable=True),
        sa.Column('job_id', sa.Integer, sa.ForeignKey('jobs.id'), nullable=True),
        sa.Column('hire_date', sa.Date(), nullable=True),
    )


def downgrade():
    op.drop_table('employees')
    op.drop_table('jobs')
    op.drop_table('departments')
