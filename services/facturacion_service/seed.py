"""
services/facturacion_service/seed.py
─────────────────────────────────────────────────────────────
Siembra datos iniciales del microservicio Facturación.
Solo se ejecuta si la BD está vacía (idempotente).
─────────────────────────────────────────────────────────────
"""

from models import db, FacturaServicio, DetalleFactura


def sembrar_datos_iniciales():
    # Solo sembrar si está vacío
    if FacturaServicio.query.count() > 0:
        return

    print("[facturacion_service] Sembrando datos iniciales...")

    # ── Factura 1: Orden completada, pagada ──
    f1 = FacturaServicio(
        orden_trabajo_id=1,
        propietario_id=1,
        propietario_nombre='Carlos Martínez',
        tipo_cliente='REGULAR',
        descuento=0,
        estado='PAGADA',
        dias_garantia=30,
        notas='Servicio de mantenimiento preventivo',
    )
    db.session.add(f1)
    db.session.flush()

    detalles_f1 = [
        DetalleFactura(
            factura_id=f1.id, tipo='SERVICIO',
            descripcion='Cambio de aceite y filtro',
            cantidad=1, precio_unitario=50000,
        ),
        DetalleFactura(
            factura_id=f1.id, tipo='REPUESTO',
            descripcion='Aceite motor 5W-30 (4L)',
            cantidad=1, precio_unitario=85000,
        ),
        DetalleFactura(
            factura_id=f1.id, tipo='REPUESTO',
            descripcion='Filtro de aceite',
            cantidad=1, precio_unitario=28000,
        ),
    ]
    db.session.add_all(detalles_f1)
    db.session.flush()
    f1.generar_total()

    # ── Factura 2: Pendiente de pago (cliente VIP) ──
    f2 = FacturaServicio(
        orden_trabajo_id=2,
        propietario_id=2,
        propietario_nombre='Ana López',
        tipo_cliente='VIP',
        descuento=20000,
        estado='PENDIENTE',
        dias_garantia=60,
        notas='Descuento por cliente frecuente',
    )
    db.session.add(f2)
    db.session.flush()

    detalles_f2 = [
        DetalleFactura(
            factura_id=f2.id, tipo='SERVICIO',
            descripcion='Diagnóstico electrónico completo',
            cantidad=1, precio_unitario=80000,
        ),
        DetalleFactura(
            factura_id=f2.id, tipo='SERVICIO',
            descripcion='Cambio de pastillas de freno',
            cantidad=1, precio_unitario=60000,
        ),
        DetalleFactura(
            factura_id=f2.id, tipo='REPUESTO',
            descripcion='Pastillas de freno delanteras',
            cantidad=1, precio_unitario=75000,
        ),
        DetalleFactura(
            factura_id=f2.id, tipo='MANO_OBRA',
            descripcion='Mano de obra (2 horas)',
            cantidad=2, precio_unitario=40000,
        ),
    ]
    db.session.add_all(detalles_f2)
    db.session.flush()
    f2.generar_total()

    # ── Factura 3: Pendiente (cliente Premium) ──
    f3 = FacturaServicio(
        orden_trabajo_id=3,
        propietario_id=3,
        propietario_nombre='Roberto Sánchez',
        tipo_cliente='PREMIUM',
        descuento=50000,
        estado='PENDIENTE',
        dias_garantia=90,
        notas='Cliente Premium — garantía extendida 90 días',
    )
    db.session.add(f3)
    db.session.flush()

    detalles_f3 = [
        DetalleFactura(
            factura_id=f3.id, tipo='SERVICIO',
            descripcion='Revisión de suspensión completa',
            cantidad=1, precio_unitario=120000,
        ),
        DetalleFactura(
            factura_id=f3.id, tipo='REPUESTO',
            descripcion='Amortiguadores delanteros (par)',
            cantidad=1, precio_unitario=290000,
        ),
        DetalleFactura(
            factura_id=f3.id, tipo='REPUESTO',
            descripcion='Bujías de iridio (set 4)',
            cantidad=1, precio_unitario=140000,
        ),
        DetalleFactura(
            factura_id=f3.id, tipo='MANO_OBRA',
            descripcion='Mano de obra (4 horas)',
            cantidad=4, precio_unitario=45000,
        ),
    ]
    db.session.add_all(detalles_f3)
    db.session.flush()
    f3.generar_total()

    db.session.commit()
    print(f"[facturacion_service] Sembradas: 3 facturas con detalles")
