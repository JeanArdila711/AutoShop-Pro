from workorders.models import WorkOrder, Vehicle, Owner
from django.utils import timezone

class WorkOrderBuilder:
    """Builder: Construye WorkOrder paso a paso validando"""
    
    def __init__(self):
        self._vehiculo = None
        self._propietario = None
        self._mecanico = None
        self._descripcion_problema = ""
        self._odometer_km = 0
    
    def para_vehiculo(self, vehiculo_id):
        try:
            self._vehiculo = Vehicle.objects.get(id=vehiculo_id)
        except Vehicle.DoesNotExist:
            raise ValueError(f"Vehículo {vehiculo_id} no existe")
        return self
    
    def del_propietario(self, propietario_id):
        try:
            self._propietario = Owner.objects.get(id=propietario_id)
        except Owner.DoesNotExist:
            raise ValueError(f"Propietario {propietario_id} no existe")
        return self
    
    def con_problema(self, descripcion):
        if not descripcion or len(descripcion) < 10:
            raise ValueError("Descripción debe tener mínimo 10 caracteres")
        self._descripcion_problema = descripcion
        return self
    
    def con_kilometraje(self, km):
        if km < 0:
            raise ValueError("Kilometraje no puede ser negativo")
        self._odometer_km = km
        return self
    
    def asignar_mecanico(self, mecanico):
        if mecanico is None:
            raise ValueError("Mecánico no puede ser None")
        self._mecanico = mecanico
        return self
    
    def build(self):
        """Construye y valida. NO guarda en BD"""
        if not self._vehiculo:
            raise ValueError("Falta vehículo")
        if not self._propietario:
            raise ValueError("Falta propietario")
        if not self._mecanico:
            raise ValueError("Falta mecánico")
        if not self._descripcion_problema:
            raise ValueError("Falta problema")
        if self._odometer_km == 0:
            raise ValueError("Falta kilometraje")
        
        work_order = WorkOrder(
            vehiculo=self._vehiculo,
            propietario=self._propietario,
            mecanico=self._mecanico,
            estado='ABIERTA',
            fecha_ingreso=timezone.now(),
            descripcion_problema=self._descripcion_problema,
            odometer_km=self._odometer_km
        )
        
        return work_order
