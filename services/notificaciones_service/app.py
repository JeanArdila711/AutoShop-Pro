"""notificaciones_service — placeholder hasta implementación completa"""
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
@app.route('/api/v2/notificaciones/health')
def health():
    return jsonify({'status': 'ok', 'servicio': 'notificaciones', 'nota': 'pendiente implementacion'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005, debug=False)
