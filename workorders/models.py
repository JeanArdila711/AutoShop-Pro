from django.db import models
from django.utils import timezone


class Owner(models.Model):
    nombre = models.CharField(max_length=120)

    def __str__(self):
        return self.nombre


class Vehicle(models.Model):
    placa = models.CharField(max_length=10, unique=True)
    marca = models.CharField(max_length=40)
    modelo = models.CharField(max_length=40)
    anio = models.PositiveIntegerField()
    km_actuales = models.PositiveIntegerField(default=0)
    propietario = models.ForeignKey(Owner, on_delete=models.PROTECT, related_name="vehiculos")

    def __str__(self):
        return f"{self.placa} - {self.marca} {self.modelo} {self.anio}"


class EstadoOrden(models.TextChoices):
    ABIERTA = "ABIERTA"
    EN_DIAGNOSTICO = "EN_DIAGNOSTICO"
    PRESUPUESTADA = "PRESUPUESTADA"
    APROBADA = "APROBADA"
    EN_REPARACION = "EN_REPARACION"
    EN_ESPERA = "EN_ESPERA"
    PRUEBA_PISTA = "PRUEBA_PISTA"
    CERRADA = "CERRADA"
    FACTURADA = "FACTURADA"
    ENTREGADA = "ENTREGADA"


class WorkOrder(models.Model):
    vehiculo = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name="ordenes")
    propietario = models.ForeignKey(Owner, on_delete=models.PROTECT, related_name="ordenes")
    mecanico = models.ForeignKey('Mechanic', on_delete=models.SET_NULL, null=True, blank=True, related_name="ordenes")
    estado = models.CharField(max_length=20, choices=EstadoOrden.choices, default=EstadoOrden.ABIERTA)


    fecha_ingreso = models.DateTimeField(default=timezone.now)
    descripcion_problema = models.TextField()
    odometer_km = models.PositiveIntegerField()

    bahia = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return f"OT#{self.id} {self.vehiculo.placa} [{self.estado}]"


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
    
    def __str__(self):
        return f"{self.nombre} - {self.especialidad}"


class ComponentePredictivo(models.Model):
    """Componentes que pueden fallar"""
    vehiculo = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='predicciones')
    nombre = models.CharField(max_length=100)
    km_promedio_fallo = models.IntegerField()
    desviacion_estandar = models.FloatField()
    
    def __str__(self):
        return f"{self.nombre} - {self.vehiculo.placa}"
