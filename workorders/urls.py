from django.urls import path
from django.http import JsonResponse
from workorders.views import CrearWorkOrderView


def ping(request):
    return JsonResponse({"ok": True, "app": "workorders"})


urlpatterns = [
    path("ping/", ping),
    path("crear/", CrearWorkOrderView.as_view(), name='crear_orden'),  # ← NUEVA
]
