from django.views import View
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from workorders.services.services import WorkOrderService
from workorders.models import Owner, CategoriaComponente
import json


class LandingPageView(View):
    """Landing page pública — primera impresión del taller"""

    def get(self, request):
        return render(request, 'workorders/landing.html')

class DashboardView(View):
    """Vista principal: coordina HTTP para el dashboard"""

    def get(self, request):
        service = WorkOrderService()
        context = service.obtener_estadisticas_dashboard()
        return render(request, 'workorders/dashboard.html', context)


class RegistrarPropietarioView(View):
    """Vista para registrar propietarios — solo coordina HTTP"""

    def get(self, request):
        service = WorkOrderService()
        context = {
            'propietarios': service.listar_propietarios(),
        }
        return render(request, 'workorders/registrar_propietario.html', context)

    def post(self, request):
        datos = {
            'nombre': request.POST.get('nombre', '').strip(),
            'email': request.POST.get('email', '').strip(),
            'telefono': request.POST.get('telefono', '').strip(),
            'tipo_cliente': request.POST.get('tipo_cliente', 'REGULAR'),
        }
        try:
            service = WorkOrderService()
            propietario = service.registrar_propietario(datos)
            messages.success(request, f'✅ Propietario "{propietario.nombre}" registrado (ID: {propietario.id})')
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')
        return redirect('registrar_propietario')


class RegistrarVehiculoView(View):
    """Vista para registrar vehículos — solo coordina HTTP"""

    def get(self, request):
        service = WorkOrderService()
        context = {
            'propietarios': service.listar_propietarios(orden='nombre'),
            'vehiculos': service.listar_vehiculos(),
        }
        return render(request, 'workorders/registrar_vehiculo.html', context)

    def post(self, request):
        datos = {
            'placa': request.POST.get('placa', '').strip().upper(),
            'vin': request.POST.get('vin', '').strip(),
            'marca': request.POST.get('marca', '').strip(),
            'modelo': request.POST.get('modelo', '').strip(),
            'anio': int(request.POST.get('anio', 2024)),
            'km_actuales': int(request.POST.get('km_actuales', 0)),
            'propietario_id': request.POST.get('propietario_id'),
        }
        try:
            service = WorkOrderService()
            vehiculo = service.registrar_vehiculo(datos)
            messages.success(request, f'✅ Vehículo "{vehiculo.placa}" registrado (ID: {vehiculo.id})')
        except Owner.DoesNotExist:
            messages.error(request, '❌ Propietario no encontrado')
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')
        return redirect('registrar_vehiculo')


class RegistrarMecanicoView(View):
    """Vista para registrar mecánicos — solo coordina HTTP"""

    def get(self, request):
        service = WorkOrderService()
        context = {
            'mecanicos': service.listar_mecanicos(),
        }
        return render(request, 'workorders/registrar_mecanico.html', context)

    def post(self, request):
        datos = {
            'nombre': request.POST.get('nombre', '').strip(),
            'especialidad': request.POST.get('especialidad', 'GENERAL'),
            'nivel': request.POST.get('nivel', 'JUNIOR'),
            'tarifa_hora': float(request.POST.get('tarifa_hora', 0)),
        }
        try:
            service = WorkOrderService()
            mecanico = service.registrar_mecanico(datos)
            messages.success(request, f'✅ Mecánico "{mecanico.nombre}" registrado (ID: {mecanico.id})')
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')
        return redirect('registrar_mecanico')


class CrearWorkOrderView(View):
    """Vista que maneja GET y POST para crear órdenes — solo coordina HTTP"""

    def get(self, request):
        import json
        from workorders.models import TRANSICIONES_VALIDAS
        service = WorkOrderService()
        context = {
            'vehiculos': service.listar_vehiculos(),
            'propietarios': service.listar_propietarios(orden='nombre'),
            'ordenes': service.listar_ordenes_recientes(),
            'transiciones_json': json.dumps(TRANSICIONES_VALIDAS),
        }
        return render(request, 'workorders/crear_orden.html', context)

    def post(self, request):
        datos = {
            'vehiculo_id': request.POST.get('vehiculo_id'),
            'descripcion_problema': request.POST.get('descripcion_problema'),
            'odometer_km': int(request.POST.get('odometer_km', 0)),
            'especialidad_requerida': request.POST.get('especialidad', 'GENERAL')
        }

        try:
            service = WorkOrderService()
            work_order, predicciones = service.crear_work_order(datos)

            messages.success(request, f'✅ Orden #{work_order.id} creada exitosamente!')
            messages.info(request, f'🔧 Mecánico asignado: {work_order.mecanico.nombre}')

            for pred in predicciones:
                messages.warning(request, pred['mensaje'])

            return redirect('crear_orden')

        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')
            return redirect('crear_orden')


class CambiarEstadoOrdenView(View):
    """Vista para cambiar el estado de una orden de trabajo"""

    def post(self, request, orden_id):
        nuevo_estado = request.POST.get('nuevo_estado')
        try:
            service = WorkOrderService()
            orden = service.cambiar_estado_orden(orden_id, nuevo_estado)
            messages.success(request, f'✅ Estado de orden #{orden.id} actualizado a {orden.estado}')
        except Exception as e:
            messages.error(request, f'❌ Error al cambiar estado: {str(e)}')
        return redirect('crear_orden')


class PredictivoDashboardView(View):
    """Vista del dashboard de mantenimiento predictivo"""

    def get(self, request):
        service = WorkOrderService()
        context = service.obtener_resumen_predictivo()
        context['vehiculos'] = service.listar_vehiculos(orden='marca')
        return render(request, 'workorders/predictivo_dashboard.html', context)


class GestionarComponentesView(View):
    """Vista para gestionar componentes predictivos de un vehículo"""

    def get(self, request, vehiculo_id):
        service = WorkOrderService()
        vehiculo, componentes = service.obtener_componentes_vehiculo(vehiculo_id)
        context = {
            'vehiculo': vehiculo,
            'componentes': componentes,
            'categorias': CategoriaComponente.choices,
        }
        return render(request, 'workorders/gestionar_componentes.html', context)

    def post(self, request, vehiculo_id):
        datos = {
            'vehiculo_id': vehiculo_id,
            'nombre': request.POST.get('nombre', '').strip(),
            'categoria': request.POST.get('categoria', 'GENERAL'),
            'km_promedio_fallo': request.POST.get('km_promedio_fallo', 0),
            'desviacion_estandar': request.POST.get('desviacion_estandar', 1000),
            'costo_promedio': request.POST.get('costo_promedio', 0),
        }
        try:
            service = WorkOrderService()
            comp = service.agregar_componente_predictivo(datos)
            messages.success(request, f'✅ Componente "{comp.nombre}" añadido correctamente')
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')
        return redirect('gestionar_componentes', vehiculo_id=vehiculo_id)


class KanbanView(View):
    """Tablero Kanban de órdenes — drag & drop entre estados"""

    def get(self, request):
        service = WorkOrderService()
        context = service.obtener_kanban()
        return render(request, 'workorders/kanban.html', context)


@method_decorator(csrf_exempt, name='dispatch')
class KanbanMoverAPIView(View):
    """Endpoint AJAX para mover orden entre estados desde el Kanban"""

    def post(self, request):
        try:
            payload = json.loads(request.body.decode('utf-8'))
            orden_id = payload['orden_id']
            nuevo_estado = payload['nuevo_estado']
            service = WorkOrderService()
            orden = service.cambiar_estado_orden(orden_id, nuevo_estado)
            return JsonResponse({'ok': True, 'estado': orden.estado})
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)}, status=400)


class BahiasView(View):
    """Gestión de bahías del taller"""

    def get(self, request):
        service = WorkOrderService()
        context = {
            'bahias': service.listar_bahias(),
            'ordenes_libres': service.listar_ordenes_recientes(limite=50),
        }
        return render(request, 'workorders/bahias.html', context)

    def post(self, request):
        accion = request.POST.get('accion', 'crear')
        service = WorkOrderService()
        try:
            if accion == 'crear':
                service.registrar_bahia({
                    'codigo': request.POST.get('codigo', '').strip(),
                    'nombre': request.POST.get('nombre', '').strip(),
                    'tipo': request.POST.get('tipo', 'GENERAL'),
                })
                messages.success(request, '✅ Bahía creada')
            elif accion == 'asignar':
                service.asignar_bahia(
                    request.POST.get('bahia_id'),
                    request.POST.get('orden_id'),
                )
                messages.success(request, '✅ Orden asignada a bahía')
            elif accion == 'liberar':
                service.liberar_bahia(request.POST.get('bahia_id'))
                messages.success(request, '✅ Bahía liberada')
        except Exception as e:
            messages.error(request, f'❌ {str(e)}')
        return redirect('bahias')


class OrdenDetalleView(View):
    """Panel operativo de una orden: timer, checklist, fotos"""

    def get(self, request, orden_id):
        service = WorkOrderService()
        context = service.obtener_detalle_orden(orden_id)
        context['categorias'] = CategoriaComponente.choices
        return render(request, 'workorders/orden_detalle.html', context)


@method_decorator(csrf_exempt, name='dispatch')
class TimerAPIView(View):
    """Iniciar/detener timer de una orden"""

    def post(self, request, orden_id):
        service = WorkOrderService()
        try:
            data = json.loads(request.body.decode('utf-8') or '{}')
            accion = data.get('accion', 'iniciar')
            if accion == 'iniciar':
                t = service.iniciar_timer(orden_id, data.get('nota', ''))
                return JsonResponse({'ok': True, 'timer_id': t.id, 'inicio': t.inicio.isoformat()})
            else:
                t = service.detener_timer(orden_id)
                return JsonResponse({'ok': True, 'duracion_horas': t.duracion_horas()})
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)}, status=400)


class CrearChecklistView(View):
    def post(self, request, orden_id):
        try:
            service = WorkOrderService()
            service.crear_checklist(orden_id, request.POST.get('categoria', 'GENERAL'))
            messages.success(request, '✅ Checklist creado')
        except Exception as e:
            messages.error(request, f'❌ {str(e)}')
        return redirect('orden_detalle', orden_id=orden_id)


@method_decorator(csrf_exempt, name='dispatch')
class ChecklistItemAPIView(View):
    def post(self, request, item_id):
        try:
            data = json.loads(request.body.decode('utf-8'))
            service = WorkOrderService()
            item = service.actualizar_item_checklist(
                item_id, data.get('estado', 'OK'), data.get('nota', ''),
            )
            return JsonResponse({'ok': True, 'estado': item.estado})
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)}, status=400)


class SubirEvidenciaView(View):
    def post(self, request, orden_id):
        try:
            imagen = request.FILES.get('imagen')
            if not imagen:
                raise ValueError("Falta archivo de imagen")
            service = WorkOrderService()
            service.subir_evidencia(
                orden_id, imagen,
                momento=request.POST.get('momento', 'ANTES'),
                descripcion=request.POST.get('descripcion', ''),
            )
            messages.success(request, '✅ Evidencia subida')
        except Exception as e:
            messages.error(request, f'❌ {str(e)}')
        return redirect('orden_detalle', orden_id=orden_id)


class EliminarEvidenciaView(View):
    def post(self, request, evidencia_id):
        orden_id = request.POST.get('orden_id')
        try:
            WorkOrderService().eliminar_evidencia(evidencia_id)
            messages.success(request, '✅ Evidencia eliminada')
        except Exception as e:
            messages.error(request, f'❌ {str(e)}')
        return redirect('orden_detalle', orden_id=orden_id)


class EliminarComponenteView(View):
    """Vista para eliminar un componente predictivo"""

    def post(self, request, comp_id):
        vehiculo_id = request.POST.get('vehiculo_id')
        try:
            service = WorkOrderService()
            service.eliminar_componente_predictivo(comp_id)
            messages.success(request, '✅ Componente eliminado')
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')

        if vehiculo_id:
            return redirect('gestionar_componentes', vehiculo_id=vehiculo_id)
        return redirect('predictivo_dashboard')
