from flask import Blueprint, request, jsonify
from database import query, execute

bp = Blueprint('unidades', __name__)

@bp.route('/api/unidades', methods=['GET'])
def get_unidades():
    """Get all units."""
    try:
        unidades = query('SELECT * FROM unidades ORDER BY nombre ASC')
        return jsonify([dict(u) for u in unidades])
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/unidades', methods=['POST'])
def create_unidad():
    """Create a new unit."""
    try:
        data = request.get_json()
        nombre = data.get('nombre', '').strip()
        
        if not nombre:
            return jsonify({'error': 'El nombre es requerido'}), 400
        
        # Check if unit already exists
        exists = query('SELECT id FROM unidades WHERE nombre = ?', (nombre,), fetch='one')
        if exists:
            return jsonify({'error': 'La unidad ya existe'}), 400
        
        id = execute('INSERT INTO unidades (nombre) VALUES (?)', (nombre,))
        return jsonify({'id': id, 'nombre': nombre}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/unidades/<int:id>', methods=['PUT'])
def update_unidad(id):
    """Update a unit."""
    try:
        data = request.get_json()
        nombre = data.get('nombre', '').strip()
        
        if not nombre:
            return jsonify({'error': 'El nombre es requerido'}), 400
        
        # Check if unit exists
        unit = query('SELECT id FROM unidades WHERE id = ?', (id,), fetch='one')
        if not unit:
            return jsonify({'error': 'Unidad no encontrada'}), 404
        
        # Check if new name already exists
        exists = query('SELECT id FROM unidades WHERE nombre = ? AND id != ?', (nombre, id), fetch='one')
        if exists:
            return jsonify({'error': 'Ya existe una unidad con ese nombre'}), 400
        
        execute('UPDATE unidades SET nombre = ? WHERE id = ?', (nombre, id))
        return jsonify({'id': id, 'nombre': nombre})
    except Exception as e:
        return jsonify({'error': str(e)}), 400
