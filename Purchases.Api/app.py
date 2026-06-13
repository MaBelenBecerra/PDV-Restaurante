from flask import Flask, jsonify, request
from flask_cors import CORS
from database import init_db
from routes.purchases import bp as purchases_bp
import uuid
from werkzeug.exceptions import HTTPException

app = Flask(__name__)

# Configure CORS to accept localhost:5173 (Vite frontend) and localhost:3000
CORS(app, origins=['http://localhost:5173', 'http://localhost:3000'])

# Database verification on startup disabled (trusted connection)

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

@app.route('/swagger', methods=['GET'])
@app.route('/swagger/', methods=['GET'])
@app.route('/swagger/index.html', methods=['GET'])
def swagger_ui():
    return """
    <!DOCTYPE html>
    <html lang="es">
    <head>
      <meta charset="UTF-8">
      <title>Documentación de la API de Compras - Swagger UI</title>
      <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui.css" />
      <style>
        html { box-sizing: border-box; overflow: -y-scroll; }
        *, *:before, *:after { box-sizing: inherit; }
        body { margin: 0; background: #fafafa; }
      </style>
    </head>
    <body>
      <div id="swagger-ui"></div>
      <script src="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui-bundle.js"></script>
      <script src="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui-standalone-preset.js"></script>
      <script>
        window.onload = function() {
          const ui = SwaggerUIBundle({
            url: "/static/swagger.json",
            dom_id: '#swagger-ui',
            deepLinking: true,
            presets: [
              SwaggerUIBundle.presets.apis,
              SwaggerUIStandalonePreset
            ],
            plugins: [
              SwaggerUIBundle.plugins.DownloadUrl
            ],
            layout: "BaseLayout"
          });
          window.ui = ui;
        };
      </script>
    </body>
    </html>
    """, 200

@app.route('/swagger.json', methods=['GET'])
@app.route('/static/swagger.json', methods=['GET'])
def serve_swagger_json():
    import os
    from flask import send_from_directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    static_dir = os.path.join(current_dir, 'static')
    return send_from_directory(static_dir, 'swagger.json')

if __name__ == '__main__':
    app.run(debug=True, port=5229, host='0.0.0.0')
