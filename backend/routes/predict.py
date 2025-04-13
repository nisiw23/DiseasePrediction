import os
import json
import numpy as np
from flask import Blueprint, request, jsonify , render_template
from sqlalchemy import text
from tensorflow.keras.models import load_model
from tensorflow.keras.layers import GRU
from database.db import engine

bp = Blueprint('predict', __name__, url_prefix='/predict')

@bp.route('/form', methods=['GET'])
def predict_page():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT id, name FROM diseases")).mappings()
        diseases = [dict(row) for row in result]

    return render_template("predict.html", diseases=diseases)


@bp.route('/', methods=['POST'])
def predict():
    data = request.get_json()

    disease_id = data.get("disease_id")
    patient_input = data.get("input")  # should be a dict of features

    if not disease_id or not patient_input:
        return jsonify({"error": "Missing disease_id or input"}), 400

    # Get model path for disease
    with engine.connect() as conn:
        result = conn.execute(text("SELECT model_path FROM models WHERE disease_id = :disease_id"),
                              {"disease_id": disease_id}).fetchone()

        if not result:
            return jsonify({"error": "No model found for this disease"}), 404

        model_path = result._mapping["model_path"]

    # Load model
    try:
        model = load_model(model_path, custom_objects={"GRU": GRU}, compile=False)
    except Exception as e:
        return jsonify({"error": f"Failed to load model: {str(e)}"}), 500

    # Prepare input
    try:
        input_array = np.array([list(patient_input.values())])
        prediction = model.predict(input_array)[0][0]
    except Exception as e:
        return jsonify({"error": f"Prediction failed: {str(e)}"}), 500

    # Store patient + prediction in DB
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO patients (disease_id, data, prediction_result)
            VALUES (:disease_id, :data, :result)
        """), {
            "disease_id": disease_id,
            "data": json.dumps(patient_input),
            "result": str(prediction)
        })

    return jsonify({
        "prediction": float(prediction)
    })
