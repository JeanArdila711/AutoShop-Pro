# ─────────────────────────────────────────────────────────────
# workorders/infra/notificacion_factory.py
# Segunda Factory: gestiona la dependencia de notificaciones.
# Retorna NotificadorConsola (DEV) o NotificadorEmail (PROD)
# según la variable de entorno ENV_TYPE.
# ─────────────────────────────────────────────────────────────

import os
from abc import ABC, abstractmethod


class NotificadorInterface(ABC):
    """Interfaz abstracta para el envío de notificaciones (ISP / DIP)"""

    @abstractmethod
    def enviar(self, destinatario, asunto, mensaje):
        """Envía una notificación al destinatario"""
        pass


class NotificadorEmail(NotificadorInterface):
    """Implementación real: envía notificaciones por email (simulado)"""

    def enviar(self, destinatario, asunto, mensaje):
        # En producción aquí se conectaría con un servicio SMTP / SendGrid / etc.
        print(f"[EMAIL] Para: {destinatario} | Asunto: {asunto} | {mensaje}")


class NotificadorConsola(NotificadorInterface):
    """Implementación mock: imprime la notificación en consola"""

    def enviar(self, destinatario, asunto, mensaje):
        print(f"[CONSOLA-MOCK] Para: {destinatario} | Asunto: {asunto} | {mensaje}")


class NotificacionFactory:
    """
    Factory para notificaciones.
    Selecciona la implementación concreta según ENV_TYPE.
    Aplica el patrón Factory Method + Principio de Inversión de Dependencias.
    """

    @staticmethod
    def crear_notificador():
        env_type = os.getenv('ENV_TYPE', 'DEV')

        if env_type == 'PROD':
            print("[NotificacionFactory] Usando NotificadorEmail")
            return NotificadorEmail()
        else:
            print("[NotificacionFactory] Usando NotificadorConsola")
            return NotificadorConsola()
