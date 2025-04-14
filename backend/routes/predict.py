import os
import json
import numpy as np
import tensorflow as tf
from flask import Blueprint, request, jsonify, render_template, redirect, flash
from sqlalchemy import text
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, Embedding, Bidirectional, GRU, GlobalAveragePooling1D, Dense, Dropout
from database.db import engine

bp = Blueprint('predict', __name__, url_prefix='/predict')

# --- Model architecture (must match training time) ---
def create_model():
    atcicd_sex_age_input = Input(shape=(None,), name="acd_icd_sex_ageindex_input")

    atcicd_sex_age_embedding = Embedding(input_dim=1772, output_dim=1772, mask_zero=True)(atcicd_sex_age_input)

    atcicd_sex_age_gru_output = Bidirectional(GRU(units=128, return_sequences=True, dropout=0.05))(atcicd_sex_age_embedding)
    atcicd_sex_age_gru = Bidirectional(GRU(units=128, return_sequences=True, dropout=0.05))(atcicd_sex_age_gru_output)

    atcicd_sex_age_pooled_output = GlobalAveragePooling1D()(atcicd_sex_age_gru_output)

    dense_output = Dense(64, activation="relu")(atcicd_sex_age_pooled_output)
    dense_output = Dropout(0.2)(dense_output)
    dense_output = Dense(32, activation="relu")(dense_output)
    final_output = Dense(1, activation="sigmoid", name="output")(dense_output)

    model = Model(inputs=[atcicd_sex_age_input], outputs=final_output)

    return model

# --- Form page ---
@bp.route('/form', methods=['GET'])
def predict_page():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT id, name FROM diseases")).mappings()
        diseases = [dict(row) for row in result]

    return render_template("predict.html", diseases=diseases)

# --- Handle form submission ---
@bp.route('/submit', methods=['POST'])
def handle_predict_form():
    disease_id = request.form.get("disease_id")
    age = request.form.get("age")
    blood_pressure = request.form.get("blood_pressure")
    glucose = request.form.get("glucose")

    input_data = {
        "age": age,
        "blood_pressure": blood_pressure,
        "glucose": glucose
    }

    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO patients (disease_id, data, prediction_result)
            VALUES (:disease_id, :data, :result)
        """), {
            "disease_id": disease_id,
            "data": json.dumps(input_data),
            "result": None
        })

    flash("Patient data stored successfully! Prediction will be available once the model is ready.", "success")
    return redirect("/predict/form")

# --- Predict via API (e.g., curl) ---
@bp.route('/', methods=['POST'])
def predict():
    data = request.get_json()

    disease_id = data.get("disease_id")
    patient_input = data.get("input")  # array of numbers

    if not disease_id or not patient_input:
        return jsonify({"error": "Missing disease_id or input"}), 400

    # Get model path for disease
    with engine.connect() as conn:
        result = conn.execute(text("SELECT model_path FROM models WHERE disease_id = :disease_id"),
                              {"disease_id": disease_id}).fetchone()

        if not result:
            return jsonify({"error": "No model found for this disease"}), 404

        model_path = result._mapping["model_path"]

    # Load model weights into recreated model
    try:
        model = create_model()
        model.load_weights(model_path)
    except Exception as e:
        return jsonify({"error": f"Failed to load model: {str(e)}"}), 500

    # Run prediction
    try:
        input_array = np.array(patient_input).reshape(1, -1)
        prediction = model.predict(input_array)[0][0]
    except Exception as e:
        return jsonify({"error": f"Prediction failed: {str(e)}"}), 500

    # Store result
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
