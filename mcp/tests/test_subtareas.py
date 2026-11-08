from tests._entorno import EntornoIntegracion


class TestActualizarSubtareas(EntornoIntegracion):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        api = cls.__new__(cls).api
        cat = api("GET", "/categories")[0]["id"]
        p = api("POST", "/projects", {"category_id": cat, "name": "P sub"})
        cls.tarea = api("POST", "/tasks", {"project_id": p["id"], "name": "Con checklist"})
        cls.sub = api("POST", f"/tasks/{cls.tarea['id']}/subtasks", {"name": "Existente"})

    def subtareas(self):
        return {s["name"]: s["is_checked"] for s in self.api("GET", f"/tasks/{self.tarea['id']}")["subtasks"]}

    def test_crear_marcar_y_desmarcar(self):
        payload, es_error = self.llamar("actualizar_subtareas", {"operaciones": [
            {"op": "crear", "task_id": self.tarea["id"], "name": "Nueva"},
            {"op": "marcar", "subtask_id": self.sub["id"], "hecha": True}]})
        self.assertFalse(es_error, payload)
        self.assertEqual(self.subtareas()["Nueva"], False)
        self.assertEqual(self.subtareas()["Existente"], True)
        payload, es_error = self.llamar("actualizar_subtareas", {"operaciones": [
            {"op": "marcar", "subtask_id": self.sub["id"], "hecha": False}]})
        self.assertFalse(es_error, payload)
        self.assertEqual(self.subtareas()["Existente"], False)

    def test_borrar_remite_a_proponer_cambios(self):
        payload, es_error = self.llamar("actualizar_subtareas", {"operaciones": [
            {"op": "crear", "task_id": self.tarea["id"], "name": "No debe crearse"},
            {"op": "borrar", "subtask_id": self.sub["id"]}]})
        self.assertTrue(es_error)
        self.assertIn("proponer_cambios", payload)
        self.assertNotIn("No debe crearse", self.subtareas())
        self.assertIn("Existente", self.subtareas())

    def test_ids_inexistentes_y_formato(self):
        payload, es_error = self.llamar("actualizar_subtareas", {"operaciones": [
            {"op": "crear", "task_id": 999999, "name": "x"},
            {"op": "marcar", "subtask_id": 999999, "hecha": True},
            {"op": "crear", "task_id": self.tarea["id"], "name": "  "},
            {"op": "marcar", "subtask_id": self.sub["id"], "hecha": "si"},
            {"op": "renombrar"}]})
        self.assertTrue(es_error)
        self.assertEqual(payload.count("\n- "), 5, payload)
