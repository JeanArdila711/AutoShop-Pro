"""
autoshop/adapters/casachef_adapter.py
─────────────────────────────────────────────────────────────
Adapter Pattern — Servicio aliado CasaChef (recomendaciones de comida).

Estructura:
  - RecomendacionAdapterInterface  → contrato interno
  - CasaChefAdapter                → implementación real (3.89.172.49)
  - MockRecomendacionAdapter       → implementación fake para DEV/tests
  - RecomendacionAdapterFactory    → selecciona según ENV_TYPE
─────────────────────────────────────────────────────────────
"""

import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone

import requests


# ─────────────────────────────────────────────────────────────
# INTERFAZ — contrato interno del dominio
# ─────────────────────────────────────────────────────────────

class RecomendacionAdapterInterface(ABC):
    """
    Contrato que el dominio conoce.
    Cualquier proveedor de recomendaciones de comida debe implementarlo.
    """

    @abstractmethod
    def obtener_recomendacion(self, ciudad: str, presupuesto: int,
                              tipo_comida: str = 'almuerzo', limit: int = 1) -> dict:
        """
        Retorna recomendaciones de comida para el personal del taller.

        Returns:
            {
                'ciudad': 'Medellin',
                'recomendaciones': [
                    {
                        'nombre': 'Menú vegetariano de temporada',
                        'precio_estimado': 24000,
                        'razon': 'Opción con menor complejidad logística...',
                        'tags': ['almuerzo', 'vegetariano', 'saludable'],
                    }
                ],
                'timestamp': '2026-05-25T...',
                'fuente': 'CasaChef',
                'error': None,
            }
        """
        pass


# ─────────────────────────────────────────────────────────────
# IMPLEMENTACIÓN REAL — API CasaChef (equipo aliado)
# ─────────────────────────────────────────────────────────────

class CasaChefAdapter(RecomendacionAdapterInterface):
    """
    Adapter real que consume http://3.89.172.49/api/v2/recommendations/
    No requiere autenticación.
    Disponible cuando el Lab de AWS Academy del equipo aliado está activo.
    """

    BASE_URL = 'http://3.89.172.49/api/v2/recommendations'
    TIMEOUT  = 5  # segundos

    def obtener_recomendacion(self, ciudad: str, presupuesto: int,
                              tipo_comida: str = 'almuerzo', limit: int = 1) -> dict:
        params = {
            'city':      ciudad,
            'budget':    presupuesto,
            'dish_type': tipo_comida,
            'limit':     limit,
        }
        try:
            respuesta = requests.get(self.BASE_URL, params=params, timeout=self.TIMEOUT)
            respuesta.raise_for_status()
            datos = respuesta.json()

            recomendaciones = [
                {
                    'nombre':           r.get('name', ''),
                    'precio_estimado':  r.get('estimated_price', 0),
                    'razon':            r.get('reason', ''),
                    'tags':             r.get('tags', []),
                }
                for r in datos.get('recommendations', [])
            ]

            return {
                'ciudad':           datos.get('city', ciudad),
                'recomendaciones':  recomendaciones,
                'timestamp':        datetime.now(timezone.utc).isoformat(),
                'fuente':           'CasaChef (casachef-recommendations-service)',
                'error':            None,
            }
        except requests.Timeout:
            return self._respuesta_error(ciudad, 'Timeout — Lab de CasaChef puede estar apagado')
        except requests.RequestException as e:
            return self._respuesta_error(ciudad, str(e))

    def _respuesta_error(self, ciudad: str, mensaje: str) -> dict:
        return {
            'ciudad':          ciudad,
            'recomendaciones': [],
            'timestamp':       datetime.now(timezone.utc).isoformat(),
            'fuente':          'CasaChef (casachef-recommendations-service)',
            'error':           mensaje,
        }


# ─────────────────────────────────────────────────────────────
# IMPLEMENTACIÓN MOCK — para desarrollo y tests
# ─────────────────────────────────────────────────────────────

class MockRecomendacionAdapter(RecomendacionAdapterInterface):
    """
    Implementación fake con datos reales tomados de la API de CasaChef.
    Se usa en DEV para no depender de que el lab aliado esté encendido.
    """

    MOCK_DATA = [
        {
            'nombre':          'Bandeja casera ejecutiva',
            'precio_estimado': 26000,
            'razon':           'Buena relación precio/cantidad para jornada laboral.',
            'tags':            ['almuerzo', 'tradicional', 'alto-proteina'],
        },
        {
            'nombre':          'Menú vegetariano de temporada',
            'precio_estimado': 24000,
            'razon':           'Opción con menor complejidad logística y alta rotación diaria.',
            'tags':            ['almuerzo', 'vegetariano', 'saludable'],
        },
        {
            'nombre':          'Cena casera premium',
            'precio_estimado': 42000,
            'razon':           'Recomendada para pedidos programados y producción limitada.',
            'tags':            ['cena', 'premium', 'tradicional'],
        },
    ]

    def obtener_recomendacion(self, ciudad: str, presupuesto: int,
                              tipo_comida: str = 'almuerzo', limit: int = 1) -> dict:
        # Filtrar por presupuesto y limitar resultados
        filtradas = [
            r for r in self.MOCK_DATA
            if r['precio_estimado'] <= presupuesto
        ][:limit]

        return {
            'ciudad':          ciudad,
            'recomendaciones': filtradas,
            'timestamp':       datetime.now(timezone.utc).isoformat(),
            'fuente':          'MockRecomendacionAdapter (DEV)',
            'error':           None,
        }


# ─────────────────────────────────────────────────────────────
# FACTORY — selecciona implementación según entorno
# ─────────────────────────────────────────────────────────────

class RecomendacionAdapterFactory:
    """
    ENV_TYPE=PROD → CasaChefAdapter    (API real del equipo aliado)
    ENV_TYPE=DEV  → MockRecomendacionAdapter (fake, siempre disponible)
    """

    @staticmethod
    def crear() -> RecomendacionAdapterInterface:
        env = os.environ.get('ENV_TYPE', 'DEV').upper()
        if env == 'PROD':
            return CasaChefAdapter()
        return MockRecomendacionAdapter()
