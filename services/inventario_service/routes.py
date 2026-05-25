"""
services/inventario_service/routes.py
─────────────────────────────────────────────────────────────
Endpoints HTTP del microservicio Inventario.

Estructura:
  - Blueprint inventario_bp  → /api/v2/inventario/*
  - Blueprint catalogo_bp    → /api/v2/catalogo/*  (público)

Las rutas son "porteros": validan sintaxis y delegan al Service Layer.
─────────────────────────────────────────────────────────────
"""

from flask import Blueprint, request, jsonify
from services import (
    ParteService, ProveedorService,
    OrdenCompraService, CatalogoService,
)

# ─────────────────────────────────────────────
# Blueprints
# ─────────────────────────────────────────────

inventario_bp = Blueprint('inventario', __name__, url_prefix='/api/v2/inventario')
catalogo_bp = Blueprint('catalogo', __name__, url_prefix='/api/v2/catalogo')


# ═════════════════════════════════════════════
# HEALTH CHECK
# ═════════════════════════════════════════════

@inventario_bp.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'servicio': 'inventario'}), 200


# ═════════════════════════════════════════════
# PARTES MECÁNICAS
# ═════════════════════════════════════════════

@inventario_bp.route('/partes/', methods=['GET'])
def listar_partes():
    categoria = request.args.get('categoria')
    solo_con_stock = request.args.get('solo_con_stock', 'false').lower() == 'true'
    partes = ParteService.listar(categoria=categoria, solo_con_stock=solo_con_stock)
    return jsonify({
        'total': len(partes),
        'partes': [p.to_dict(incluir_proveedor=True) for p in partes],
    }), 200


@inventario_bp.route('/partes/<int:parte_id>/', methods=['GET'])
def obtener_parte(parte_id):
    try:
        parte = ParteService.obtener(parte_id)
        return jsonify(parte.to_dict(incluir_proveedor=True)), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 404


@inventario_bp.route('/partes/', methods=['POST'])
def crear_parte():
    datos = request.get_json() or {}
    requeridos = ['codigo_oem', 'nombre', 'precio_compra', 'precio_venta']
    faltantes = [c for c in requeridos if c not in datos]
    if faltantes:
        return jsonify({'error': f'Faltan campos: {faltantes}'}), 400
    try:
        parte = ParteService.crear(datos)
        return jsonify(parte.to_dict()), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 409


@inventario_bp.route('/partes/<int:parte_id>/stock/', methods=['PUT'])
def actualizar_stock(parte_id):
    datos = request.get_json() or {}
    cantidad = datos.get('cantidad')
    operacion = datos.get('operacion', 'descontar')
    if cantidad is None:
        return jsonify({'error': 'Falta el campo cantidad'}), 400
    try:
        parte = ParteService.actualizar_stock(parte_id, int(cantidad), operacion)
        return jsonify(parte.to_dict()), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@inventario_bp.route('/partes/stock-bajo/', methods=['GET'])
def stock_bajo():
    partes = ParteService.partes_con_stock_bajo()
    return jsonify({
        'total': len(partes),
        'partes': [p.to_dict() for p in partes],
    }), 200


# ═════════════════════════════════════════════
# PROVEEDORES
# ═════════════════════════════════════════════

@inventario_bp.route('/proveedores/', methods=['GET'])
def listar_proveedores():
    solo_activos = request.args.get('solo_activos', 'true').lower() == 'true'
    proveedores = ProveedorService.listar(solo_activos=solo_activos)
    return jsonify({
        'total': len(proveedores),
        'proveedores': [p.to_dict() for p in proveedores],
    }), 200


@inventario_bp.route('/proveedores/<int:proveedor_id>/', methods=['GET'])
def obtener_proveedor(proveedor_id):
    try:
        prov = ProveedorService.obtener(proveedor_id)
        return jsonify(prov.to_dict()), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 404


@inventario_bp.route('/proveedores/', methods=['POST'])
def crear_proveedor():
    datos = request.get_json() or {}
    requeridos = ['nit', 'nombre']
    faltantes = [c for c in requeridos if c not in datos]
    if faltantes:
        return jsonify({'error': f'Faltan campos: {faltantes}'}), 400
    try:
        prov = ProveedorService.crear(datos)
        return jsonify(prov.to_dict()), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 409


@inventario_bp.route('/proveedores/<int:proveedor_id>/desactivar/', methods=['POST'])
def desactivar_proveedor(proveedor_id):
    try:
        prov = ProveedorService.desactivar(proveedor_id)
        return jsonify(prov.to_dict()), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 404


# ═════════════════════════════════════════════
# ÓRDENES DE COMPRA
# ═════════════════════════════════════════════

@inventario_bp.route('/ordenes-compra/', methods=['GET'])
def listar_ordenes_compra():
    estado = request.args.get('estado')
    ordenes = OrdenCompraService.listar(estado=estado)
    return jsonify({
        'total': len(ordenes),
        'ordenes': [o.to_dict(incluir_detalles=False) for o in ordenes],
    }), 200


@inventario_bp.route('/ordenes-compra/<int:orden_id>/', methods=['GET'])
def obtener_orden_compra(orden_id):
    try:
        orden = OrdenCompraService.obtener(orden_id)
        return jsonify(orden.to_dict()), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 404


@inventario_bp.route('/ordenes-compra/', methods=['POST'])
def crear_orden_compra():
    datos = request.get_json() or {}
    if 'proveedor_id' not in datos or 'detalles' not in datos:
        return jsonify({'error': 'Faltan proveedor_id o detalles'}), 400
    try:
        orden = OrdenCompraService.crear(datos)
        return jsonify(orden.to_dict()), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@inventario_bp.route('/ordenes-compra/<int:orden_id>/enviar/', methods=['POST'])
def enviar_orden_compra(orden_id):
    try:
        orden = OrdenCompraService.enviar(orden_id)
        return jsonify(orden.to_dict()), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@inventario_bp.route('/ordenes-compra/<int:orden_id>/recibir/', methods=['POST'])
def recibir_orden_compra(orden_id):
    try:
        orden = OrdenCompraService.recibir(orden_id)
        return jsonify({
            'orden': orden.to_dict(),
            'mensaje': 'Stock actualizado correctamente',
        }), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@inventario_bp.route('/ordenes-compra/<int:orden_id>/cancelar/', methods=['POST'])
def cancelar_orden_compra(orden_id):
    try:
        orden = OrdenCompraService.cancelar(orden_id)
        return jsonify(orden.to_dict()), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


# ═════════════════════════════════════════════
# CATÁLOGO PÚBLICO (Servicio a Proveer — Entregable 2)
# ═════════════════════════════════════════════

@catalogo_bp.route('/', methods=['GET'])
def obtener_catalogo():
    """
    Endpoint público para equipos aliados.
    Expone servicios del taller + partes destacadas.
    """
    catalogo = CatalogoService.obtener_catalogo()
    return jsonify(catalogo), 200


@catalogo_bp.route('/health', methods=['GET'])
def health_catalogo():
    return jsonify({'status': 'ok', 'servicio': 'catalogo'}), 200
