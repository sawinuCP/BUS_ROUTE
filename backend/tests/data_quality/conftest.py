"""Expose the integration-suite fixtures to the data-quality tests.

Same mechanism as `tests/routing/conftest.py`: pytest collects fixture
functions imported into a conftest module, so tests here share the
dedicated test database (I-18/I-21), the session-scoped Alembic migration
bootstrap and the per-test canonical-table cleanup with `tests/integration`.
"""

from tests.integration.conftest import (  # noqa: F401
    _CLEANUP_ORDER,
    _migrate_test_database,
    _seed_route,
    clean_canonical_tables,
    db_conn,
)
