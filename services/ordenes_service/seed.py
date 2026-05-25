"""
services/ordenes_service/seed.py
─────────────────────────────────────────────────────────────
Siembra datos iniciales del microservicio Órdenes.
Solo se ejecuta si la BD está vacía (idempotente).
─────────────────────────────────────────────────────────────
"""

from datetime import datetime, timezone, timedelta
from models import (
    db, OrdenTrabajo, Bahia, TimerSession,
    ChecklistTemplate, ChecklistTemplateItem,
)


def sembrar_datos_iniciales():
    # Solo sembrar si está vacío
    if OrdenTrabajo.query.count() > 0:
        return

    print("[ordenes_service] Sembrando datos iniciales...")

    # ── Bahías ──
    bahias = [
        Bahia(codigo='B-01', nombre='Bahía 1 — General', tipo='GENERAL'),
        Bahia(codigo='B-02', nombre='Bahía 2 — Mecánica', tipo='MECANICA'),
        Bahia(codigo='B-03', nombre='Bahía 3 — Eléctrica', tipo='ELECTRICA'),
        Bahia(codigo='B-04', nombre='Bahía 4 — Carrocería', tipo='CARROCERIA'),
        Bahia(codigo='B-05', nombre='Bahía 5 — Alineación', tipo='ALINEACION'),
    ]
    db.session.add_all(bahias)
    db.session.flush()

    # ── Plantillas de Checklist ──
    templates_data = {
        'MOTOR': {
            'desc': 'Checklist de diagnóstico de motor',
            'items': [
                'Verificar nivel de aceite',
                'Verificar estado de bujías',
                'Revisar mangueras y conexiones',
                'Verificar filtro de aire',
                'Comprobar compresión de cilindros',
                'Revisar correa de distribución',
                'Verificar sistema de enfriamiento',
            ],
        },
        'FRENOS': {
            'desc': 'Checklist de diagnóstico de frenos',
            'items': [
                'Medir espesor de pastillas delanteras',
                'Medir espesor de pastillas traseras',
                'Verificar discos de freno',
                'Revisar líquido de frenos',
                'Comprobar freno de mano',
                'Verificar latiguillos',
                'Probar ABS (si aplica)',
            ],
        },
        'SUSPENSION': {
            'desc': 'Checklist de diagnóstico de suspensión',
            'items': [
                'Verificar amortiguadores delanteros',
                'Verificar amortiguadores traseros',
                'Revisar rótulas',
                'Verificar terminales de dirección',
                'Revisar bujes de barra estabilizadora',
                'Comprobar alineación visual',
            ],
        },
        'ELECTRICO': {
            'desc': 'Checklist de diagnóstico eléctrico',
            'items': [
                'Verificar voltaje de batería',
                'Probar alternador',
                'Revisar luces exteriores',
                'Verificar luces interiores',
                'Comprobar sistema de arranque',
                'Revisar fusibles principales',
            ],
        },
        'GENERAL': {
            'desc': 'Checklist de inspección general',
            'items': [
                'Verificar niveles de fluidos',
                'Revisar estado de llantas',
                'Verificar limpiaparabrisas',
                'Revisar espejos y vidrios',
                'Comprobar cinturones de seguridad',
                'Verificar documentación del vehículo',
            ],
        },
    }

    for cat, data in templates_data.items():
        template = ChecklistTemplate(
            categoria=cat, descripcion=data['desc'],
        )
        db.session.add(template)
        db.session.flush()
        for i, texto in enumerate(data['items']):
            item = ChecklistTemplateItem(
                template_id=template.id, texto=texto, orden=i + 1,
            )
            db.session.add(item)

    # ── Órdenes de ejemplo ──
    ahora = datetime.now(timezone.utc)

    ordenes = [
        OrdenTrabajo(
            vehiculo_id=1, vehiculo_placa='ABC123',
            vehiculo_marca='Chevrolet', vehiculo_modelo='Spark',
            propietario_id=1, propietario_nombre='Carlos Martínez',
            mecanico_id=1, mecanico_nombre='Pedro García',
            estado='EN_REPARACION',
            descripcion_problema='Ruido en frenos delanteros al frenar',
            odometer_km=45000,
            costo_presupuestado=250000,
            costo_real=180000,
            tiempo_estimado=3,
            bahia_codigo='B-02',
            fecha_ingreso=ahora - timedelta(days=2),
        ),
        OrdenTrabajo(
            vehiculo_id=2, vehiculo_placa='DEF456',
            vehiculo_marca='Renault', vehiculo_modelo='Logan',
            propietario_id=2, propietario_nombre='Ana López',
            mecanico_id=2, mecanico_nombre='Luis Ramírez',
            estado='EN_DIAGNOSTICO',
            descripcion_problema='Motor pierde potencia en subidas',
            odometer_km=78000,
            costo_presupuestado=0,
            tiempo_estimado=2,
            bahia_codigo='B-01',
            fecha_ingreso=ahora - timedelta(days=1),
        ),
        OrdenTrabajo(
            vehiculo_id=3, vehiculo_placa='GHI789',
            vehiculo_marca='Toyota', vehiculo_modelo='Corolla',
            propietario_id=3, propietario_nombre='Roberto Sánchez',
            estado='ABIERTA',
            descripcion_problema='Revisión preventiva 80.000km',
            odometer_km=79500,
            costo_presupuestado=350000,
            tiempo_estimado=4,
            fecha_ingreso=ahora,
        ),
    ]
    db.session.add_all(ordenes)
    db.session.flush()

    # Asignar bahías a las órdenes que las tienen
    bahias[1].orden_actual_id = ordenes[0].id  # B-02 → OT#1
    bahias[0].orden_actual_id = ordenes[1].id  # B-01 → OT#2

    # ── Timers de ejemplo ──
    timer1 = TimerSession(
        orden_id=ordenes[0].id,
        inicio=ahora - timedelta(hours=5),
        fin=ahora - timedelta(hours=3),
        nota='Desmontaje de ruedas y revisión de frenos',
    )
    timer2 = TimerSession(
        orden_id=ordenes[0].id,
        inicio=ahora - timedelta(hours=2),
        fin=ahora - timedelta(hours=1),
        nota='Cambio de pastillas y rectificado de discos',
    )
    db.session.add_all([timer1, timer2])

    db.session.commit()
    print(
        f"[ordenes_service] Sembrados: {len(bahias)} bahías, "
        f"{len(templates_data)} templates checklist, "
        f"{len(ordenes)} órdenes, 2 timers"
    )
