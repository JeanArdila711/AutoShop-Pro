# ─────────────────────────────────────────────────────────────
# workorders/api_views.py
# API Views de DRF: actúan como "porteros".
# Reciben JSON → validan sintaxis → llaman al Service → retornan Response.
# NO contienen lógica de negocio.
# ─────────────────────────────────────────────────────────────

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from workorders.serializers import OrdenTrabajoInputSerializer, OrdenTrabajoOutputSerializer
from workorders.services.services import WorkOrderService
from workorders.models import Vehicle, Owner


class CrearOrdenAPIView(APIView):
    """
    POST /workorders/api/ordenes/
    Crea una nueva orden de trabajo.

    Códigos de respuesta:
      201 — Orden creada exitosamente
      400 — Datos de entrada inválidos (sintaxis)
      404 — Vehículo o propietario no encontrado
      409 — Conflicto (ej: no hay mecánicos disponibles)
    """

    def post(self, request):
        # 1. Validar sintaxis con el Serializer
        input_serializer = OrdenTrabajoInputSerializer(data=request.data)
        if not input_serializer.is_valid():
            return Response(
                {'error': 'Datos de entrada inválidos', 'detalle': input_serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        datos_validados = input_serializer.validated_data

        try:
            # 2. Delegar toda la lógica al Service Layer
            service = WorkOrderService()
            work_order, predicciones = service.crear_work_order(datos_validados)

            # 3. Serializar la salida
            output_data = OrdenTrabajoOutputSerializer(work_order).data
            output_data['predicciones'] = predicciones

            return Response(output_data, status=status.HTTP_201_CREATED)

        except Vehicle.DoesNotExist:
            return Response(
                {'error': f"Vehículo con id={datos_validados['vehiculo_id']} no encontrado"},
                status=status.HTTP_404_NOT_FOUND,
            )

        except Owner.DoesNotExist:
            return Response(
                {'error': f"Propietario con id={datos_validados['propietario_id']} no encontrado"},
                status=status.HTTP_404_NOT_FOUND,
            )

        except ValueError as e:
            # Conflictos de negocio: mecánico no disponible, validaciones del builder, etc.
            return Response(
                {'error': str(e)},
                status=status.HTTP_409_CONFLICT,
            )
