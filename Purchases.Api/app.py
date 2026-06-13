from flask import Flask, jsonify, request
from flask_cors import CORS
from database import init_db
from routes.purchases import bp as purchases_bp
import uuid
from werkzeug.exceptions import HTTPException

app = Flask(__name__)

# Configure CORS to accept localhost:5173 (Vite frontend) and localhost:3000
CORS(app, origins=['http://localhost:5173', 'http://localhost:3000'])

# Initialize database
init_db()

@app.errorhandler(Exception)
def handle_exception(e):
    # Pass through HTTP exceptions
    if isinstance(e, HTTPException):
        response = jsonify({
            "status": e.code,
            "title": e.name,
            "detail": e.description,
            "instance": request.path,
            "traceId": "00-" + str(uuid.uuid4())
        })
        response.content_type = "application/problem+json"
        return response, e.code

    # Map Python exception types to ProblemDetails HTTP status codes
    status = 500
    title = "Error interno del servidor"
    detail = "Ocurrio un error inesperado. Intenta nuevamente o contacta a soporte."
    
    e_str = str(e).lower()
    if isinstance(e, KeyError) or isinstance(e, FileNotFoundError) or "not found" in e_str:
        status = 404
        title = "Recurso no encontrado"
        detail = str(e)
    elif isinstance(e, ValueError) or isinstance(e, TypeError) or "invalid" in e_str:
        status = 400
        title = "Argumento invalido"
        detail = str(e)
    elif isinstance(e, PermissionError):
        status = 403
        title = "Acceso no autorizado"
        detail = str(e)
        
    response = jsonify({
        "status": status,
        "title": title,
        "detail": detail,
        "instance": request.path,
        "traceId": "00-" + str(uuid.uuid4())
    })
    response.content_type = "application/problem+json"
    return response, status

# Register blueprints
app.register_blueprint(purchases_bp)

@app.route('/health', methods=['GET'])
def health():
    return {'status': 'ok', 'service': 'purchases-api'}, 200


if __name__ == '__main__':
    app.run(debug=True, port=5229, host='0.0.0.0')
