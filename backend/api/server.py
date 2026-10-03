"""
[DEPRECATED] SOL AI Legacy HTTP REST API Server.

WARNING: This module is deprecated as of Phase 1 / Step 1 of the architecture roadmap.
The primary API transport layer has migrated to Django (backend/sol_django).
This legacy server is retained strictly as a fallback reference and for parity verification.

To run the primary Django backend:
    python backend/sol_django/manage.py runserver 0.0.0.0:8000
"""

import os
import sys
import json
import argparse
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Optional

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Basic .env file loader
env_path = Path(__file__).resolve().parents[2] / ".env"
if env_path.exists():
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip().strip('"').strip("'")

from backend.retrieval.engine import RetrievalEngine
from backend.interpretation.evidence_pack import build_evidence_pack
from backend.interpretation.interpreter import get_interpreter


class SOLAPIRequestHandler(BaseHTTPRequestHandler):
    """
    HTTP Request Handler for SOL AI REST API.
    """

    # Lazy-loaded singleton RetrievalEngine instance
    _engine: Optional[RetrievalEngine] = None

    @classmethod
    def get_engine(cls) -> RetrievalEngine:
        if cls._engine is None:
            cls._engine = RetrievalEngine()
        return cls._engine

    def _send_json(self, status_code: int, data: Dict[str, Any]):
        try:
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, HEAD")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
            self.end_headers()
            response_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
            self.wfile.write(response_bytes)
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            # Client disconnected before the response could be sent
            pass

    def log_message(self, format: str, *args):
        # Override to suppress default verbose request logging in stdio
        pass

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, HEAD")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/")
        if path in ["/api/health", "/health"]:
            self._send_json(200, {"status": "ok"})
        else:
            self._send_json(404, {"error": f"Endpoint not found: {self.path}"})

    def do_POST(self):
        path = self.path.split("?")[0].rstrip("/")
        if path in ["/api/query", "/query"]:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                self._send_json(
                    400,
                    {"error": "Missing JSON payload. Request body must contain {'query': '<tamil_word>'}."}
                )
                return

            try:
                body_bytes = self.rfile.read(content_length)
                payload = json.loads(body_bytes.decode("utf-8"))
            except Exception:
                self._send_json(400, {"error": "Invalid JSON payload in request body."})
                return

            query = payload.get("query")
            if not query or not str(query).strip():
                self._send_json(400, {"error": "Field 'query' is required and cannot be empty."})
                return

            provider = payload.get("provider")
            context = payload.get("context")

            print(f"DEBUG: Incoming request payload: {ascii(payload)}")
            print(f"DEBUG: OS SOL_LLM_PROVIDER is: {ascii(os.environ.get('SOL_LLM_PROVIDER'))}")

            try:
                engine = self.get_engine()
                retrieval_result = engine.search(str(query).strip())
                pack = build_evidence_pack(retrieval_result, query_context=context)
                
                interpreter = get_interpreter(provider)
                
                try:
                    response = interpreter.interpret(pack)
                except Exception as primary_err:
                    print(f"Primary LLM Error: {primary_err}")
                    
                    provider = os.environ.get("SOL_LLM_PROVIDER", "mock").lower()
                    
                    if provider != "groq" and os.environ.get("GROQ_API_KEY"):
                        print("Attempting Groq fallback...")
                        try:
                            groq_interpreter = get_interpreter("groq")
                            response = groq_interpreter.interpret(pack)
                        except Exception as groq_err:
                            print(f"Groq Fallback Error: {groq_err}. Falling back to deterministic mock interpreter.")
                            fallback_interpreter = get_interpreter("mock")
                            response = fallback_interpreter.interpret(pack)
                            response.contextual_meaning = None
                            response.uncertainties.append("AI Contextual Interpretation is currently unavailable due to high server load.")
                    else:
                        print("Falling back to deterministic mock interpreter.")
                        fallback_interpreter = get_interpreter("mock")
                        response = fallback_interpreter.interpret(pack)
                        response.contextual_meaning = None
                        response.uncertainties.append("AI Contextual Interpretation is currently unavailable due to high server load.")
                
                # --- OVERRIDE LLM FALLIBILITY ---
                # The LLM often fails to accurately format or reproduce structural deterministic evidence. 
                # We inject the related words and literary context directly from the retrieval pack.
                
                # 1. Related Words
                rel_words = []
                for ev in pack.related_evidence:
                    if hasattr(ev, 'relations') and ev.relations:
                        for r in ev.relations:
                            if r not in rel_words:
                                rel_words.append(r)
                
                # Fallback heuristic: extract short words from dictionary meanings if empty (mimics MockLLM behavior)
                if not rel_words and response.meaning:
                    import re
                    parts = re.split(r'[,;]\s*', response.meaning)
                    for p in parts:
                        p = p.strip(' .')
                        is_tamil = bool(re.match(r'^[\u0B80-\u0BFF\s]+$', p))
                        if p and is_tamil and len(p.split()) <= 2 and len(p) > 2 and p != query:
                            if not any(char in p for char in ['(', ')', '[', ']', '"', "'"]):
                                if p not in rel_words:
                                    rel_words.append(p)

                if rel_words:
                    response.related_words = rel_words

                # 2. Literary Context
                from backend.interpretation.schemas import LiteraryContextItem
                lit_items = []
                for ev in pack.literary_evidence:
                    lit_items.append(
                        LiteraryContextItem(
                            work=ev.work or ev.metadata.get("source_text"),
                            author=ev.author,
                            period=ev.period or ev.metadata.get("period"),
                            passage=ev.passage or ev.metadata.get("classical_tamil"),
                            verse_number=str(ev.metadata.get("verse_number", ev.metadata.get("verse_id", ""))),
                            meaning=ev.meaning or ev.metadata.get("modern_tamil"),
                            source=ev.source or "Sentamizh",
                        )
                    )
                if lit_items:
                    response.literary_context = lit_items
                
                # 3. Morphology override
                if pack.morphology_evidence:
                    first_morph = pack.morphology_evidence[0]
                    fst_model = first_morph.metadata.get("fst_model", "unknown")
                    analysis_type = first_morph.metadata.get("analysis_type", "guesser" if "guess" in fst_model.lower() else "core")
                    response.morphology = {
                        "pos": getattr(first_morph, "pos", "Unknown"),
                        "fst_model": fst_model,
                        "analysis_type": analysis_type,
                        "raw_morphology": getattr(first_morph, "morphology", None)
                    }

                # 4. Senses synchronization
                if not getattr(response, "senses", None) and response.meaning:
                    from backend.interpretation.schemas import parse_senses_from_meaning_string
                    response.senses = parse_senses_from_meaning_string(
                        response.meaning, response.english_meaning
                    )

                self._send_json(200, response.model_dump())
            except ValueError as val_err:
                # Configuration error (e.g. GEMINI_API_KEY missing)
                self._send_json(400, {"error": str(val_err)})
            except Exception as err:
                # Unexpected error
                self._send_json(
                    500,
                    {"error": f"An error occurred while processing query '{query}': {str(err)}"}
                )
        else:
            self._send_json(404, {"error": f"Endpoint not found: {self.path}"})


def run_server(host: str = "0.0.0.0", port: int = 8000):
    print("\n" + "!" * 70)
    print("[DEPRECATION WARNING] Running legacy http.server (backend/api/server.py).")
    print("The production backend has migrated to Django: backend/sol_django")
    print("!" * 70 + "\n")
    server_address = (host, port)
    httpd = ThreadingHTTPServer(server_address, SOLAPIRequestHandler)
    print("Pre-warming SOL AI Retrieval Engine...")
    SOLAPIRequestHandler.get_engine()
    print(f"SOL AI REST API Server running at http://{host}:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down SOL AI REST API Server.")
        httpd.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SOL AI REST API Server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host address")
    parser.add_argument("--port", type=int, default=8000, help="Port number")
    args = parser.parse_args()
    run_server(host=args.host, port=args.port)
