from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

est_sqlite = settings.DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if est_sqlite else {}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)

# SQLite n'applique pas les clés étrangères par défaut : on les active
if est_sqlite:
    @event.listens_for(engine, "connect")
    def activer_cles_etrangeres(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()