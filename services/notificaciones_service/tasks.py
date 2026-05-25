"""
services/notificaciones_service/tasks.py
─────────────────────────────────────────────────────────────
Placeholder de tareas Celery — se implementará completamente
junto con notificaciones_service + SendGrid Adapter.
─────────────────────────────────────────────────────────────
"""

import os
from celery import Celery

REDIS_URL = os.environ.get('REDIS_URL', 'redis://redis:6379/0')

app = Celery('autoshop', broker=REDIS_URL, backend=REDIS_URL)

app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='America/Bogota',
    enable_utc=True,
)


@app.task(name='enviar_notificacion_email')
def enviar_notificacion_email(destinatario, asunto, cuerpo):
    """Envío asíncrono de email — implementación pendiente con SendGrid"""
    print(f"[celery] Email a {destinatario}: {asunto}")
    return {'status': 'pendiente', 'destinatario': destinatario}


@app.task(name='generar_reporte_diario')
def generar_reporte_diario():
    """Reporte diario de órdenes — implementación pendiente"""
    print("[celery] Generando reporte diario...")
    return {'status': 'pendiente'}


@app.task(name='alertas_predictivas_batch')
def alertas_predictivas_batch():
    """Calcular alertas predictivas batch — implementación pendiente"""
    print("[celery] Calculando alertas predictivas...")
    return {'status': 'pendiente'}
