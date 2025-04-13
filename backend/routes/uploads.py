import os
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from sqlalchemy import text
from database.db import engine

bp = Blueprint('uploads', __name__, url_prefix='/upload_csv')

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'uploads')
ALLOWED_EXTENSIONS = {'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/', methods=['POST'])
def upload_csv():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    disease_id = request.form.get('disease_id')

    if not disease_id:
        return jsonify({'error': 'Missing disease_id'}), 400

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(save_path)

        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO csv_uploads (disease_id, filename) VALUES (:disease_id, :filename)"),
                {"disease_id": disease_id, "filename": filename}
            )

        return jsonify({'message': 'CSV uploaded successfully'}), 201

    return jsonify({'error': 'Invalid file format. Only CSV allowed'}), 400
