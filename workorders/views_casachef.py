"""
workorders/views_casachef.py
Endpoint que expone la recomendación de CasaChef al dashboard.
GET /api/v1/recomendacion-almuerzo/?presupuesto=25000&tipo=almuerzo
"""

from django.http import JsonResponse
from django.views import View

from autoshop.adapters.casachef_adapter import RecomendacionAdapterFactory


class RecomendacionAlmuerzoView(View):
    def get(self, request):
        presupuesto = int(request.GET.get('presupuesto', 25000))
        tipo        = request.GET.get('tipo', 'almuerzo')
        ciudad      = request.GET.get('ciudad', 'Medellin')

        adapter     = RecomendacionAdapterFactory.crear()
        resultado   = adapter.obtener_recomendacion(
            ciudad=ciudad,
            presupuesto=presupuesto,
            tipo_comida=tipo,
            limit=1,
        )

        return JsonResponse({
            'ok':              resultado['error'] is None,
            'ciudad':          resultado['ciudad'],
            'recomendacion':   resultado['recomendaciones'][0] if resultado['recomendaciones'] else None,
            'fuente':          resultado['fuente'],
            'timestamp':       resultado['timestamp'],
            'error':           resultado['error'],
        })
