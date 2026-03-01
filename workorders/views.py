from django.views import View
from django.shortcuts import render, redirect
from django.contrib import messages
from workorders.services.services import WorkOrderService
from workorders.models import Owner


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
        service = WorkOrderService()
        context = {
            'vehiculos': service.listar_vehiculos(),
            'propietarios': service.listar_propietarios(orden='nombre'),
            'ordenes': service.listar_ordenes_recientes(),
        }
        return render(request, 'workorders/crear_orden.html', context)

    def post(self, request):
        datos = {
            'vehiculo_id': request.POST.get('vehiculo_id'),
            'propietario_id': request.POST.get('propietario_id'),
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
