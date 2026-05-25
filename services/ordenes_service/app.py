"""
services/ordenes_service/app.py
─────────────────────────────────────────────────────────────
Entrypoint del microservicio Órdenes de Trabajo (Flask).

Inicializa:
  - Flask app
  - SQLAlchemy con SQLite local (en /app/data/ordenes.db)
  - Blueprint de órdenes
  - Crea tablas si no existen y siembra datos iniciales
─────────────────────────────────────────────────────────────
"""

import os
from flask import Flask, jsonify
from models import db
from routes import ordenes_bp
from seed import sembrar_datos_iniciales


def crear_app():
    app = Flask(__name__)

    # ── Configuración ──
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'ordenes.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JSON_AS_ASCII'] = False
    app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024  # 25MB max upload

    # ── Inicializar extensiones ──
    db.init_app(app)

    # ── Registrar blueprints ──
    app.register_blueprint(ordenes_bp)

    # ── Endpoint raíz ──
    @app.route('/')
    def root():
        return jsonify({
            'servicio': 'ordenes',
            'version': '2.0',
            'endpoints': [
                '/api/v2/ordenes/health',
                '/api/v2/ordenes/',
                '/api/v2/ordenes/<id>/',
                '/api/v2/ordenes/<id>/estado/',
                '/api/v2/ordenes/<id>/timer/iniciar/',
                '/api/v2/ordenes/<id>/timer/detener/',
                '/api/v2/ordenes/<id>/checklist/',
                '/api/v2/ordenes/<id>/evidencia/',
                '/api/v2/ordenes/bahias/',
                '/api/v2/ordenes/estadisticas/',
            ],
        }), 200

    # ── Crear tablas y sembrar ──
    with app.app_context():
        db.create_all()
        sembrar_datos_iniciales()

    return app


if __name__ == '__main__':
    app = crear_app()
    app.run(host='0.0.0.0', port=5001, debug=False)
