# ─────────────────────────────────────────────────────────────
# workorders/serializers.py
# Serializers de DRF: solo validan SINTAXIS (tipos, campos requeridos).
# La SEMÁNTICA / NEGOCIO se valida en el Service Layer.
# ─────────────────────────────────────────────────────────────

from rest_framework import serializers


class OrdenTrabajoInputSerializer(serializers.Serializer):
    """
    Serializer de ENTRADA para crear una Orden de Trabajo.
    Valida sintaxis: tipos de dato, campos obligatorios, largo mínimo.
    NO hace consultas a la BD — eso corresponde al Service.
    """
    vehiculo_id = serializers.IntegerField(
        required=True,
        help_text="ID del vehículo registrado",
    )
    propietario_id = serializers.IntegerField(
        required=True,
        help_text="ID del propietario del vehículo",
    )
    descripcion_problema = serializers.CharField(
        required=True,
        min_length=10,
        help_text="Descripción del problema (mín. 10 caracteres)",
    )
    odometer_km = serializers.IntegerField(
        required=True,
        min_value=0,
        help_text="Kilometraje actual del vehículo",
    )
    especialidad_requerida = serializers.ChoiceField(
        choices=['MOTOR', 'TRANSMISION', 'SUSPENSION', 'ELECTRICO', 'GENERAL'],
        required=False,
        default='GENERAL',
        help_text="Especialidad mecánica requerida",
    )


class OrdenTrabajoOutputSerializer(serializers.Serializer):
    """
    Serializer de SALIDA para representar la orden creada.
    Formatea la respuesta JSON con datos anidados.
    """
    id = serializers.IntegerField()
    vehiculo = serializers.SerializerMethodField()
    propietario = serializers.SerializerMethodField()
    mecanico = serializers.SerializerMethodField()
    estado = serializers.CharField()
    fecha_ingreso = serializers.DateTimeField()
    descripcion_problema = serializers.CharField()
    odometer_km = serializers.IntegerField()
    predicciones = serializers.ListField(child=serializers.DictField(), default=[])

    def get_vehiculo(self, obj):
        """Serializa los datos básicos del vehículo"""
        v = obj.vehiculo
        return {
            'id': v.id,
            'placa': v.placa,
            'marca': v.marca,
            'modelo': v.modelo,
            'anio': v.anio,
        }

    def get_propietario(self, obj):
        """Serializa los datos básicos del propietario"""
        p = obj.propietario
        return {
            'id': p.id,
            'nombre': p.nombre,
            'email': p.email,
            'tipo_cliente': p.tipo_cliente,
        }

    def get_mecanico(self, obj):
        """Serializa los datos del mecánico asignado"""
        m = obj.mecanico
        if m is None:
            return None
        return {
            'id': m.id,
            'nombre': m.nombre,
            'especialidad': m.especialidad,
            'nivel': m.nivel,
        }
