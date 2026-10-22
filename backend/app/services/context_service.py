"""Construye el contexto de datos reales que se le pasa al modelo en cada turno.

Por defecto se sirve la jerarquia activa completa (todas las categorias,
proyectos y tareas): el asistente debe poder priorizar con criterio real, y
"acotar el alcance" es una decision de que proponer, no de que datos puede ver
-- ver `assistant_service.SYSTEM_PROMPT` para la instruccion blanda de enfoque
cuando el usuario lo pide en su mensaje. El unico filtro *duro* es el que llega
de un boton contextual (`AssistantScope.task_id`/`project_id`), resuelto aqui
como una nota explicita al principio del contexto.
"""

from sqlmodel import Session, select

from app.models import Category, Project, Task
from app.schemas import AssistantScope


def build_context(session: Session, scope: AssistantScope | None = None) -> str:
    lines: list[str] = []

    if scope and scope.task_id:
        task = session.get(Task, scope.task_id)
        if task:
            lines.append(f"ENFOQUE SOLICITADO: la peticion se refiere en concreto a la tarea #{task.id} \"{task.name}\".")
    if scope and scope.project_id:
        project = session.get(Project, scope.project_id)
        if project:
            lines.append(f"ENFOQUE SOLICITADO: la peticion se refiere en concreto al proyecto #{project.id} \"{project.name}\".")

    lines.append("")
    lines.append("=== Categorias, proyectos y tareas activas ===")

    categories = session.exec(select(Category).order_by(Category.id)).all()
    for category in categories:
        lines.append(f"\n# Categoria: {category.name}")
        projects = session.exec(
            select(Project)
            .where(Project.category_id == category.id, Project.is_archived == False)  # noqa: E712
            .order_by(Project.created_at)
        ).all()
        if not projects:
            lines.append("  (sin proyectos activos)")
            continue
        for project in projects:
            client_part = f" (cliente: {project.client})" if project.client else ""
            lines.append(f"  ## Proyecto #{project.id}: {project.name}{client_part}")
            tasks = session.exec(
                select(Task)
                .where(Task.project_id == project.id, Task.is_archived == False)  # noqa: E712
                .order_by(Task.due_date.is_(None), Task.due_date)
            ).all()
            if not tasks:
                lines.append("    (sin tareas activas)")
                continue
            for task in tasks:
                due = f", vence {task.due_date.isoformat()}" if task.due_date else ""
                if task.due_date and task.due_time:
                    due += f" a las {task.due_time.strftime('%H:%M')}"
                today_flag = ", en Hoy" if task.in_today else ""
                subtask_count = len(task.subtasks)
                checked = sum(1 for s in task.subtasks if s.is_checked)
                subtask_part = f", subtareas {checked}/{subtask_count}" if subtask_count else ""
                lines.append(
                    f"    - Tarea #{task.id}: \"{task.name}\" [estado: {task.status.value}, "
                    f"prioridad: {task.priority.value}{due}{today_flag}{subtask_part}]"
                )

    standalone_tasks = session.exec(
        select(Task)
        .where(Task.project_id.is_(None), Task.is_archived == False)  # noqa: E712
        .order_by(Task.created_at)
    ).all()
    lines.append("\n# Tareas sueltas en Hoy (sin proyecto)")
    if not standalone_tasks:
        lines.append("  (ninguna)")
    else:
        for task in standalone_tasks:
            today_flag = ", en Hoy" if task.in_today else ""
            lines.append(f"  - Tarea #{task.id}: \"{task.name}\" [estado: {task.status.value}{today_flag}]")

    archived_projects = session.exec(
        select(Project).where(Project.is_archived == True).order_by(Project.archived_at.desc())  # noqa: E712
    ).all()
    if archived_projects:
        lines.append("\n=== Proyectos archivados (solo referencia, para reabrir si se pide) ===")
        for project in archived_projects:
            lines.append(f"  - Proyecto #{project.id}: {project.name} (archivado)")

    return "\n".join(lines)
