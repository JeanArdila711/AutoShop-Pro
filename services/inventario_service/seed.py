"""
services/inventario_service/seed.py
─────────────────────────────────────────────────────────────
Siembra datos iniciales del microservicio Inventario.
Solo se ejecuta si la BD está vacía (idempotente).
─────────────────────────────────────────────────────────────
"""

from models import db, ParteMecanica, Proveedor


def sembrar_datos_iniciales():
    # Solo sembrar si está vacío
    if Proveedor.query.count() > 0:
        return

    print("[inventario_service] Sembrando datos iniciales...")

    # ── Proveedores ──
    proveedores = [
        Proveedor(
            nit='900111222-1',
            nombre='Repuestos La 13',
            contacto='Carlos Pérez',
            telefono='3001112233',
            email='ventas@repuestos13.co',
            direccion='Cra 13 # 45-67, Medellín',
            tiempo_entrega_dias=3,
            calificacion=4.8,
        ),
        Proveedor(
            nit='900333444-2',
            nombre='AutoPartes del Norte',
            contacto='María González',
            telefono='3014445566',
            email='contacto@autopartesnorte.co',
            direccion='Cl 80 # 12-34, Bogotá',
            tiempo_entrega_dias=5,
            calificacion=4.2,
        ),
        Proveedor(
            nit='900555666-3',
            nombre='Importadora Andina',
            contacto='Jorge Ramírez',
            telefono='3027778899',
            email='ventas@andina.com',
            direccion='Av El Dorado # 100-50, Bogotá',
            tiempo_entrega_dias=10,
            calificacion=4.5,
        ),
    ]
    db.session.add_all(proveedores)
    db.session.flush()

    # ── Partes mecánicas ──
    partes = [
        ParteMecanica(
            codigo_oem='OEM-FRENO-001', nombre='Pastillas de freno delanteras',
            categoria='FRENOS', precio_compra=45000, precio_venta=75000,
            stock_actual=20, stock_minimo=5, proveedor_id=proveedores[0].id,
        ),
        ParteMecanica(
            codigo_oem='OEM-FRENO-002', nombre='Discos de freno (par)',
            categoria='FRENOS', precio_compra=120000, precio_venta=190000,
            stock_actual=8, stock_minimo=4, proveedor_id=proveedores[0].id,
        ),
        ParteMecanica(
            codigo_oem='OEM-MOTOR-001', nombre='Filtro de aceite',
            categoria='MOTOR', precio_compra=15000, precio_venta=28000,
            stock_actual=50, stock_minimo=10, proveedor_id=proveedores[1].id,
        ),
        ParteMecanica(
            codigo_oem='OEM-MOTOR-002', nombre='Bujías de iridio (set 4)',
            categoria='MOTOR', precio_compra=80000, precio_venta=140000,
            stock_actual=12, stock_minimo=4, proveedor_id=proveedores[2].id,
        ),
        ParteMecanica(
            codigo_oem='OEM-MOTOR-003', nombre='Bomba de gasolina',
            categoria='MOTOR', precio_compra=250000, precio_venta=380000,
            stock_actual=3, stock_minimo=2, proveedor_id=proveedores[2].id,
        ),
        ParteMecanica(
            codigo_oem='OEM-SUSP-001', nombre='Amortiguadores delanteros (par)',
            categoria='SUSPENSION', precio_compra=180000, precio_venta=290000,
            stock_actual=6, stock_minimo=3, proveedor_id=proveedores[1].id,
        ),
        ParteMecanica(
            codigo_oem='OEM-ELEC-001', nombre='Batería 12V 60Ah',
            categoria='ELECTRICO', precio_compra=220000, precio_venta=330000,
            stock_actual=10, stock_minimo=3, proveedor_id=proveedores[0].id,
        ),
        ParteMecanica(
            codigo_oem='OEM-TRANS-001', nombre='Aceite de transmisión 5L',
            categoria='TRANSMISION', precio_compra=95000, precio_venta=145000,
            stock_actual=15, stock_minimo=5, proveedor_id=proveedores[1].id,
        ),
        ParteMecanica(
            codigo_oem='OEM-GEN-001', nombre='Aceite motor 5W-30 (4L)',
            categoria='GENERAL', precio_compra=55000, precio_venta=85000,
            stock_actual=30, stock_minimo=10, proveedor_id=proveedores[2].id,
        ),
    ]
    db.session.add_all(partes)
    db.session.commit()
    print(f"[inventario_service] Sembrados: {len(proveedores)} proveedores, {len(partes)} partes")
