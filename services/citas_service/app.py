"""
services/citas_service/app.py
─────────────────────────────────────────────────────────────
Flask application factory para citas_service.
Puerto: 5004
─────────────────────────────────────────────────────────────
"""

import os

from flask import Flask, jsonify

from models import db
from routes import bp as citas_bp
from seed import sembrar_datos


def crear_app() -> Flask:
    app = Flask(__name__)

    # ── Configuración ────────────────────────────────────────
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'citas.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JSON_SORT_KEYS'] = False

    # ── Extensiones ──────────────────────────────────────────
    db.init_app(app)

    # ── Blueprints ───────────────────────────────────────────
    app.register_blueprint(citas_bp)

    # ── Health raíz ──────────────────────────────────────────
    @app.route('/')
    def root():
        return jsonify({'servicio': 'citas_service', 'status': 'ok'}), 200

    # ── Inicialización DB ────────────────────────────────────
    with app.app_context():
        db.create_all()

    sembrar_datos(app)

    return app


app = crear_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5004, debug=False)
