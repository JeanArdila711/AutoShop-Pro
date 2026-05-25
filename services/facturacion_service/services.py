"""
services/facturacion_service/services.py
─────────────────────────────────────────────────────────────
Service Layer del microservicio Facturación.

Servicios:
  - FacturaService     — CRUD + lógica de negocio de facturas
  - ReporteService     — resumen de facturación
─────────────────────────────────────────────────────────────
"""

from models import db, FacturaServicio, DetalleFactura


class FacturaService:
    """Servicio de dominio para facturas"""

    @staticmethod
    def listar(estado=None, propietario_id=None):
        """Lista facturas con filtros opcionales"""
        query = FacturaServicio.query
        if estado:
            query = query.filter_by(estado=estado.upper())
        if propietario_id:
            query = query.filter_by(propietario_id=propietario_id)
        return query.order_by(FacturaServicio.fecha_emision.desc()).all()

    @staticmethod
    def obtener(factura_id):
        """Obtiene una factura por ID"""
        factura = FacturaServicio.query.get(factura_id)
        if not factura:
            raise ValueError(f"Factura #{factura_id} no encontrada")
        return factura

    @staticmethod
    def obtener_por_orden(orden_trabajo_id):
        """Obtiene la factura de una orden de trabajo"""
        factura = FacturaServicio.query.filter_by(
            orden_trabajo_id=orden_trabajo_id
        ).first()
        if not factura:
            raise ValueError(
                f"No existe factura para la orden #{orden_trabajo_id}"
            )
        return factura

    @staticmethod
    def crear(datos):
        """
        Crea una factura con sus detalles.

        datos esperados:
          - orden_trabajo_id (int, requerido)
          - propietario_id (int, requerido)
          - propietario_nombre (str, opcional)
          - tipo_cliente (str, opcional: REGULAR/VIP/PREMIUM)
          - descuento (float, opcional)
          - notas (str, opcional)
          - detalles (list of dict, requerido):
              - tipo: SERVICIO|REPUESTO|MANO_OBRA
              - descripcion: str
              - cantidad: int
              - precio_unitario: float
        """
        # Validar que no exista factura para esa orden
        existente = FacturaServicio.query.filter_by(
            orden_trabajo_id=datos['orden_trabajo_id']
        ).first()
        if existente:
            raise ValueError(
                f"Ya existe factura #{existente.id} para la orden "
                f"#{datos['orden_trabajo_id']}"
            )

        # Validar detalles
        detalles_data = datos.get('detalles', [])
        if not detalles_data:
            raise ValueError("La factura debe tener al menos un detalle")

        # Crear factura
        factura = FacturaServicio(
            orden_trabajo_id=datos['orden_trabajo_id'],
            propietario_id=datos['propietario_id'],
            propietario_nombre=datos.get('propietario_nombre', ''),
            tipo_cliente=datos.get('tipo_cliente', 'REGULAR'),
            descuento=datos.get('descuento', 0),
            notas=datos.get('notas', ''),
        )

        # Asignar garantía según tipo de cliente
        factura.asignar_garantia()

        db.session.add(factura)
        db.session.flush()  # para obtener factura.id

        # Crear detalles
        for det in detalles_data:
            detalle = DetalleFactura(
                factura_id=factura.id,
                tipo=det.get('tipo', 'SERVICIO'),
                descripcion=det['descripcion'],
                cantidad=det.get('cantidad', 1),
                precio_unitario=det.get('precio_unitario', 0),
            )
            db.session.add(detalle)

        db.session.flush()

        # Calcular totales
        factura.generar_total()
        db.session.commit()

        # Publicar evento
        try:
            import sys
            sys.path.insert(0, '/app/_shared')
            from events import EventBus, EVENTO_FACTURA_GENERADA
            EventBus.publicar(EVENTO_FACTURA_GENERADA, {
                'factura_id': factura.id,
                'orden_trabajo_id': factura.orden_trabajo_id,
                'total': factura.total,
                'propietario_nombre': factura.propietario_nombre,
            })
        except Exception as e:
            print(f"[facturacion] Evento no publicado: {e}")

        return factura

    @staticmethod
    def pagar(factura_id):
        """Marca una factura como pagada"""
        factura = FacturaService.obtener(factura_id)
        factura.pagar()
        db.session.commit()

        # Publicar evento
        try:
            import sys
            sys.path.insert(0, '/app/_shared')
            from events import EventBus, EVENTO_FACTURA_PAGADA
            EventBus.publicar(EVENTO_FACTURA_PAGADA, {
                'factura_id': factura.id,
                'orden_trabajo_id': factura.orden_trabajo_id,
                'total': factura.total,
            })
        except Exception as e:
            print(f"[facturacion] Evento no publicado: {e}")

        return factura

    @staticmethod
    def anular(factura_id):
        """Anula una factura"""
        factura = FacturaService.obtener(factura_id)
        factura.anular()
        db.session.commit()
        return factura

    @staticmethod
    def agregar_detalle(factura_id, datos):
        """Agrega una línea de detalle y recalcula totales"""
        factura = FacturaService.obtener(factura_id)

        if factura.estado != 'PENDIENTE':
            raise ValueError(
                "Solo se pueden agregar detalles a facturas pendientes"
            )

        detalle = DetalleFactura(
            factura_id=factura.id,
            tipo=datos.get('tipo', 'SERVICIO'),
            descripcion=datos['descripcion'],
            cantidad=datos.get('cantidad', 1),
            precio_unitario=datos.get('precio_unitario', 0),
        )
        db.session.add(detalle)
        db.session.flush()

        # Recalcular totales
        factura.generar_total()
        db.session.commit()

        return factura


class ReporteService:
    """Servicio de reportes de facturación"""

    @staticmethod
    def resumen():
        """Retorna resumen general de facturación"""
        todas = FacturaServicio.query.all()
        pendientes = [f for f in todas if f.estado == 'PENDIENTE']
        pagadas = [f for f in todas if f.estado == 'PAGADA']
        anuladas = [f for f in todas if f.estado == 'ANULADA']

        return {
            'total_facturas': len(todas),
            'pendientes': len(pendientes),
            'pagadas': len(pagadas),
            'anuladas': len(anuladas),
            'monto_pendiente': round(sum(f.total for f in pendientes), 2),
            'monto_cobrado': round(sum(f.total for f in pagadas), 2),
            'monto_anulado': round(sum(f.total for f in anuladas), 2),
            'impuestos_recaudados': round(
                sum(f.impuestos for f in pagadas), 2
            ),
        }
