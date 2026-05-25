"""
services/citas_service/seed.py
─────────────────────────────────────────────────────────────
Datos de prueba para desarrollo local.
Se ejecuta solo si la tabla está vacía (idempotente).
─────────────────────────────────────────────────────────────
"""

from datetime import date, time, timedelta

from models import BloqueoAgenda, Cita, db


def sembrar_datos(app):
    with app.app_context():
        if Cita.query.count() > 0:
            print("[citas_service] seed: datos ya existen, omitiendo.")
            return

        hoy   = date.today()
        manana = hoy + timedelta(days=1)
        pasado = hoy + timedelta(days=2)

        citas = [
            Cita(
                propietario_id=1,
                propietario_nombre='Carlos Rodríguez',
                propietario_email='carlos@example.com',
                propietario_telefono='3001234567',
                vehiculo_id=1,
                vehiculo_placa='ABC123',
                vehiculo_marca='Toyota',
                vehiculo_modelo='Corolla 2020',
                mecanico_id=1,
                mecanico_nombre='Juan Mecánico',
                fecha=manana,
                hora_inicio=time(9, 0),
                duracion_minutos=60,
                tipo_servicio='MANTENIMIENTO_PREVENTIVO',
                estado='CONFIRMADA',
                notas='Cambio de aceite y filtros.',
            ),
            Cita(
                propietario_id=2,
                propietario_nombre='María García',
                propietario_email='maria@example.com',
                propietario_telefono='3109876543',
                vehiculo_id=2,
                vehiculo_placa='XYZ789',
                vehiculo_marca='Chevrolet',
                vehiculo_modelo='Spark 2019',
                fecha=manana,
                hora_inicio=time(11, 0),
                duracion_minutos=90,
                tipo_servicio='DIAGNOSTICO_ELECTRICO',
                estado='PENDIENTE',
                notas='Falla en el tablero — luz de check engine.',
            ),
            Cita(
                propietario_id=3,
                propietario_nombre='Luis Pérez',
                propietario_email='luis@example.com',
                propietario_telefono='3151112233',
                vehiculo_id=3,
                vehiculo_placa='DEF456',
                vehiculo_marca='Mazda',
                vehiculo_modelo='3 2021',
                fecha=pasado,
                hora_inicio=time(14, 0),
                duracion_minutos=60,
                tipo_servicio='ALINEACION_BALANCEO',
                estado='PENDIENTE',
                notas='Vibración a altas velocidades.',
            ),
            Cita(
                propietario_id=1,
                propietario_nombre='Carlos Rodríguez',
                propietario_email='carlos@example.com',
                vehiculo_id=1,
                vehiculo_placa='ABC123',
                vehiculo_marca='Toyota',
                vehiculo_modelo='Corolla 2020',
                fecha=hoy - timedelta(days=3),
                hora_inicio=time(10, 0),
                duracion_minutos=60,
                tipo_servicio='REVISION_GENERAL',
                estado='COMPLETADA',
                orden_trabajo_id=1,
            ),
        ]

        for c in citas:
            db.session.add(c)

        # Bloqueo de feriado de ejemplo
        bloqueo = BloqueoAgenda(
            fecha=hoy + timedelta(days=7),
            hora_inicio=None,
            hora_fin=None,
            motivo='Festivo — taller cerrado',
        )
        db.session.add(bloqueo)

        db.session.commit()
        print(f"[citas_service] seed: {len(citas)} citas + 1 bloqueo creados.")
