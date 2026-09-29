"""
URL configuration for SOL AI API application.
"""

from django.urls import path
from . import views

urlpatterns = [
    path('health', views.health_view, name='api-health-no-slash'),
    path('health/', views.health_view, name='api-health'),
    path('query', views.query_view, name='api-query-no-slash'),
    path('query/', views.query_view, name='api-query'),
]
