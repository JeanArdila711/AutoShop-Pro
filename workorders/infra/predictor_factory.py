import os
from abc import ABC, abstractmethod

class PredictorInterface(ABC):
    @abstractmethod
    def obtener_predicciones(self, vehiculo):
        pass

class PredictorReal(PredictorInterface):
    def obtener_predicciones(self, vehiculo):
        from workorders.models import ComponentePredictivo
        
        componentes = ComponentePredictivo.objects.filter(vehiculo=vehiculo)
        
        alertas = []
        for comp in componentes:
            diferencia = comp.km_promedio_fallo - vehiculo.km_actuales
            prob = max(0, min(1, 1 - (diferencia / (comp.desviacion_estandar * 2))))
            
            if prob > 0.4:
                urgencia = 'ALTA' if prob > 0.7 else 'MEDIA'
                alertas.append({
                    'componente': comp.nombre,
                    'probabilidad': round(prob * 100, 1),
                    'urgencia': urgencia,
                    'mensaje': f"⚠️ {urgencia}: {comp.nombre} prob {prob*100:.0f}%"
                })
        
        return alertas

class PredictorMock(PredictorInterface):
    def obtener_predicciones(self, vehiculo):
        print(f"[MOCK] Predicciones para {vehiculo.placa}")
        return [
            {
                'componente': 'Bomba Gasolina (MOCK)',
                'probabilidad': 65.0,
                'urgencia': 'MEDIA',
                'mensaje': '⚠️ MEDIA: Bomba Gasolina prob 65% (MOCK)'
            },
            {
                'componente': 'Pastillas Freno (MOCK)',
                'probabilidad': 85.0,
                'urgencia': 'ALTA',
                'mensaje': '⚠️ ALTA: Pastillas Freno prob 85% (MOCK)'
            }
        ]

class PredictorFactory:
    @staticmethod
    def crear_predictor():
        env_type = os.getenv('ENV_TYPE', 'DEV')
        
        if env_type == 'PROD':
            print("[Factory] Usando PredictorReal")
            return PredictorReal()
        else:
            print("[Factory] Usando PredictorMock")
            return PredictorMock()
