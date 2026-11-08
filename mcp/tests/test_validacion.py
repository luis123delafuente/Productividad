import unittest

from pd_api import NotFound
from pd_tasks import validate
from validacion import comprobar_contra_api, comprobar_subtareas_contra_api, errores_formato_cambios


class TestFormatos(unittest.TestCase):
    # Valores que Python 3.11+ acepta en fromisoformat y 3.9 no: deben fallar igual en los dos.
    MALOS = [
        {"task_id": 1, "due_date": "20261108"},
        {"task_id": 1, "due_date": "2026-11-08T10:00"},
        {"task_id": 1, "due_date": "2026-02-30"},
        {"task_id": 1, "due_time": "1600"},
        {"task_id": 1, "due_time": "16:00:00"},
        {"task_id": 1, "due_time": "25:00"},
        {"task_id": 1, "planned_start": "2026-11-10T16:00:00+01:00"},
        {"task_id": 1, "planned_start": "2026-11-10 16:00"},
        {"task_id": 1, "planned_minutes": 4},
        {"task_id": 1, "planned_minutes": 721},
        {"task_id": 1, "planned_minutes": True},
        {"task_id": 1, "name": None},
        {"task_id": 1, "name": "   "},
        {"task_id": 1, "priority": "Urgente"},
        {"task_id": 1, "status": "Hecho"},
        {"task_id": 1, "project_id": None},
        {"task_id": 1, "in_today": "si"},
        {"task_id": 1, "due_date": None, "due_time": "10:00"},
        {"task_id": 1, "color": "rojo"},
        {"task_id": 1},
        {"task_id": "1", "name": "x"},
    ]
    BUENOS = [
        {"task_id": 1, "due_date": "2026-11-08", "due_time": "16:00"},
        {"task_id": 1, "due_date": None},
        {"task_id": 1, "planned_start": "2026-11-10T16:00", "planned_minutes": 90},
        {"task_id": 1, "planned_start": None},
        {"task_id": 1, "name": "Nuevo", "description": None, "priority": "Alta", "status": "En proceso"},
        {"task_id": 1, "in_today": False, "project_id": 3},
    ]

    def test_malos(self):
        for cambio in self.MALOS:
            with self.subTest(cambio):
                self.assertTrue(errores_formato_cambios([cambio]))

    def test_buenos(self):
        for cambio in self.BUENOS:
            with self.subTest(cambio):
                self.assertEqual(errores_formato_cambios([cambio]), [])

    def test_task_id_repetido(self):
        errores = errores_formato_cambios([{"task_id": 1, "name": "a"}, {"task_id": 1, "priority": "Alta"}])
        self.assertTrue(any("ya aparece" in e for e in errores))

    def test_devuelve_todos_los_errores(self):
        errores = errores_formato_cambios([
            {"task_id": 1, "due_date": "ayer", "priority": "X"},
            {"task_id": 2, "name": ""},
        ])
        self.assertEqual(len(errores), 3)

    def test_lote_vacio(self):
        self.assertTrue(errores_formato_cambios([]))

    def test_crear_tareas_usa_los_mismos_formatos(self):
        for malo in ("20261108", "2026-02-30"):
            self.assertTrue(validate({"project_id": 1, "tasks": [{"name": "x", "due_date": malo}]}))
        self.assertTrue(validate({"project_id": 1, "tasks": [{"name": "x", "due_date": "2026-11-08", "due_time": "1600"}]}))
        self.assertEqual(validate({"project_id": 1, "tasks": [{"name": "x", "due_date": "2026-11-08", "due_time": "16:00"}]}), [])


def api_falsa(tareas, proyectos):
    def request(method, path, body=None):
        assert method == "GET", "la validación nunca escribe"
        if path == "/tasks":
            return list(tareas.values())
        recurso, _, ident = path.strip("/").partition("/")
        datos = {"tasks": tareas, "projects": proyectos}[recurso]
        if int(ident) not in datos:
            raise NotFound(path)
        return datos[int(ident)]
    return request


TAREAS = {
    1: {"id": 1, "project_id": 10, "due_date": None, "due_time": None, "is_archived": False,
        "subtasks": [{"id": 100, "name": "s", "is_checked": False}]},
    2: {"id": 2, "project_id": 10, "due_date": "2026-11-12", "due_time": None, "is_archived": False, "subtasks": []},
    3: {"id": 3, "project_id": 10, "due_date": None, "due_time": None, "is_archived": True, "subtasks": []},
}
PROYECTOS = {10: {"id": 10, "name": "Activo", "is_archived": False}, 11: {"id": 11, "name": "Viejo", "is_archived": True}}


class TestContraApi(unittest.TestCase):
    def setUp(self):
        self.request = api_falsa(TAREAS, PROYECTOS)

    def comprobar(self, cambios):
        return comprobar_contra_api(cambios, self.request)

    def test_todo_bien(self):
        errores, actuales = self.comprobar([{"task_id": 1, "project_id": 10}, {"task_id": 2, "due_time": "10:00"}])
        self.assertEqual(errores, [])
        self.assertEqual(sorted(actuales), [1, 2])

    def test_tarea_inexistente(self):
        errores, _ = self.comprobar([{"task_id": 99, "name": "x"}])
        self.assertIn("#99 no existe", errores[0])

    def test_tarea_archivada(self):
        errores, _ = self.comprobar([{"task_id": 3, "name": "x"}])
        self.assertIn("archivada", errores[0])

    def test_proyecto_destino_archivado_o_inexistente(self):
        errores, _ = self.comprobar([{"task_id": 1, "project_id": 11}, {"task_id": 2, "project_id": 12}])
        self.assertEqual(len(errores), 2)
        self.assertIn("archivado", errores[0])
        self.assertIn("no existe", errores[1])

    def test_hora_sin_fecha_efectiva(self):
        errores, _ = self.comprobar([{"task_id": 1, "due_time": "10:00"}])
        self.assertIn("necesita 'due_date'", errores[0])

    def test_varios_errores_a_la_vez(self):
        errores, _ = self.comprobar([
            {"task_id": 99, "name": "x"},
            {"task_id": 1, "project_id": 11, "due_time": "10:00"},
        ])
        self.assertEqual(len(errores), 3)

    def test_subtareas(self):
        errores, indice = comprobar_subtareas_contra_api([100, 999], self.request)
        self.assertEqual(indice, {100: 1})
        self.assertEqual(len(errores), 1)
        self.assertIn("#999", errores[0])
