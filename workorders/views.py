from django.views import View
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from workorders.services.services import WorkOrderService
from workorders.models import Vehicle, Owner, WorkOrder

class CrearWorkOrderView(View):
    """Vista que maneja GET y POST para crear órdenes"""
    
    def get(self, request):
        """Muestra el formulario"""
        vehiculos = Vehicle.objects.all()
        propietarios = Owner.objects.all()
        ordenes = WorkOrder.objects.all().order_by('-fecha_ingreso')[:5]
        
        context = {
            'vehiculos': vehiculos,
            'propietarios': propietarios,
            'ordenes': ordenes
        }
        
        return render(request, 'workorders/crear_orden.html', context)
    
    def post(self, request):
        """Procesa la creación de orden"""
        datos = {
            'vehiculo_id': request.POST.get('vehiculo_id'),
            'propietario_id': request.POST.get('propietario_id'),
            'descripcion_problema': request.POST.get('descripcion_problema'),
            'odometer_km': int(request.POST.get('odometer_km', 0)),
            'especialidad_requerida': request.POST.get('especialidad', 'GENERAL')
        }
        
        try:
            # Llamar al Service
            service = WorkOrderService()
            work_order, predicciones = service.crear_work_order(datos)
            
            messages.success(request, f'✅ Orden #{work_order.id} creada exitosamente!')
            messages.info(request, f'🔧 Mecánico asignado: {work_order.mecanico.nombre}')
            
            # Mostrar predicciones
            for pred in predicciones:
                messages.warning(request, pred['mensaje'])
            
            return redirect('crear_orden')
            
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')
            return redirect('crear_orden')
