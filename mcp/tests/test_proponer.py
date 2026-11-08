import unittest

from pd_api import ApiError
from proponer import AlmacenPropuestas, PropuestaInvalida, aplicar_propuesta
from tests._entorno import EntornoIntegracion


class RelojFalso:
    def __init__(self):
        self.ahora = 1000.0

    def __call__(self):
        return self.ahora


class TestAlmacen(unittest.TestCase):
    def test_codigo_de_un_solo_uso(self):
        almacen = AlmacenPropuestas(reloj=RelojFalso())
        codigo = almacen.guardar({"x": 1})
        self.assertEqual(almacen.tomar(codigo), {"x": 1})
        with self.assertRaisesRegex(PropuestaInvalida, "ya se usó"):
            almacen.tomar(codigo)

    def test_caduca_a_los_30_minutos(self):
        reloj = RelojFalso()
        almacen = AlmacenPropuestas(reloj=reloj)
        vigente = almacen.guardar("a")
        caducada = almacen.guardar("b")
        reloj.ahora += 30 * 60
        self.assertEqual(almacen.tomar(vigente), "a")
        reloj.ahora += 1
        with self.assertRaisesRegex(PropuestaInvalida, "caducó"):
            almacen.tomar(caducada)

    def test_codigo_inexistente(self):
        with self.assertRaisesRegex(PropuestaInvalida, "no existe"):
            AlmacenPropuestas().tomar("nope")


class TestAplicarParcial(unittest.TestCase):
    def test_fallo_a_medias_queda_en_el_informe(self):
        def request(method, path, body=None):
            if path == "/tasks/2":
                raise ApiError("DELETE /tasks/2 → HTTP 500: boom")
            return {"calendar_sync_warning": "Google falló"} if path == "/tasks/1" else None

        informe = aplicar_propuesta(
            [{"tipo": "borrar_tareas", "task_ids": [1, 2, 3]}, {"tipo": "archivar_proyecto", "project_id": 9}], request
        )
        self.assertFalse(informe["ok"])
        self.assertEqual(informe["aplicados"], ["borrada tarea #1", "borrada tarea #3", "archivado proyecto #9"])
        self.assertIn("boom", informe["fallidos"][0])
        self.assertEqual(informe["avisos_google"], ["tarea #1: Google falló"])


class TestProponerYConfirmar(EntornoIntegracion):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        api = cls.__new__(cls).api
        cls.cat = api("GET", "/categories")[0]["id"]

    def setUp(self):
        super().setUp()
        self.p = self.api("POST", "/projects", {"category_id": self.cat, "name": "P prop"})

    def nueva(self, **campos):
        return self.api("POST", "/tasks", {"project_id": self.p["id"], "name": "T", **campos})

    def proponer(self, operaciones):
        payload, es_error = self.llamar("proponer_cambios", {"operaciones": operaciones})
        self.assertFalse(es_error, payload)
        return payload

    def confirmar(self, codigo):
        return self.llamar("confirmar_cambios", {"codigo": codigo})

    def existe(self, tid):
        import urllib.error

        try:
            self.api("GET", f"/tasks/{tid}")
            return True
        except urllib.error.HTTPError as exc:
            exc.close()
            return False

    def test_las_siete_operaciones_no_cambian_nada_hasta_confirmar(self):
        con_hora = self.nueva(name="Cita", due_date="2026-11-12", due_time="10:00")
        borrar = self.nueva(name="A borrar")
        suelta = self.api("POST", "/tasks", {"project_id": None, "name": "Suelta", "in_today": True})
        con_sub = self.nueva(name="Con sub")
        sub = self.api("POST", f"/tasks/{con_sub['id']}/subtasks", {"name": "Sub"})
        otro = self.api("POST", "/projects", {"category_id": self.cat, "name": "A archivar"})
        viejo = self.api("POST", "/projects", {"category_id": self.cat, "name": "A reabrir"})
        self.api("POST", f"/projects/{viejo['id']}/archive")

        payload = self.proponer([
            {"tipo": "crear_tareas", "project_id": self.p["id"], "tasks": [{"name": "Reunión", "due_date": "2026-11-20", "due_time": "09:30"}]},
            {"tipo": "actualizar", "cambios": [{"task_id": con_hora["id"], "due_date": "2026-11-19"}]},
            {"tipo": "quitar_de_hoy", "task_ids": [suelta["id"]]},
            {"tipo": "borrar_tareas", "task_ids": [borrar["id"]]},
            {"tipo": "borrar_subtareas", "subtask_ids": [sub["id"]]},
            {"tipo": "archivar_proyecto", "project_id": otro["id"]},
            {"tipo": "reabrir_proyecto", "project_id": viejo["id"]},
        ])
        previa = "\n".join(payload["vista_previa"])
        self.assertIn("crea un evento en Google Calendar el 2026-11-20 a las 09:30", previa)
        self.assertIn("mueve el evento de Google Calendar a 2026-11-19 10:00", previa)
        self.assertIn("borra la tarea suelta", previa)
        self.assertIn("Borra definitivamente la tarea", previa)
        self.assertIn("Sus eventos de Google se mantienen", previa)
        self.assertIn("sus tareas en Hoy siguen visibles", previa)

        # Nada ha cambiado todavía.
        self.assertEqual(self.api("GET", f"/tasks/{con_hora['id']}")["due_date"], "2026-11-12")
        self.assertTrue(self.existe(suelta["id"]) and self.existe(borrar["id"]))
        self.assertEqual([s["name"] for s in self.api("GET", f"/tasks/{con_sub['id']}")["subtasks"]], ["Sub"])
        self.assertFalse(self.api("GET", f"/projects/{otro['id']}")["is_archived"])
        self.assertTrue(self.api("GET", f"/projects/{viejo['id']}")["is_archived"])
        self.assertNotIn("Reunión", [t["name"] for t in self.api("GET", f"/tasks?project_id={self.p['id']}")])

        resultado, es_error = self.confirmar(payload["codigo"])
        self.assertFalse(es_error, resultado)
        self.assertEqual(self.api("GET", f"/tasks/{con_hora['id']}")["due_date"], "2026-11-19")
        self.assertFalse(self.existe(suelta["id"]) or self.existe(borrar["id"]))
        self.assertEqual(self.api("GET", f"/tasks/{con_sub['id']}")["subtasks"], [])
        self.assertTrue(self.api("GET", f"/projects/{otro['id']}")["is_archived"])
        self.assertFalse(self.api("GET", f"/projects/{viejo['id']}")["is_archived"])
        reunion = [t for t in self.api("GET", f"/tasks?project_id={self.p['id']}") if t["name"] == "Reunión"]
        self.assertEqual(reunion[0]["due_time"], "09:30:00")

    def test_codigo_reutilizado_se_rechaza(self):
        t = self.nueva(name="Una vez")
        payload = self.proponer([{"tipo": "borrar_tareas", "task_ids": [t["id"]]}])
        self.assertFalse(self.confirmar(payload["codigo"])[1])
        resultado, es_error = self.confirmar(payload["codigo"])
        self.assertTrue(es_error)
        self.assertIn("ya se usó", resultado)

    def test_tarea_modificada_entre_medias_no_aplica_nada(self):
        t = self.nueva(name="Original", due_date="2026-11-12", due_time="10:00")
        otra = self.nueva(name="Otra")
        payload = self.proponer([
            {"tipo": "actualizar", "cambios": [{"task_id": t["id"], "due_date": "2026-11-19"}]},
            {"tipo": "borrar_tareas", "task_ids": [otra["id"]]},
        ])
        self.api("PATCH", f"/tasks/{t['id']}", {"name": "Renombrada en la app"})
        resultado, es_error = self.confirmar(payload["codigo"])
        self.assertTrue(es_error)
        self.assertIn(f"tarea #{t['id']}", resultado)
        self.assertEqual(self.api("GET", f"/tasks/{t['id']}")["due_date"], "2026-11-12")
        self.assertTrue(self.existe(otra["id"]))

    def test_codigo_inventado(self):
        resultado, es_error = self.confirmar("abcd1234")
        self.assertTrue(es_error)
        self.assertIn("no existe", resultado)

    def test_errores_de_validacion_no_proponen_nada(self):
        payload, es_error = self.llamar("proponer_cambios", {"operaciones": [
            {"tipo": "borrar_tareas", "task_ids": [999999]},
            {"tipo": "reabrir_proyecto", "project_id": self.p["id"]},
            {"tipo": "teletransportar"}]})
        self.assertTrue(es_error)
        self.assertIn("#999999 no existe", payload)
        self.assertIn("no está archivado", payload)
        self.assertIn("'tipo' debe ser", payload)

    def test_misma_tarea_en_dos_operaciones(self):
        t = self.nueva(name="Doble")
        payload, es_error = self.llamar("proponer_cambios", {"operaciones": [
            {"tipo": "quitar_de_hoy", "task_ids": [t["id"]]},
            {"tipo": "borrar_tareas", "task_ids": [t["id"]]}]})
        self.assertTrue(es_error)
        self.assertIn("más de una operación", payload)
