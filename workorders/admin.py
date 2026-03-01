from django.contrib import admin
from .models import (
    WorkOrder, Owner, Vehicle, Mechanic,
    ComponentePredictivo, ParteMecanica, FacturaServicio,
)


@admin.register(Owner)
class OwnerAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'email', 'tipo_cliente')
    search_fields = ('nombre', 'email')
    list_filter = ('tipo_cliente',)


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('placa', 'marca', 'modelo', 'anio', 'km_actuales', 'propietario')
    list_filter = ('marca',)
    search_fields = ('placa', 'marca', 'modelo', 'vin')


@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'vehiculo', 'propietario', 'mecanico', 'estado', 'fecha_ingreso')
    list_filter = ('estado', 'fecha_ingreso')
    search_fields = ('vehiculo__placa', 'propietario__nombre', 'descripcion_problema')
    ordering = ('-fecha_ingreso',)


@admin.register(Mechanic)
class MechanicAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'especialidad', 'nivel', 'disponible', 'horas_pendientes', 'eficiencia')
    list_filter = ('especialidad', 'nivel', 'disponible')
    search_fields = ('nombre',)


@admin.register(ComponentePredictivo)
class ComponentePredictivoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'vehiculo', 'categoria', 'km_promedio_fallo', 'desviacion_estandar')
    list_filter = ('categoria', 'nombre')
    search_fields = ('nombre', 'vehiculo__placa')


@admin.register(ParteMecanica)
class ParteMecanicaAdmin(admin.ModelAdmin):
    list_display = ('codigo_oem', 'nombre', 'categoria', 'stock_actual', 'stock_minimo', 'precio_venta')
    list_filter = ('categoria',)
    search_fields = ('codigo_oem', 'nombre')


@admin.register(FacturaServicio)
class FacturaServicioAdmin(admin.ModelAdmin):
    list_display = ('id', 'orden_trabajo', 'propietario', 'total', 'estado', 'fecha_emision')
    list_filter = ('estado',)
    search_fields = ('propietario__nombre',)
