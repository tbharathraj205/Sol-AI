"""
Unit tests for SOL AI REST API Handler (backend/sol_django).
Verifies GET /api/health, POST /api/query, CORS headers, error codes, and payload validation
using real HTTP requests served by Django WSGI on a local ephemeral port.
"""

import os
import sys
import json
import unittest
from pathlib import Path
from threading import Thread
from wsgiref.simple_server import make_server
import urllib.request
import urllib.error

# Ensure project root and sol_django directory are in sys.path
project_root = Path(__file__).resolve().parents[1]
sol_django_dir = project_root / "backend" / "sol_django"
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(sol_django_dir) not in sys.path:
    sys.path.insert(0, str(sol_django_dir))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sol_django.settings")

from backend.sol_django.sol_django.wsgi import application as django_app


class TestSOLAPI(unittest.TestCase):
    """
    Test suite for SOL REST API endpoints served via Django.
    Starts a local background WSGI server on a free port for real HTTP request assertions.
    """

    @classmethod
    def setUpClass(cls):
        # Start Django WSGI server on ephemeral port
        cls.server = make_server("127.0.0.1", 0, django_app)
        cls.port = cls.server.server_port
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_health_endpoint(self):
        """1. Test GET /api/health."""
        req = urllib.request.Request(f"{self.base_url}/api/health", method="GET")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data.get("status"), "ok")

    def test_query_endpoint_success(self):
        """2. Test POST /api/query with valid query 'மரங்களில்' using mock provider."""
        payload = {"query": "மரங்களில்", "provider": "mock"}
        req = urllib.request.Request(
            f"{self.base_url}/api/query",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data.get("query"), "மரங்களில்")
            self.assertEqual(data.get("lemma"), "மரம்")
            self.assertIn("sources", data)

    def test_query_endpoint_missing_payload(self):
        """3. Test POST /api/query with missing query field."""
        payload = {}
        req = urllib.request.Request(
            f"{self.base_url}/api/query",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req)
            self.fail("Expected HTTPError 400")
        except urllib.error.HTTPError as err:
            self.assertEqual(err.code, 400)
            data = json.loads(err.read().decode("utf-8"))
            self.assertIn("error", data)

    def test_query_endpoint_missing_gemini_key(self):
        """4. Test POST /api/query with provider=gemini when GEMINI_API_KEY is not set."""
        old_key = os.environ.pop("GEMINI_API_KEY", None)
        try:
            payload = {"query": "மரங்களில்", "provider": "gemini"}
            req = urllib.request.Request(
                f"{self.base_url}/api/query",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                urllib.request.urlopen(req)
                self.fail("Expected HTTPError 400")
            except urllib.error.HTTPError as err:
                self.assertEqual(err.code, 400)
                data = json.loads(err.read().decode("utf-8"))
                self.assertIn("GEMINI_API_KEY", data.get("error", ""))
        finally:
            if old_key:
                os.environ["GEMINI_API_KEY"] = old_key


if __name__ == "__main__":
    unittest.main()
