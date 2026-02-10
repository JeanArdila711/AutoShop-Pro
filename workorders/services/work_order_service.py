from workorders.domain.work_order_builder import WorkOrderBuilder
from workorders.infra.predictor_factory import PredictorFactory
from workorders.models import Mechanic, Vehicle

class WorkOrderService:
    def __init__(self, predictor=None):
        self.predictor = predictor or PredictorFactory.crear_predictor()
    
    def crear_work_order(self, datos):
        vehiculo = Vehicle.objects.get(id=datos['vehiculo_id'])
        predicciones = self.predictor.obtener_predicciones(vehiculo)
        especialidad = datos.get('especialidad_requerida', 'GENERAL')
        mecanico = self._asignar_mejor_mecanico(especialidad)
        
        work_order = (WorkOrderBuilder()
                      .para_vehiculo(datos['vehiculo_id'])
                      .del_propietario(datos['propietario_id'])
                      .con_problema(datos['descripcion_problema'])
                      .con_kilometraje(datos['odometer_km'])
                      .asignar_mecanico(mecanico)
                      .build())
        
        work_order.save()
        
        tiempo = self._estimar_tiempo(datos['descripcion_problema'])
        mecanico.horas_pendientes += tiempo
        mecanico.disponible = mecanico.horas_pendientes < 40
        mecanico.save()
        
        return work_order, predicciones
    
    def _asignar_mejor_mecanico(self, especialidad_requerida):
        mecanicos = Mechanic.objects.filter(disponible=True)
        
        if not mecanicos.exists():
            raise ValueError("No hay mecánicos disponibles")
        
        mejor = None
        mejor_score = 0
        
        for mec in mecanicos:
            score = 0
            
            if mec.especialidad == especialidad_requerida:
                score += 30
            elif mec.especialidad == 'GENERAL':
                score += 15
            
            score += 20 * (1 - mec.horas_pendientes / 40)
            
            if mec.nivel == 'EXPERTO':
                score += 10
            
            if score > mejor_score:
                mejor_score = score
                mejor = mec
        
        return mejor
    
    def _estimar_tiempo(self, descripcion):
        desc = descripcion.lower()
        
        if 'aceite' in desc or 'filtro' in desc:
            return 1
        elif 'transmision' in desc:
            return 8
        elif 'motor' in desc:
            return 6
        elif 'frenos' in desc:
            return 2
        else:
            return 3
