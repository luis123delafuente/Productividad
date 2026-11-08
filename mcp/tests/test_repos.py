import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from pd_api import ApiError, NotFound
from repos import asociar_repo, proyecto_de_repo, raiz_repo

PROYECTOS = {
    1: {"id": 1, "name": "Activo", "is_archived": False},
    2: {"id": 2, "name": "Archivado", "is_archived": True},
}


def request(method, path, body=None):
    assert method == "GET"
    pid = int(path.rsplit("/", 1)[1])
    if pid not in PROYECTOS:
        raise NotFound(path)
    return PROYECTOS[pid]


class TestRepos(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name).resolve()
        self.repo = base / "mi-repo"
        (self.repo / "src" / "mod").mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.mapa = base / "conf" / "repo-map.json"

    def tearDown(self):
        self._tmp.cleanup()

    def test_asociar_y_resolver_desde_una_subcarpeta(self):
        resultado = asociar_repo(str(self.repo / "src"), 1, request, self.mapa)
        self.assertEqual(resultado["repo"], str(self.repo))
        self.assertEqual(json.loads(self.mapa.read_text()), {str(self.repo): 1})
        encontrado = proyecto_de_repo(str(self.repo / "src" / "mod"), request, self.mapa)
        self.assertEqual(encontrado["project"], {"id": 1, "name": "Activo"})

    def test_sin_asociacion(self):
        self.assertIsNone(proyecto_de_repo(str(self.repo), request, self.mapa)["project"])

    def test_asociar_a_proyecto_archivado_o_inexistente_es_error(self):
        with self.assertRaisesRegex(ApiError, "archivado"):
            asociar_repo(str(self.repo), 2, request, self.mapa)
        with self.assertRaisesRegex(ApiError, "no existe"):
            asociar_repo(str(self.repo), 99, request, self.mapa)
        self.assertFalse(self.mapa.exists())

    def test_mapa_que_apunta_a_archivado_o_inexistente_es_null(self):
        self.mapa.parent.mkdir(parents=True)
        for pid in (2, 99):
            with self.subTest(pid):
                self.mapa.write_text(json.dumps({str(self.repo): pid}))
                resultado = proyecto_de_repo(str(self.repo), request, self.mapa)
                self.assertIsNone(resultado["project"])
                self.assertIn(f"#{pid}", resultado["nota"])

    def test_conserva_otras_asociaciones(self):
        self.mapa.parent.mkdir(parents=True)
        self.mapa.write_text(json.dumps({"/otro/repo": 7}))
        asociar_repo(str(self.repo), 1, request, self.mapa)
        self.assertEqual(json.loads(self.mapa.read_text()), {"/otro/repo": 7, str(self.repo): 1})

    def test_carpeta_que_no_es_repo_usa_la_propia_ruta(self):
        suelta = Path(self._tmp.name).resolve() / "no-git"
        suelta.mkdir()
        self.assertEqual(raiz_repo(str(suelta)), str(suelta))

    def test_ruta_inexistente(self):
        with self.assertRaisesRegex(ApiError, "no existe"):
            raiz_repo("/no/existe/de/verdad")
