"""
Comprehensive tests for SOL AI Django REST API.
Verifies:
1. Valid query (POST /api/query)
2. Empty query validation
3. Malformed JSON validation
4. Missing query & empty payload validation
5. Provider selection
6. Context input handling
7. LLM fallback cascade
8. Resource failure handling
9. Response schema (Pydantic SOLResponse validation)
10. CORS headers (GET, POST, OPTIONS)
11. 404 route JSON error
12. Backward-compatible route aliases (/health, /query)
"""

import os
import sys
import json
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parents[1]
sol_django_dir = project_root / "backend" / "sol_django"
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(sol_django_dir) not in sys.path:
    sys.path.insert(0, str(sol_django_dir))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sol_django.settings")

import django
django.setup()

from django.test import Client, SimpleTestCase
from backend.interpretation.schemas import SOLResponse
from backend.sol_django.api.services import SOLServiceRegistry


class TestDjangoAPI(SimpleTestCase):
    """Test suite for SOL AI Django API endpoints."""

    def setUp(self):
        self.client = Client()

    def test_01_health_endpoint(self):
        """GET /api/health and alias /health return 200 with status ok."""
        for path in ["/api/health", "/health"]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data.get("status"), "ok")

    def test_02_valid_query_mock_provider(self):
        """POST /api/query with valid query 'மரங்களில்' returns 200 with correct lemma and structure."""
        payload = {"query": "மரங்களில்", "provider": "mock"}
        response = self.client.post(
            "/api/query",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Validate against Pydantic SOLResponse schema
        sol_response = SOLResponse(**data)
        self.assertEqual(sol_response.query, "மரங்களில்")
        self.assertEqual(sol_response.lemma, "மரம்")
        self.assertTrue(len(sol_response.sources) > 0)
        self.assertIsNotNone(sol_response.morphology)
        self.assertIn(" ThamizhiMorph", [f" {s}" for s in sol_response.sources] + sol_response.sources)

    def test_03_query_with_context(self):
        """POST /api/query accepts and processes context parameter."""
        payload = {
            "query": "மரம்",
            "context": "தோட்டத்தில் ஒரு பெரிய மரம் உள்ளது.",
            "provider": "mock",
        }
        response = self.client.post(
            "/api/query",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        sol_response = SOLResponse(**data)
        self.assertEqual(sol_response.query, "மரம்")
        self.assertIsNotNone(sol_response.lemma)

    def test_04_empty_query_string(self):
        """POST /api/query with empty or whitespace query returns 400."""
        for empty_q in ["", "   ", None]:
            payload = {"query": empty_q, "provider": "mock"}
            response = self.client.post(
                "/api/query",
                data=json.dumps(payload),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 400)
            data = response.json()
            self.assertIn("error", data)
            self.assertEqual(data["error"], "Field 'query' is required and cannot be empty.")

    def test_05_missing_query_field(self):
        """POST /api/query with payload missing 'query' returns 400."""
        payload = {"provider": "mock"}
        response = self.client.post(
            "/api/query",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"], "Field 'query' is required and cannot be empty.")

    def test_06_empty_request_body(self):
        """POST /api/query with empty body returns 400."""
        response = self.client.post(
            "/api/query",
            data="",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)
        self.assertIn("Missing JSON payload", data["error"])

    def test_07_malformed_json_body(self):
        """POST /api/query with invalid JSON returns 400."""
        response = self.client.post(
            "/api/query",
            data="{query: not_valid_json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"], "Invalid JSON payload in request body.")

    def test_08_missing_gemini_api_key(self):
        """POST /api/query requesting gemini provider when GEMINI_API_KEY is not set returns 400."""
        old_key = os.environ.pop("GEMINI_API_KEY", None)
        try:
            payload = {"query": "மரங்களில்", "provider": "gemini"}
            response = self.client.post(
                "/api/query",
                data=json.dumps(payload),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 400)
            data = response.json()
            self.assertIn("error", data)
            self.assertIn("GEMINI_API_KEY", data["error"])
        finally:
            if old_key:
                os.environ["GEMINI_API_KEY"] = old_key

    def test_09_llm_fallback_cascade(self):
        """When primary interpreter fails, system falls back gracefully without 500 crash."""
        from backend.interpretation.interpreter import MockLLMInterpreter
        mock_real = MockLLMInterpreter()

        # Simulate failing primary interpreter
        mock_failing_interpreter = MagicMock()
        mock_failing_interpreter.interpret.side_effect = RuntimeError("Primary API Timeout")

        call_count = 0

        def side_effect(provider):
            nonlocal call_count
            call_count += 1
            if provider == "mock" and call_count > 1:
                # Return real mock only on fallback
                return mock_real
            return mock_failing_interpreter

        with patch("backend.interpretation.interpreter.get_interpreter", side_effect=side_effect):
            payload = {"query": "மரம்", "provider": "mock"}
            response = self.client.post(
                "/api/query",
                data=json.dumps(payload),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data.get("query"), "மரம்")
            self.assertIn(
                "AI Contextual Interpretation is currently unavailable due to high server load.",
                data.get("uncertainties", []),
            )

    def test_10_not_found_endpoint(self):
        """Unmapped routes return 404 with JSON error."""
        for path in ["/api/nonexistent", "/unknown/endpoint", "/api/query/extra"]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 404)
            data = response.json()
            self.assertIn("error", data)
            self.assertIn("Endpoint not found", data["error"])

    def test_11_cors_headers(self):
        """CORS headers are properly returned for cross-origin requests."""
        # Test OPTIONS preflight
        response = self.client.options(
            "/api/query",
            HTTP_ORIGIN="http://localhost:3000",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="content-type",
        )
        self.assertIn(response.status_code, [200, 204])
        self.assertIn("access-control-allow-origin", response.headers)

        # Test GET with Origin
        get_resp = self.client.get(
            "/api/health",
            HTTP_ORIGIN="http://localhost:3000",
        )
        self.assertEqual(get_resp.status_code, 200)
        self.assertIn("access-control-allow-origin", get_resp.headers)

    def test_12_root_query_alias(self):
        """POST /query (alias without /api) works identically."""
        payload = {"query": "மரம்", "provider": "mock"}
        response = self.client.post(
            "/query",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("query"), "மரம்")


if __name__ == "__main__":
    unittest.main()
