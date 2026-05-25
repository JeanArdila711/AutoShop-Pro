"""
services/inventario_service/app.py
─────────────────────────────────────────────────────────────
Entrypoint del microservicio Inventario (Flask).

Inicializa:
  - Flask app
  - SQLAlchemy con SQLite local (en /app/data/inventario.db)
  - Blueprints de inventario y catálogo
  - Crea tablas si no existen y siembra datos iniciales si la BD está vacía
─────────────────────────────────────────────────────────────
"""

import os
from flask import Flask, jsonify
from models import db
from routes import inventario_bp, catalogo_bp
from seed import sembrar_datos_iniciales


def crear_app():
    app = Flask(__name__)

    # ── Configuración ──
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'inventario.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JSON_AS_ASCII'] = False

    # ── Inicializar extensiones ──
    db.init_app(app)

    # ── Registrar blueprints ──
    app.register_blueprint(inventario_bp)
    app.register_blueprint(catalogo_bp)

    # ── Endpoint raíz ──
    @app.route('/')
    def root():
        return jsonify({
            'servicio': 'inventario',
            'version': '2.0',
            'endpoints': [
                '/api/v2/inventario/health',
                '/api/v2/inventario/partes/',
                '/api/v2/inventario/proveedores/',
                '/api/v2/inventario/ordenes-compra/',
                '/api/v2/catalogo/',
            ],
        }), 200

    # ── Crear tablas y sembrar ──
    with app.app_context():
        db.create_all()
        sembrar_datos_iniciales()

    return app


if __name__ == '__main__':
    app = crear_app()
    app.run(host='0.0.0.0', port=5002, debug=False)
