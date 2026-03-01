from django.urls import path
from django.http import JsonResponse
from workorders.views import CrearWorkOrderView
from workorders.api_views import CrearOrdenAPIView


def ping(request):
    return JsonResponse({"ok": True, "app": "workorders"})


urlpatterns = [
    # ── Rutas HTML (SSR) ──
    path("ping/", ping),
    path("crear/", CrearWorkOrderView.as_view(), name='crear_orden'),

    # ── Rutas API (DRF) ──
    path("api/ordenes/", CrearOrdenAPIView.as_view(), name='api_crear_orden'),
]
