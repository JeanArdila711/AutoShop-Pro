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
        return {
            'total_propietarios': Owner.objects.count(),
            'total_vehiculos': Vehicle.objects.count(),
            'total_mecanicos': Mechanic.objects.count(),
            'total_ordenes': WorkOrder.objects.count(),
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
        propietario = Owner.objects.get(id=datos['propietario_id'])
        predicciones = self.predictor.obtener_predicciones(vehiculo)

        # 2. Asignar mecánico
        especialidad = datos.get('especialidad_requerida', 'GENERAL')
        mecanico = self._asignar_mejor_mecanico(especialidad)

        # 3. Construir la orden con el Builder (Fluent Interface)
        work_order = (
            WorkOrderBuilder()
            .para_vehiculo(datos['vehiculo_id'])
            .del_propietario(datos['propietario_id'])
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
