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
        if "order_today" not in existing:
            connection.execute(text("ALTER TABLE task ADD COLUMN order_today INTEGER"))
        if "order_kanban" not in existing:
            connection.execute(text("ALTER TABLE task ADD COLUMN order_kanban INTEGER"))
        if "due_time" not in existing:
            connection.execute(text("ALTER TABLE task ADD COLUMN due_time TIME"))
        if "planned_start" not in existing:
            connection.execute(text("ALTER TABLE task ADD COLUMN planned_start DATETIME"))
        if "planned_minutes" not in existing:
            connection.execute(text("ALTER TABLE task ADD COLUMN planned_minutes INTEGER"))

        existing_settings = {row[1] for row in connection.execute(text("PRAGMA table_info(appsettings)"))}
        if existing_settings and "last_daily_today_reset_run" not in existing_settings:
            connection.execute(text("ALTER TABLE appsettings ADD COLUMN last_daily_today_reset_run DATETIME"))

        existing_token = {row[1] for row in connection.execute(text("PRAGMA table_info(googletoken)"))}
        if existing_token and "needs_reauth" not in existing_token:
            connection.execute(text("ALTER TABLE googletoken ADD COLUMN needs_reauth BOOLEAN NOT NULL DEFAULT 0"))

        existing_category = {row[1] for row in connection.execute(text("PRAGMA table_info(category)"))}
        if existing_category and "is_archived" not in existing_category:
            connection.execute(text("ALTER TABLE category ADD COLUMN is_archived BOOLEAN NOT NULL DEFAULT 0"))
        if existing_category and "archived_at" not in existing_category:
            connection.execute(text("ALTER TABLE category ADD COLUMN archived_at DATETIME"))


def _make_task_project_id_nullable() -> None:
    """Permite tareas sueltas sin proyecto (creadas desde Hoy). SQLite no
    soporta quitar un NOT NULL con ALTER TABLE: hay que recrear la tabla.

    El truco para no romper la foreign key de subtask.task_id -> task.id es
    crear la tabla nueva con OTRO nombre (nunca renombrar la original), asi el
    texto "REFERENCES task" que ya tiene subtask nunca se toca; al final se
    borra la tabla vieja y se renombra la nueva a "task", momento en el que
    ese texto (siempre igual) vuelve a resolver correctamente.
    """
    with engine.connect() as connection:
        columns = list(connection.execute(text("PRAGMA table_info(task)")))
        project_id_col = next((c for c in columns if c[1] == "project_id"), None)
        if project_id_col is None or project_id_col[3] == 0:
            return  # Ya nullable, o la tabla se acaba de crear con el schema nuevo.

    # PRAGMA foreign_keys es un no-op si ya hay una transaccion abierta en esta
    # conexion, y DROP TABLE de una tabla referenciada por FK falla con FKs
    # activas (aunque no se toque ninguna fila de la tabla hija): hace falta
    # aislamiento AUTOCOMMIT para que el OFF surta efecto antes del DROP.
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text("PRAGMA foreign_keys=OFF"))
        connection.execute(
            text(
                """
                CREATE TABLE task_new (
                    id INTEGER NOT NULL,
                    project_id INTEGER,
                    name VARCHAR NOT NULL,
                    status VARCHAR NOT NULL,
                    priority VARCHAR NOT NULL,
                    due_date DATE,
                    created_at DATETIME NOT NULL,
                    is_archived BOOLEAN NOT NULL,
                    archived_at DATETIME,
                    in_today BOOLEAN NOT NULL,
                    google_event_id VARCHAR,
                    description VARCHAR,
                    order_today INTEGER,
                    order_kanban INTEGER,
                    PRIMARY KEY (id),
                    FOREIGN KEY(project_id) REFERENCES project (id)
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO task_new (id, project_id, name, status, priority, due_date,
                    created_at, is_archived, archived_at, in_today, google_event_id,
                    description, order_today, order_kanban)
                SELECT id, project_id, name, status, priority, due_date,
                    created_at, is_archived, archived_at, in_today, google_event_id,
                    description, order_today, order_kanban
                FROM task
                """
            )
        )
        connection.execute(text("DROP TABLE task"))
        connection.execute(text("ALTER TABLE task_new RENAME TO task"))
        connection.execute(text("CREATE INDEX ix_task_project_id ON task (project_id)"))
        connection.execute(text("PRAGMA foreign_keys=ON"))


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    # El rebuild de la tabla va ANTES de los parches de columnas: recrea
    # `task` con una lista de columnas fija, asi que cualquier columna
    # anadida antes se perderia por el camino.
    _make_task_project_id_nullable()
    _add_missing_columns()


def get_session():
    with Session(engine) as session:
        yield session
