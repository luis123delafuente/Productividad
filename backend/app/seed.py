from sqlmodel import Session, select

from app.models import AppSettings, Category, GoogleToken

FIXED_CATEGORIES = [
    ("Trabajo", "trabajo"),
    ("Freelance", "freelance"),
    ("Universidad", "universidad"),
    ("Personal", "personal"),
]


def run_seed(session: Session) -> None:
    existing_slugs = set(session.exec(select(Category.slug)).all())
    for name, slug in FIXED_CATEGORIES:
        if slug not in existing_slugs:
            session.add(Category(name=name, slug=slug))

    if session.get(AppSettings, 1) is None:
        session.add(AppSettings(id=1, last_weekly_archive_run=None))

    if session.get(GoogleToken, 1) is None:
        session.add(GoogleToken(id=1, connected=False))

    session.commit()
