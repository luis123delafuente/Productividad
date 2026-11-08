import unittest

from escritura import ResultadoParcial, aplicar_cambios_tareas, informe_o_error, pasos_de_cambio
from pd_api import ApiError
from tests._entorno import EntornoIntegracion


class TestInformeParcial(unittest.TestCase):
    def test_fallo_en_el_segundo_cambio(self):
        llamadas = []

        def request(method, path, body=None):
            llamadas.append(path)
            if path.startswith("/tasks/2"):
                raise ApiError("PATCH /tasks/2/status → HTTP 500: boom")
            return {"id": int(path.split("/")[2]), "name": "t", "status": "Terminado", "priority": "Media",
                    "calendar_sync_warning": "Google no respondió" if path.endswith("due_date") else None}

        informe = aplicar_cambios_tareas(
            [{"task_id": 1, "status": "Terminado", "due_date": "2026-11-20"},
             {"task_id": 2, "status": "Terminado"},
             {"task_id": 3, "priority": "Alta"}],
            request,
        )
        self.assertFalse(informe["ok"])
        self.assertEqual([a["task_id"] for a in informe["aplicados"]], [1, 3])
        self.assertEqual(informe["fallidos"][0]["task_id"], 2)
        self.assertIn("boom", informe["fallidos"][0]["error"])
        self.assertEqual(informe["avisos_google"], ["tarea #1: Google no respondió"])
        with self.assertRaises(ResultadoParcial):
            informe_o_error(informe)

    def test_pasos_solo_con_campos_enviados(self):
        self.assertEqual(
            pasos_de_cambio({"task_id": 5, "due_date": "2026-11-20"}),
            [("PATCH", "/tasks/5/due_date", {"due_date": "2026-11-20"})],
        )
        self.assertEqual(pasos_de_cambio({"task_id": 5, "in_today": True, "name": "x"})[-1][1], "/tasks/5/in_today")


class TestCrearYActualizar(EntornoIntegracion):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        api = cls.__new__(cls).api
        cats = {c["slug"]: c["id"] for c in api("GET", "/categories")}
        cls.cat = cats["trabajo"]
        cls.p1 = api("POST", "/projects", {"category_id": cls.cat, "name": "P1"})
        cls.p2 = api("POST", "/projects", {"category_id": cls.cat, "name": "P2"})
        cls.parchivado = api("POST", "/projects", {"category_id": cls.cat, "name": "P archivado"})
        api("POST", f"/projects/{cls.parchivado['id']}/archive")

    def nueva(self, **campos):
        return self.api("POST", "/tasks", {"project_id": self.p1["id"], "name": "T", **campos})

    def test_crear_sin_hora_crea_y_omite_duplicados(self):
        tareas = [{"name": "Fase 1", "due_date": "2026-11-20", "priority": "Alta", "subtasks": ["a", "b"]},
                  {"name": "Fase 2", "description": "Hecho cuando X"}]
        payload, es_error = self.llamar("crear_tareas", {"project_id": self.p2["id"], "tasks": tareas})
        self.assertFalse(es_error, payload)
        self.assertEqual(len(payload["creadas"]), 2)
        payload, _ = self.llamar("crear_tareas", {"project_id": self.p2["id"], "tasks": [{"name": "fase 1"}]})
        self.assertEqual(payload["omitidas_por_duplicado"], ["fase 1"])

    def test_crear_con_hora_no_crea_nada(self):
        antes = len(self.api("GET", f"/tasks?project_id={self.p1['id']}"))
        payload, es_error = self.llamar("crear_tareas", {"project_id": self.p1["id"], "tasks": [
            {"name": "Sin hora"}, {"name": "Cita", "due_date": "2026-11-20", "due_time": "10:00"}]})
        self.assertTrue(es_error)
        self.assertIn("proponer_cambios", payload)
        self.assertEqual(len(self.api("GET", f"/tasks?project_id={self.p1['id']}")), antes)

    def test_cada_campo_directo(self):
        t = self.nueva(due_date="2026-11-12")
        cambio = {
            "task_id": t["id"], "name": "Renombrada", "description": "D", "priority": "Alta", "status": "En proceso",
            "project_id": self.p2["id"], "in_today": True, "planned_start": "2026-11-10T16:00", "planned_minutes": 90,
            "due_date": "2026-11-15",
        }
        payload, es_error = self.llamar("actualizar_tareas", {"cambios": [cambio]})
        self.assertFalse(es_error, payload)
        final = self.api("GET", f"/tasks/{t['id']}")
        self.assertEqual(
            (final["name"], final["description"], final["priority"], final["status"], final["project_id"],
             final["in_today"], final["planned_start"], final["planned_minutes"], final["due_date"]),
            ("Renombrada", "D", "Alta", "En proceso", self.p2["id"], True, "2026-11-10T16:00:00", 90, "2026-11-15"),
        )
        self.assertEqual(payload["aplicados"][0]["tarea"]["name"], "Renombrada")

    def test_quitar_de_hoy_con_proyecto_y_desplanificar(self):
        t = self.nueva(in_today=True)
        self.api("PATCH", f"/tasks/{t['id']}/planning", {"planned_start": "2026-11-10T09:00:00"})
        payload, es_error = self.llamar("actualizar_tareas", {"cambios": [
            {"task_id": t["id"], "in_today": False, "planned_start": None}]})
        self.assertFalse(es_error, payload)
        final = self.api("GET", f"/tasks/{t['id']}")
        self.assertEqual((final["in_today"], final["planned_start"]), (False, None))

    def test_lote_mixto_no_aplica_nada(self):
        a = self.nueva(name="A")
        b = self.nueva(name="B", due_date="2026-11-12")
        payload, es_error = self.llamar("actualizar_tareas", {"cambios": [
            {"task_id": a["id"], "priority": "Alta"},
            {"task_id": b["id"], "due_time": "10:00"}]})
        self.assertTrue(es_error)
        self.assertIn("proponer_cambios", payload)
        self.assertIn(f"#{b['id']}", payload)
        self.assertEqual(self.api("GET", f"/tasks/{a['id']}")["priority"], "Media")
        self.assertIsNone(self.api("GET", f"/tasks/{b['id']}")["due_time"])

    def test_quitar_de_hoy_una_suelta_se_rechaza(self):
        s = self.api("POST", "/tasks", {"project_id": None, "name": "Suelta", "in_today": True})
        payload, es_error = self.llamar("actualizar_tareas", {"cambios": [{"task_id": s["id"], "in_today": False}]})
        self.assertTrue(es_error)
        self.assertIn("borra la tarea suelta", payload)
        self.assertTrue(self.api("GET", f"/tasks/{s['id']}")["in_today"])

    def test_errores_de_validacion_no_aplican_nada(self):
        a = self.nueva(name="Intacta")
        payload, es_error = self.llamar("actualizar_tareas", {"cambios": [
            {"task_id": a["id"], "name": "Cambiada"},
            {"task_id": 999999, "priority": "Alta"},
            {"task_id": a["id"] + 100000, "project_id": self.parchivado["id"]}]})
        self.assertTrue(es_error)
        self.assertIn("#999999 no existe", payload)
        self.assertEqual(self.api("GET", f"/tasks/{a['id']}")["name"], "Intacta")

    def test_mover_a_proyecto_archivado_se_rechaza(self):
        a = self.nueva(name="No me muevas")
        payload, es_error = self.llamar("actualizar_tareas", {"cambios": [
            {"task_id": a["id"], "project_id": self.parchivado["id"]}]})
        self.assertTrue(es_error)
        self.assertIn("archivado", payload)
        self.assertEqual(self.api("GET", f"/tasks/{a['id']}")["project_id"], self.p1["id"])
