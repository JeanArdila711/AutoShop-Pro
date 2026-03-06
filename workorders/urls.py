from django.urls import path
from django.http import JsonResponse
from workorders.views import (
    DashboardView,
    CrearWorkOrderView,
    RegistrarPropietarioView,
    RegistrarVehiculoView,
    RegistrarMecanicoView,
)


def ping(request):
    return JsonResponse({"ok": True, "app": "workorders"})


urlpatterns = [
    # ── Rutas HTML (SSR) ──
    path("", DashboardView.as_view(), name='dashboard'),
    path("ping/", ping),
    path("crear/", CrearWorkOrderView.as_view(), name='crear_orden'),
    path("propietarios/", RegistrarPropietarioView.as_view(), name='registrar_propietario'),
    path("vehiculos/", RegistrarVehiculoView.as_view(), name='registrar_vehiculo'),
    path("mecanicos/", RegistrarMecanicoView.as_view(), name='registrar_mecanico'),
]
