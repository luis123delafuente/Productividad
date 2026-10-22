from datetime import datetime

from app.models import Project, Task, TaskStatus
from app.services.archive_service import (
    check_and_run_daily_today_reset,
    check_and_run_weekly_archive,
    compute_start_of_current_week,
)


def _make_project(session, is_archived=False):
    project = Project(category_id=_ensure_category(session), name="P", is_archived=is_archived)
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def _ensure_category(session):
    from sqlmodel import select

    from app.models import Category

    category = session.exec(select(Category).where(Category.slug == "trabajo")).one()
    return category.id


def test_compute_start_of_current_week_is_monday_midnight():
    # Un jueves cualquiera -> el lunes de esa misma semana, a medianoche.
    thursday = datetime(2026, 7, 23, 15, 30)  # jueves 2026-07-23
    monday = compute_start_of_current_week(thursday)
    assert monday == datetime(2026, 7, 20, 0, 0)


def test_archives_terminado_tasks_of_active_projects(session):
    project = _make_project(session)
    task = Task(project_id=project.id, name="hecha", status=TaskStatus.terminado)
    session.add(task)
    session.commit()

    now = datetime(2026, 7, 23, 10, 0)
    archived_count = check_and_run_weekly_archive(session, now=now)

    session.refresh(task)
    assert archived_count == 1
    assert task.is_archived is True
    assert task.archived_at == now


def test_never_touches_tasks_in_manually_archived_projects(session):
    archived_project = _make_project(session, is_archived=True)
    task = Task(project_id=archived_project.id, name="hecha", status=TaskStatus.terminado)
    session.add(task)
    session.commit()

    check_and_run_weekly_archive(session, now=datetime(2026, 7, 23, 10, 0))

    session.refresh(task)
    assert task.is_archived is False


def test_idempotent_within_same_week(session):
    project = _make_project(session)
    task = Task(project_id=project.id, name="hecha", status=TaskStatus.terminado)
    session.add(task)
    session.commit()

    first_run = check_and_run_weekly_archive(session, now=datetime(2026, 7, 23, 10, 0))
    assert first_run == 1

    # Otra tarea Terminado aparece mas tarde en la MISMA semana: no se archiva
    # hasta el siguiente limite de semana, aunque se vuelva a llamar a la funcion.
    another_task = Task(project_id=project.id, name="otra", status=TaskStatus.terminado)
    session.add(another_task)
    session.commit()

    second_run = check_and_run_weekly_archive(session, now=datetime(2026, 7, 24, 9, 0))
    assert second_run == 0
    session.refresh(another_task)
    assert another_task.is_archived is False


def test_runs_again_after_crossing_next_monday(session):
    project = _make_project(session)
    task = Task(project_id=project.id, name="hecha", status=TaskStatus.terminado)
    session.add(task)
    session.commit()

    check_and_run_weekly_archive(session, now=datetime(2026, 7, 23, 10, 0))

    another_task = Task(project_id=project.id, name="otra", status=TaskStatus.terminado)
    session.add(another_task)
    session.commit()

    next_week_count = check_and_run_weekly_archive(session, now=datetime(2026, 7, 27, 9, 0))
    assert next_week_count == 1
    session.refresh(another_task)
    assert another_task.is_archived is True


def test_daily_reset_clears_terminado_tasks_from_today(session):
    project = _make_project(session)
    done = Task(project_id=project.id, name="hecha", status=TaskStatus.terminado, in_today=True)
    pending = Task(project_id=project.id, name="pendiente", status=TaskStatus.pendiente, in_today=True)
    session.add_all([done, pending])
    session.commit()

    cleared_count = check_and_run_daily_today_reset(session, now=datetime(2026, 7, 23, 10, 0))

    session.refresh(done)
    session.refresh(pending)
    assert cleared_count == 1
    assert done.in_today is False
    assert pending.in_today is True


def test_daily_reset_idempotent_within_same_day(session):
    project = _make_project(session)
    done = Task(project_id=project.id, name="hecha", status=TaskStatus.terminado, in_today=True)
    session.add(done)
    session.commit()

    first_run = check_and_run_daily_today_reset(session, now=datetime(2026, 7, 23, 10, 0))
    assert first_run == 1

    # Otra tarea Terminado aparece mas tarde el MISMO dia: no se quita de Hoy
    # hasta el siguiente limite de dia, aunque se vuelva a llamar a la funcion.
    another_done = Task(project_id=project.id, name="otra", status=TaskStatus.terminado, in_today=True)
    session.add(another_done)
    session.commit()

    second_run = check_and_run_daily_today_reset(session, now=datetime(2026, 7, 23, 20, 0))
    assert second_run == 0
    session.refresh(another_done)
    assert another_done.in_today is True


def test_daily_reset_runs_again_after_crossing_midnight(session):
    project = _make_project(session)
    done = Task(project_id=project.id, name="hecha", status=TaskStatus.terminado, in_today=True)
    session.add(done)
    session.commit()

    check_and_run_daily_today_reset(session, now=datetime(2026, 7, 23, 10, 0))

    another_done = Task(project_id=project.id, name="otra", status=TaskStatus.terminado, in_today=True)
    session.add(another_done)
    session.commit()

    next_day_count = check_and_run_daily_today_reset(session, now=datetime(2026, 7, 24, 9, 0))
    assert next_day_count == 1
    session.refresh(another_done)
    assert another_done.in_today is False
