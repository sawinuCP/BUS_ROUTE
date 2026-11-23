"""Expose the integration-suite fixtures to the routing tests.

pytest registers fixture functions found in a conftest module's namespace,
including names imported here, so tests in this directory get exactly the
same infrastructure as `tests/integration`: the dedicated test database
created and migrated once per session (I-18/I-21), per-test canonical-table
cleanup, and the rolled-back `db_conn` fixture — without duplicating them.

Imports are explicit because `from ... import *` would silently skip the
underscore-prefixed helpers (`_migrate_test_database` is autouse).
"""

from tests.integration.conftest import (  # noqa: F401
    _CLEANUP_ORDER,
    _migrate_test_database,
    _seed_route,
    clean_canonical_tables,
    db_conn,
)
