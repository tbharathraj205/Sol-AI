"""
HTTP Controllers and Views for SOL AI REST API.

Provides:
- GET  /api/health (and /health)
- POST /api/query  (and /query)
- 404 handler returning JSON error

All application/domain logic is delegated to SOLServiceRegistry in services.py.
Views handle only HTTP transport, request validation, status codes, and serialization.
"""

import json
import logging
from typing import Any, Dict

from django.http import HttpRequest, JsonResponse, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .services import SOLServiceRegistry

logger = logging.getLogger(__name__)


def _json_response(data: Dict[str, Any], status: int = 200) -> JsonResponse:
    """Standardized JSON response helper preserving utf-8 and indentation."""
    return JsonResponse(
        data,
        status=status,
        safe=False,
        json_dumps_params={"ensure_ascii": False, "indent": 2},
    )


@csrf_exempt
@require_http_methods(["GET", "HEAD"])
def health_view(request: HttpRequest) -> JsonResponse:
    """
    Health check endpoint.
    GET /api/health or GET /health
    """
    return _json_response({"status": "ok"}, status=200)


@csrf_exempt
def query_view(request: HttpRequest) -> JsonResponse:
    """
    Main query endpoint for linguistic and contextual evidence.
    POST /api/query or POST /query
    """
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    # 1. Validate request body exists
    if not request.body or len(request.body.strip()) == 0:
        return _json_response(
            {"error": "Missing JSON payload. Request body must contain {'query': '<tamil_word>'}."},
            status=400,
        )

    # 2. Parse JSON
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return _json_response(
            {"error": "Invalid JSON payload in request body."},
            status=400,
        )

    if not isinstance(payload, dict):
        return _json_response(
            {"error": "Invalid JSON payload in request body."},
            status=400,
        )

    # 3. Validate query parameter
    query = payload.get("query")
    if not query or not str(query).strip():
        return _json_response(
            {"error": "Field 'query' is required and cannot be empty."},
            status=400,
        )

    provider = payload.get("provider")
    context = payload.get("context")

    # 4. Delegate execution to domain service
    try:
        service = SOLServiceRegistry.get_instance()
        response = service.process_query(
            query=str(query),
            provider=provider,
            context=context,
        )
        return _json_response(response.model_dump(), status=200)
    except ValueError as val_err:
        # Configuration errors (e.g. missing API key for requested provider)
        return _json_response({"error": str(val_err)}, status=400)
    except Exception as err:
        # Unhandled execution errors
        logger.exception("Error processing query '%s'", query)
        return _json_response(
            {"error": f"An error occurred while processing query '{query}': {str(err)}"},
            status=500,
        )


def not_found_view(request: HttpRequest, exception=None) -> JsonResponse:
    """
    JSON 404 handler for invalid routes, matching legacy server.py behavior.
    """
    return _json_response(
        {"error": f"Endpoint not found: {request.get_full_path()}"},
        status=404,
    )
