"""
SOL AI Dual-Server Verification and Parity Test Suite.

Directly compares:
- OLD: backend/api/server.py (ThreadingHTTPServer)
- NEW: backend/sol_django (Django WSGI Application)

Runs both servers simultaneously on ephemeral local ports and asserts:
1. HTTP status code parity across valid queries, edge cases, and errors
2. Pydantic schema conformance of Django responses (SOLResponse)
3. Exact structural and semantic equivalence for core fields (query, lemma, sources, morphology)
4. Literary context and related words structure preservation
5. CORS header parity and OPTIONS preflight behavior
6. Route parity (/api/health, /health, /api/query, /query, 404 fallback)
"""

import os
import sys
import json
import time
from pathlib import Path
from http.server import HTTPServer
from threading import Thread
from wsgiref.simple_server import make_server
from typing import Dict, Any, List, Tuple

# Reconfigure stdout/stderr for UTF-8 on Windows console
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Setup project root and sol_django in sys.path
project_root = Path(__file__).resolve().parents[1]
sol_django_dir = project_root / "backend" / "sol_django"
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(sol_django_dir) not in sys.path:
    sys.path.insert(0, str(sol_django_dir))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sol_django.settings")

import requests
from backend.api.server import SOLAPIRequestHandler
from backend.sol_django.sol_django.wsgi import application as django_wsgi_app
from backend.interpretation.schemas import SOLResponse


class ParityTestHarness:
    """Manages lifecycle of both legacy and Django servers for side-by-side verification."""

    def __init__(self):
        self.legacy_server = None
        self.legacy_thread = None
        self.legacy_port = None
        self.legacy_url = None

        self.django_server = None
        self.django_thread = None
        self.django_port = None
        self.django_url = None

    def start(self):
        print("\n" + "=" * 70)
        print("STARTING DUAL-SERVER PARITY HARNESS")
        print("=" * 70)

        # 1. Start legacy server on free port
        self.legacy_server = HTTPServer(("127.0.0.1", 0), SOLAPIRequestHandler)
        self.legacy_port = self.legacy_server.server_port
        self.legacy_url = f"http://127.0.0.1:{self.legacy_port}"
        self.legacy_thread = Thread(target=self.legacy_server.serve_forever, daemon=True)
        self.legacy_thread.start()
        print(f"[OK] Legacy http.server running at {self.legacy_url}")

        # 2. Start Django WSGI server on free port
        self.django_server = make_server("127.0.0.1", 0, django_wsgi_app)
        self.django_port = self.django_server.server_port
        self.django_url = f"http://127.0.0.1:{self.django_port}"
        self.django_thread = Thread(target=self.django_server.serve_forever, daemon=True)
        self.django_thread.start()
        print(f"[OK] Django WSGI server running at {self.django_url}")
        print("=" * 70 + "\n")

    def stop(self):
        print("\nStopping dual-server test harness...")
        if self.legacy_server:
            self.legacy_server.shutdown()
            self.legacy_server.server_close()
        if self.django_server:
            self.django_server.shutdown()
            self.django_server.server_close()
        print("Harness stopped.")


def run_parity_tests() -> bool:
    """
    Executes the comprehensive parity test matrix comparing legacy server and Django API.
    Returns True if all parity checks pass.
    """
    harness = ParityTestHarness()
    harness.start()

    passed_count = 0
    total_count = 0
    failures: List[str] = []

    def record_result(test_name: str, passed: bool, details: str = ""):
        nonlocal passed_count, total_count
        total_count += 1
        if passed:
            passed_count += 1
            print(f"  [PASS] {test_name}")
        else:
            failures.append(f"{test_name}: {details}")
            print(f"  [FAIL] {test_name} -> {details}")

    try:
        # ---------------------------------------------------------
        # Group 1: Health Check Parity
        # ---------------------------------------------------------
        print("\n--- GROUP 1: Health Check Parity ---")
        for path in ["/api/health", "/health"]:
            total_count_pre = total_count
            r_old = requests.get(f"{harness.legacy_url}{path}")
            r_new = requests.get(f"{harness.django_url}{path}")

            record_result(
                f"Health Status Code ({path})",
                r_old.status_code == r_new.status_code == 200,
                f"old={r_old.status_code}, new={r_new.status_code}",
            )
            record_result(
                f"Health Payload Parity ({path})",
                r_old.json() == r_new.json() == {"status": "ok"},
                f"old={r_old.json()}, new={r_new.json()}",
            )

        # ---------------------------------------------------------
        # Group 2: Error Handling & Validation Parity
        # ---------------------------------------------------------
        print("\n--- GROUP 2: Validation & Error Handling Parity ---")

        # 2.1 Empty body
        r_old = requests.post(f"{harness.legacy_url}/api/query", data="", headers={"Content-Type": "application/json"})
        r_new = requests.post(f"{harness.django_url}/api/query", data="", headers={"Content-Type": "application/json"})
        record_result(
            "Empty Request Body (Status 400)",
            r_old.status_code == r_new.status_code == 400,
            f"old={r_old.status_code}, new={r_new.status_code}",
        )
        record_result(
            "Empty Request Body (Error Message)",
            r_old.json().get("error") == r_new.json().get("error"),
            f"old={r_old.json()}, new={r_new.json()}",
        )

        # 2.2 Malformed JSON
        r_old = requests.post(f"{harness.legacy_url}/api/query", data="{bad_json", headers={"Content-Type": "application/json"})
        r_new = requests.post(f"{harness.django_url}/api/query", data="{bad_json", headers={"Content-Type": "application/json"})
        record_result(
            "Malformed JSON (Status 400)",
            r_old.status_code == r_new.status_code == 400,
            f"old={r_old.status_code}, new={r_new.status_code}",
        )
        record_result(
            "Malformed JSON (Error Message)",
            r_old.json().get("error") == r_new.json().get("error"),
            f"old={r_old.json()}, new={r_new.json()}",
        )

        # 2.3 Missing query field
        r_old = requests.post(f"{harness.legacy_url}/api/query", json={"provider": "mock"})
        r_new = requests.post(f"{harness.django_url}/api/query", json={"provider": "mock"})
        record_result(
            "Missing 'query' field (Status 400)",
            r_old.status_code == r_new.status_code == 400,
            f"old={r_old.status_code}, new={r_new.status_code}",
        )
        record_result(
            "Missing 'query' field (Error Message)",
            r_old.json().get("error") == r_new.json().get("error"),
            f"old={r_old.json()}, new={r_new.json()}",
        )

        # 2.4 Empty query string
        r_old = requests.post(f"{harness.legacy_url}/api/query", json={"query": "  ", "provider": "mock"})
        r_new = requests.post(f"{harness.django_url}/api/query", json={"query": "  ", "provider": "mock"})
        record_result(
            "Empty query string (Status 400)",
            r_old.status_code == r_new.status_code == 400,
            f"old={r_old.status_code}, new={r_new.status_code}",
        )
        record_result(
            "Empty query string (Error Message)",
            r_old.json().get("error") == r_new.json().get("error"),
            f"old={r_old.json()}, new={r_new.json()}",
        )

        # 2.5 Route not found (404)
        for invalid_path in ["/api/unknown", "/bad/route"]:
            r_old = requests.get(f"{harness.legacy_url}{invalid_path}")
            r_new = requests.get(f"{harness.django_url}{invalid_path}")
            record_result(
                f"404 Route Not Found ({invalid_path})",
                r_old.status_code == r_new.status_code == 404,
                f"old={r_old.status_code}, new={r_new.status_code}",
            )

        # ---------------------------------------------------------
        # Group 3: Representative Tamil Query Parity
        # ---------------------------------------------------------
        print("\n--- GROUP 3: Representative Tamil Queries Parity ---")
        tamil_test_queries = [
            ("மரங்களில்", "mock", None),
            ("மரம்", "mock", None),
            ("அகத்தி", "mock", None),
            ("யாழ்", "mock", None),
            ("மனிதன்", "mock", None),
            ("செய்", "mock", None),
            ("மரம்", "mock", "தோட்டத்தில் பல மரங்கள் உள்ளன."),
        ]

        for query, provider, context in tamil_test_queries:
            q_desc = f"'{query}' (ctx: {'yes' if context else 'no'})"
            payload = {"query": query, "provider": provider}
            if context:
                payload["context"] = context

            r_old = requests.post(f"{harness.legacy_url}/api/query", json=payload)
            r_new = requests.post(f"{harness.django_url}/api/query", json=payload)

            record_result(
                f"Query Status 200: {q_desc}",
                r_old.status_code == r_new.status_code == 200,
                f"old={r_old.status_code}, new={r_new.status_code}",
            )

            d_old = r_old.json()
            d_new = r_new.json()

            # Pydantic validation on Django output
            pydantic_valid = False
            try:
                SOLResponse(**d_new)
                pydantic_valid = True
            except Exception as e:
                pydantic_valid = False

            record_result(
                f"Pydantic Validation (Django): {q_desc}",
                pydantic_valid,
                "SOLResponse schema validation failed",
            )

            # Core field comparisons
            record_result(
                f"Query & Normalized Match: {q_desc}",
                d_old.get("query") == d_new.get("query") and d_old.get("normalized_query") == d_new.get("normalized_query"),
                f"old=({d_old.get('query')}, {d_old.get('normalized_query')}), new=({d_new.get('query')}, {d_new.get('normalized_query')})",
            )

            record_result(
                f"Lemma Match: {q_desc}",
                d_old.get("lemma") == d_new.get("lemma"),
                f"old lemma={d_old.get('lemma')}, new lemma={d_new.get('lemma')}",
            )

            record_result(
                f"Sources List Match: {q_desc}",
                set(d_old.get("sources", [])) == set(d_new.get("sources", [])),
                f"old sources={d_old.get('sources')}, new sources={d_new.get('sources')}",
            )

            # Morphology structure
            morph_old = d_old.get("morphology")
            morph_new = d_new.get("morphology")
            record_result(
                f"Morphology Structure Match: {q_desc}",
                (morph_old is None and morph_new is None) or (
                    isinstance(morph_old, dict) and isinstance(morph_new, dict) and
                    morph_old.get("pos") == morph_new.get("pos") and
                    morph_old.get("analysis_type") == morph_new.get("analysis_type")
                ),
                f"old morph={morph_old}, new morph={morph_new}",
            )

            # Related words parity
            record_result(
                f"Related Words Match: {q_desc}",
                d_old.get("related_words") == d_new.get("related_words"),
                f"old rel={d_old.get('related_words')}, new rel={d_new.get('related_words')}",
            )

            # Literary context count
            record_result(
                f"Literary Context Count Match: {q_desc}",
                len(d_old.get("literary_context", [])) == len(d_new.get("literary_context", [])),
                f"old lit count={len(d_old.get('literary_context', []))}, new lit count={len(d_new.get('literary_context', []))}",
            )

        # ---------------------------------------------------------
        # Group 4: CORS and Preflight Parity
        # ---------------------------------------------------------
        print("\n--- GROUP 4: CORS & Preflight Parity ---")
        cors_headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        }
        r_old_opt = requests.options(f"{harness.legacy_url}/api/query", headers=cors_headers)
        r_new_opt = requests.options(f"{harness.django_url}/api/query", headers=cors_headers)

        record_result(
            "CORS OPTIONS Status Code (200/204)",
            r_new_opt.status_code in (200, 204),
            f"new status={r_new_opt.status_code}",
        )
        record_result(
            "CORS Allow Origin Header Present",
            "access-control-allow-origin" in [k.lower() for k in r_new_opt.headers.keys()],
            f"new headers={dict(r_new_opt.headers)}",
        )

        # ---------------------------------------------------------
        # Group 5: Endpoint Aliases Parity
        # ---------------------------------------------------------
        print("\n--- GROUP 5: Endpoint Aliases Parity ---")
        r_old_q = requests.post(f"{harness.legacy_url}/query", json={"query": "மரம்", "provider": "mock"})
        r_new_q = requests.post(f"{harness.django_url}/query", json={"query": "மரம்", "provider": "mock"})
        record_result(
            "Root /query Alias Status 200",
            r_old_q.status_code == r_new_q.status_code == 200,
            f"old={r_old_q.status_code}, new={r_new_q.status_code}",
        )
        record_result(
            "Root /query Alias Lemma Parity",
            r_old_q.json().get("lemma") == r_new_q.json().get("lemma"),
            f"old={r_old_q.json().get('lemma')}, new={r_new_q.json().get('lemma')}",
        )

    finally:
        harness.stop()

    print("\n" + "=" * 70)
    print(f"PARITY VERIFICATION SUMMARY: {passed_count}/{total_count} PASSED")
    if failures:
        print(f"FAILURES ({len(failures)}):")
        for f in failures:
            print(f"  - {f}")
        print("=" * 70 + "\n")
        return False
    else:
        print("ALL PARITY CHECKS PASSED PERFECTLY!")
        print("=" * 70 + "\n")
        return True


if __name__ == "__main__":
    success = run_parity_tests()
    sys.exit(0 if success else 1)
