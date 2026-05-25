"""
services/facturacion_service/app.py
─────────────────────────────────────────────────────────────
Entrypoint del microservicio Facturación (Flask).

Inicializa:
  - Flask app
  - SQLAlchemy con SQLite local (en /app/data/facturacion.db)
  - Blueprint de facturación
  - Crea tablas si no existen y siembra datos iniciales
─────────────────────────────────────────────────────────────
"""

import os
from flask import Flask, jsonify
from models import db
from routes import facturacion_bp
from seed import sembrar_datos_iniciales


def crear_app():
    app = Flask(__name__)

    # ── Configuración ──
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'facturacion.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JSON_AS_ASCII'] = False

    # ── Inicializar extensiones ──
    db.init_app(app)

    # ── Registrar blueprints ──
    app.register_blueprint(facturacion_bp)

    # ── Endpoint raíz ──
    @app.route('/')
    def root():
        return jsonify({
            'servicio': 'facturacion',
            'version': '2.0',
            'endpoints': [
                '/api/v2/facturacion/health',
                '/api/v2/facturacion/',
                '/api/v2/facturacion/<id>/',
                '/api/v2/facturacion/por-orden/<orden_id>/',
                '/api/v2/facturacion/<id>/pagar/',
                '/api/v2/facturacion/<id>/anular/',
                '/api/v2/facturacion/<id>/detalle/',
                '/api/v2/facturacion/resumen/',
            ],
        }), 200

    # ── Crear tablas y sembrar ──
    with app.app_context():
        db.create_all()
        sembrar_datos_iniciales()

    return app


if __name__ == '__main__':
    app = crear_app()
    app.run(host='0.0.0.0', port=5003, debug=False)
