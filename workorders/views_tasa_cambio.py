"""
workorders/views_tasa_cambio.py
─────────────────────────────────────────────────────────────
Vista que expone la tasa de cambio USD/COP usando el Adapter Pattern.
El dominio no sabe qué proveedor de tasas se usa — solo conoce la interfaz.
─────────────────────────────────────────────────────────────
"""

from django.http import JsonResponse
from django.views import View

from autoshop.adapters.exchange_rate_adapter import TasaCambioAdapterFactory


class TasaCambioView(View):
    """
    GET /workorders/tasa-cambio/
    Devuelve la tasa USD→COP para mostrar en el dashboard.
    Usa el Adapter Pattern — el proveedor real se selecciona en la Factory.
    """

    def get(self, request):
        adapter = TasaCambioAdapterFactory.crear()
        resultado = adapter.obtener_multiples_tasas(
            moneda_base='USD',
            destinos=['COP', 'EUR', 'MXN'],
        )

        # Formateo amigable para el dashboard
        cop = resultado['tasas'].get('COP')
        return JsonResponse({
            'tasa_usd_cop': cop,
            'tasa_usd_cop_formateada': f"${cop:,.2f}" if cop else 'No disponible',
            'tasas': resultado['tasas'],
            'fuente': resultado['fuente'],
            'timestamp': resultado['timestamp'],
            'error': resultado.get('error'),
        })
