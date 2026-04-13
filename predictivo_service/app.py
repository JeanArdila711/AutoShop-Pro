# predictivo_service/app.py
# ─────────────────────────────────────────────────────────────
# Microservicio Flask: ComponentePredictivo
# Expone la lógica de predicción de fallos mediante una API REST.
# Es stateless: recibe datos por JSON, no accede a la BD directamente.
# ─────────────────────────────────────────────────────────────

import math
from flask import Flask, request, jsonify

app = Flask(__name__)


# ── Función pura de negocio (extraída del monolito Django) ──

def calcular_probabilidad_fallo(km_actuales: int, km_promedio_fallo: int, desviacion_estandar: float) -> float:
    """
    Calcula la probabilidad de que un componente falle dado el kilometraje actual.
    
    Lógica idéntica a ComponentePredictivo.calcular_probabilidad_fallo() en Django,
    pero sin dependencia de ORM ni base de datos.

    Args:
        km_actuales: Kilometraje actual del vehículo.
        km_promedio_fallo: Km promedio en que falla este componente históricamente.
        desviacion_estandar: Desviación estándar del km de fallo.

    Returns:
        Probabilidad entre 0.0 y 1.0, redondeada a 4 decimales.
    """
    if desviacion_estandar == 0:
        return 1.0 if km_actuales >= km_promedio_fallo else 0.0
    
    diferencia = km_promedio_fallo - km_actuales
    prob = max(0.0, min(1.0, 1 - (diferencia / (desviacion_estandar * 2))))
    return round(prob, 4)


def generar_alerta(nombre: str, prob: float) -> str:
    """Genera mensaje de alerta según la probabilidad de fallo."""
    if prob > 0.7:
        return f"⚠️ ALTA: {nombre} probabilidad {prob*100:.0f}%"
    elif prob > 0.4:
        return f"⚠️ MEDIA: {nombre} probabilidad {prob*100:.0f}%"
    return ""


# ── Endpoints ──

@app.route("/api/v2/predictivo/health", methods=["GET"])
def health():
    """Endpoint de salud para verificar que el servicio está activo."""
    return jsonify({"status": "ok", "servicio": "predictivo"}), 200


@app.route("/api/v2/predictivo/calcular", methods=["POST"])
def calcular_prediccion():
    """
    Calcula la probabilidad de fallo de UN componente.

    Body JSON esperado:
    {
        "vehiculo_id": 1,
        "km_actuales": 85000,
        "componente": "Pastillas de Freno",
        "km_promedio_fallo": 80000,
        "desviacion_estandar": 5000.0
    }

    Respuesta 200:
    {
        "componente": "Pastillas de Freno",
        "vehiculo_id": 1,
        "km_actuales": 85000,
        "probabilidad": 0.6,
        "urgencia": "MEDIA",
        "alerta": "⚠️ MEDIA: Pastillas de Freno probabilidad 60%"
    }

    Errores:
        400 — Falta algún campo requerido o tipo inválido
        500 — Error interno inesperado
    """
    # ── Validación de entrada (error 400) ──
    try:
        body = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "El cuerpo de la petición debe ser JSON válido"}), 400

    if body is None:
        return jsonify({"error": "El cuerpo de la petición no puede estar vacío"}), 400

    campos_requeridos = ["vehiculo_id", "km_actuales", "componente", "km_promedio_fallo", "desviacion_estandar"]
    for campo in campos_requeridos:
        if campo not in body:
            return jsonify({
                "error": f"Campo requerido faltante: '{campo}'",
                "campos_requeridos": campos_requeridos
            }), 400

    # ── Validación de tipos ──
    try:
        vehiculo_id       = int(body["vehiculo_id"])
        km_actuales       = int(body["km_actuales"])
        componente        = str(body["componente"])
        km_promedio_fallo = int(body["km_promedio_fallo"])
        desviacion        = float(body["desviacion_estandar"])
    except (ValueError, TypeError) as e:
        return jsonify({
            "error": "Tipo de dato inválido en alguno de los campos",
            "detalle": str(e)
        }), 400

    if km_actuales < 0 or km_promedio_fallo < 0 or desviacion < 0:
        return jsonify({"error": "Los valores de kilometraje y desviación no pueden ser negativos"}), 400

    # ── Cálculo principal (error 500 si algo falla inesperadamente) ──
    try:
        prob = calcular_probabilidad_fallo(km_actuales, km_promedio_fallo, desviacion)
        
        if prob > 0.7:
            urgencia = "ALTA"
        elif prob > 0.4:
            urgencia = "MEDIA"
        else:
            urgencia = "BAJA"

        alerta = generar_alerta(componente, prob)

        return jsonify({
            "componente":    componente,
            "vehiculo_id":   vehiculo_id,
            "km_actuales":   km_actuales,
            "probabilidad":  prob,
            "urgencia":      urgencia,
            "alerta":        alerta
        }), 200

    except Exception as e:
        return jsonify({
            "error": "Error interno del servidor al calcular predicción",
            "detalle": str(e)
        }), 500


@app.route("/api/v2/predictivo/batch", methods=["POST"])
def calcular_batch():
    """
    Calcula predicciones para MÚLTIPLES componentes de un vehículo.
    Útil para reemplazar la llamada completa a PredictorReal en Django.

    Body JSON esperado:
    {
        "vehiculo_id": 1,
        "km_actuales": 85000,
        "componentes": [
            { "nombre": "Pastillas de Freno", "km_promedio_fallo": 80000, "desviacion_estandar": 5000 },
            { "nombre": "Filtro de Aceite",   "km_promedio_fallo": 10000, "desviacion_estandar": 1000 }
        ]
    }

    Respuesta 200:
    {
        "vehiculo_id": 1,
        "km_actuales": 85000,
        "total_componentes": 2,
        "alertas": [
            { "componente": "...", "probabilidad": 0.6, "urgencia": "MEDIA", "alerta": "..." }
        ]
    }
    """
    try:
        body = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "El cuerpo de la petición debe ser JSON válido"}), 400

    if body is None:
        return jsonify({"error": "El cuerpo no puede estar vacío"}), 400

    if "vehiculo_id" not in body or "km_actuales" not in body or "componentes" not in body:
        return jsonify({
            "error": "Faltan campos requeridos",
            "campos_requeridos": ["vehiculo_id", "km_actuales", "componentes"]
        }), 400

    if not isinstance(body["componentes"], list):
        return jsonify({"error": "'componentes' debe ser una lista"}), 400

    try:
        vehiculo_id = int(body["vehiculo_id"])
        km_actuales = int(body["km_actuales"])
    except (ValueError, TypeError) as e:
        return jsonify({"error": "Tipo inválido en vehiculo_id o km_actuales", "detalle": str(e)}), 400

    try:
        alertas = []
        for comp in body["componentes"]:
            nombre   = str(comp.get("nombre", "Desconocido"))
            km_fallo = int(comp.get("km_promedio_fallo", 0))
            desv     = float(comp.get("desviacion_estandar", 1))

            prob = calcular_probabilidad_fallo(km_actuales, km_fallo, desv)

            if prob > 0.4:
                urgencia = "ALTA" if prob > 0.7 else "MEDIA"
                alertas.append({
                    "componente":   nombre,
                    "probabilidad": prob,
                    "urgencia":     urgencia,
                    "alerta":       generar_alerta(nombre, prob)
                })

        return jsonify({
            "vehiculo_id":        vehiculo_id,
            "km_actuales":        km_actuales,
            "total_componentes":  len(body["componentes"]),
            "alertas":            alertas
        }), 200

    except Exception as e:
        return jsonify({
            "error": "Error interno al procesar el batch",
            "detalle": str(e)
        }), 500


# ── Entry point ──
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)