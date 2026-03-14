from flask import Flask
from flask_cors import CORS
from database import init_db

# Create Flask app
app = Flask(__name__)

# Enable CORS for localhost:5173
CORS(app, origins=['http://localhost:5173', 'http://localhost:3000'])

# Initialize database
init_db()

# Register blueprints
from routes.categorias import bp as categorias_bp
from routes.unidades import bp as unidades_bp
from routes.productos import bp as productos_bp
from routes.inventario import bp as inventario_bp
from routes.tickets import bp as tickets_bp
from routes.comandas import bp as comandas_bp
from routes.dashboard import bp as dashboard_bp

app.register_blueprint(categorias_bp)
app.register_blueprint(unidades_bp)
app.register_blueprint(productos_bp)
app.register_blueprint(inventario_bp)
app.register_blueprint(tickets_bp)
app.register_blueprint(comandas_bp)
app.register_blueprint(dashboard_bp)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return {'status': 'ok'}, 200

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')
