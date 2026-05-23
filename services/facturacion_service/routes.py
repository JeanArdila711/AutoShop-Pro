"""
services/facturacion_service/routes.py
─────────────────────────────────────────────────────────────
Endpoints HTTP del microservicio Facturación.

Blueprint facturacion_bp → /api/v2/facturacion/*

Las rutas son "porteros": validan sintaxis y delegan al Service Layer.
─────────────────────────────────────────────────────────────
"""

from flask import Blueprint, request, jsonify
from services import FacturaService, ReporteService

facturacion_bp = Blueprint(
    'facturacion', __name__, url_prefix='/api/v2/facturacion'
)


# ═════════════════════════════════════════════
# HEALTH CHECK
# ═════════════════════════════════════════════

@facturacion_bp.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'servicio': 'facturacion'}), 200


# ═════════════════════════════════════════════
# FACTURAS — CRUD
# ═════════════════════════════════════════════

@facturacion_bp.route('/', methods=['GET'])
def listar_facturas():
    """Lista facturas. Filtros: ?estado=PENDIENTE&propietario_id=1"""
    estado = request.args.get('estado')
    propietario_id = request.args.get('propietario_id', type=int)
    facturas = FacturaService.listar(
        estado=estado, propietario_id=propietario_id,
    )
    return jsonify({
        'total': len(facturas),
        'facturas': [f.to_dict(incluir_detalles=False) for f in facturas],
    }), 200


@facturacion_bp.route('/<int:factura_id>/', methods=['GET'])
def obtener_factura(factura_id):
    """Obtiene una factura con sus detalles"""
    try:
        factura = FacturaService.obtener(factura_id)
        return jsonify(factura.to_dict()), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 404


@facturacion_bp.route('/por-orden/<int:orden_id>/', methods=['GET'])
def obtener_por_orden(orden_id):
    """Obtiene la factura asociada a una orden de trabajo"""
    try:
        factura = FacturaService.obtener_por_orden(orden_id)
        return jsonify(factura.to_dict()), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 404


@facturacion_bp.route('/', methods=['POST'])
def crear_factura():
    """
    Crea una factura con detalles.

    Body JSON:
    {
        "orden_trabajo_id": 1,
        "propietario_id": 1,
        "propietario_nombre": "Juan Pérez",
        "tipo_cliente": "VIP",
        "descuento": 15000,
        "notas": "Descuento por cliente frecuente",
        "detalles": [
            {
                "tipo": "SERVICIO",
                "descripcion": "Cambio de aceite",
                "cantidad": 1,
                "precio_unitario": 50000
            },
            {
                "tipo": "REPUESTO",
                "descripcion": "Filtro de aceite OEM-MOTOR-001",
                "cantidad": 1,
                "precio_unitario": 28000
            }
        ]
    }
    """
    datos = request.get_json() or {}

    # Validación de campos requeridos
    requeridos = ['orden_trabajo_id', 'propietario_id', 'detalles']
    faltantes = [c for c in requeridos if c not in datos]
    if faltantes:
        return jsonify({'error': f'Faltan campos: {faltantes}'}), 400

    if not isinstance(datos['detalles'], list) or len(datos['detalles']) == 0:
        return jsonify({'error': 'Debe incluir al menos un detalle'}), 400

    # Validar cada detalle
    for i, det in enumerate(datos['detalles']):
        if 'descripcion' not in det:
            return jsonify({
                'error': f'Falta descripcion en detalle [{i}]'
            }), 400
        if 'precio_unitario' not in det:
            return jsonify({
                'error': f'Falta precio_unitario en detalle [{i}]'
            }), 400

    try:
        factura = FacturaService.crear(datos)
        return jsonify(factura.to_dict()), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 409


# ═════════════════════════════════════════════
# FACTURAS — ACCIONES
# ═════════════════════════════════════════════

@facturacion_bp.route('/<int:factura_id>/pagar/', methods=['POST'])
def pagar_factura(factura_id):
    """Marca una factura como pagada"""
    try:
        factura = FacturaService.pagar(factura_id)
        return jsonify({
            'factura': factura.to_dict(),
            'mensaje': 'Factura marcada como pagada',
        }), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@facturacion_bp.route('/<int:factura_id>/anular/', methods=['POST'])
def anular_factura(factura_id):
    """Anula una factura"""
    try:
        factura = FacturaService.anular(factura_id)
        return jsonify({
            'factura': factura.to_dict(),
            'mensaje': 'Factura anulada',
        }), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@facturacion_bp.route('/<int:factura_id>/detalle/', methods=['POST'])
def agregar_detalle(factura_id):
    """
    Agrega un detalle a una factura pendiente y recalcula totales.

    Body JSON:
    {
        "tipo": "REPUESTO",
        "descripcion": "Pastillas de freno",
        "cantidad": 1,
        "precio_unitario": 75000
    }
    """
    datos = request.get_json() or {}
    if 'descripcion' not in datos or 'precio_unitario' not in datos:
        return jsonify({
            'error': 'Faltan campos: descripcion, precio_unitario'
        }), 400

    try:
        factura = FacturaService.agregar_detalle(factura_id, datos)
        return jsonify(factura.to_dict()), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


# ═════════════════════════════════════════════
# REPORTES
# ═════════════════════════════════════════════

@facturacion_bp.route('/resumen/', methods=['GET'])
def resumen_facturacion():
    """Retorna resumen general de facturación"""
    resumen = ReporteService.resumen()
    return jsonify(resumen), 200
