from django.contrib import admin
from .models import WorkOrder, Owner, Vehicle, Mechanic, ComponentePredictivo

@admin.register(Owner)
class OwnerAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')
    search_fields = ('nombre',)

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('placa', 'marca', 'modelo', 'anio', 'km_actuales', 'propietario')
    list_filter = ('marca',)
    search_fields = ('placa', 'marca', 'modelo')

@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'vehiculo', 'propietario', 'mecanico', 'estado', 'fecha_ingreso')
    list_filter = ('estado', 'fecha_ingreso')
    search_fields = ('vehiculo__placa', 'propietario__nombre', 'descripcion_problema')
    ordering = ('-fecha_ingreso',)

@admin.register(Mechanic)
class MechanicAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'especialidad', 'nivel', 'disponible', 'horas_pendientes')
    list_filter = ('especialidad', 'nivel', 'disponible')
    search_fields = ('nombre',)

@admin.register(ComponentePredictivo)
class ComponentePredictivoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'vehiculo', 'km_promedio_fallo', 'desviacion_estandar')
    list_filter = ('nombre',)
    search_fields = ('nombre', 'vehiculo__placa')
