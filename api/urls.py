# ─────────────────────────────────────────────────────────────
# api/urls.py
# Rutas de la API REST (DRF)
# ─────────────────────────────────────────────────────────────

from django.urls import path
from api.views import CrearOrdenAPIView

urlpatterns = [
    path("ordenes/", CrearOrdenAPIView.as_view(), name='api_crear_orden'),
]
