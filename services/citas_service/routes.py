"""
services/citas_service/routes.py
─────────────────────────────────────────────────────────────
Porteros HTTP — solo coordinan request/response.
Toda la lógica de negocio está en services.py (SOLID/SRP).
─────────────────────────────────────────────────────────────
"""

from flask import Blueprint, jsonify, request

from services import AgendaService, BloqueoService, CitaService

bp = Blueprint('citas', __name__, url_prefix='/api/v2/citas')

_cita_svc   = CitaService()
_agenda_svc = AgendaService()
_bloqueo_svc = BloqueoService()


# ── Health ───────────────────────────────────────────────────

@bp.route('/health')
def health():
    return jsonify({'status': 'ok', 'servicio': 'citas'}), 200


# ── CRUD Citas ───────────────────────────────────────────────

@bp.route('/', methods=['GET'])
def listar_citas():
    """GET /api/v2/citas/?estado=PENDIENTE&fecha=2026-05-25&mecanico_id=1"""
    try:
        citas = _cita_svc.listar(
            estado=request.args.get('estado'),
            fecha=request.args.get('fecha'),
            mecanico_id=request.args.get('mecanico_id', type=int),
            propietario_id=request.args.get('propietario_id', type=int),
        )
        return jsonify({'citas': citas, 'total': len(citas)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:cita_id>/', methods=['GET'])
def obtener_cita(cita_id):
    try:
        cita = _cita_svc.obtener(cita_id)
        return jsonify(cita.to_dict()), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 404


@bp.route('/', methods=['POST'])
def agendar_cita():
    """POST /api/v2/citas/
    Body JSON:
      propietario_id, propietario_nombre, vehiculo_id, vehiculo_placa,
      fecha (YYYY-MM-DD), hora_inicio (HH:MM),
      tipo_servicio?, duracion_minutos?, notas?
    """
    datos = request.get_json(force=True) or {}
    try:
        cita = _cita_svc.agendar(datos)
        return jsonify(cita), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/<int:cita_id>/', methods=['PUT'])
def actualizar_cita(cita_id):
    datos = request.get_json(force=True) or {}
    try:
        cita = _cita_svc.actualizar(cita_id, datos)
        return jsonify(cita), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


# ── Transiciones de estado ───────────────────────────────────

@bp.route('/<int:cita_id>/confirmar/', methods=['POST'])
def confirmar_cita(cita_id):
    """POST body opcional: {mecanico_id, mecanico_nombre}"""
    datos = request.get_json(force=True) or {}
    try:
        cita = _cita_svc.confirmar(
            cita_id,
            mecanico_id=datos.get('mecanico_id'),
            mecanico_nombre=datos.get('mecanico_nombre'),
        )
        return jsonify(cita), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@bp.route('/<int:cita_id>/cancelar/', methods=['POST'])
def cancelar_cita(cita_id):
    """POST body opcional: {motivo}"""
    datos = request.get_json(force=True) or {}
    try:
        cita = _cita_svc.cancelar(cita_id, motivo=datos.get('motivo'))
        return jsonify(cita), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@bp.route('/<int:cita_id>/completar/', methods=['POST'])
def completar_cita(cita_id):
    """POST body opcional: {orden_trabajo_id}"""
    datos = request.get_json(force=True) or {}
    try:
        cita = _cita_svc.completar(cita_id, orden_trabajo_id=datos.get('orden_trabajo_id'))
        return jsonify(cita), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@bp.route('/<int:cita_id>/no-asistio/', methods=['POST'])
def no_asistio(cita_id):
    try:
        cita = _cita_svc.marcar_no_asistio(cita_id)
        return jsonify(cita), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


# ── Agenda ───────────────────────────────────────────────────

@bp.route('/agenda/slots/', methods=['GET'])
def slots_disponibles():
    """GET /api/v2/citas/agenda/slots/?fecha=2026-05-25"""
    fecha = request.args.get('fecha')
    if not fecha:
        return jsonify({'error': 'Parámetro requerido: fecha'}), 400
    try:
        slots = _agenda_svc.slots_disponibles(fecha)
        return jsonify({'fecha': fecha, 'slots': slots}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@bp.route('/agenda/dia/', methods=['GET'])
def citas_del_dia():
    """GET /api/v2/citas/agenda/dia/?fecha=2026-05-25"""
    fecha = request.args.get('fecha')
    if not fecha:
        return jsonify({'error': 'Parámetro requerido: fecha'}), 400
    try:
        citas = _agenda_svc.citas_del_dia(fecha)
        return jsonify({'fecha': fecha, 'citas': citas, 'total': len(citas)}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


# ── Bloqueos ─────────────────────────────────────────────────

@bp.route('/bloqueos/', methods=['GET'])
def listar_bloqueos():
    return jsonify({'bloqueos': _bloqueo_svc.listar()}), 200


@bp.route('/bloqueos/', methods=['POST'])
def crear_bloqueo():
    """POST body: {fecha, hora_inicio?, hora_fin?, motivo?}"""
    datos = request.get_json(force=True) or {}
    try:
        bloqueo = _bloqueo_svc.crear(datos)
        return jsonify(bloqueo), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@bp.route('/bloqueos/<int:bloqueo_id>/', methods=['DELETE'])
def eliminar_bloqueo(bloqueo_id):
    try:
        resultado = _bloqueo_svc.eliminar(bloqueo_id)
        return jsonify(resultado), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 404


# ── Estadísticas ─────────────────────────────────────────────

@bp.route('/estadisticas/', methods=['GET'])
def estadisticas():
    try:
        stats = _cita_svc.estadisticas()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
