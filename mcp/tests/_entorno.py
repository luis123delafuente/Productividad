"""Entorno de integración: backend real con SQLite temporal + servidor MCP por stdio.

Nunca toca localhost:8000, backend/data/app.db ni Google: el backend se arranca en
un puerto libre con DATABASE_URL apuntando a un directorio temporal (la copia de
seguridad del arranque también va ahí) y con Google sin conectar.

Uso:
    class MiTest(EntornoIntegracion):
        def test_algo(self):
            proyecto = self.api("POST", "/projects", {...})
            resultado = self.llamar("listar_proyectos")
"""

import json
import os
import select
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
BACKEND = RAIZ / "backend"
PYTHON_BACKEND = BACKEND / ".venv" / "bin" / "python"
SERVIDOR_MCP = RAIZ / "mcp" / "server.py"
TIEMPO_MAXIMO_RESPUESTA = 30


def _puerto_libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class ClienteMCP:
    """Habla JSON-RPC por stdio con mcp/server.py lanzado con el intérprete actual."""

    def __init__(self, api_url):
        env = dict(os.environ, PRODUCTIVIDAD_API_URL=api_url)
        self.proceso = subprocess.Popen(
            [sys.executable, str(SERVIDOR_MCP)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        self._id = 0

    def enviar(self, method, params=None):
        self._id += 1
        mensaje = {"jsonrpc": "2.0", "id": self._id, "method": method, "params": params or {}}
        self.proceso.stdin.write(json.dumps(mensaje) + "\n")
        self.proceso.stdin.flush()
        listos, _, _ = select.select([self.proceso.stdout], [], [], TIEMPO_MAXIMO_RESPUESTA)
        if not listos:
            self.proceso.kill()
            raise RuntimeError(
                f"El servidor MCP no respondió a {method!r} en {TIEMPO_MAXIMO_RESPUESTA}s. stderr: "
                + self.proceso.stderr.read()
            )
        linea = self.proceso.stdout.readline()
        if not linea:
            raise RuntimeError("El servidor MCP se cerró: " + self.proceso.stderr.read())
        return json.loads(linea)

    def notificar(self, method):
        self.proceso.stdin.write(json.dumps({"jsonrpc": "2.0", "method": method}) + "\n")
        self.proceso.stdin.flush()

    def cerrar(self):
        if not self.proceso.stdin.closed:
            self.proceso.stdin.close()
        try:
            self.proceso.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proceso.kill()
            self.proceso.wait()
        self.proceso.stdout.close()
        self.proceso.stderr.close()


@unittest.skipUnless(
    PYTHON_BACKEND.exists(),
    f"Tests de integración omitidos: no existe {PYTHON_BACKEND} (crea el venv del backend).",
)
class EntornoIntegracion(unittest.TestCase):
    """Un backend temporal por clase de test; un cliente MCP por test."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.mkdtemp(prefix="productividad-mcp-test-")
        puerto = _puerto_libre()
        cls.api_url = f"http://127.0.0.1:{puerto}/api"
        env = dict(os.environ, DATABASE_URL=f"sqlite:///{cls._tmp}/app.db")
        cls._log = open(Path(cls._tmp) / "backend.log", "w")
        cls._backend = subprocess.Popen(
            [str(PYTHON_BACKEND), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(puerto)],
            cwd=str(BACKEND),
            env=env,
            stdout=cls._log,
            stderr=subprocess.STDOUT,
        )
        limite = time.monotonic() + 30
        while time.monotonic() < limite:
            if cls._backend.poll() is not None:
                break
            try:
                urllib.request.urlopen(cls.api_url + "/health", timeout=1)
                return
            except (urllib.error.URLError, ConnectionError):
                time.sleep(0.2)
        cls.tearDownClass()
        raise RuntimeError("El backend temporal no arrancó; mira " + str(Path(cls._tmp) / "backend.log"))

    @classmethod
    def tearDownClass(cls):
        cls._backend.terminate()
        try:
            cls._backend.wait(timeout=10)
        except subprocess.TimeoutExpired:
            cls._backend.kill()
        cls._log.close()
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def setUp(self):
        self.mcp = ClienteMCP(self.api_url)
        respuesta = self.mcp.enviar("initialize", {"protocolVersion": "2025-11-25", "capabilities": {}})
        self.assertIn("result", respuesta)
        self.mcp.notificar("notifications/initialized")

    def tearDown(self):
        self.mcp.cerrar()

    # --- utilidades ---

    def api(self, method, path, body=None):
        """Llamada directa a la API temporal, para preparar y comprobar datos."""
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            self.api_url + path, data=data, method=method, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as respuesta:
            raw = respuesta.read()
            return json.loads(raw) if raw else None

    def llamar(self, herramienta, argumentos=None):
        """Llama a una herramienta y devuelve (payload_json_o_texto, is_error)."""
        respuesta = self.mcp.enviar("tools/call", {"name": herramienta, "arguments": argumentos or {}})
        self.assertIn("result", respuesta, respuesta)
        resultado = respuesta["result"]
        texto = resultado["content"][0]["text"]
        try:
            payload = json.loads(texto)
        except ValueError:
            payload = texto
        return payload, resultado.get("isError", False)
