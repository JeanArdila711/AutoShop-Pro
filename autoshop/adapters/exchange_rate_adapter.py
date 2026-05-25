"""
autoshop/adapters/exchange_rate_adapter.py
─────────────────────────────────────────────────────────────
Adapter Pattern — Inversión de Dependencias para tasas de cambio.

Estructura:
  - TasaCambioAdapterInterface  → contrato interno (tu dominio manda)
  - ExchangeRateAdapter         → implementación real (open.er-api.com)
  - MockExchangeRateAdapter     → implementación fake para tests/DEV
  - TasaCambioAdapterFactory    → selecciona implementación según ENV_TYPE

El núcleo del negocio NUNCA importa ExchangeRateAdapter directamente.
Solo conoce TasaCambioAdapterInterface.
─────────────────────────────────────────────────────────────
"""

import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone

import requests


# ─────────────────────────────────────────────────────────────
# INTERFAZ — contrato interno del dominio
# ─────────────────────────────────────────────────────────────

class TasaCambioAdapterInterface(ABC):
    """
    Contrato que el dominio conoce.
    Cualquier proveedor de tasas de cambio debe implementar esta interfaz.
    """

    @abstractmethod
    def obtener_tasa(self, moneda_origen: str, moneda_destino: str) -> dict:
        """
        Retorna la tasa de cambio entre dos monedas.

        Returns:
            {
                'origen': 'USD',
                'destino': 'COP',
                'tasa': 4200.50,
                'timestamp': '2026-05-24T21:00:00Z',
                'fuente': 'ExchangeRate-API',
            }
        """
        pass

    @abstractmethod
    def obtener_multiples_tasas(self, moneda_base: str, destinos: list[str]) -> dict:
        """
        Retorna tasas de cambio para múltiples monedas destino.

        Returns:
            {
                'base': 'USD',
                'tasas': {'COP': 4200.50, 'EUR': 0.92, 'MXN': 17.3},
                'timestamp': '2026-05-24T21:00:00Z',
                'fuente': 'ExchangeRate-API',
            }
        """
        pass


# ─────────────────────────────────────────────────────────────
# IMPLEMENTACIÓN REAL — ExchangeRate-API (sin API key, gratis)
# ─────────────────────────────────────────────────────────────

class ExchangeRateAdapter(TasaCambioAdapterInterface):
    """
    Adapter real que consume https://open.er-api.com/v6/latest/{base}
    No requiere API key. Límite: 1500 peticiones/mes en plan gratuito.
    """

    BASE_URL = 'https://open.er-api.com/v6/latest'
    TIMEOUT  = 5  # segundos

    def obtener_tasa(self, moneda_origen: str, moneda_destino: str) -> dict:
        resultado = self.obtener_multiples_tasas(moneda_origen, [moneda_destino])
        tasa = resultado['tasas'].get(moneda_destino.upper())
        return {
            'origen': moneda_origen.upper(),
            'destino': moneda_destino.upper(),
            'tasa': tasa,
            'timestamp': resultado['timestamp'],
            'fuente': resultado['fuente'],
        }

    def obtener_multiples_tasas(self, moneda_base: str, destinos: list[str]) -> dict:
        url = f"{self.BASE_URL}/{moneda_base.upper()}"
        try:
            respuesta = requests.get(url, timeout=self.TIMEOUT)
            respuesta.raise_for_status()
            datos = respuesta.json()

            tasas_filtradas = {
                moneda: datos['rates'][moneda]
                for moneda in [d.upper() for d in destinos]
                if moneda in datos['rates']
            }

            return {
                'base': moneda_base.upper(),
                'tasas': tasas_filtradas,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'fuente': 'ExchangeRate-API (open.er-api.com)',
                'error': None,
            }
        except requests.Timeout:
            return self._respuesta_error(moneda_base, destinos, 'Timeout al conectar con ExchangeRate-API')
        except requests.RequestException as e:
            return self._respuesta_error(moneda_base, destinos, str(e))

    def _respuesta_error(self, base: str, destinos: list[str], mensaje: str) -> dict:
        return {
            'base': base.upper(),
            'tasas': {d.upper(): None for d in destinos},
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'fuente': 'ExchangeRate-API (open.er-api.com)',
            'error': mensaje,
        }


# ─────────────────────────────────────────────────────────────
# IMPLEMENTACIÓN MOCK — para desarrollo y tests
# ─────────────────────────────────────────────────────────────

class MockExchangeRateAdapter(TasaCambioAdapterInterface):
    """
    Implementación fake que devuelve tasas hardcodeadas.
    Úsala en DEV para no gastar cuota de la API real.
    """

    TASAS_MOCK = {
        'USD': {'COP': 4187.50, 'EUR': 0.92, 'MXN': 17.15, 'BRL': 5.10},
        'EUR': {'COP': 4550.00, 'USD': 1.09, 'MXN': 18.65},
        'COP': {'USD': 0.000239, 'EUR': 0.000220},
    }

    def obtener_tasa(self, moneda_origen: str, moneda_destino: str) -> dict:
        origen  = moneda_origen.upper()
        destino = moneda_destino.upper()
        tasa = self.TASAS_MOCK.get(origen, {}).get(destino, 0.0)
        return {
            'origen': origen,
            'destino': destino,
            'tasa': tasa,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'fuente': 'MockExchangeRateAdapter (DEV)',
        }

    def obtener_multiples_tasas(self, moneda_base: str, destinos: list[str]) -> dict:
        base = moneda_base.upper()
        tasas = {
            d.upper(): self.TASAS_MOCK.get(base, {}).get(d.upper(), 0.0)
            for d in destinos
        }
        return {
            'base': base,
            'tasas': tasas,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'fuente': 'MockExchangeRateAdapter (DEV)',
            'error': None,
        }


# ─────────────────────────────────────────────────────────────
# FACTORY — selecciona implementación según entorno
# ─────────────────────────────────────────────────────────────

class TasaCambioAdapterFactory:
    """
    Factory que decide qué adapter usar según la variable ENV_TYPE.
    ENV_TYPE=PROD  → ExchangeRateAdapter  (API real)
    ENV_TYPE=DEV   → MockExchangeRateAdapter (fake)
    """

    @staticmethod
    def crear() -> TasaCambioAdapterInterface:
        env = os.environ.get('ENV_TYPE', 'DEV').upper()
        if env == 'PROD':
            return ExchangeRateAdapter()
        return MockExchangeRateAdapter()
