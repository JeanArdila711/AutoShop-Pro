"""
services/_shared/events.py
─────────────────────────────────────────────────────────────
Publisher de eventos a Redis — usado por todos los microservicios
para emitir eventos asíncronos que serán consumidos por
notificaciones_service (vía Celery) o cualquier otro suscriptor.

Patrón: Publish/Subscribe (Observer distribuido)
─────────────────────────────────────────────────────────────
"""

import os
import json
import redis
from datetime import datetime


# Nombres canónicos de los eventos del sistema
EVENTO_ORDEN_CREADA = "orden.creada"
EVENTO_ORDEN_CERRADA = "orden.cerrada"
EVENTO_ORDEN_ESTADO_CAMBIADO = "orden.estado_cambiado"
EVENTO_FACTURA_GENERADA = "factura.generada"
EVENTO_FACTURA_PAGADA = "factura.pagada"
EVENTO_CITA_AGENDADA = "cita.agendada"
EVENTO_CITA_CANCELADA = "cita.cancelada"
EVENTO_ALERTA_CRITICA = "alerta.critica"
EVENTO_STOCK_BAJO = "inventario.stock_bajo"


class EventBus:
    """
    Bus de eventos basado en Redis Pub/Sub.
    Cada microservicio instancia uno y emite/escucha eventos.
    """

    def __init__(self, redis_url=None):
        url = redis_url or os.getenv("REDIS_URL", "redis://redis:6379/0")
        self._redis = redis.from_url(url, decode_responses=True)

    def publicar(self, evento, payload):
        """
        Publica un evento en el canal correspondiente.

        Args:
            evento: nombre canónico del evento (constantes EVENTO_*)
            payload: dict con datos del evento (serializable a JSON)
        """
        mensaje = {
            "evento": evento,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": payload,
        }
        self._redis.publish(evento, json.dumps(mensaje))
        # También guardamos en una lista para procesamiento via Celery
        self._redis.lpush(f"queue:{evento}", json.dumps(mensaje))
        return mensaje

    def health_check(self):
        """Verifica que Redis está accesible"""
        try:
            return self._redis.ping()
        except Exception:
            return False
