from flask import Blueprint, request, jsonify, redirect, flash
from sqlalchemy import text
from database.db import engine
from werkzeug.utils import secure_filename
import os
import datetime

bp = Blueprint('diseases', __name__, url_prefix='/diseases')

# GET /diseases - fetch all diseases
@bp.route('/', methods=['GET'])
def get_diseases():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT id, name, description FROM diseases")).mappings()
        diseases = [dict(row) for row in result]
    return jsonify(diseases)

# POST /diseases - add a new disease
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


#form submission with file upload
@bp.route('/form', methods=['POST'])
def add_disease_from_form():
    name = request.form.get('name')
    description = request.form.get('description')
    file = request.files.get('file')

    if not name or not file:
        return "Missing disease name or CSV file", 400

    #Save file to backend/uploads
    upload_folder = os.path.join("backend", "uploads")
    os.makedirs(upload_folder, exist_ok=True)

    filename = secure_filename(file.filename)
    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)

    #Save relative path in DB
    relative_path = f"backend/uploads/{filename}"

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
                "filename": relative_path,
                "uploaded_at": datetime.datetime.utcnow()
            })

            flash("Disease added successfully!", "success")
        except Exception as e:
            if "UNIQUE constraint failed: diseases.name" in str(e):
                flash("Disease already exists!", "error")
            else:
                flash("An error occurred while adding the disease.", "error")

        return redirect('/')

