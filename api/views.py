# ─────────────────────────────────────────────────────────────
# api/views.py
# API Views JSON: actúan como "porteros".
# Reciben JSON → validan sintaxis → llaman al Service → retornan Response.
# NO contienen lógica de negocio.
# ─────────────────────────────────────────────────────────────

import json

from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from api.serializers import OrdenTrabajoInputSerializer, OrdenTrabajoOutputSerializer
from workorders.services.services import WorkOrderService
from workorders.models import Vehicle, Owner


class CrearOrdenAPIView(APIView):
    """
    POST /api/v1/ordenes/
    Crea una nueva orden de trabajo.

    Códigos de respuesta:
      201 — Orden creada exitosamente
      400 — Datos de entrada inválidos (sintaxis)
      404 — Vehículo o propietario no encontrado
      409 — Conflicto (ej: no hay mecánicos disponibles)
    """

    def post(self, request):
        input_serializer = OrdenTrabajoInputSerializer(data=request.data)
        if not input_serializer.is_valid():
            return Response(
                {'error': 'Datos de entrada inválidos', 'detalle': input_serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        datos_validados = input_serializer.validated_data

        try:
            service = WorkOrderService()
            work_order, predicciones = service.crear_work_order(datos_validados)

            output_data = OrdenTrabajoOutputSerializer(work_order).data
            output_data['predicciones'] = predicciones

            return Response(output_data, status=status.HTTP_201_CREATED)

        except Vehicle.DoesNotExist:
            return Response(
                {'error': f"Vehículo con id={datos_validados['vehiculo_id']} no encontrado"},
                status=status.HTTP_404_NOT_FOUND,
            )

        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_409_CONFLICT,
            )


class AsignacionPreviewAPIView(View):
    """GET /api/v1/asignacion/preview/?especialidad=MOTOR"""

    def get(self, request):
        esp = request.GET.get('especialidad', 'GENERAL')
        service = WorkOrderService()
        res = service.preview_mejor_mecanico(esp)
        if res is None:
            return JsonResponse({'ok': False, 'error': 'No hay mecánicos disponibles'}, status=200)
        m = res['mecanico']
        return JsonResponse({
            'ok': True,
            'nombre': m.nombre,
            'especialidad': m.especialidad,
            'nivel': m.nivel,
            'carga_horas': m.horas_pendientes,
            'score': res['score'],
        })


@method_decorator(csrf_exempt, name='dispatch')
class KanbanMoverAPIView(View):
    """POST /api/v1/kanban/mover/ — mover orden entre estados"""

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


@method_decorator(csrf_exempt, name='dispatch')
class TimerAPIView(View):
    """POST /api/v1/orden/<id>/timer/ — iniciar/detener timer"""

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


@method_decorator(csrf_exempt, name='dispatch')
class ChecklistItemAPIView(View):
    """POST /api/v1/checklist/item/<id>/ — actualizar estado de ítem"""

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
