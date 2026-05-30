from flask import Flask
from flask_cors import CORS
from database import init_db
from routes.sales import bp as sales_bp

app = Flask(__name__)

# Configure CORS to accept localhost:5173 (Vite frontend) and localhost:3000
CORS(app, origins=['http://localhost:5173', 'http://localhost:3000'])

# Initialize database
init_db()

# Register blueprints
app.register_blueprint(sales_bp)

@app.route('/health', methods=['GET'])
def health():
    return {'status': 'ok', 'service': 'sales-api'}, 200

if __name__ == '__main__':
    app.run(debug=True, port=5074, host='0.0.0.0')
