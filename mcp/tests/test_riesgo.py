import unittest

from riesgo import efecto_google_fecha, motivos_cambio, motivos_creacion, par_efectivo

SIN_HORA = {"project_id": 1, "due_date": "2026-11-12", "due_time": None, "google_event_id": None}
CON_HORA = {"project_id": 1, "due_date": "2026-11-12", "due_time": "10:00:00", "google_event_id": "ev1"}
HEREDADA = {"project_id": 1, "due_date": "2026-11-12", "due_time": None, "google_event_id": "ev-todo-el-dia"}
SIN_FECHA = {"project_id": 1, "due_date": None, "due_time": None, "google_event_id": None}
SUELTA = {"project_id": None, "due_date": None, "due_time": None, "google_event_id": None}


class TestAfectaGoogle(unittest.TestCase):
    CASOS = [
        # (nombre, actual, cambio, afecta)
        ("sin hora -> otra fecha sin hora", SIN_HORA, {"due_date": "2026-11-20"}, False),
        ("sin hora -> con hora", SIN_HORA, {"due_time": "16:00"}, True),
        ("sin fecha -> fecha y hora", SIN_FECHA, {"due_date": "2026-11-20", "due_time": "09:00"}, True),
        ("con hora -> otra hora", CON_HORA, {"due_time": "11:00"}, True),
        ("con hora -> solo fecha, hora omitida (ejemplo 4)", CON_HORA, {"due_date": "2026-11-19"}, True),
        ("con hora -> quitar fecha", CON_HORA, {"due_date": None}, True),
        ("con hora -> quitar hora", CON_HORA, {"due_time": None}, True),
        ("solo fecha -> quitar fecha", SIN_HORA, {"due_date": None}, False),
        ("evento heredado de todo el dia -> otra fecha", HEREDADA, {"due_date": "2026-11-13"}, True),
        ("mismo valor con hora", CON_HORA, {"due_date": "2026-11-12", "due_time": "10:00"}, False),
        ("mismo valor sin hora", SIN_HORA, {"due_date": "2026-11-12"}, False),
        ("no toca fechas", CON_HORA, {"priority": "Alta"}, False),
    ]

    def test_tabla(self):
        for nombre, actual, cambio, afecta in self.CASOS:
            with self.subTest(nombre):
                self.assertEqual(efecto_google_fecha(actual, cambio) is not None, afecta)

    def test_textos_del_efecto(self):
        self.assertIn("mueve", efecto_google_fecha(CON_HORA, {"due_date": "2026-11-19"}))
        self.assertIn("19 10:00", efecto_google_fecha(CON_HORA, {"due_date": "2026-11-19"}))
        self.assertIn("crea", efecto_google_fecha(SIN_HORA, {"due_time": "16:00"}))
        self.assertIn("borra", efecto_google_fecha(CON_HORA, {"due_date": None}))

    def test_par_efectivo_quitar_fecha_se_lleva_la_hora(self):
        self.assertEqual(par_efectivo(CON_HORA, {"due_date": None}), (None, None))


class TestMotivos(unittest.TestCase):
    def test_quitar_de_hoy_suelta_requiere_confirmacion(self):
        motivos = motivos_cambio(SUELTA, {"in_today": False})
        self.assertEqual(len(motivos), 1)
        self.assertIn("borra la tarea suelta", motivos[0])

    def test_quitar_de_hoy_con_proyecto_es_directo(self):
        self.assertEqual(motivos_cambio(SIN_HORA, {"in_today": False}), [])

    def test_anadir_a_hoy_suelta_es_directo(self):
        self.assertEqual(motivos_cambio(SUELTA, {"in_today": True}), [])

    def test_cambios_directos(self):
        for cambio in ({"name": "x"}, {"status": "Terminado"}, {"planned_start": "2026-11-10T16:00"}, {"project_id": 2}):
            with self.subTest(cambio):
                self.assertEqual(motivos_cambio(CON_HORA, cambio), [])

    def test_crear_con_fecha_y_hora(self):
        self.assertTrue(motivos_creacion({"due_date": "2026-11-12", "due_time": "10:30"}))
        self.assertEqual(motivos_creacion({"due_date": "2026-11-12"}), [])
        self.assertEqual(motivos_creacion({"due_date": "2026-11-12", "due_time": None}), [])
