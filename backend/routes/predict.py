import os
import json
import numpy as np
import tensorflow as tf
import importlib.util
from flask import Blueprint, request, jsonify, render_template, redirect, flash, send_file, session
from sqlalchemy import text
from tensorflow.keras.models import load_model
from database.db import engine

bp = Blueprint('predict', __name__, url_prefix='/predict')

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

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT model_path, preprocess_path, name 
            FROM models JOIN diseases ON models.disease_id = diseases.id 
            WHERE disease_id = :disease_id
        """), {"disease_id": disease_id}).fetchone()

    if not result:
        flash("No model found for this disease", "error")
        return redirect("/predict/form")

    model_path = result._mapping["model_path"]
    preprocess_path = result._mapping["preprocess_path"]
    disease_name = result._mapping["name"].lower()

    try:
        spec = importlib.util.spec_from_file_location("preprocessing", preprocess_path)
        preprocessing = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(preprocessing)

        if "smoking" in disease_name:
            input_text = request.form.get("Indhold")
            if not input_text:
                flash("Missing input for smoking prediction.", "error")
                return redirect("/predict/form")

            prediction = preprocessing.make_predictions(input_text)
            preprocessing.generate_explanation(input_text)
            flash(f"Smoking Behaviour: {prediction[0]}", "success")

        elif "sclerosis" in disease_name:
            aggregated_inputs = {}
            for key in request.form.keys():
                if key == "disease_id":
                    continue
                values = request.form.getlist(key)
                aggregated_inputs[key] = ", ".join([v.strip() for v in values if v.strip()])

            final_input = preprocessing.preprocess_inputs(aggregated_inputs)
            model = preprocessing.create_model()
            model.load_weights(model_path)
            prediction = model.predict(final_input)[0][0]

            preprocessing.generate_explanation(model)
            flash(f"Risk of MS: {prediction:.4f}", "success")

        else:
            flash("Unsupported disease for explanation.", "error")

    except Exception as e:
        flash(f"Prediction Failed: {str(e)}", "error")

    return redirect("/predict/form")

# --- Predict via JSON API ---
@bp.route('/', methods=['POST'])
def predict():
    data = request.get_json()
    disease_id = data.get("disease_id")
    raw_input = data.get("input")

    if not disease_id or not raw_input:
        return jsonify({"error": "Missing disease_id or input"}), 400

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT model_path, preprocess_path, name 
            FROM models JOIN diseases ON models.disease_id = diseases.id 
            WHERE disease_id = :disease_id
        """), {"disease_id": disease_id}).fetchone()

    if not result:
        return jsonify({"error": "No model found for this disease"}), 404

    model_path = result._mapping["model_path"]
    preprocess_path = result._mapping["preprocess_path"]
    disease_name = result._mapping["name"].lower()

    try:
        spec = importlib.util.spec_from_file_location("preprocessing", preprocess_path)
        preprocessing = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(preprocessing)

        if "smoking" in disease_name:
            prediction = preprocessing.make_predictions(raw_input)
            return jsonify({"prediction": prediction[0]})
        else:
            final_input = preprocessing.preprocess_inputs(raw_input)
            model = preprocessing.create_model()
            model.load_weights(model_path)
            prediction = model.predict(final_input)[0][0]
            return jsonify({"prediction": float(prediction)})

    except Exception as e:
        return jsonify({"error": f"Prediction failed: {str(e)}"}), 500

EXPLANATION_HTML_PATH = os.path.abspath("backend/static/explanations/lime_explanation.html")
# --- Route to return explanation HTML file ---
@bp.route('/explanation/view', methods=['GET'])
def view_explanation_html():
    if not os.path.exists(EXPLANATION_HTML_PATH):
        return "Explanation file not found.", 404
    return send_file(EXPLANATION_HTML_PATH)
