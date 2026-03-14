from flask import Blueprint, request, jsonify
from database import query, execute

bp = Blueprint('categorias', __name__)

@bp.route('/api/categorias', methods=['GET'])
def get_categorias():
    """Get all categories."""
    try:
        categorias = query('SELECT * FROM categorias ORDER BY nombre ASC')
        return jsonify([dict(cat) for cat in categorias])
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/categorias', methods=['POST'])
def create_categoria():
    """Create a new category."""
    try:
        data = request.get_json()
        nombre = data.get('nombre', '').strip()
        
        if not nombre:
            return jsonify({'error': 'El nombre es requerido'}), 400
        
        # Check if category already exists
        exists = query('SELECT id FROM categorias WHERE nombre = ?', (nombre,), fetch='one')
        if exists:
            return jsonify({'error': 'La categoría ya existe'}), 400
        
        id = execute('INSERT INTO categorias (nombre) VALUES (?)', (nombre,))
        return jsonify({'id': id, 'nombre': nombre}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/categorias/<int:id>', methods=['PUT'])
def update_categoria(id):
    """Update a category."""
    try:
        data = request.get_json()
        nombre = data.get('nombre', '').strip()
        
        if not nombre:
            return jsonify({'error': 'El nombre es requerido'}), 400
        
        # Check if category exists
        cat = query('SELECT id FROM categorias WHERE id = ?', (id,), fetch='one')
        if not cat:
            return jsonify({'error': 'Categoría no encontrada'}), 404
        
        # Check if new name already exists
        exists = query('SELECT id FROM categorias WHERE nombre = ? AND id != ?', (nombre, id), fetch='one')
        if exists:
            return jsonify({'error': 'Ya existe una categoría con ese nombre'}), 400
        
        execute('UPDATE categorias SET nombre = ? WHERE id = ?', (nombre, id))
        return jsonify({'id': id, 'nombre': nombre})
    except Exception as e:
        return jsonify({'error': str(e)}), 400
