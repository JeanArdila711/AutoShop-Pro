"""
services/ordenes_service/models.py
─────────────────────────────────────────────────────────────
Entidades del dominio de órdenes de trabajo.

Modelos migrados desde Django:
  - OrdenTrabajo       (WorkOrder)
  - Bahia
  - TimerSession
  - ChecklistTemplate  + ChecklistTemplateItem
  - DiagnosticoChecklist + DiagnosticoChecklistItem
  - EvidenciaFoto
─────────────────────────────────────────────────────────────
"""

from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


# ─────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────

ESTADOS_ORDEN = [
    'ABIERTA', 'EN_DIAGNOSTICO', 'PRESUPUESTADA', 'APROBADA',
    'EN_REPARACION', 'EN_ESPERA', 'PRUEBA_PISTA',
    'CERRADA', 'FACTURADA', 'ENTREGADA',
]

TRANSICIONES_VALIDAS = {
    'ABIERTA': ['EN_DIAGNOSTICO'],
    'EN_DIAGNOSTICO': ['PRESUPUESTADA', 'EN_ESPERA'],
    'PRESUPUESTADA': ['APROBADA'],
    'APROBADA': ['EN_REPARACION'],
    'EN_REPARACION': ['PRUEBA_PISTA', 'EN_ESPERA'],
    'EN_ESPERA': ['EN_REPARACION', 'EN_DIAGNOSTICO'],
    'PRUEBA_PISTA': ['CERRADA', 'EN_REPARACION'],
    'CERRADA': ['FACTURADA'],
    'FACTURADA': ['ENTREGADA'],
    'ENTREGADA': [],
}

ESTADOS_ACTIVOS = [
    'ABIERTA', 'EN_DIAGNOSTICO', 'PRESUPUESTADA', 'APROBADA',
    'EN_REPARACION', 'EN_ESPERA', 'PRUEBA_PISTA',
]

CATEGORIAS_COMPONENTE = [
    'MOTOR', 'TRANSMISION', 'SUSPENSION', 'FRENOS',
    'ELECTRICO', 'CARROCERIA', 'GENERAL',
]

TIPOS_BAHIA = ['GENERAL', 'MECANICA', 'ELECTRICA', 'CARROCERIA', 'ALINEACION']


# ─────────────────────────────────────────────
# MODELO: Orden de Trabajo
# ─────────────────────────────────────────────

class OrdenTrabajo(db.Model):
    """Orden de trabajo del taller mecánico"""
    __tablename__ = 'orden_trabajo'

    id = db.Column(db.Integer, primary_key=True)

    # ── Referencias externas (IDs del monolito Django) ──
    vehiculo_id = db.Column(db.Integer, nullable=False)
    vehiculo_placa = db.Column(db.String(10), default='')
    vehiculo_marca = db.Column(db.String(40), default='')
    vehiculo_modelo = db.Column(db.String(40), default='')

    propietario_id = db.Column(db.Integer, nullable=False)
    propietario_nombre = db.Column(db.String(120), default='')

    mecanico_id = db.Column(db.Integer, nullable=True)
    mecanico_nombre = db.Column(db.String(100), default='')

    # ── Estado y flujo ──
    estado = db.Column(db.String(20), default='ABIERTA')
    fecha_ingreso = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc),
    )
    fecha_estimada_salida = db.Column(db.DateTime, nullable=True)
    fecha_cierre = db.Column(db.DateTime, nullable=True)

    # ── Descripción ──
    descripcion_problema = db.Column(db.Text, nullable=False)
    diagnostico = db.Column(db.Text, default='')
    odometer_km = db.Column(db.Integer, default=0)

    # ── Costos ──
    costo_presupuestado = db.Column(db.Float, default=0.0)
    costo_real = db.Column(db.Float, default=0.0)

    # ── Tiempos ──
    tiempo_estimado = db.Column(db.Integer, default=0)  # horas
    tiempo_real = db.Column(db.Integer, default=0)       # horas

    # ── Bahía asignada ──
    bahia_codigo = db.Column(db.String(10), nullable=True)

    # ── Relaciones ──
    timers = db.relationship(
        'TimerSession', backref='orden',
        cascade='all, delete-orphan', lazy=True,
    )
    checklists = db.relationship(
        'DiagnosticoChecklist', backref='orden',
        cascade='all, delete-orphan', lazy=True,
    )
    evidencias = db.relationship(
        'EvidenciaFoto', backref='orden',
        cascade='all, delete-orphan', lazy=True,
    )

    def __repr__(self):
        return f"<OT#{self.id} {self.vehiculo_placa} [{self.estado}]>"

    # ── Métodos de negocio ──

    def validar_cambio_estado(self, nuevo_estado):
        """Verifica si la transición de estado es válida"""
        permitidos = TRANSICIONES_VALIDAS.get(self.estado, [])
        if nuevo_estado not in permitidos:
            raise ValueError(
                f"No se puede cambiar de {self.estado} a {nuevo_estado}. "
                f"Transiciones permitidas: {permitidos}"
            )
        return True

    def cambiar_estado(self, nuevo_estado):
        """Cambia el estado validando la transición"""
        self.validar_cambio_estado(nuevo_estado)
        self.estado = nuevo_estado
        if nuevo_estado == 'CERRADA':
            self.fecha_cierre = datetime.now(timezone.utc)
        return self

    def detectar_exceso_costo(self):
        """True si costo real supera presupuestado en más de 20%"""
        if self.costo_presupuestado == 0:
            return False
        return self.costo_real > self.costo_presupuestado * 1.20

    def esta_activa(self):
        """True si la orden está en un estado activo"""
        return self.estado in ESTADOS_ACTIVOS

    def calcular_tiempo_total_timers(self):
        """Suma el tiempo de todas las sesiones de timer en horas"""
        total_seg = sum(t.duracion_segundos() for t in self.timers)
        return round(total_seg / 3600.0, 2)

    def to_dict(self, incluir_detalles=False):
        data = {
            'id': self.id,
            'vehiculo_id': self.vehiculo_id,
            'vehiculo_placa': self.vehiculo_placa,
            'vehiculo_marca': self.vehiculo_marca,
            'vehiculo_modelo': self.vehiculo_modelo,
            'propietario_id': self.propietario_id,
            'propietario_nombre': self.propietario_nombre,
            'mecanico_id': self.mecanico_id,
            'mecanico_nombre': self.mecanico_nombre,
            'estado': self.estado,
            'fecha_ingreso': self.fecha_ingreso.isoformat() if self.fecha_ingreso else None,
            'fecha_estimada_salida': self.fecha_estimada_salida.isoformat() if self.fecha_estimada_salida else None,
            'fecha_cierre': self.fecha_cierre.isoformat() if self.fecha_cierre else None,
            'descripcion_problema': self.descripcion_problema,
            'diagnostico': self.diagnostico,
            'odometer_km': self.odometer_km,
            'costo_presupuestado': self.costo_presupuestado,
            'costo_real': self.costo_real,
            'tiempo_estimado': self.tiempo_estimado,
            'tiempo_real': self.tiempo_real,
            'bahia_codigo': self.bahia_codigo,
            'esta_activa': self.esta_activa(),
            'exceso_costo': self.detectar_exceso_costo(),
        }
        if incluir_detalles:
            data['timers'] = [t.to_dict() for t in self.timers]
            data['checklists'] = [c.to_dict() for c in self.checklists]
            data['evidencias'] = [e.to_dict() for e in self.evidencias]
            data['tiempo_total_timers'] = self.calcular_tiempo_total_timers()
        return data


# ─────────────────────────────────────────────
# MODELO: Bahía
# ─────────────────────────────────────────────

class Bahia(db.Model):
    """Bahía física del taller"""
    __tablename__ = 'bahia'

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(10), unique=True, nullable=False)
    nombre = db.Column(db.String(60), nullable=False)
    tipo = db.Column(db.String(15), default='GENERAL')
    activa = db.Column(db.Boolean, default=True)
    orden_actual_id = db.Column(db.Integer, nullable=True)

    def esta_ocupada(self):
        return self.orden_actual_id is not None

    def to_dict(self):
        return {
            'id': self.id,
            'codigo': self.codigo,
            'nombre': self.nombre,
            'tipo': self.tipo,
            'activa': self.activa,
            'orden_actual_id': self.orden_actual_id,
            'ocupada': self.esta_ocupada(),
        }


# ─────────────────────────────────────────────
# MODELO: Timer Session
# ─────────────────────────────────────────────

class TimerSession(db.Model):
    """Sesiones de cronómetro asociadas a una orden"""
    __tablename__ = 'timer_session'

    id = db.Column(db.Integer, primary_key=True)
    orden_id = db.Column(
        db.Integer, db.ForeignKey('orden_trabajo.id'), nullable=False,
    )
    inicio = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc),
    )
    fin = db.Column(db.DateTime, nullable=True)
    nota = db.Column(db.String(200), default='')

    @property
    def activo(self):
        return self.fin is None

    def duracion_segundos(self):
        fin = self.fin or datetime.now(timezone.utc)
        return int((fin - self.inicio).total_seconds())

    def duracion_horas(self):
        return round(self.duracion_segundos() / 3600.0, 2)

    def detener(self):
        if self.fin is not None:
            raise ValueError("El timer ya está detenido")
        self.fin = datetime.now(timezone.utc)
        return self

    def to_dict(self):
        return {
            'id': self.id,
            'orden_id': self.orden_id,
            'inicio': self.inicio.isoformat() if self.inicio else None,
            'fin': self.fin.isoformat() if self.fin else None,
            'activo': self.activo,
            'duracion_segundos': self.duracion_segundos(),
            'duracion_horas': self.duracion_horas(),
            'nota': self.nota,
        }


# ─────────────────────────────────────────────
# MODELO: Checklist Template
# ─────────────────────────────────────────────

class ChecklistTemplate(db.Model):
    """Plantilla de checklist por categoría de diagnóstico"""
    __tablename__ = 'checklist_template'

    id = db.Column(db.Integer, primary_key=True)
    categoria = db.Column(db.String(20), unique=True, nullable=False)
    descripcion = db.Column(db.String(200), default='')

    items = db.relationship(
        'ChecklistTemplateItem', backref='template',
        cascade='all, delete-orphan', lazy=True,
        order_by='ChecklistTemplateItem.orden',
    )

    def to_dict(self):
        return {
            'id': self.id,
            'categoria': self.categoria,
            'descripcion': self.descripcion,
            'items': [i.to_dict() for i in self.items],
        }


class ChecklistTemplateItem(db.Model):
    """Ítem de una plantilla de checklist"""
    __tablename__ = 'checklist_template_item'

    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(
        db.Integer, db.ForeignKey('checklist_template.id'), nullable=False,
    )
    texto = db.Column(db.String(200), nullable=False)
    orden = db.Column(db.Integer, default=0)

    def to_dict(self):
        return {
            'id': self.id,
            'texto': self.texto,
            'orden': self.orden,
        }


# ─────────────────────────────────────────────
# MODELO: Diagnóstico Checklist (resultado)
# ─────────────────────────────────────────────

class DiagnosticoChecklist(db.Model):
    """Resultado de checklist aplicado a una orden"""
    __tablename__ = 'diagnostico_checklist'

    ESTADOS_ITEM = ['OK', 'REVISAR', 'FALLA', 'PENDIENTE']

    id = db.Column(db.Integer, primary_key=True)
    orden_id = db.Column(
        db.Integer, db.ForeignKey('orden_trabajo.id'), nullable=False,
    )
    categoria = db.Column(db.String(20), nullable=False)
    fecha = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc),
    )

    items = db.relationship(
        'DiagnosticoChecklistItem', backref='checklist',
        cascade='all, delete-orphan', lazy=True,
    )

    def resumen(self):
        """Resumen de resultados del checklist"""
        total = len(self.items)
        por_estado = {}
        for item in self.items:
            por_estado[item.estado] = por_estado.get(item.estado, 0) + 1
        return {'total': total, 'por_estado': por_estado}

    def to_dict(self):
        return {
            'id': self.id,
            'orden_id': self.orden_id,
            'categoria': self.categoria,
            'fecha': self.fecha.isoformat() if self.fecha else None,
            'items': [i.to_dict() for i in self.items],
            'resumen': self.resumen(),
        }


class DiagnosticoChecklistItem(db.Model):
    """Ítem individual de un checklist de diagnóstico"""
    __tablename__ = 'diagnostico_checklist_item'

    id = db.Column(db.Integer, primary_key=True)
    checklist_id = db.Column(
        db.Integer, db.ForeignKey('diagnostico_checklist.id'), nullable=False,
    )
    texto = db.Column(db.String(200), nullable=False)
    estado = db.Column(db.String(12), default='PENDIENTE')
    nota = db.Column(db.String(300), default='')

    def to_dict(self):
        return {
            'id': self.id,
            'texto': self.texto,
            'estado': self.estado,
            'nota': self.nota,
        }


# ─────────────────────────────────────────────
# MODELO: Evidencia Fotográfica
# ─────────────────────────────────────────────

class EvidenciaFoto(db.Model):
    """Evidencia fotográfica antes/durante/después"""
    __tablename__ = 'evidencia_foto'

    MOMENTOS = ['ANTES', 'DURANTE', 'DESPUES']

    id = db.Column(db.Integer, primary_key=True)
    orden_id = db.Column(
        db.Integer, db.ForeignKey('orden_trabajo.id'), nullable=False,
    )
    ruta_archivo = db.Column(db.String(300), nullable=False)
    momento = db.Column(db.String(10), default='ANTES')
    descripcion = db.Column(db.String(200), default='')
    fecha = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'orden_id': self.orden_id,
            'ruta_archivo': self.ruta_archivo,
            'momento': self.momento,
            'descripcion': self.descripcion,
            'fecha': self.fecha.isoformat() if self.fecha else None,
        }
