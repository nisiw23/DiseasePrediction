from flask import Flask, render_template, request
from flask_cors import CORS
from routes import disease, uploads, predict 

app = Flask(
    __name__,
    static_url_path='/static',  
    static_folder='static',
    template_folder='templates'
)
app.secret_key = "supersecretkey" 
CORS(app)

from routes import disease, uploads, predict

app.register_blueprint(disease.bp)
app.register_blueprint(uploads.bp)
app.register_blueprint(predict.bp)

@app.route('/')
def index():
    from sqlalchemy import text
    from database.db import engine

    with engine.connect() as conn:
        result = conn.execute(text("SELECT id, name FROM diseases")).mappings()
        diseases = [dict(row) for row in result]

    return render_template("home.html", diseases=diseases)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)