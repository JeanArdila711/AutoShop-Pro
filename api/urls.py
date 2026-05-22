# ─────────────────────────────────────────────────────────────
# api/urls.py
# Rutas de la API REST — todos los endpoints JSON del proyecto
# ─────────────────────────────────────────────────────────────

from django.urls import path
from api.views import (
    CrearOrdenAPIView,
    AsignacionPreviewAPIView,
    KanbanMoverAPIView,
    TimerAPIView,
    ChecklistItemAPIView,
)

urlpatterns = [
    path("ordenes/", CrearOrdenAPIView.as_view(), name='api_crear_orden'),
    path("asignacion/preview/", AsignacionPreviewAPIView.as_view(), name='asignacion_preview'),
    path("kanban/mover/", KanbanMoverAPIView.as_view(), name='kanban_mover'),
    path("orden/<int:orden_id>/timer/", TimerAPIView.as_view(), name='orden_timer'),
    path("checklist/item/<int:item_id>/", ChecklistItemAPIView.as_view(), name='checklist_item'),
]
