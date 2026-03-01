from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator


# ─────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────

class TipoCliente(models.TextChoices):
    """Tipos de cliente del taller"""
    REGULAR = 'REGULAR', 'Regular'
    VIP = 'VIP', 'VIP'
    PREMIUM = 'PREMIUM', 'Premium'


class EstadoOrden(models.TextChoices):
    """Estados válidos de una orden de trabajo"""
    ABIERTA = 'ABIERTA'
    EN_DIAGNOSTICO = 'EN_DIAGNOSTICO'
    PRESUPUESTADA = 'PRESUPUESTADA'
    APROBADA = 'APROBADA'
    EN_REPARACION = 'EN_REPARACION'
    EN_ESPERA = 'EN_ESPERA'
    PRUEBA_PISTA = 'PRUEBA_PISTA'
    CERRADA = 'CERRADA'
    FACTURADA = 'FACTURADA'
    ENTREGADA = 'ENTREGADA'


class CategoriaComponente(models.TextChoices):
    """Categorías de componentes mecánicos"""
    MOTOR = 'MOTOR', 'Motor'
    TRANSMISION = 'TRANSMISION', 'Transmisión'
    SUSPENSION = 'SUSPENSION', 'Suspensión'
    FRENOS = 'FRENOS', 'Frenos'
    ELECTRICO = 'ELECTRICO', 'Eléctrico'
    CARROCERIA = 'CARROCERIA', 'Carrocería'
    GENERAL = 'GENERAL', 'General'


class EstadoFactura(models.TextChoices):
    """Estados de una factura de servicio"""
    PENDIENTE = 'PENDIENTE', 'Pendiente'
    PAGADA = 'PAGADA', 'Pagada'
    ANULADA = 'ANULADA', 'Anulada'


# Mapa de transiciones válidas de estado para OrdenTrabajo
TRANSICIONES_VALIDAS = {
    EstadoOrden.ABIERTA: [EstadoOrden.EN_DIAGNOSTICO],
    EstadoOrden.EN_DIAGNOSTICO: [EstadoOrden.PRESUPUESTADA, EstadoOrden.EN_ESPERA],
    EstadoOrden.PRESUPUESTADA: [EstadoOrden.APROBADA],
    EstadoOrden.APROBADA: [EstadoOrden.EN_REPARACION],
    EstadoOrden.EN_REPARACION: [EstadoOrden.PRUEBA_PISTA, EstadoOrden.EN_ESPERA],
    EstadoOrden.EN_ESPERA: [EstadoOrden.EN_REPARACION, EstadoOrden.EN_DIAGNOSTICO],
    EstadoOrden.PRUEBA_PISTA: [EstadoOrden.CERRADA, EstadoOrden.EN_REPARACION],
    EstadoOrden.CERRADA: [EstadoOrden.FACTURADA],
    EstadoOrden.FACTURADA: [EstadoOrden.ENTREGADA],
    EstadoOrden.ENTREGADA: [],
}


# ─────────────────────────────────────────────
# MODELO: Propietario (Owner)
# ─────────────────────────────────────────────

class Owner(models.Model):
    """Propietario de un vehículo"""
    nombre = models.CharField(max_length=120)
    email = models.EmailField(max_length=254, blank=True, default='')
    telefono = models.CharField(max_length=20, blank=True, default='')
    tipo_cliente = models.CharField(
        max_length=10,
        choices=TipoCliente.choices,
        default=TipoCliente.REGULAR,
    )
    descuento_acumulado = models.FloatField(default=0.0)
    total_gastado_mes = models.FloatField(default=0.0)

    def __str__(self):
        return self.nombre

    # ── Métodos de negocio (validación a nivel de entidad) ──

    def calcular_descuento(self):
        """Calcula el porcentaje de descuento según tipo de cliente"""
        tasas = {
            TipoCliente.REGULAR: 0.0,
            TipoCliente.VIP: 0.10,
            TipoCliente.PREMIUM: 0.15,
        }
        return tasas.get(self.tipo_cliente, 0.0)

    def es_cliente_vip(self):
        """Determina si el cliente es VIP o superior"""
        return self.tipo_cliente in (TipoCliente.VIP, TipoCliente.PREMIUM)


# ─────────────────────────────────────────────
# MODELO: Vehículo (Vehicle)
# ─────────────────────────────────────────────

class Vehicle(models.Model):
    """Vehículo registrado en el taller"""
    placa = models.CharField(
        max_length=6,          
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^[A-Z]{3}[0-9]{3}$',
                message='Formato inválido. La placa colombiana debe ser 3 letras + 3 números (Ej: ABC123)'
            )
        ]
    )
    vin = models.CharField(max_length=17, blank=True, default='')
    marca = models.CharField(max_length=40)
    modelo = models.CharField(max_length=40)
    anio = models.PositiveIntegerField()
    km_actuales = models.PositiveIntegerField(default=0)
    propietario = models.ForeignKey(
        Owner, on_delete=models.PROTECT, related_name='vehiculos',
    )

    def __str__(self):
        return f"{self.placa} - {self.marca} {self.modelo} {self.anio}"

    # ── Métodos de negocio ──

    def actualizar_kilometraje(self, nuevo_km):
        """Actualiza el kilometraje; no permite retroceder"""
        if nuevo_km < self.km_actuales:
            raise ValidationError("El kilometraje no puede disminuir")
        self.km_actuales = nuevo_km

    def necesita_mantenimiento(self):
        """Verifica si algún componente predictivo requiere atención"""
        for comp in self.predicciones.all():
            if comp.debe_reemplazarse_ya(self.km_actuales):
                return True
        return False


# ─────────────────────────────────────────────
# MODELO: Mecánico (Mechanic)
# ─────────────────────────────────────────────

class Mechanic(models.Model):
    """Mecánico del taller"""
    ESPECIALIDADES = [
        ('MOTOR', 'Motor'),
        ('TRANSMISION', 'Transmisión'),
        ('SUSPENSION', 'Suspensión'),
        ('ELECTRICO', 'Eléctrico'),
        ('GENERAL', 'General'),
    ]

    NIVELES = [
        ('JUNIOR', 'Junior'),
        ('INTERMEDIO', 'Intermedio'),
        ('EXPERTO', 'Experto'),
    ]

    nombre = models.CharField(max_length=100)
    especialidad = models.CharField(max_length=20, choices=ESPECIALIDADES)
    nivel = models.CharField(max_length=15, choices=NIVELES)
    tarifa_hora = models.DecimalField(max_digits=10, decimal_places=2)
    disponible = models.BooleanField(default=True)
    horas_pendientes = models.IntegerField(default=0)
    eficiencia = models.FloatField(default=1.0)

    def __str__(self):
        return f"{self.nombre} - {self.especialidad}"

    # ── Métodos de negocio ──

    def puede_atender(self, especialidad_requerida):
        """Determina si el mecánico puede atender un tipo de problema"""
        if not self.disponible:
            return False
        return (
            self.especialidad == especialidad_requerida
            or self.especialidad == 'GENERAL'
        )

    def calcular_costo_mano_obra(self, horas):
        """Calcula el costo de mano de obra según tarifa y horas"""
        return float(self.tarifa_hora) * horas

    def verificar_disponibilidad(self):
        """Retorna True si el mecánico puede tomar más trabajos"""
        return self.disponible and self.horas_pendientes < 40

    def calcular_carga(self):
        """Retorna las horas pendientes como indicador de carga"""
        return self.horas_pendientes


# ─────────────────────────────────────────────
# MODELO: Orden de Trabajo (WorkOrder)
# ─────────────────────────────────────────────

class WorkOrder(models.Model):
    """Orden de trabajo del taller mecánico"""
    vehiculo = models.ForeignKey(
        Vehicle, on_delete=models.PROTECT, related_name='ordenes',
    )
    propietario = models.ForeignKey(
        Owner, on_delete=models.PROTECT, related_name='ordenes',
    )
    mecanico = models.ForeignKey(
        'Mechanic', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='ordenes',
    )
    estado = models.CharField(
        max_length=20, choices=EstadoOrden.choices, default=EstadoOrden.ABIERTA,
    )
    fecha_ingreso = models.DateTimeField(default=timezone.now)
    fecha_estimada_salida = models.DateTimeField(null=True, blank=True)
    descripcion_problema = models.TextField()
    diagnostico = models.TextField(blank=True, default='')
    odometer_km = models.PositiveIntegerField()
    costo_presupuestado = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
    )
    costo_real = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
    )
    tiempo_estimado = models.PositiveIntegerField(default=0)  # horas
    tiempo_real = models.PositiveIntegerField(default=0)      # horas
    bahia = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return f"OT#{self.id} {self.vehiculo.placa} [{self.estado}]"

    # ── Métodos de negocio (validación a nivel de entidad) ──

    def calcular_costo_total(self):
        """Calcula costo total: mano de obra + costo real de partes"""
        mano_obra = 0
        if self.mecanico and self.tiempo_real:
            mano_obra = self.mecanico.calcular_costo_mano_obra(self.tiempo_real)
        return mano_obra + float(self.costo_real)

    def validar_cambio_estado(self, nuevo_estado):
        """Verifica si la transición de estado es válida según el flujo definido"""
        permitidos = TRANSICIONES_VALIDAS.get(self.estado, [])
        if nuevo_estado not in permitidos:
            raise ValidationError(
                f"No se puede cambiar de {self.estado} a {nuevo_estado}. "
                f"Transiciones permitidas: {permitidos}"
            )
        return True

    def detectar_exceso_costo(self):
        """Retorna True si el costo real supera el presupuestado en más del 20%"""
        if self.costo_presupuestado == 0:
            return False
        return float(self.costo_real) > float(self.costo_presupuestado) * 1.20

    def cerrar_orden(self):
        """Cierra la orden validando la transición de estado"""
        self.validar_cambio_estado(EstadoOrden.CERRADA)
        self.estado = EstadoOrden.CERRADA


# ─────────────────────────────────────────────
# MODELO: Parte Mecánica (ParteMecanica)
# ─────────────────────────────────────────────

class ParteMecanica(models.Model):
    """Repuesto o parte mecánica del inventario"""
    codigo_oem = models.CharField(max_length=30, unique=True)
    nombre = models.CharField(max_length=120)
    categoria = models.CharField(
        max_length=20, choices=CategoriaComponente.choices,
        default=CategoriaComponente.GENERAL,
    )
    precio_compra = models.DecimalField(max_digits=12, decimal_places=2)
    precio_venta = models.DecimalField(max_digits=12, decimal_places=2)
    stock_actual = models.PositiveIntegerField(default=0)
    stock_minimo = models.PositiveIntegerField(default=5)
    fecha_vencimiento = models.DateField(null=True, blank=True)

    # Relación M2M con WorkOrder
    ordenes = models.ManyToManyField(
        WorkOrder, blank=True, related_name='partes',
    )

    def __str__(self):
        return f"{self.codigo_oem} - {self.nombre}"

    # ── Métodos de negocio ──

    def verificar_stock(self, cantidad):
        """Verifica si hay stock suficiente"""
        return self.stock_actual >= cantidad

    def necesita_reorden(self):
        """Retorna True si el stock está por debajo del mínimo"""
        return self.stock_actual < self.stock_minimo

    def actualizar_stock(self, cantidad):
        """Descuenta stock; lanza error si no hay suficiente"""
        if not self.verificar_stock(cantidad):
            raise ValidationError(
                f"Stock insuficiente para {self.nombre}. "
                f"Disponible: {self.stock_actual}, solicitado: {cantidad}"
            )
        self.stock_actual -= cantidad


# ─────────────────────────────────────────────
# MODELO: Factura de Servicio (FacturaServicio)
# ─────────────────────────────────────────────

class FacturaServicio(models.Model):
    """Factura asociada a una orden de trabajo"""
    TASA_IMPUESTO = 0.19  # IVA Colombia 19%

    orden_trabajo = models.OneToOneField(
        WorkOrder, on_delete=models.PROTECT, related_name='factura',
    )
    propietario = models.ForeignKey(
        Owner, on_delete=models.PROTECT, related_name='facturas',
    )
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    descuento = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    impuestos = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fecha_emision = models.DateTimeField(default=timezone.now)
    estado = models.CharField(
        max_length=15, choices=EstadoFactura.choices,
        default=EstadoFactura.PENDIENTE,
    )
    dias_garantia = models.PositiveIntegerField(default=30)

    def __str__(self):
        return f"Factura #{self.id} - OT#{self.orden_trabajo_id}"

    # ── Métodos de negocio ──

    def calcular_impuestos(self):
        """Calcula los impuestos sobre el subtotal menos descuento"""
        base = float(self.subtotal) - float(self.descuento)
        self.impuestos = round(base * self.TASA_IMPUESTO, 2)
        return self.impuestos

    def generar_total(self):
        """Calcula y establece el total de la factura"""
        self.calcular_impuestos()
        self.total = float(self.subtotal) - float(self.descuento) + float(self.impuestos)
        return self.total

    def asignar_garantia(self):
        """Asigna días de garantía según el tipo de cliente"""
        garantias = {
            TipoCliente.REGULAR: 30,
            TipoCliente.VIP: 60,
            TipoCliente.PREMIUM: 90,
        }
        self.dias_garantia = garantias.get(
            self.propietario.tipo_cliente, 30,
        )
        return self.dias_garantia


# ─────────────────────────────────────────────
# MODELO: Componente Predictivo
# ─────────────────────────────────────────────

class ComponentePredictivo(models.Model):
    """Componentes que pueden fallar — para mantenimiento predictivo"""
    vehiculo = models.ForeignKey(
        Vehicle, on_delete=models.CASCADE, related_name='predicciones',
    )
    nombre = models.CharField(max_length=100)
    modelo_vehiculo = models.CharField(max_length=40, blank=True, default='')
    categoria = models.CharField(
        max_length=20, choices=CategoriaComponente.choices,
        default=CategoriaComponente.GENERAL,
    )
    km_promedio_fallo = models.IntegerField()
    desviacion_estandar = models.FloatField()
    costo_promedio = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
    )

    def __str__(self):
        return f"{self.nombre} - {self.vehiculo.placa}"

    # ── Métodos de negocio ──

    def calcular_probabilidad_fallo(self, km_actuales):
        """Calcula la probabilidad de fallo dado el km actual"""
        diferencia = self.km_promedio_fallo - km_actuales
        if self.desviacion_estandar == 0:
            return 1.0 if diferencia <= 0 else 0.0
        prob = max(0, min(1, 1 - (diferencia / (self.desviacion_estandar * 2))))
        return round(prob, 4)

    def generar_alerta(self, km_actuales):
        """Genera un mensaje de alerta según la probabilidad de fallo"""
        prob = self.calcular_probabilidad_fallo(km_actuales)
        if prob > 0.7:
            return f"⚠️ ALTA: {self.nombre} probabilidad {prob*100:.0f}%"
        elif prob > 0.4:
            return f"⚠️ MEDIA: {self.nombre} probabilidad {prob*100:.0f}%"
        return ""

    def debe_reemplazarse_ya(self, km_actuales):
        """Retorna True si la probabilidad de fallo supera el 70%"""
        return self.calcular_probabilidad_fallo(km_actuales) > 0.7
