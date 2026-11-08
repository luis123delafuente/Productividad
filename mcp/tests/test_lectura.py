from tests._entorno import EntornoIntegracion


class TestProtocoloYProyectos(EntornoIntegracion):
    def test_tools_list_expone_las_herramientas(self):
        respuesta = self.mcp.enviar("tools/list")
        nombres = {t["name"] for t in respuesta["result"]["tools"]}
        self.assertIn("listar_proyectos", nombres)

    def test_listar_proyectos_separa_activos_y_archivados(self):
        categorias = {c["slug"]: c["id"] for c in self.api("GET", "/categories")}
        activo = self.api("POST", "/projects", {"category_id": categorias["trabajo"], "name": "Activo X"})
        archivado = self.api("POST", "/projects", {"category_id": categorias["freelance"], "name": "Viejo Y"})
        self.api("POST", f"/projects/{archivado['id']}/archive")

        payload, es_error = self.llamar("listar_proyectos")

        self.assertFalse(es_error, payload)
        self.assertEqual(
            [b["name"] for b in payload["bloques"]], ["Trabajo", "Freelance", "Universidad", "Personal"]
        )
        trabajo = next(b for b in payload["bloques"] if b["name"] == "Trabajo")
        self.assertIn(activo["id"], [p["id"] for p in trabajo["projects"]])
        todos_activos = [p["id"] for b in payload["bloques"] for p in b["projects"]]
        self.assertNotIn(archivado["id"], todos_activos)
        self.assertEqual(
            payload["proyectos_archivados"],
            [{"id": archivado["id"], "name": "Viejo Y", "category_id": categorias["freelance"], "category": "Freelance"}],
        )

    def test_app_caida_devuelve_aviso_claro(self):
        from tests._entorno import ClienteMCP

        self.mcp.cerrar()
        self.mcp = ClienteMCP("http://127.0.0.1:1/api")
        self.mcp.enviar("initialize", {"protocolVersion": "2025-11-25", "capabilities": {}})
        payload, es_error = self.llamar("listar_proyectos")
        self.assertTrue(es_error)
        self.assertIn("http://127.0.0.1:1/api", payload)


class TestListarTareas(EntornoIntegracion):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        tmp = cls.__new__(cls)  # para usar self.api sin un test en marcha
        cats = {c["slug"]: c["id"] for c in tmp.api("GET", "/categories")}
        cls.proyecto = tmp.api("POST", "/projects", {"category_id": cats["trabajo"], "name": "Proyecto L"})
        cls.archivado = tmp.api("POST", "/projects", {"category_id": cats["trabajo"], "name": "Archivado L"})
        cls.con_todo = tmp.api("POST", "/tasks", {
            "project_id": cls.proyecto["id"], "name": "Con todo", "description": "Desc", "priority": "Alta",
            "status": "En proceso", "due_date": "2026-11-12", "in_today": True,
        })
        tmp.api("PATCH", f"/tasks/{cls.con_todo['id']}/planning", {"planned_start": "2026-11-10T09:30:00", "planned_minutes": 45})
        cls.subtarea = tmp.api("POST", f"/tasks/{cls.con_todo['id']}/subtasks", {"name": "Paso A"})
        tmp.api("PATCH", f"/subtasks/{cls.subtarea['id']}", {"is_checked": True})
        cls.suelta = tmp.api("POST", "/tasks", {"project_id": None, "name": "Suelta L", "in_today": False})
        tmp.api("POST", "/tasks", {"project_id": cls.archivado["id"], "name": "Oculta L"})
        tmp.api("POST", f"/projects/{cls.archivado['id']}/archive")

    def test_con_proyecto_devuelve_todos_los_campos(self):
        payload, es_error = self.llamar("listar_tareas", {"project_id": self.proyecto["id"]})
        self.assertFalse(es_error, payload)
        self.assertEqual(payload["project"], {"id": self.proyecto["id"], "name": "Proyecto L"})
        self.assertEqual(payload["tasks"], [{
            "id": self.con_todo["id"],
            "project": {"id": self.proyecto["id"], "name": "Proyecto L"},
            "name": "Con todo",
            "description": "Desc",
            "status": "En proceso",
            "priority": "Alta",
            "due_date": "2026-11-12",
            "due_time": None,
            "in_today": True,
            "planned_start": "2026-11-10T09:30",
            "planned_minutes": 45,
            "subtasks": [{"id": self.subtarea["id"], "name": "Paso A", "done": True}],
        }])

    def test_sin_proyecto_incluye_sueltas_y_omite_archivados(self):
        payload, es_error = self.llamar("listar_tareas")
        self.assertFalse(es_error, payload)
        nombres = sorted(t["name"] for t in payload["tasks"])
        self.assertEqual(nombres, ["Con todo", "Suelta L"])
        suelta = next(t for t in payload["tasks"] if t["name"] == "Suelta L")
        self.assertIsNone(suelta["project"])

    def test_proyecto_inexistente_es_error(self):
        payload, es_error = self.llamar("listar_tareas", {"project_id": 99999})
        self.assertTrue(es_error)
        self.assertIn("no existe", payload)

    def test_proyecto_archivado_es_error_claro(self):
        payload, es_error = self.llamar("listar_tareas", {"project_id": self.archivado["id"]})
        self.assertTrue(es_error)
        self.assertIn("archivado", payload)
