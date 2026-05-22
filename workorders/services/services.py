# ─────────────────────────────────────────────────────────────
# workorders/services/services.py
# Service Layer: orquesta TODA la lógica de negocio.
# Es independiente de la capa de presentación — lo llaman
# tanto la View HTML como la APIView de DRF.
# ─────────────────────────────────────────────────────────────

from workorders.domain.work_order_builder import WorkOrderBuilder
from workorders.infra.predictor_factory import PredictorFactory
from workorders.infra.notificacion_factory import NotificacionFactory
from workorders.models import Mechanic, Vehicle, Owner, WorkOrder


class WorkOrderService:
    """
    Servicio principal del taller.
    Centraliza TODA la lógica de negocio (SRP).
    Dependencias inyectables: predictor y notificador (DIP).
    """

    def __init__(self, predictor=None, notificador=None):
        # Inyección de dependencias con valores por defecto vía Factories
        self.predictor = predictor or PredictorFactory.crear_predictor()
        self.notificador = notificador or NotificacionFactory.crear_notificador()

    # ─────────────────────────────────────────────
    # Dashboard
    # ─────────────────────────────────────────────

    def obtener_estadisticas_dashboard(self):
        """Retorna las estadísticas y órdenes recientes para el dashboard"""
        from workorders.models import ComponentePredictivo

        alertas_criticas = 0
        for comp in ComponentePredictivo.objects.select_related('vehiculo').all():
            if comp.calcular_probabilidad_fallo(comp.vehiculo.km_actuales) > 0.7:
                alertas_criticas += 1

        return {
            'total_propietarios': Owner.objects.count(),
            'total_vehiculos': Vehicle.objects.count(),
            'total_mecanicos': Mechanic.objects.count(),
            'total_ordenes': WorkOrder.objects.count(),
            'alertas_criticas': alertas_criticas,
            'ordenes': WorkOrder.objects.all().order_by('-fecha_ingreso')[:10],
        }

    # ─────────────────────────────────────────────
    # Propietarios
    # ─────────────────────────────────────────────

    def listar_propietarios(self, orden='-id'):
        """Retorna todos los propietarios ordenados"""
        return Owner.objects.all().order_by(orden)

    def registrar_propietario(self, datos):
        """Crea y retorna un nuevo propietario"""
        propietario = Owner.objects.create(
            nombre=datos['nombre'],
            email=datos['email'],
            telefono=datos['telefono'],
            tipo_cliente=datos.get('tipo_cliente', 'REGULAR'),
        )
        return propietario

    # ─────────────────────────────────────────────
    # Vehículos
    # ─────────────────────────────────────────────

    def listar_vehiculos(self, orden='-id'):
        """Retorna todos los vehículos ordenados"""
        return Vehicle.objects.all().order_by(orden)

    def registrar_vehiculo(self, datos):
        """Crea y retorna un nuevo vehículo asociado a un propietario"""
        propietario = Owner.objects.get(id=datos['propietario_id'])
        
        vehiculo = Vehicle(
            placa=datos['placa'].upper(),
            vin=datos.get('vin', ''),
            marca=datos['marca'],
            modelo=datos['modelo'],
            anio=int(datos.get('anio', 2024)),
            km_actuales=int(datos.get('km_actuales', 0)),
            propietario=propietario,
        )
    
        vehiculo.full_clean()  # ← dispara el RegexValidator de la placa
        vehiculo.save()
        return vehiculo


    # ─────────────────────────────────────────────
    # Mecánicos
    # ─────────────────────────────────────────────

    def listar_mecanicos(self, orden='-id'):
        """Retorna todos los mecánicos ordenados"""
        return Mechanic.objects.all().order_by(orden)

    def registrar_mecanico(self, datos):
        """Crea y retorna un nuevo mecánico"""
        mecanico = Mechanic.objects.create(
            nombre=datos['nombre'],
            especialidad=datos.get('especialidad', 'GENERAL'),
            nivel=datos.get('nivel', 'JUNIOR'),
            tarifa_hora=datos.get('tarifa_hora', 0),
        )
        return mecanico

    # ─────────────────────────────────────────────
    # Órdenes de Trabajo
    # ─────────────────────────────────────────────

    def listar_ordenes_recientes(self, limite=5):
        """Retorna las órdenes más recientes"""
        return WorkOrder.objects.all().order_by('-fecha_ingreso')[:limite]

    def crear_work_order(self, datos):
        """
        Orquesta la creación de una orden de trabajo:
        1. Obtener vehículo y predicciones
        2. Asignar el mejor mecánico disponible
        3. Construir la orden con el Builder
        4. Guardar, actualizar carga del mecánico
        5. Notificar al propietario
        """
        # 1. Obtener entidades y predicciones
        vehiculo = Vehicle.objects.get(id=datos['vehiculo_id'])
        propietario = vehiculo.propietario
        predicciones = self.predictor.obtener_predicciones(vehiculo)

        # 2. Asignar mecánico
        especialidad = datos.get('especialidad_requerida', 'GENERAL')
        mecanico = self._asignar_mejor_mecanico(especialidad)

        # 3. Construir la orden con el Builder (Fluent Interface)
        work_order = (
            WorkOrderBuilder()
            .para_vehiculo(datos['vehiculo_id'])
            .del_propietario(propietario.id)
            .con_problema(datos['descripcion_problema'])
            .con_kilometraje(datos['odometer_km'])
            .asignar_mecanico(mecanico)
            .build()
        )

        # 4. Persistir la orden y actualizar carga del mecánico
        work_order.save()

        tiempo = self._estimar_tiempo(datos['descripcion_problema'])
        mecanico.horas_pendientes += tiempo
        mecanico.disponible = mecanico.horas_pendientes < 40
        mecanico.save()

        # 5. Notificar al propietario
        self.notificador.enviar(
            destinatario=propietario.nombre,
            asunto=f"Orden de Trabajo #{work_order.id} creada",
            mensaje=(
                f"Su vehículo {vehiculo.placa} ha ingresado al taller. "
                f"Mecánico asignado: {mecanico.nombre}."
            ),
        )

        return work_order, predicciones

    def cambiar_estado_orden(self, orden_id, nuevo_estado):
        """Cambia el estado de una orden de trabajo si la transición es válida"""
        orden = WorkOrder.objects.get(id=orden_id)
        orden.validar_cambio_estado(nuevo_estado)
        orden.estado = nuevo_estado
        orden.save()
        return orden

    # ─────────────────────────────────────────────
    # Componentes Predictivos
    # ─────────────────────────────────────────────

    def obtener_resumen_predictivo(self):
        """Retorna resumen de alertas predictivas para todos los vehículos"""
        from workorders.models import ComponentePredictivo

        componentes = ComponentePredictivo.objects.select_related(
            'vehiculo', 'vehiculo__propietario'
        ).all()

        todos = []
        for comp in componentes:
            km = comp.vehiculo.km_actuales
            prob = comp.calcular_probabilidad_fallo(km)
            prob_pct = round(prob * 100, 1)

            if prob > 0.7:
                urgencia = 'ALTA'
            elif prob > 0.4:
                urgencia = 'MEDIA'
            else:
                urgencia = 'BAJA'

            todos.append({
                'componente': comp,
                'vehiculo': comp.vehiculo,
                'probabilidad': prob_pct,
                'urgencia': urgencia,
            })

        todos.sort(key=lambda x: x['probabilidad'], reverse=True)

        alertas_alta = [c for c in todos if c['urgencia'] == 'ALTA']
        alertas_media = [c for c in todos if c['urgencia'] == 'MEDIA']

        return {
            'todos_componentes': todos,
            'alertas_alta': alertas_alta,
            'alertas_media': alertas_media,
            'total_riesgo_alto': len(alertas_alta),
            'total_riesgo_medio': len(alertas_media),
            'total_sin_riesgo': len([c for c in todos if c['urgencia'] == 'BAJA']),
            'total_componentes': len(todos),
        }

    def obtener_componentes_vehiculo(self, vehiculo_id):
        """Retorna un vehículo y sus componentes predictivos con probabilidades calculadas"""
        from workorders.models import ComponentePredictivo

        vehiculo = Vehicle.objects.select_related('propietario').get(id=vehiculo_id)
        componentes = ComponentePredictivo.objects.filter(vehiculo=vehiculo)

        resultado = []
        for comp in componentes:
            prob = comp.calcular_probabilidad_fallo(vehiculo.km_actuales)
            prob_pct = round(prob * 100, 1)

            if prob > 0.7:
                urgencia = 'ALTA'
            elif prob > 0.4:
                urgencia = 'MEDIA'
            else:
                urgencia = 'BAJA'

            resultado.append({
                'componente': comp,
                'probabilidad': prob_pct,
                'urgencia': urgencia,
            })

        resultado.sort(key=lambda x: x['probabilidad'], reverse=True)
        return vehiculo, resultado

    def agregar_componente_predictivo(self, datos):
        """Crea un componente predictivo asociado a un vehículo"""
        from workorders.models import ComponentePredictivo

        vehiculo = Vehicle.objects.get(id=datos['vehiculo_id'])
        comp = ComponentePredictivo.objects.create(
            vehiculo=vehiculo,
            nombre=datos['nombre'],
            categoria=datos.get('categoria', 'GENERAL'),
            km_promedio_fallo=int(datos['km_promedio_fallo']),
            desviacion_estandar=float(datos['desviacion_estandar']),
            costo_promedio=float(datos.get('costo_promedio', 0)),
        )
        return comp

    def eliminar_componente_predictivo(self, comp_id):
        """Elimina un componente predictivo por id"""
        from workorders.models import ComponentePredictivo

        comp = ComponentePredictivo.objects.get(id=comp_id)
        comp.delete()

    # ─────────────────────────────────────────────
    # Métodos privados de apoyo
    # ─────────────────────────────────────────────

    def _asignar_mejor_mecanico(self, especialidad_requerida):
        """Selecciona el mecánico con mejor score según especialidad y carga"""
        mecanicos = Mechanic.objects.filter(disponible=True)

        if not mecanicos.exists():
            raise ValueError("No hay mecánicos disponibles")

        mejor = None
        mejor_score = 0

        for mec in mecanicos:
            score = 0

            # Coincidencia de especialidad
            if mec.especialidad == especialidad_requerida:
                score += 30
            elif mec.especialidad == 'GENERAL':
                score += 15

            # Carga de trabajo (menor carga = mayor score)
            score += 20 * (1 - mec.horas_pendientes / 40)

            # Nivel de experiencia
            if mec.nivel == 'EXPERTO':
                score += 10

            if score > mejor_score:
                mejor_score = score
                mejor = mec

        return mejor

    def _estimar_tiempo(self, descripcion):
        """Estima horas de trabajo según palabras clave en la descripción"""
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
