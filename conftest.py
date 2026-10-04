"""
Pin the test suite to a scratch database.

Every test fixture that clears tables was running against algorise_prod.db
and deleting the live client's record. conftest sets VEDIC_TEST_DB before any
test module imports the engine, so sync_session() cannot reach production.
"""
from pathlib import Path
import os
import tempfile

ROOT = Path(__file__).resolve().parent.parent
_SCRATCH = Path(tempfile.gettempdir()) / "algorise_test.db"

if _SCRATCH.exists():
    _SCRATCH.unlink()

os.environ["VEDIC_TEST_DB"] = f"sqlite:///{_SCRATCH}"

# Import after the environment is set: engine.database resolves the URL on
# first use, but importing early keeps the ordering explicit.
import sys  # noqa: E402

sys.path.insert(0, str(ROOT))

# Create the schema in the scratch database once, so fixtures that query
# tables do not each have to build them.
from engine.models_sqlalchemy import Base  # noqa: E402

import engine.models_sqlalchemy as _models  # noqa: E402,F401
from engine.database import sync_engine  # noqa: E402

Base.metadata.create_all(bind=sync_engine())