from django.urls import path
from django.http import JsonResponse
from workorders.views import (
    DashboardView,
    CrearWorkOrderView,
    RegistrarPropietarioView,
    RegistrarVehiculoView,
    RegistrarMecanicoView,
    CambiarEstadoOrdenView,
    PredictivoDashboardView,
    GestionarComponentesView,
    EliminarComponenteView,
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
    path("orden/<int:orden_id>/cambiar-estado/", CambiarEstadoOrdenView.as_view(), name='cambiar_estado_orden'),
    # ── Predictivo ──
    path("predictivo/", PredictivoDashboardView.as_view(), name='predictivo_dashboard'),
    path("predictivo/vehiculo/<int:vehiculo_id>/", GestionarComponentesView.as_view(), name='gestionar_componentes'),
    path("predictivo/componente/<int:comp_id>/eliminar/", EliminarComponenteView.as_view(), name='eliminar_componente'),
]
