"""
services/ordenes_service/services.py
─────────────────────────────────────────────────────────────
Service Layer del microservicio Órdenes de Trabajo.

Servicios:
  - OrdenService       — CRUD + cambio de estado + asignaciones
  - TimerService       — iniciar/detener cronómetros
  - ChecklistService   — templates + aplicar checklist a orden
  - EvidenciaService   — subir/eliminar evidencias fotográficas
  - BahiaService       — gestión de bahías del taller
─────────────────────────────────────────────────────────────
"""

import os
import uuid
from models import (
    db, OrdenTrabajo, Bahia, TimerSession,
    ChecklistTemplate, ChecklistTemplateItem,
    DiagnosticoChecklist, DiagnosticoChecklistItem,
    EvidenciaFoto, ESTADOS_ACTIVOS,
)


class OrdenService:
    """Servicio de dominio para órdenes de trabajo"""

    @staticmethod
    def listar(estado=None, mecanico_id=None, solo_activas=False):
        """Lista órdenes con filtros opcionales"""
        query = OrdenTrabajo.query
        if estado:
            query = query.filter_by(estado=estado.upper())
        if mecanico_id:
            query = query.filter_by(mecanico_id=mecanico_id)
        if solo_activas:
            query = query.filter(OrdenTrabajo.estado.in_(ESTADOS_ACTIVOS))
        return query.order_by(OrdenTrabajo.fecha_ingreso.desc()).all()

    @staticmethod
    def obtener(orden_id):
        """Obtiene una orden por ID"""
        orden = OrdenTrabajo.query.get(orden_id)
        if not orden:
            raise ValueError(f"Orden #{orden_id} no encontrada")
        return orden

    @staticmethod
    def crear(datos):
        """
        Crea una nueva orden de trabajo.

        datos esperados:
          - vehiculo_id, vehiculo_placa, vehiculo_marca, vehiculo_modelo
          - propietario_id, propietario_nombre
          - mecanico_id (opcional), mecanico_nombre (opcional)
          - descripcion_problema
          - odometer_km
          - costo_presupuestado (opcional)
          - tiempo_estimado (opcional, horas)
          - bahia_codigo (opcional)
        """
        orden = OrdenTrabajo(
            vehiculo_id=datos['vehiculo_id'],
            vehiculo_placa=datos.get('vehiculo_placa', ''),
            vehiculo_marca=datos.get('vehiculo_marca', ''),
            vehiculo_modelo=datos.get('vehiculo_modelo', ''),
            propietario_id=datos['propietario_id'],
            propietario_nombre=datos.get('propietario_nombre', ''),
            mecanico_id=datos.get('mecanico_id'),
            mecanico_nombre=datos.get('mecanico_nombre', ''),
            descripcion_problema=datos['descripcion_problema'],
            odometer_km=datos.get('odometer_km', 0),
            costo_presupuestado=datos.get('costo_presupuestado', 0),
            tiempo_estimado=datos.get('tiempo_estimado', 0),
            bahia_codigo=datos.get('bahia_codigo'),
        )

        db.session.add(orden)
        db.session.commit()

        # Publicar evento
        OrdenService._publicar_evento('orden.creada', {
            'orden_id': orden.id,
            'vehiculo_placa': orden.vehiculo_placa,
            'propietario_nombre': orden.propietario_nombre,
        })

        return orden

    @staticmethod
    def cambiar_estado(orden_id, nuevo_estado):
        """Cambia el estado de una orden validando transiciones"""
        orden = OrdenService.obtener(orden_id)
        estado_anterior = orden.estado
        orden.cambiar_estado(nuevo_estado)
        db.session.commit()

        # Publicar evento
        OrdenService._publicar_evento('orden.estado_cambiado', {
            'orden_id': orden.id,
            'estado_anterior': estado_anterior,
            'estado_nuevo': nuevo_estado,
            'vehiculo_placa': orden.vehiculo_placa,
        })

        # Evento especial para orden cerrada
        if nuevo_estado == 'CERRADA':
            OrdenService._publicar_evento('orden.cerrada', {
                'orden_id': orden.id,
                'vehiculo_placa': orden.vehiculo_placa,
                'propietario_nombre': orden.propietario_nombre,
                'costo_real': orden.costo_real,
            })

        return orden

    @staticmethod
    def actualizar(orden_id, datos):
        """Actualiza campos de una orden"""
        orden = OrdenService.obtener(orden_id)

        campos_actualizables = [
            'mecanico_id', 'mecanico_nombre', 'diagnostico',
            'costo_presupuestado', 'costo_real',
            'tiempo_estimado', 'tiempo_real',
            'bahia_codigo', 'fecha_estimada_salida',
        ]

        for campo in campos_actualizables:
            if campo in datos:
                setattr(orden, campo, datos[campo])

        db.session.commit()
        return orden

    @staticmethod
    def asignar_mecanico(orden_id, mecanico_id, mecanico_nombre=''):
        """Asigna un mecánico a una orden"""
        orden = OrdenService.obtener(orden_id)
        orden.mecanico_id = mecanico_id
        orden.mecanico_nombre = mecanico_nombre
        db.session.commit()
        return orden

    @staticmethod
    def asignar_bahia(orden_id, bahia_codigo):
        """Asigna una bahía a una orden"""
        orden = OrdenService.obtener(orden_id)

        # Verificar que la bahía existe y está libre
        bahia = Bahia.query.filter_by(codigo=bahia_codigo).first()
        if not bahia:
            raise ValueError(f"Bahía '{bahia_codigo}' no encontrada")
        if bahia.esta_ocupada() and bahia.orden_actual_id != orden_id:
            raise ValueError(f"Bahía '{bahia_codigo}' está ocupada")

        # Liberar bahía anterior si tenía una
        if orden.bahia_codigo:
            bahia_anterior = Bahia.query.filter_by(
                codigo=orden.bahia_codigo
            ).first()
            if bahia_anterior:
                bahia_anterior.orden_actual_id = None

        # Asignar nueva bahía
        orden.bahia_codigo = bahia_codigo
        bahia.orden_actual_id = orden_id
        db.session.commit()
        return orden

    @staticmethod
    def estadisticas():
        """Retorna estadísticas generales de órdenes"""
        todas = OrdenTrabajo.query.all()
        activas = [o for o in todas if o.esta_activa()]

        por_estado = {}
        for o in todas:
            por_estado[o.estado] = por_estado.get(o.estado, 0) + 1

        return {
            'total': len(todas),
            'activas': len(activas),
            'completadas': len(todas) - len(activas),
            'por_estado': por_estado,
        }

    @staticmethod
    def _publicar_evento(evento, datos):
        """Publica un evento via Redis (best-effort)"""
        try:
            import sys
            sys.path.insert(0, '/app/_shared')
            from events import EventBus
            EventBus.publicar(evento, datos)
        except Exception as e:
            print(f"[ordenes] Evento '{evento}' no publicado: {e}")


class TimerService:
    """Servicio para cronómetros de órdenes"""

    @staticmethod
    def iniciar(orden_id, nota=''):
        """Inicia un nuevo timer para una orden"""
        orden = OrdenService.obtener(orden_id)

        # Verificar que no haya timer activo
        timer_activo = TimerSession.query.filter_by(
            orden_id=orden_id, fin=None,
        ).first()
        if timer_activo:
            raise ValueError(
                f"Ya hay un timer activo (#{timer_activo.id}) para esta orden"
            )

        timer = TimerSession(orden_id=orden_id, nota=nota)
        db.session.add(timer)
        db.session.commit()
        return timer

    @staticmethod
    def detener(orden_id):
        """Detiene el timer activo de una orden"""
        timer = TimerSession.query.filter_by(
            orden_id=orden_id, fin=None,
        ).first()
        if not timer:
            raise ValueError("No hay timer activo para esta orden")

        timer.detener()

        # Actualizar tiempo_real de la orden
        orden = OrdenService.obtener(orden_id)
        orden.tiempo_real = int(orden.calcular_tiempo_total_timers())
        db.session.commit()
        return timer

    @staticmethod
    def listar(orden_id):
        """Lista todos los timers de una orden"""
        return TimerSession.query.filter_by(
            orden_id=orden_id,
        ).order_by(TimerSession.inicio.desc()).all()


class ChecklistService:
    """Servicio para checklists de diagnóstico"""

    @staticmethod
    def listar_templates():
        """Lista todas las plantillas de checklist"""
        return ChecklistTemplate.query.all()

    @staticmethod
    def obtener_template(categoria):
        """Obtiene una plantilla por categoría"""
        template = ChecklistTemplate.query.filter_by(
            categoria=categoria.upper(),
        ).first()
        if not template:
            raise ValueError(f"No hay plantilla para categoría '{categoria}'")
        return template

    @staticmethod
    def aplicar_checklist(orden_id, categoria):
        """
        Aplica una plantilla de checklist a una orden.
        Crea el DiagnosticoChecklist con items en estado PENDIENTE.
        """
        orden = OrdenService.obtener(orden_id)
        template = ChecklistService.obtener_template(categoria)

        checklist = DiagnosticoChecklist(
            orden_id=orden_id,
            categoria=categoria.upper(),
        )
        db.session.add(checklist)
        db.session.flush()

        for item_tpl in template.items:
            item = DiagnosticoChecklistItem(
                checklist_id=checklist.id,
                texto=item_tpl.texto,
                estado='PENDIENTE',
            )
            db.session.add(item)

        db.session.commit()
        return checklist

    @staticmethod
    def actualizar_item(item_id, estado, nota=''):
        """Actualiza el estado de un ítem del checklist"""
        item = DiagnosticoChecklistItem.query.get(item_id)
        if not item:
            raise ValueError(f"Ítem #{item_id} no encontrado")

        estados_validos = ['OK', 'REVISAR', 'FALLA', 'PENDIENTE']
        if estado.upper() not in estados_validos:
            raise ValueError(
                f"Estado inválido. Válidos: {estados_validos}"
            )

        item.estado = estado.upper()
        if nota:
            item.nota = nota
        db.session.commit()
        return item

    @staticmethod
    def listar_checklists(orden_id):
        """Lista todos los checklists aplicados a una orden"""
        return DiagnosticoChecklist.query.filter_by(
            orden_id=orden_id,
        ).order_by(DiagnosticoChecklist.fecha.desc()).all()


class EvidenciaService:
    """Servicio para evidencias fotográficas"""

    UPLOAD_DIR = '/app/uploads/evidencias'

    @staticmethod
    def subir(orden_id, archivo, momento='ANTES', descripcion=''):
        """Sube una foto de evidencia para una orden"""
        orden = OrdenService.obtener(orden_id)

        momentos_validos = ['ANTES', 'DURANTE', 'DESPUES']
        if momento.upper() not in momentos_validos:
            raise ValueError(
                f"Momento inválido. Válidos: {momentos_validos}"
            )

        # Guardar archivo con nombre único
        ext = os.path.splitext(archivo.filename)[1] or '.jpg'
        nombre_archivo = f"ot{orden_id}_{momento}_{uuid.uuid4().hex[:8]}{ext}"
        ruta = os.path.join(EvidenciaService.UPLOAD_DIR, nombre_archivo)
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        archivo.save(ruta)

        evidencia = EvidenciaFoto(
            orden_id=orden_id,
            ruta_archivo=nombre_archivo,
            momento=momento.upper(),
            descripcion=descripcion,
        )
        db.session.add(evidencia)
        db.session.commit()
        return evidencia

    @staticmethod
    def listar(orden_id):
        """Lista todas las evidencias de una orden"""
        return EvidenciaFoto.query.filter_by(
            orden_id=orden_id,
        ).order_by(EvidenciaFoto.fecha).all()

    @staticmethod
    def eliminar(evidencia_id):
        """Elimina una evidencia"""
        evidencia = EvidenciaFoto.query.get(evidencia_id)
        if not evidencia:
            raise ValueError(f"Evidencia #{evidencia_id} no encontrada")

        # Eliminar archivo físico
        ruta = os.path.join(EvidenciaService.UPLOAD_DIR, evidencia.ruta_archivo)
        if os.path.exists(ruta):
            os.remove(ruta)

        db.session.delete(evidencia)
        db.session.commit()
        return True


class BahiaService:
    """Servicio para gestión de bahías del taller"""

    @staticmethod
    def listar(solo_activas=True):
        """Lista bahías del taller"""
        query = Bahia.query
        if solo_activas:
            query = query.filter_by(activa=True)
        return query.order_by(Bahia.codigo).all()

    @staticmethod
    def obtener(bahia_id):
        """Obtiene una bahía por ID"""
        bahia = Bahia.query.get(bahia_id)
        if not bahia:
            raise ValueError(f"Bahía #{bahia_id} no encontrada")
        return bahia

    @staticmethod
    def crear(datos):
        """Crea una nueva bahía"""
        existente = Bahia.query.filter_by(codigo=datos['codigo']).first()
        if existente:
            raise ValueError(f"Ya existe bahía con código '{datos['codigo']}'")

        bahia = Bahia(
            codigo=datos['codigo'],
            nombre=datos['nombre'],
            tipo=datos.get('tipo', 'GENERAL'),
        )
        db.session.add(bahia)
        db.session.commit()
        return bahia

    @staticmethod
    def liberar(bahia_id):
        """Libera una bahía ocupada"""
        bahia = BahiaService.obtener(bahia_id)
        if not bahia.esta_ocupada():
            raise ValueError("La bahía no está ocupada")

        # Quitar referencia de la orden
        orden = OrdenTrabajo.query.get(bahia.orden_actual_id)
        if orden:
            orden.bahia_codigo = None

        bahia.orden_actual_id = None
        db.session.commit()
        return bahia

    @staticmethod
    def desactivar(bahia_id):
        """Desactiva una bahía"""
        bahia = BahiaService.obtener(bahia_id)
        if bahia.esta_ocupada():
            raise ValueError(
                "No se puede desactivar una bahía ocupada"
            )
        bahia.activa = False
        db.session.commit()
        return bahia
