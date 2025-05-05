from flask import Blueprint, request, jsonify, redirect, flash
from sqlalchemy import text
from database.db import engine
from werkzeug.utils import secure_filename
import os
import datetime
import pandas as pd

bp = Blueprint('diseases', __name__, url_prefix='/diseases')

@bp.route('/', methods=['GET'])
def get_diseases():
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT id, name, description FROM diseases
        """)).mappings()
        diseases = [dict(row) for row in result]
    return jsonify(diseases)

@bp.route('/', methods=['POST'])
def add_disease():
    data = request.get_json()
    name = data.get('name')
    description = data.get('description', '')
    if not name:
        return jsonify({'error': 'Name is required'}), 400
    with engine.begin() as conn:
        try:
            conn.execute(
                text("INSERT INTO diseases (name, description) VALUES (:name, :description)"),
                {"name": name, "description": description}
            )
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    return jsonify({'message': 'Disease added successfully'}), 201

@bp.route('/form', methods=['POST'])
def add_disease_from_form():
    name = request.form.get('name')
    description = request.form.get('description')
    csv_file = request.files.get('file')
    model_file = request.files.get('model_file')
    preprocess_file = request.files.get('preprocess_file')
    input_description_file = request.files.get('Input_description')

    if not name or not csv_file or not model_file or not preprocess_file or not input_description_file:
        return "Missing required fields", 400

    base_upload_path = os.path.join("backend", "uploads")
    csv_folder = os.path.join(base_upload_path, "DiseaseCSV")
    model_folder = os.path.join(base_upload_path, "ModelFile")
    preprocess_folder = os.path.join(base_upload_path, "Preprocessing")
    input_desc_folder = os.path.join(base_upload_path, "InputDesc")

    os.makedirs(csv_folder, exist_ok=True)
    os.makedirs(model_folder, exist_ok=True)
    os.makedirs(preprocess_folder, exist_ok=True)
    os.makedirs(input_desc_folder, exist_ok=True)

    csv_filename = secure_filename(csv_file.filename)
    model_filename = secure_filename(model_file.filename)
    preprocess_filename = secure_filename(preprocess_file.filename)
    input_desc_filename = secure_filename(input_description_file.filename)

    csv_path = os.path.join(csv_folder, csv_filename)
    model_path = os.path.join(model_folder, model_filename)
    preprocess_path = os.path.join(preprocess_folder, preprocess_filename)
    input_desc_path = os.path.join(input_desc_folder, input_desc_filename)

    csv_file.save(csv_path)
    model_file.save(model_path)
    preprocess_file.save(preprocess_path)
    input_description_file.save(input_desc_path)

    relative_csv_path = f"backend/uploads/DiseaseCSV/{csv_filename}"
    relative_model_path = f"backend/uploads/ModelFile/{model_filename}"
    relative_preprocess_path = f"backend/uploads/Preprocessing/{preprocess_filename}"
    relative_input_desc_path = f"backend/uploads/InputDesc/{input_desc_filename}"

    with engine.begin() as conn:
        try:
            conn.execute(text("""
                INSERT INTO diseases (name, description) 
                VALUES (:name, :description)
            """), {"name": name, "description": description})
            disease_id = conn.execute(text("SELECT last_insert_rowid()")).scalar()
            conn.execute(text("""
                INSERT INTO csv_uploads (disease_id, filename, upload_time)
                VALUES (:disease_id, :filename, :uploaded_at)
            """), {
                "disease_id": disease_id,
                "filename": relative_csv_path,
                "uploaded_at": datetime.datetime.utcnow()
            })
            conn.execute(text("""
                INSERT INTO models (disease_id, model_path, preprocess_path, input_description_path)
                VALUES (:disease_id, :model_path, :preprocess_path, :input_description_path)
            """), {
                "disease_id": disease_id,
                "model_path": relative_model_path,
                "preprocess_path": relative_preprocess_path,
                "input_description_path": relative_input_desc_path
            })
            flash("Disease added successfully!", "success")
        except Exception as e:
            print("ERROR:", e)
            if "UNIQUE constraint failed: diseases.name" in str(e):
                flash("Disease already exists!", "error")
            else:
                flash("An error occurred while adding the disease.", "error")

    return redirect('/')

#form input fields (column names)
@bp.route('/<int:disease_id>/columns', methods=['GET'])
def get_input_columns_from_description(disease_id):
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT input_description_path FROM models WHERE disease_id = :disease_id
        """), {"disease_id": disease_id}).fetchone()

        if not result:
            return jsonify({"error": "Input description file not found"}), 404

        path = result._mapping["input_description_path"]
    try:
        df = pd.read_excel(path, header=None)
        if df.shape[0] >= 1:
            keys = df.iloc[0].tolist()
            return jsonify(keys)
        else:
            return jsonify([])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#displaying the preview box
@bp.route('/<int:disease_id>/input_description', methods=['GET'])
def get_input_description(disease_id):
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT input_description_path FROM models WHERE disease_id = :disease_id
        """), {"disease_id": disease_id}).fetchone()

        if not result:
            return jsonify({"error": "Description file not found"}), 404

        path = result._mapping["input_description_path"]

    try:
        df = pd.read_excel(path, header=None)
        if df.shape[0] >= 2:
            keys = df.iloc[0].tolist()
            values = df.iloc[1].tolist()
            rows = list(zip(keys, values))  # Convert to list of [key, value] pairs
            return jsonify({"rows": rows})
        else:
            return jsonify({"rows": []})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

