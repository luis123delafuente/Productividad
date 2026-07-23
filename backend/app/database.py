from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings

settings = get_settings()

connect_args = {"check_same_thread": False}
engine = create_engine(settings.database_url, connect_args=connect_args)


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def _add_missing_columns() -> None:
    """create_all no altera tablas ya existentes: parches puntuales de columnas
    nuevas para bases de datos SQLite creadas antes de anadirlas al modelo."""
    with engine.begin() as connection:
        existing = {row[1] for row in connection.execute(text("PRAGMA table_info(task)"))}
        if "description" not in existing:
            connection.execute(text("ALTER TABLE task ADD COLUMN description VARCHAR"))


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    _add_missing_columns()


def get_session():
    with Session(engine) as session:
        yield session
