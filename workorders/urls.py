from django.urls import path
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
    KanbanView,
    BahiasView,
    OrdenDetalleView,
    CrearChecklistView,
    SubirEvidenciaView,
    EliminarEvidenciaView,
)

urlpatterns = [
    # ── Rutas HTML (SSR) ──
    path("", DashboardView.as_view(), name='dashboard'),
    path("crear/", CrearWorkOrderView.as_view(), name='crear_orden'),
    path("propietarios/", RegistrarPropietarioView.as_view(), name='registrar_propietario'),
    path("vehiculos/", RegistrarVehiculoView.as_view(), name='registrar_vehiculo'),
    path("mecanicos/", RegistrarMecanicoView.as_view(), name='registrar_mecanico'),
    path("orden/<int:orden_id>/cambiar-estado/", CambiarEstadoOrdenView.as_view(), name='cambiar_estado_orden'),

    # ── Operación taller (vistas HTML) ──
    path("kanban/", KanbanView.as_view(), name='kanban'),
    path("bahias/", BahiasView.as_view(), name='bahias'),
    path("orden/<int:orden_id>/", OrdenDetalleView.as_view(), name='orden_detalle'),
    path("orden/<int:orden_id>/checklist/", CrearChecklistView.as_view(), name='orden_crear_checklist'),
    path("orden/<int:orden_id>/evidencia/", SubirEvidenciaView.as_view(), name='subir_evidencia'),
    path("evidencia/<int:evidencia_id>/eliminar/", EliminarEvidenciaView.as_view(), name='eliminar_evidencia'),

    # ── Predictivo ──
    path("predictivo/", PredictivoDashboardView.as_view(), name='predictivo_dashboard'),
    path("predictivo/vehiculo/<int:vehiculo_id>/", GestionarComponentesView.as_view(), name='gestionar_componentes'),
    path("predictivo/componente/<int:comp_id>/eliminar/", EliminarComponenteView.as_view(), name='eliminar_componente'),
]
