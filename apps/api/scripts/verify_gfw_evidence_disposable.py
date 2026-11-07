"""Verify GFW event evidence binding on a disposable database.

Creates a uniquely named temporary database, migrates it to head, runs the
focused report/case evidence checks, then drops it. Never touches the shared
development database.
"""
import os
import subprocess
import sys
import uuid

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.config import settings


def main():
    name = "samudra_gfw_evidence_test_" + uuid.uuid4().hex[:12]
    url = make_url(settings.DATABASE_URL)
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    created = False
    try:
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{name}"'))
            created = True
        test_url = url.set(database=name).render_as_string(hide_password=False)
        env = os.environ.copy()
        env.update(DATABASE_URL=test_url, TEST_DATABASE_URL=test_url, PYTHONPATH="/app")
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], env=env, check=True)
        subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_report_gfw_evidence.py", "-q"],
            env=env,
            check=True,
        )
    finally:
        if created:
            with admin.connect() as connection:
                connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        admin.dispose()


if __name__ == "__main__":
    main()
