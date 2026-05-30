from flask import Flask
from flask_cors import CORS
from database import init_db
from routes.inventory import bp as inventory_bp

app = Flask(__name__)

# Configure CORS to accept localhost:5173 (Vite frontend) and localhost:3000
CORS(app, origins=['http://localhost:5173', 'http://localhost:3000'])

# Initialize database
init_db()

# Register blueprints
app.register_blueprint(inventory_bp)

@app.route('/health', methods=['GET'])
def health():
    return {'status': 'ok', 'service': 'inventory-api'}, 200

@app.route('/swagger', methods=['GET'])
@app.route('/swagger/', methods=['GET'])
@app.route('/swagger/index.html', methods=['GET'])
def swagger_ui():
    return """
    <!DOCTYPE html>
    <html lang="es">
    <head>
      <meta charset="UTF-8">
      <title>Documentación de la API de Inventario - Swagger UI</title>
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
    app.run(debug=True, port=5143, host='0.0.0.0')
