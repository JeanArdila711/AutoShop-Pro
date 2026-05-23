"""
services/inventario_service/services.py
─────────────────────────────────────────────────────────────
Service Layer del microservicio Inventario.
Centraliza la lógica de negocio. Las views (routes) solo coordinan HTTP.
─────────────────────────────────────────────────────────────
"""

from models import db, ParteMecanica, Proveedor, OrdenCompra, DetalleOrdenCompra


# ═════════════════════════════════════════════
# SERVICIO: Partes Mecánicas
# ═════════════════════════════════════════════

class ParteService:

    @staticmethod
    def listar(categoria=None, solo_con_stock=False):
        query = ParteMecanica.query
        if categoria:
            query = query.filter_by(categoria=categoria)
        if solo_con_stock:
            query = query.filter(ParteMecanica.stock_actual > 0)
        return query.order_by(ParteMecanica.nombre).all()

    @staticmethod
    def obtener(parte_id):
        parte = ParteMecanica.query.get(parte_id)
        if not parte:
            raise ValueError(f"Parte {parte_id} no encontrada")
        return parte

    @staticmethod
    def crear(datos):
        # Validar duplicados
        if ParteMecanica.query.filter_by(codigo_oem=datos['codigo_oem']).first():
            raise ValueError(f"Ya existe una parte con código OEM {datos['codigo_oem']}")

        parte = ParteMecanica(
            codigo_oem=datos['codigo_oem'].upper(),
            nombre=datos['nombre'],
            categoria=datos.get('categoria', 'GENERAL'),
            precio_compra=datos['precio_compra'],
            precio_venta=datos['precio_venta'],
            stock_actual=datos.get('stock_actual', 0),
            stock_minimo=datos.get('stock_minimo', 5),
            proveedor_id=datos.get('proveedor_id'),
        )
        db.session.add(parte)
        db.session.commit()
        return parte

    @staticmethod
    def actualizar_stock(parte_id, cantidad, operacion='descontar'):
        """
        Actualiza el stock. operacion='descontar' o 'incrementar'.
        """
        parte = ParteService.obtener(parte_id)
        if operacion == 'descontar':
            parte.descontar_stock(cantidad)
        elif operacion == 'incrementar':
            parte.incrementar_stock(cantidad)
        else:
            raise ValueError(f"Operación inválida: {operacion}")
        db.session.commit()
        return parte

    @staticmethod
    def partes_con_stock_bajo():
        """Lista de partes que necesitan reorden"""
        return [p for p in ParteMecanica.query.all() if p.necesita_reorden()]


# ═════════════════════════════════════════════
# SERVICIO: Proveedores
# ═════════════════════════════════════════════

class ProveedorService:

    @staticmethod
    def listar(solo_activos=True):
        query = Proveedor.query
        if solo_activos:
            query = query.filter_by(activo=True)
        return query.order_by(Proveedor.nombre).all()

    @staticmethod
    def obtener(proveedor_id):
        proveedor = Proveedor.query.get(proveedor_id)
        if not proveedor:
            raise ValueError(f"Proveedor {proveedor_id} no encontrado")
        return proveedor

    @staticmethod
    def crear(datos):
        if Proveedor.query.filter_by(nit=datos['nit']).first():
            raise ValueError(f"Ya existe un proveedor con NIT {datos['nit']}")

        proveedor = Proveedor(
            nit=datos['nit'],
            nombre=datos['nombre'],
            contacto=datos.get('contacto', ''),
            telefono=datos.get('telefono', ''),
            email=datos.get('email', ''),
            direccion=datos.get('direccion', ''),
            tiempo_entrega_dias=datos.get('tiempo_entrega_dias', 7),
            calificacion=datos.get('calificacion', 5.0),
        )
        db.session.add(proveedor)
        db.session.commit()
        return proveedor

    @staticmethod
    def desactivar(proveedor_id):
        proveedor = ProveedorService.obtener(proveedor_id)
        proveedor.activo = False
        db.session.commit()
        return proveedor


# ═════════════════════════════════════════════
# SERVICIO: Órdenes de Compra
# ═════════════════════════════════════════════

class OrdenCompraService:

    @staticmethod
    def listar(estado=None):
        query = OrdenCompra.query
        if estado:
            query = query.filter_by(estado=estado)
        return query.order_by(OrdenCompra.fecha_creacion.desc()).all()

    @staticmethod
    def obtener(orden_id):
        orden = OrdenCompra.query.get(orden_id)
        if not orden:
            raise ValueError(f"Orden de compra {orden_id} no encontrada")
        return orden

    @staticmethod
    def crear(datos):
        """
        Crea una orden de compra con sus detalles.

        datos = {
            'proveedor_id': int,
            'notas': str (opcional),
            'detalles': [
                {'parte_id': int, 'cantidad': int, 'precio_unitario': float},
                ...
            ]
        }
        """
        proveedor = ProveedorService.obtener(datos['proveedor_id'])

        if not datos.get('detalles'):
            raise ValueError("La orden de compra debe tener al menos un detalle")

        orden = OrdenCompra(
            proveedor_id=proveedor.id,
            notas=datos.get('notas', ''),
        )
        db.session.add(orden)
        db.session.flush()  # para obtener el id

        for d in datos['detalles']:
            parte = ParteService.obtener(d['parte_id'])
            detalle = DetalleOrdenCompra(
                orden_compra_id=orden.id,
                parte_id=parte.id,
                cantidad=d['cantidad'],
                precio_unitario=d['precio_unitario'],
            )
            detalle.calcular_subtotal()
            db.session.add(detalle)

        # Recargar relación detalles antes de calcular total
        db.session.flush()
        orden.calcular_total()
        db.session.commit()
        return orden

    @staticmethod
    def enviar(orden_id):
        orden = OrdenCompraService.obtener(orden_id)
        orden.enviar()
        db.session.commit()
        return orden

    @staticmethod
    def recibir(orden_id):
        orden = OrdenCompraService.obtener(orden_id)
        orden.recibir()  # esto incrementa stock de cada parte
        db.session.commit()
        return orden

    @staticmethod
    def cancelar(orden_id):
        orden = OrdenCompraService.obtener(orden_id)
        orden.cancelar()
        db.session.commit()
        return orden


# ═════════════════════════════════════════════
# SERVICIO: Catálogo Público (para equipo aliado)
# ═════════════════════════════════════════════

class CatalogoService:
    """
    Expone el catálogo de servicios y partes del taller.
    Este es el endpoint público que consume el equipo aliado.
    """

    # Catálogo de servicios estáticos del taller (no son entidades)
    SERVICIOS_TALLER = [
        {
            'codigo': 'CAMBIO_ACEITE',
            'nombre': 'Cambio de aceite y filtro',
            'categoria': 'MOTOR',
            'precio_estimado': 80000,
            'tiempo_estimado_horas': 1,
        },
        {
            'codigo': 'REVISION_FRENOS',
            'nombre': 'Revisión y cambio de pastillas de freno',
            'categoria': 'FRENOS',
            'precio_estimado': 150000,
            'tiempo_estimado_horas': 2,
        },
        {
            'codigo': 'ALINEACION_BALANCEO',
            'nombre': 'Alineación y balanceo',
            'categoria': 'SUSPENSION',
            'precio_estimado': 90000,
            'tiempo_estimado_horas': 2,
        },
        {
            'codigo': 'DIAGNOSTICO_ELECTRICO',
            'nombre': 'Diagnóstico eléctrico computarizado',
            'categoria': 'ELECTRICO',
            'precio_estimado': 60000,
            'tiempo_estimado_horas': 1,
        },
        {
            'codigo': 'REVISION_TRANSMISION',
            'nombre': 'Revisión de transmisión',
            'categoria': 'TRANSMISION',
            'precio_estimado': 250000,
            'tiempo_estimado_horas': 4,
        },
        {
            'codigo': 'MANTENIMIENTO_GENERAL',
            'nombre': 'Mantenimiento general preventivo',
            'categoria': 'GENERAL',
            'precio_estimado': 200000,
            'tiempo_estimado_horas': 3,
        },
    ]

    @staticmethod
    def obtener_catalogo():
        """
        Retorna el catálogo completo para consumo externo.
        Incluye servicios + partes destacadas en stock.
        """
        partes_destacadas = [
            p.to_dict() for p in
            ParteMecanica.query.filter(ParteMecanica.stock_actual > 0)
            .order_by(ParteMecanica.nombre)
            .limit(20).all()
        ]
        return {
            'taller': 'AutoShop Pro',
            'servicios': CatalogoService.SERVICIOS_TALLER,
            'partes_disponibles': partes_destacadas,
            'especialidades': ['MOTOR', 'TRANSMISION', 'SUSPENSION', 'FRENOS', 'ELECTRICO'],
            'horario': 'Lun-Vie 8:00-18:00, Sab 8:00-13:00',
        }
