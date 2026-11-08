from tests._entorno import EntornoIntegracion


class TestVerAgenda(EntornoIntegracion):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        api = cls.__new__(cls).api
        cats = {c["slug"]: c["id"] for c in api("GET", "/categories")}
        proyecto = api("POST", "/projects", {"category_id": cats["trabajo"], "name": "P agenda"})
        archivado = api("POST", "/projects", {"category_id": cats["trabajo"], "name": "P archivado"})
        nueva = lambda **c: api("POST", "/tasks", {"project_id": proyecto["id"], **c})
        cls.vencida_media = nueva(name="Vencida media", priority="Media", due_date="2026-11-09")
        cls.vencida_hecha = nueva(name="Vencida hecha", priority="Alta", due_date="2026-11-09", status="Terminado")
        api("POST", "/tasks", {"project_id": archivado["id"], "name": "Vencida archivada", "due_date": "2026-11-01"})
        api("POST", f"/projects/{archivado['id']}/archive")
        cls.entrega_hoy = nueva(name="Entrega hoy", due_date="2026-11-10")
        cls.entrega_manana = nueva(name="Entrega manana", due_date="2026-11-11")
        cls.entrega_lejos = nueva(name="Entrega lejos", due_date="2026-11-12")
        cls.planificada = nueva(name="Planificada")
        api("PATCH", f"/tasks/{cls.planificada['id']}/planning", {"planned_start": "2026-11-10T16:00:00", "planned_minutes": 120})
        cls.en_hoy = nueva(name="En hoy", in_today=True)

    def agenda(self, **args):
        payload, es_error = self.llamar("ver_agenda", {"desde": "2026-11-10", **args})
        self.assertFalse(es_error, payload)
        return payload

    def test_por_defecto_dos_dias(self):
        payload = self.agenda()
        self.assertEqual((payload["desde"], payload["hasta"]), ("2026-11-10", "2026-11-11"))
        self.assertEqual(sorted(t["name"] for t in payload["deadlines"]), ["Entrega hoy", "Entrega manana"])

    def test_secciones(self):
        payload = self.agenda()
        self.assertEqual(
            set(payload), {"desde", "hasta", "today", "planned_blocks", "deadlines", "overdue", "google_events", "google"}
        )
        self.assertIn("En hoy", [t["name"] for t in payload["today"]["selected"]])
        self.assertIn("suggestions", payload["today"])
        bloque = next(t for t in payload["planned_blocks"] if t["name"] == "Planificada")
        self.assertEqual((bloque["planned_start"], bloque["planned_minutes"]), ("2026-11-10T16:00", 120))

    def test_vencidas_de_cualquier_prioridad_sin_terminadas_ni_archivadas(self):
        nombres = [t["name"] for t in self.agenda()["overdue"]]
        self.assertEqual(nombres, ["Vencida media"])

    def test_google_sin_conectar_no_es_error(self):
        payload = self.agenda()
        self.assertEqual(payload["google_events"], [])
        self.assertFalse(payload["google"]["connected"])

    def test_rango_de_dias_validado(self):
        for dias in (0, 8):
            payload, es_error = self.llamar("ver_agenda", {"desde": "2026-11-10", "dias": dias})
            self.assertTrue(es_error, dias)
            self.assertIn("1 y 7", payload)

    def test_fecha_mal_formada(self):
        payload, es_error = self.llamar("ver_agenda", {"desde": "10/11/2026"})
        self.assertTrue(es_error)
        self.assertIn("YYYY-MM-DD", payload)

    def test_sin_desde_usa_hoy(self):
        payload, es_error = self.llamar("ver_agenda")
        self.assertFalse(es_error, payload)
        import datetime
        self.assertEqual(payload["desde"], datetime.date.today().isoformat())
