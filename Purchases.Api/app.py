from flask import Flask
from flask_cors import CORS
from database import init_db
from routes.purchases import bp as purchases_bp

app = Flask(__name__)

# Configure CORS to accept localhost:5173 (Vite frontend) and localhost:3000
CORS(app, origins=['http://localhost:5173', 'http://localhost:3000'])

# Initialize database
init_db()

# Register blueprints
app.register_blueprint(purchases_bp)

@app.route('/health', methods=['GET'])
def health():
    return {'status': 'ok', 'service': 'purchases-api'}, 200

if __name__ == '__main__':
    app.run(debug=True, port=5229, host='0.0.0.0')
