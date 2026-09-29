"""
Root URL configuration for SOL AI Django project.

Exposes:
- /api/health and /api/query (canonical endpoints)
- /health and /query (backward-compatible aliases)
- Custom JSON 404 handler for all unmatched endpoints
"""

from django.urls import path, include, re_path
from api import views

urlpatterns = [
    # Canonical API endpoints
    path('api/', include('api.urls')),

    # Backward compatibility aliases for legacy clients
    path('health', views.health_view, name='root-health-no-slash'),
    path('health/', views.health_view, name='root-health'),
    path('query', views.query_view, name='root-query-no-slash'),
    path('query/', views.query_view, name='root-query'),

    # Catch-all pattern to guarantee JSON 404 responses for any unmapped route
    re_path(r'^.*$', views.not_found_view, name='catch-all-404'),
]

handler404 = 'api.views.not_found_view'
