"""
services/ordenes_service/routes.py
─────────────────────────────────────────────────────────────
Endpoints HTTP del microservicio Órdenes de Trabajo.

Blueprints:
  - ordenes_bp → /api/v2/ordenes/*
  - bahias_bp  → /api/v2/ordenes/bahias/*

Las rutas son "porteros": validan sintaxis y delegan al Service Layer.
─────────────────────────────────────────────────────────────
"""

from flask import Blueprint, request, jsonify, send_from_directory
from services import (
    OrdenService, TimerService, ChecklistService,
    EvidenciaService, BahiaService,
)

ordenes_bp = Blueprint('ordenes', __name__, url_prefix='/api/v2/ordenes')


# ═════════════════════════════════════════════
# HEALTH CHECK
# ═════════════════════════════════════════════

@ordenes_bp.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'servicio': 'ordenes'}), 200


# ═════════════════════════════════════════════
# ÓRDENES — CRUD
# ═════════════════════════════════════════════

@ordenes_bp.route('/', methods=['GET'])
def listar_ordenes():
    """Lista órdenes. Filtros: ?estado=ABIERTA&mecanico_id=1&activas=true"""
    estado = request.args.get('estado')
    mecanico_id = request.args.get('mecanico_id', type=int)
    solo_activas = request.args.get('activas', 'false').lower() == 'true'
    ordenes = OrdenService.listar(
        estado=estado, mecanico_id=mecanico_id, solo_activas=solo_activas,
    )
    return jsonify({
        'total': len(ordenes),
        'ordenes': [o.to_dict() for o in ordenes],
    }), 200


@ordenes_bp.route('/<int:orden_id>/', methods=['GET'])
def obtener_orden(orden_id):
    """Obtiene una orden con todos sus detalles"""
    try:
        orden = OrdenService.obtener(orden_id)
        return jsonify(orden.to_dict(incluir_detalles=True)), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 404


@ordenes_bp.route('/', methods=['POST'])
def crear_orden():
    """
    Crea una orden de trabajo.

    Body JSON:
    {
        "vehiculo_id": 1,
        "vehiculo_placa": "ABC123",
        "vehiculo_marca": "Chevrolet",
        "vehiculo_modelo": "Spark",
        "propietario_id": 1,
        "propietario_nombre": "Carlos Martínez",
        "descripcion_problema": "Ruido en frenos delanteros",
        "odometer_km": 45000,
        "mecanico_id": 1,
        "mecanico_nombre": "Pedro García",
        "costo_presupuestado": 250000,
        "tiempo_estimado": 3
    }
    """
    datos = request.get_json() or {}
    requeridos = ['vehiculo_id', 'propietario_id', 'descripcion_problema']
    faltantes = [c for c in requeridos if c not in datos]
    if faltantes:
        return jsonify({'error': f'Faltan campos: {faltantes}'}), 400
    try:
        orden = OrdenService.crear(datos)
        return jsonify(orden.to_dict()), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@ordenes_bp.route('/<int:orden_id>/', methods=['PUT'])
def actualizar_orden(orden_id):
    """Actualiza campos de una orden"""
    datos = request.get_json() or {}
    try:
        orden = OrdenService.actualizar(orden_id, datos)
        return jsonify(orden.to_dict()), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


# ═════════════════════════════════════════════
# ÓRDENES — ESTADO
# ═════════════════════════════════════════════

@ordenes_bp.route('/<int:orden_id>/estado/', methods=['PUT'])
def cambiar_estado(orden_id):
    """
    Cambia el estado de una orden.
    Body: { "estado": "EN_DIAGNOSTICO" }
    """
    datos = request.get_json() or {}
    nuevo_estado = datos.get('estado', '').upper()
    if not nuevo_estado:
        return jsonify({'error': 'Falta el campo estado'}), 400
    try:
        orden = OrdenService.cambiar_estado(orden_id, nuevo_estado)
        return jsonify({
            'orden': orden.to_dict(),
            'mensaje': f'Estado cambiado a {nuevo_estado}',
        }), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


# ═════════════════════════════════════════════
# ÓRDENES — ASIGNACIONES
# ═════════════════════════════════════════════

@ordenes_bp.route('/<int:orden_id>/asignar-mecanico/', methods=['POST'])
def asignar_mecanico(orden_id):
    """Body: { "mecanico_id": 1, "mecanico_nombre": "Pedro" }"""
    datos = request.get_json() or {}
    if 'mecanico_id' not in datos:
        return jsonify({'error': 'Falta mecanico_id'}), 400
    try:
        orden = OrdenService.asignar_mecanico(
            orden_id, datos['mecanico_id'],
            datos.get('mecanico_nombre', ''),
        )
        return jsonify(orden.to_dict()), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@ordenes_bp.route('/<int:orden_id>/asignar-bahia/', methods=['POST'])
def asignar_bahia(orden_id):
    """Body: { "bahia_codigo": "B-01" }"""
    datos = request.get_json() or {}
    if 'bahia_codigo' not in datos:
        return jsonify({'error': 'Falta bahia_codigo'}), 400
    try:
        orden = OrdenService.asignar_bahia(orden_id, datos['bahia_codigo'])
        return jsonify(orden.to_dict()), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


# ═════════════════════════════════════════════
# TIMER — CRONÓMETRO
# ═════════════════════════════════════════════

@ordenes_bp.route('/<int:orden_id>/timer/iniciar/', methods=['POST'])
def iniciar_timer(orden_id):
    """Inicia un timer. Body opcional: { "nota": "Diagnóstico motor" }"""
    datos = request.get_json() or {}
    try:
        timer = TimerService.iniciar(orden_id, datos.get('nota', ''))
        return jsonify(timer.to_dict()), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@ordenes_bp.route('/<int:orden_id>/timer/detener/', methods=['POST'])
def detener_timer(orden_id):
    """Detiene el timer activo de una orden"""
    try:
        timer = TimerService.detener(orden_id)
        return jsonify({
            'timer': timer.to_dict(),
            'mensaje': f'Timer detenido. Duración: {timer.duracion_horas()}h',
        }), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@ordenes_bp.route('/<int:orden_id>/timers/', methods=['GET'])
def listar_timers(orden_id):
    """Lista todos los timers de una orden"""
    timers = TimerService.listar(orden_id)
    return jsonify({
        'total': len(timers),
        'timers': [t.to_dict() for t in timers],
    }), 200


# ═════════════════════════════════════════════
# CHECKLIST — DIAGNÓSTICO
# ═════════════════════════════════════════════

@ordenes_bp.route('/checklists/templates/', methods=['GET'])
def listar_templates():
    """Lista todas las plantillas de checklist disponibles"""
    templates = ChecklistService.listar_templates()
    return jsonify({
        'total': len(templates),
        'templates': [t.to_dict() for t in templates],
    }), 200


@ordenes_bp.route('/<int:orden_id>/checklist/', methods=['POST'])
def aplicar_checklist(orden_id):
    """
    Aplica una plantilla de checklist a una orden.
    Body: { "categoria": "MOTOR" }
    """
    datos = request.get_json() or {}
    categoria = datos.get('categoria', '')
    if not categoria:
        return jsonify({'error': 'Falta el campo categoria'}), 400
    try:
        checklist = ChecklistService.aplicar_checklist(orden_id, categoria)
        return jsonify(checklist.to_dict()), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@ordenes_bp.route('/<int:orden_id>/checklists/', methods=['GET'])
def listar_checklists(orden_id):
    """Lista todos los checklists aplicados a una orden"""
    checklists = ChecklistService.listar_checklists(orden_id)
    return jsonify({
        'total': len(checklists),
        'checklists': [c.to_dict() for c in checklists],
    }), 200


@ordenes_bp.route('/checklist-item/<int:item_id>/', methods=['PUT'])
def actualizar_checklist_item(item_id):
    """
    Actualiza estado de un ítem del checklist.
    Body: { "estado": "OK", "nota": "Sin problemas" }
    """
    datos = request.get_json() or {}
    estado = datos.get('estado', '')
    if not estado:
        return jsonify({'error': 'Falta el campo estado'}), 400
    try:
        item = ChecklistService.actualizar_item(
            item_id, estado, datos.get('nota', ''),
        )
        return jsonify(item.to_dict()), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


# ═════════════════════════════════════════════
# EVIDENCIAS — FOTOS
# ═════════════════════════════════════════════

@ordenes_bp.route('/<int:orden_id>/evidencia/', methods=['POST'])
def subir_evidencia(orden_id):
    """
    Sube una foto de evidencia (multipart/form-data).
    Campos: archivo (file), momento (ANTES/DURANTE/DESPUES), descripcion
    """
    if 'archivo' not in request.files:
        return jsonify({'error': 'Falta el archivo de imagen'}), 400

    archivo = request.files['archivo']
    momento = request.form.get('momento', 'ANTES')
    descripcion = request.form.get('descripcion', '')

    try:
        evidencia = EvidenciaService.subir(
            orden_id, archivo, momento, descripcion,
        )
        return jsonify(evidencia.to_dict()), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@ordenes_bp.route('/<int:orden_id>/evidencias/', methods=['GET'])
def listar_evidencias(orden_id):
    """Lista todas las evidencias de una orden"""
    evidencias = EvidenciaService.listar(orden_id)
    return jsonify({
        'total': len(evidencias),
        'evidencias': [e.to_dict() for e in evidencias],
    }), 200


@ordenes_bp.route('/evidencia/<int:evidencia_id>/', methods=['DELETE'])
def eliminar_evidencia(evidencia_id):
    """Elimina una evidencia fotográfica"""
    try:
        EvidenciaService.eliminar(evidencia_id)
        return jsonify({'mensaje': 'Evidencia eliminada'}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 404


@ordenes_bp.route('/evidencias/archivo/<path:nombre>/', methods=['GET'])
def servir_evidencia(nombre):
    """Sirve un archivo de evidencia"""
    return send_from_directory(EvidenciaService.UPLOAD_DIR, nombre)


# ═════════════════════════════════════════════
# BAHÍAS
# ═════════════════════════════════════════════

@ordenes_bp.route('/bahias/', methods=['GET'])
def listar_bahias():
    """Lista bahías. Filtro: ?todas=true para incluir inactivas"""
    solo_activas = request.args.get('todas', 'false').lower() != 'true'
    bahias = BahiaService.listar(solo_activas=solo_activas)
    return jsonify({
        'total': len(bahias),
        'bahias': [b.to_dict() for b in bahias],
    }), 200


@ordenes_bp.route('/bahias/', methods=['POST'])
def crear_bahia():
    """Body: { "codigo": "B-06", "nombre": "Bahía 6", "tipo": "MECANICA" }"""
    datos = request.get_json() or {}
    requeridos = ['codigo', 'nombre']
    faltantes = [c for c in requeridos if c not in datos]
    if faltantes:
        return jsonify({'error': f'Faltan campos: {faltantes}'}), 400
    try:
        bahia = BahiaService.crear(datos)
        return jsonify(bahia.to_dict()), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 409


@ordenes_bp.route('/bahias/<int:bahia_id>/liberar/', methods=['POST'])
def liberar_bahia(bahia_id):
    """Libera una bahía ocupada"""
    try:
        bahia = BahiaService.liberar(bahia_id)
        return jsonify(bahia.to_dict()), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@ordenes_bp.route('/bahias/<int:bahia_id>/desactivar/', methods=['POST'])
def desactivar_bahia(bahia_id):
    """Desactiva una bahía"""
    try:
        bahia = BahiaService.desactivar(bahia_id)
        return jsonify(bahia.to_dict()), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


# ═════════════════════════════════════════════
# ESTADÍSTICAS
# ═════════════════════════════════════════════

@ordenes_bp.route('/estadisticas/', methods=['GET'])
def estadisticas():
    """Retorna estadísticas de órdenes"""
    stats = OrdenService.estadisticas()
    return jsonify(stats), 200
