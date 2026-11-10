import os

# Antes de importar la app: TestClient manda "Host: testserver", que la
# TrustedHostMiddleware rechazaria con los hosts de produccion.
os.environ["ALLOWED_HOSTS"] = '["localhost", "127.0.0.1", "testserver"]'

import pytest  # noqa: E402
from sqlmodel import Session, SQLModel, create_engine  # noqa: E402
from sqlmodel.pool import StaticPool  # noqa: E402

from app.seed import run_seed  # noqa: E402


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        run_seed(session)
        yield session
