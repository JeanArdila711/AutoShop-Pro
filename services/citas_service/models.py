"""
services/citas_service/models.py
─────────────────────────────────────────────────────────────
Entidades del dominio de citas / agendamiento.

Modelos:
  - Cita          (nueva entidad — no existía en Django)
  - BloqueoAgenda (bloqueos manuales de horario)
─────────────────────────────────────────────────────────────
"""

from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


# ─────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────

ESTADOS_CITA = ['PENDIENTE', 'CONFIRMADA', 'CANCELADA', 'COMPLETADA', 'NO_ASISTIO']

TIPOS_SERVICIO = [
    'MANTENIMIENTO_PREVENTIVO',
    'REPARACION_MECANICA',
    'DIAGNOSTICO_ELECTRICO',
    'CARROCERIA_PINTURA',
    'ALINEACION_BALANCEO',
    'REVISION_GENERAL',
    'OTRO',
]

TRANSICIONES_CITA = {
    'PENDIENTE':   ['CONFIRMADA', 'CANCELADA'],
    'CONFIRMADA':  ['COMPLETADA', 'CANCELADA', 'NO_ASISTIO'],
    'CANCELADA':   [],
    'COMPLETADA':  [],
    'NO_ASISTIO':  [],
}


# ─────────────────────────────────────────────
# MODELOS
# ─────────────────────────────────────────────

class Cita(db.Model):
    __tablename__ = 'citas'

    id = db.Column(db.Integer, primary_key=True)

    # Referencias a otros servicios (IDs externos, no FK cruzadas)
    propietario_id     = db.Column(db.Integer, nullable=False)
    propietario_nombre = db.Column(db.String(200), nullable=False)
    propietario_email  = db.Column(db.String(200), nullable=True)
    propietario_telefono = db.Column(db.String(20), nullable=True)

    vehiculo_id   = db.Column(db.Integer, nullable=False)
    vehiculo_placa = db.Column(db.String(10), nullable=False)
    vehiculo_marca = db.Column(db.String(100), nullable=True)
    vehiculo_modelo = db.Column(db.String(100), nullable=True)

    mecanico_id     = db.Column(db.Integer, nullable=True)   # asignado en confirmación
    mecanico_nombre = db.Column(db.String(200), nullable=True)

    # Agendamiento
    fecha          = db.Column(db.Date, nullable=False)
    hora_inicio    = db.Column(db.Time, nullable=False)
    duracion_minutos = db.Column(db.Integer, default=60, nullable=False)
    tipo_servicio  = db.Column(db.String(50), nullable=False, default='REVISION_GENERAL')

    # Estado
    estado     = db.Column(db.String(20), nullable=False, default='PENDIENTE')
    notas      = db.Column(db.Text, nullable=True)
    notas_cancelacion = db.Column(db.Text, nullable=True)

    # Vinculación con orden de trabajo (una vez completada)
    orden_trabajo_id = db.Column(db.Integer, nullable=True)

    # Timestamps
    creado_en    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    actualizado_en = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                               onupdate=lambda: datetime.now(timezone.utc))

    # ── Métodos de dominio ──────────────────────────────────

    def cambiar_estado(self, nuevo_estado: str) -> None:
        """Valida y aplica transición de estado."""
        permitidos = TRANSICIONES_CITA.get(self.estado, [])
        if nuevo_estado not in permitidos:
            raise ValueError(
                f"Transición inválida: {self.estado} → {nuevo_estado}. "
                f"Permitidos: {permitidos}"
            )
        self.estado = nuevo_estado
        self.actualizado_en = datetime.now(timezone.utc)

    def confirmar(self, mecanico_id: int = None, mecanico_nombre: str = None) -> None:
        self.cambiar_estado('CONFIRMADA')
        if mecanico_id:
            self.mecanico_id = mecanico_id
            self.mecanico_nombre = mecanico_nombre

    def cancelar(self, motivo: str = None) -> None:
        self.cambiar_estado('CANCELADA')
        self.notas_cancelacion = motivo

    def completar(self, orden_trabajo_id: int = None) -> None:
        self.cambiar_estado('COMPLETADA')
        self.orden_trabajo_id = orden_trabajo_id

    def marcar_no_asistio(self) -> None:
        self.cambiar_estado('NO_ASISTIO')

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'propietario_id': self.propietario_id,
            'propietario_nombre': self.propietario_nombre,
            'propietario_email': self.propietario_email,
            'propietario_telefono': self.propietario_telefono,
            'vehiculo_id': self.vehiculo_id,
            'vehiculo_placa': self.vehiculo_placa,
            'vehiculo_marca': self.vehiculo_marca,
            'vehiculo_modelo': self.vehiculo_modelo,
            'mecanico_id': self.mecanico_id,
            'mecanico_nombre': self.mecanico_nombre,
            'fecha': self.fecha.isoformat() if self.fecha else None,
            'hora_inicio': self.hora_inicio.strftime('%H:%M') if self.hora_inicio else None,
            'duracion_minutos': self.duracion_minutos,
            'tipo_servicio': self.tipo_servicio,
            'estado': self.estado,
            'notas': self.notas,
            'notas_cancelacion': self.notas_cancelacion,
            'orden_trabajo_id': self.orden_trabajo_id,
            'creado_en': self.creado_en.isoformat() if self.creado_en else None,
            'actualizado_en': self.actualizado_en.isoformat() if self.actualizado_en else None,
        }


class BloqueoAgenda(db.Model):
    """Bloqueos manuales de franja horaria (feriados, mantenimiento taller, etc.)."""
    __tablename__ = 'bloqueos_agenda'

    id = db.Column(db.Integer, primary_key=True)
    fecha       = db.Column(db.Date, nullable=False)
    hora_inicio = db.Column(db.Time, nullable=True)   # None = día completo
    hora_fin    = db.Column(db.Time, nullable=True)
    motivo      = db.Column(db.String(200), nullable=False, default='Bloqueo manual')
    creado_en   = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'fecha': self.fecha.isoformat() if self.fecha else None,
            'hora_inicio': self.hora_inicio.strftime('%H:%M') if self.hora_inicio else None,
            'hora_fin': self.hora_fin.strftime('%H:%M') if self.hora_fin else None,
            'motivo': self.motivo,
            'creado_en': self.creado_en.isoformat() if self.creado_en else None,
        }
