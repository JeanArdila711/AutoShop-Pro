"""
services/citas_service/services.py
─────────────────────────────────────────────────────────────
Capa de negocio — toda la lógica aquí, las rutas son porteros.

Clases:
  - CitaService      → CRUD + flujo de estados
  - AgendaService    → disponibilidad, slots libres
  - BloqueoService   → gestión de bloqueos de agenda
─────────────────────────────────────────────────────────────
"""

import json
import os
from datetime import date, datetime, time, timedelta, timezone

import redis

from models import BloqueoAgenda, Cita, ESTADOS_CITA, TIPOS_SERVICIO, db

# ── Redis (opcional — no falla si no conecta) ────────────────
try:
    _redis = redis.from_url(os.environ.get('REDIS_URL', 'redis://redis:6379/0'))
    _redis.ping()
except Exception:
    _redis = None


def _publicar_evento(canal: str, payload: dict) -> None:
    if _redis:
        try:
            _redis.publish(canal, json.dumps(payload, default=str))
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────
# CitaService
# ─────────────────────────────────────────────────────────────

class CitaService:

    # ── Consultas ────────────────────────────────────────────

    def listar(self, estado: str = None, fecha: str = None,
               mecanico_id: int = None, propietario_id: int = None) -> list[dict]:
        q = Cita.query
        if estado:
            q = q.filter_by(estado=estado)
        if fecha:
            try:
                fecha_obj = date.fromisoformat(fecha)
                q = q.filter_by(fecha=fecha_obj)
            except ValueError:
                pass
        if mecanico_id:
            q = q.filter_by(mecanico_id=mecanico_id)
        if propietario_id:
            q = q.filter_by(propietario_id=propietario_id)
        return [c.to_dict() for c in q.order_by(Cita.fecha, Cita.hora_inicio).all()]

    def obtener(self, cita_id: int) -> Cita:
        cita = Cita.query.get(cita_id)
        if not cita:
            raise ValueError(f"Cita {cita_id} no encontrada")
        return cita

    # ── Creación ─────────────────────────────────────────────

    def agendar(self, datos: dict) -> dict:
        """Crea una nueva cita validando disponibilidad."""
        campos_req = ['propietario_id', 'propietario_nombre', 'vehiculo_id',
                      'vehiculo_placa', 'fecha', 'hora_inicio']
        for campo in campos_req:
            if not datos.get(campo):
                raise ValueError(f"Campo requerido: {campo}")

        fecha_obj = date.fromisoformat(datos['fecha'])
        hora_obj  = time.fromisoformat(datos['hora_inicio'])

        # Validar que no sea en el pasado
        ahora = datetime.now(timezone.utc).date()
        if fecha_obj < ahora:
            raise ValueError("No se pueden agendar citas en fechas pasadas")

        # Validar solapamiento para el mismo vehículo
        duracion = datos.get('duracion_minutos', 60)
        if self._hay_solapamiento(fecha_obj, hora_obj, duracion, vehiculo_id=datos['vehiculo_id']):
            raise ValueError(
                f"El vehículo {datos['vehiculo_placa']} ya tiene una cita en ese horario"
            )

        # Validar que no haya bloqueo de agenda
        if BloqueoService().hay_bloqueo(fecha_obj, hora_obj):
            raise ValueError("El horario seleccionado está bloqueado")

        tipo = datos.get('tipo_servicio', 'REVISION_GENERAL')
        if tipo not in TIPOS_SERVICIO:
            raise ValueError(f"Tipo de servicio inválido: {tipo}")

        cita = Cita(
            propietario_id=datos['propietario_id'],
            propietario_nombre=datos['propietario_nombre'],
            propietario_email=datos.get('propietario_email'),
            propietario_telefono=datos.get('propietario_telefono'),
            vehiculo_id=datos['vehiculo_id'],
            vehiculo_placa=datos['vehiculo_placa'],
            vehiculo_marca=datos.get('vehiculo_marca'),
            vehiculo_modelo=datos.get('vehiculo_modelo'),
            fecha=fecha_obj,
            hora_inicio=hora_obj,
            duracion_minutos=duracion,
            tipo_servicio=tipo,
            notas=datos.get('notas'),
        )
        db.session.add(cita)
        db.session.commit()

        _publicar_evento('cita.agendada', {'cita_id': cita.id, **cita.to_dict()})
        return cita.to_dict()

    # ── Transiciones de estado ───────────────────────────────

    def confirmar(self, cita_id: int, mecanico_id: int = None,
                  mecanico_nombre: str = None) -> dict:
        cita = self.obtener(cita_id)
        cita.confirmar(mecanico_id=mecanico_id, mecanico_nombre=mecanico_nombre)
        db.session.commit()
        _publicar_evento('cita.confirmada', {'cita_id': cita.id, 'mecanico_id': mecanico_id})
        return cita.to_dict()

    def cancelar(self, cita_id: int, motivo: str = None) -> dict:
        cita = self.obtener(cita_id)
        cita.cancelar(motivo=motivo)
        db.session.commit()
        _publicar_evento('cita.cancelada', {'cita_id': cita.id, 'motivo': motivo})
        return cita.to_dict()

    def completar(self, cita_id: int, orden_trabajo_id: int = None) -> dict:
        cita = self.obtener(cita_id)
        cita.completar(orden_trabajo_id=orden_trabajo_id)
        db.session.commit()
        _publicar_evento('cita.completada', {
            'cita_id': cita.id, 'orden_trabajo_id': orden_trabajo_id
        })
        return cita.to_dict()

    def marcar_no_asistio(self, cita_id: int) -> dict:
        cita = self.obtener(cita_id)
        cita.marcar_no_asistio()
        db.session.commit()
        _publicar_evento('cita.no_asistio', {'cita_id': cita.id})
        return cita.to_dict()

    def actualizar(self, cita_id: int, datos: dict) -> dict:
        """Actualiza campos editables (solo en estado PENDIENTE)."""
        cita = self.obtener(cita_id)
        if cita.estado != 'PENDIENTE':
            raise ValueError("Solo se pueden editar citas en estado PENDIENTE")

        campos_editables = [
            'notas', 'tipo_servicio', 'duracion_minutos',
            'vehiculo_marca', 'vehiculo_modelo',
            'propietario_email', 'propietario_telefono',
        ]
        for campo in campos_editables:
            if campo in datos:
                setattr(cita, campo, datos[campo])

        # Reagendar fecha/hora si se envían
        if 'fecha' in datos:
            cita.fecha = date.fromisoformat(datos['fecha'])
        if 'hora_inicio' in datos:
            cita.hora_inicio = time.fromisoformat(datos['hora_inicio'])

        db.session.commit()
        return cita.to_dict()

    # ── Estadísticas ─────────────────────────────────────────

    def estadisticas(self) -> dict:
        from sqlalchemy import func
        total = Cita.query.count()
        por_estado = {
            e: Cita.query.filter_by(estado=e).count()
            for e in ESTADOS_CITA
        }
        hoy = date.today()
        hoy_count = Cita.query.filter_by(fecha=hoy).count()
        return {
            'total': total,
            'por_estado': por_estado,
            'hoy': hoy_count,
        }

    # ── Helpers privados ─────────────────────────────────────

    def _hay_solapamiento(self, fecha: date, hora: time,
                          duracion: int, vehiculo_id: int) -> bool:
        """Verifica si el vehículo tiene otra cita activa que se solapa."""
        citas_dia = Cita.query.filter(
            Cita.fecha == fecha,
            Cita.vehiculo_id == vehiculo_id,
            Cita.estado.in_(['PENDIENTE', 'CONFIRMADA']),
        ).all()

        nueva_inicio = datetime.combine(fecha, hora)
        nueva_fin    = nueva_inicio + timedelta(minutes=duracion)

        for c in citas_dia:
            ex_inicio = datetime.combine(c.fecha, c.hora_inicio)
            ex_fin    = ex_inicio + timedelta(minutes=c.duracion_minutos)
            if nueva_inicio < ex_fin and nueva_fin > ex_inicio:
                return True
        return False


# ─────────────────────────────────────────────────────────────
# AgendaService
# ─────────────────────────────────────────────────────────────

class AgendaService:
    HORA_APERTURA = time(7, 0)
    HORA_CIERRE   = time(18, 0)
    DURACION_SLOT = 60  # minutos

    def slots_disponibles(self, fecha_str: str) -> list[dict]:
        """Devuelve todos los slots del día con su estado (libre/ocupado)."""
        fecha = date.fromisoformat(fecha_str)
        bloqueo_svc = BloqueoService()

        slots = []
        slot_actual = datetime.combine(fecha, self.HORA_APERTURA)
        cierre      = datetime.combine(fecha, self.HORA_CIERRE)

        while slot_actual < cierre:
            hora = slot_actual.time()
            fin  = (slot_actual + timedelta(minutes=self.DURACION_SLOT)).time()

            bloqueado = bloqueo_svc.hay_bloqueo(fecha, hora)
            ocupado = Cita.query.filter(
                Cita.fecha == fecha,
                Cita.hora_inicio == hora,
                Cita.estado.in_(['PENDIENTE', 'CONFIRMADA']),
            ).count() > 0

            slots.append({
                'hora': hora.strftime('%H:%M'),
                'hora_fin': fin.strftime('%H:%M'),
                'disponible': not bloqueado and not ocupado,
                'bloqueado': bloqueado,
                'ocupado': ocupado,
            })
            slot_actual += timedelta(minutes=self.DURACION_SLOT)

        return slots

    def citas_del_dia(self, fecha_str: str) -> list[dict]:
        fecha = date.fromisoformat(fecha_str)
        citas = Cita.query.filter_by(fecha=fecha)\
                          .order_by(Cita.hora_inicio).all()
        return [c.to_dict() for c in citas]


# ─────────────────────────────────────────────────────────────
# BloqueoService
# ─────────────────────────────────────────────────────────────

class BloqueoService:

    def listar(self) -> list[dict]:
        return [b.to_dict() for b in
                BloqueoAgenda.query.order_by(BloqueoAgenda.fecha).all()]

    def crear(self, datos: dict) -> dict:
        if not datos.get('fecha'):
            raise ValueError("Campo requerido: fecha")
        bloqueo = BloqueoAgenda(
            fecha=date.fromisoformat(datos['fecha']),
            hora_inicio=time.fromisoformat(datos['hora_inicio']) if datos.get('hora_inicio') else None,
            hora_fin=time.fromisoformat(datos['hora_fin']) if datos.get('hora_fin') else None,
            motivo=datos.get('motivo', 'Bloqueo manual'),
        )
        db.session.add(bloqueo)
        db.session.commit()
        return bloqueo.to_dict()

    def eliminar(self, bloqueo_id: int) -> dict:
        bloqueo = BloqueoAgenda.query.get(bloqueo_id)
        if not bloqueo:
            raise ValueError(f"Bloqueo {bloqueo_id} no encontrado")
        db.session.delete(bloqueo)
        db.session.commit()
        return {'mensaje': f'Bloqueo {bloqueo_id} eliminado'}

    def hay_bloqueo(self, fecha: date, hora: time) -> bool:
        """Verifica si existe un bloqueo que cubra esa fecha/hora."""
        bloqueos = BloqueoAgenda.query.filter_by(fecha=fecha).all()
        for b in bloqueos:
            if b.hora_inicio is None:  # día completo
                return True
            if b.hora_inicio <= hora < b.hora_fin:
                return True
        return False
