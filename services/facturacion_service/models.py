"""
services/facturacion_service/models.py
─────────────────────────────────────────────────────────────
Entidades del dominio de facturación.

Modelos:
  - FacturaServicio  (migrada desde Django)
  - DetalleFactura   (NUEVA — líneas de detalle de la factura)
─────────────────────────────────────────────────────────────
"""

from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


# ─────────────────────────────────────────────
# MODELO: FacturaServicio
# ─────────────────────────────────────────────

class FacturaServicio(db.Model):
    """Factura asociada a una orden de trabajo"""
    __tablename__ = 'factura_servicio'

    TASA_IMPUESTO = 0.19  # IVA Colombia 19%

    # ── Estados ──
    ESTADOS = ['PENDIENTE', 'PAGADA', 'ANULADA']

    # ── Tipos de cliente (para garantía) ──
    GARANTIAS_POR_TIPO = {
        'REGULAR': 30,
        'VIP': 60,
        'PREMIUM': 90,
    }

    id = db.Column(db.Integer, primary_key=True)
    orden_trabajo_id = db.Column(db.Integer, nullable=False, unique=True)
    propietario_id = db.Column(db.Integer, nullable=False)
    propietario_nombre = db.Column(db.String(120), default='')
    tipo_cliente = db.Column(db.String(10), default='REGULAR')

    # ── Montos ──
    subtotal = db.Column(db.Float, default=0.0)
    descuento = db.Column(db.Float, default=0.0)
    impuestos = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)

    # ── Fechas y estado ──
    fecha_emision = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
    estado = db.Column(db.String(15), default='PENDIENTE')
    dias_garantia = db.Column(db.Integer, default=30)

    # ── Notas ──
    notas = db.Column(db.Text, default='')

    # ── Relaciones ──
    detalles = db.relationship(
        'DetalleFactura', backref='factura',
        cascade='all, delete-orphan', lazy=True,
    )

    def __repr__(self):
        return f"<Factura #{self.id} OT#{self.orden_trabajo_id} [{self.estado}]>"

    # ── Métodos de negocio ──

    def calcular_impuestos(self):
        """Calcula IVA 19% sobre (subtotal - descuento)"""
        base = self.subtotal - self.descuento
        self.impuestos = round(max(base, 0) * self.TASA_IMPUESTO, 2)
        return self.impuestos

    def generar_total(self):
        """Calcula subtotal desde detalles, aplica descuento e impuestos"""
        self.subtotal = sum(d.calcular_subtotal() for d in self.detalles)
        self.calcular_impuestos()
        self.total = round(self.subtotal - self.descuento + self.impuestos, 2)
        return self.total

    def asignar_garantia(self):
        """Asigna días de garantía según el tipo de cliente"""
        self.dias_garantia = self.GARANTIAS_POR_TIPO.get(
            self.tipo_cliente, 30
        )
        return self.dias_garantia

    def pagar(self):
        """Marca la factura como pagada"""
        if self.estado != 'PENDIENTE':
            raise ValueError(
                f"No se puede pagar una factura en estado {self.estado}"
            )
        self.estado = 'PAGADA'
        return self

    def anular(self):
        """Anula la factura"""
        if self.estado == 'ANULADA':
            raise ValueError("La factura ya está anulada")
        self.estado = 'ANULADA'
        return self

    def to_dict(self, incluir_detalles=True):
        data = {
            'id': self.id,
            'orden_trabajo_id': self.orden_trabajo_id,
            'propietario_id': self.propietario_id,
            'propietario_nombre': self.propietario_nombre,
            'tipo_cliente': self.tipo_cliente,
            'subtotal': self.subtotal,
            'descuento': self.descuento,
            'impuestos': self.impuestos,
            'total': self.total,
            'fecha_emision': self.fecha_emision.isoformat() if self.fecha_emision else None,
            'estado': self.estado,
            'dias_garantia': self.dias_garantia,
            'notas': self.notas,
        }
        if incluir_detalles:
            data['detalles'] = [d.to_dict() for d in self.detalles]
        return data


# ─────────────────────────────────────────────
# MODELO: DetalleFactura (NUEVO)
# ─────────────────────────────────────────────

class DetalleFactura(db.Model):
    """Línea de detalle de una factura"""
    __tablename__ = 'detalle_factura'

    # ── Tipos de línea ──
    TIPOS = ['SERVICIO', 'REPUESTO', 'MANO_OBRA']

    id = db.Column(db.Integer, primary_key=True)
    factura_id = db.Column(
        db.Integer, db.ForeignKey('factura_servicio.id'), nullable=False,
    )
    tipo = db.Column(db.String(15), default='SERVICIO')
    descripcion = db.Column(db.String(200), nullable=False)
    cantidad = db.Column(db.Integer, default=1)
    precio_unitario = db.Column(db.Float, default=0.0)

    def calcular_subtotal(self):
        """Retorna cantidad * precio_unitario"""
        return round(self.cantidad * self.precio_unitario, 2)

    def to_dict(self):
        return {
            'id': self.id,
            'factura_id': self.factura_id,
            'tipo': self.tipo,
            'descripcion': self.descripcion,
            'cantidad': self.cantidad,
            'precio_unitario': self.precio_unitario,
            'subtotal': self.calcular_subtotal(),
        }
