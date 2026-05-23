"""
services/inventario_service/models.py
─────────────────────────────────────────────────────────────
Modelos del microservicio de Inventario.

Entidades:
  - ParteMecanica       (migrada desde Django)
  - Proveedor           (NUEVA — Entregable 2)
  - OrdenCompra         (NUEVA — Entregable 2)
  - DetalleOrdenCompra  (NUEVA — Entregable 2)
─────────────────────────────────────────────────────────────
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


# ─────────────────────────────────────────────
# ENUMS (como constantes — SQLAlchemy no tiene TextChoices)
# ─────────────────────────────────────────────

CATEGORIAS_COMPONENTE = [
    'MOTOR', 'TRANSMISION', 'SUSPENSION',
    'FRENOS', 'ELECTRICO', 'CARROCERIA', 'GENERAL',
]

ESTADOS_ORDEN_COMPRA = [
    'BORRADOR',   # se está armando
    'ENVIADA',    # enviada al proveedor
    'RECIBIDA',   # llegó la mercancía
    'CANCELADA',  # cancelada
]


# ─────────────────────────────────────────────
# MODELO: Parte Mecánica (migrado desde Django)
# ─────────────────────────────────────────────

class ParteMecanica(db.Model):
    __tablename__ = 'partes_mecanicas'

    id = db.Column(db.Integer, primary_key=True)
    codigo_oem = db.Column(db.String(30), unique=True, nullable=False)
    nombre = db.Column(db.String(120), nullable=False)
    categoria = db.Column(db.String(20), default='GENERAL')
    precio_compra = db.Column(db.Numeric(12, 2), nullable=False)
    precio_venta = db.Column(db.Numeric(12, 2), nullable=False)
    stock_actual = db.Column(db.Integer, default=0)
    stock_minimo = db.Column(db.Integer, default=5)
    fecha_vencimiento = db.Column(db.Date, nullable=True)

    # Relación opcional con proveedor preferido
    proveedor_id = db.Column(db.Integer, db.ForeignKey('proveedores.id'), nullable=True)
    proveedor = db.relationship('Proveedor', back_populates='partes')

    def to_dict(self, incluir_proveedor=False):
        data = {
            'id': self.id,
            'codigo_oem': self.codigo_oem,
            'nombre': self.nombre,
            'categoria': self.categoria,
            'precio_compra': float(self.precio_compra),
            'precio_venta': float(self.precio_venta),
            'stock_actual': self.stock_actual,
            'stock_minimo': self.stock_minimo,
            'necesita_reorden': self.necesita_reorden(),
            'fecha_vencimiento': self.fecha_vencimiento.isoformat() if self.fecha_vencimiento else None,
        }
        if incluir_proveedor and self.proveedor:
            data['proveedor'] = {
                'id': self.proveedor.id,
                'nombre': self.proveedor.nombre,
            }
        return data

    # ── Métodos de negocio ──

    def verificar_stock(self, cantidad):
        return self.stock_actual >= cantidad

    def necesita_reorden(self):
        return self.stock_actual < self.stock_minimo

    def descontar_stock(self, cantidad):
        if not self.verificar_stock(cantidad):
            raise ValueError(
                f"Stock insuficiente para {self.nombre}. "
                f"Disponible: {self.stock_actual}, solicitado: {cantidad}"
            )
        self.stock_actual -= cantidad

    def incrementar_stock(self, cantidad):
        if cantidad <= 0:
            raise ValueError("La cantidad debe ser positiva")
        self.stock_actual += cantidad


# ─────────────────────────────────────────────
# MODELO: Proveedor (NUEVO)
# ─────────────────────────────────────────────

class Proveedor(db.Model):
    __tablename__ = 'proveedores'

    id = db.Column(db.Integer, primary_key=True)
    nit = db.Column(db.String(20), unique=True, nullable=False)
    nombre = db.Column(db.String(120), nullable=False)
    contacto = db.Column(db.String(120), default='')
    telefono = db.Column(db.String(20), default='')
    email = db.Column(db.String(254), default='')
    direccion = db.Column(db.String(200), default='')
    tiempo_entrega_dias = db.Column(db.Integer, default=7)
    calificacion = db.Column(db.Float, default=5.0)  # 1.0 a 5.0
    activo = db.Column(db.Boolean, default=True)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones
    partes = db.relationship('ParteMecanica', back_populates='proveedor')
    ordenes_compra = db.relationship('OrdenCompra', back_populates='proveedor')

    def to_dict(self):
        return {
            'id': self.id,
            'nit': self.nit,
            'nombre': self.nombre,
            'contacto': self.contacto,
            'telefono': self.telefono,
            'email': self.email,
            'direccion': self.direccion,
            'tiempo_entrega_dias': self.tiempo_entrega_dias,
            'calificacion': self.calificacion,
            'activo': self.activo,
            'total_ordenes': len(self.ordenes_compra),
        }

    def es_confiable(self):
        """Un proveedor es confiable si su calificación es >= 4.0"""
        return self.calificacion >= 4.0


# ─────────────────────────────────────────────
# MODELO: Orden de Compra (NUEVA)
# ─────────────────────────────────────────────

class OrdenCompra(db.Model):
    __tablename__ = 'ordenes_compra'

    id = db.Column(db.Integer, primary_key=True)
    proveedor_id = db.Column(db.Integer, db.ForeignKey('proveedores.id'), nullable=False)
    estado = db.Column(db.String(15), default='BORRADOR')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_envio = db.Column(db.DateTime, nullable=True)
    fecha_recepcion = db.Column(db.DateTime, nullable=True)
    subtotal = db.Column(db.Numeric(12, 2), default=0)
    total = db.Column(db.Numeric(12, 2), default=0)
    notas = db.Column(db.Text, default='')

    # Relaciones
    proveedor = db.relationship('Proveedor', back_populates='ordenes_compra')
    detalles = db.relationship(
        'DetalleOrdenCompra',
        back_populates='orden_compra',
        cascade='all, delete-orphan',
    )

    def to_dict(self, incluir_detalles=True):
        data = {
            'id': self.id,
            'proveedor': {
                'id': self.proveedor.id,
                'nombre': self.proveedor.nombre,
            },
            'estado': self.estado,
            'fecha_creacion': self.fecha_creacion.isoformat(),
            'fecha_envio': self.fecha_envio.isoformat() if self.fecha_envio else None,
            'fecha_recepcion': self.fecha_recepcion.isoformat() if self.fecha_recepcion else None,
            'subtotal': float(self.subtotal),
            'total': float(self.total),
            'notas': self.notas,
        }
        if incluir_detalles:
            data['detalles'] = [d.to_dict() for d in self.detalles]
        return data

    # ── Métodos de negocio ──

    def calcular_total(self):
        """Recalcula el total sumando los detalles"""
        self.subtotal = sum(float(d.subtotal) for d in self.detalles)
        self.total = self.subtotal  # sin IVA por ahora (lo agrega facturación)
        return self.total

    def enviar(self):
        """Marca la orden como enviada al proveedor"""
        if self.estado != 'BORRADOR':
            raise ValueError(f"Solo se pueden enviar órdenes en BORRADOR (actual: {self.estado})")
        if not self.detalles:
            raise ValueError("La orden no tiene detalles")
        self.estado = 'ENVIADA'
        self.fecha_envio = datetime.utcnow()

    def recibir(self):
        """Marca la orden como recibida y suma stock a cada parte"""
        if self.estado != 'ENVIADA':
            raise ValueError(f"Solo se pueden recibir órdenes ENVIADAS (actual: {self.estado})")
        self.estado = 'RECIBIDA'
        self.fecha_recepcion = datetime.utcnow()
        # Incrementar stock de cada parte
        for detalle in self.detalles:
            detalle.parte.incrementar_stock(detalle.cantidad)

    def cancelar(self):
        if self.estado == 'RECIBIDA':
            raise ValueError("No se puede cancelar una orden ya recibida")
        self.estado = 'CANCELADA'


# ─────────────────────────────────────────────
# MODELO: Detalle de Orden de Compra (NUEVO)
# ─────────────────────────────────────────────

class DetalleOrdenCompra(db.Model):
    __tablename__ = 'detalles_orden_compra'

    id = db.Column(db.Integer, primary_key=True)
    orden_compra_id = db.Column(db.Integer, db.ForeignKey('ordenes_compra.id'), nullable=False)
    parte_id = db.Column(db.Integer, db.ForeignKey('partes_mecanicas.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Numeric(12, 2), nullable=False)
    subtotal = db.Column(db.Numeric(12, 2), nullable=False)

    orden_compra = db.relationship('OrdenCompra', back_populates='detalles')
    parte = db.relationship('ParteMecanica')

    def to_dict(self):
        return {
            'id': self.id,
            'parte': {
                'id': self.parte.id,
                'codigo_oem': self.parte.codigo_oem,
                'nombre': self.parte.nombre,
            },
            'cantidad': self.cantidad,
            'precio_unitario': float(self.precio_unitario),
            'subtotal': float(self.subtotal),
        }

    def calcular_subtotal(self):
        self.subtotal = float(self.precio_unitario) * self.cantidad
        return self.subtotal
