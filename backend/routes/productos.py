from flask import Blueprint, request, jsonify
from database import query, execute

bp = Blueprint('productos', __name__)

@bp.route('/api/productos', methods=['GET'])
def get_productos():
    """Get products with optional filters."""
    try:
        categoria_id = request.args.get('categoria_id', type=int)
        activo = request.args.get('activo', type=int)
        buscar = request.args.get('buscar', '').strip()
        
        sql = '''
            SELECT p.id, p.nombre, p.categoria_id, p.unidad_id, p.precio, 
                   p.stock, p.activo, p.agotado, c.nombre as categoria, u.nombre as unidad
            FROM productos p
            JOIN categorias c ON c.id = p.categoria_id
            JOIN unidades u ON u.id = p.unidad_id
            WHERE 1=1
        '''
        params = []
        
        if categoria_id is not None:
            sql += ' AND p.categoria_id = ?'
            params.append(categoria_id)
        
        if activo is not None:
            sql += ' AND p.activo = ?'
            params.append(activo)
        
        if buscar:
            sql += ' AND LOWER(p.nombre) LIKE LOWER(?)'
            params.append(f'%{buscar}%')
        
        sql += ' ORDER BY p.nombre ASC'
        
        productos = query(sql, tuple(params) if params else None)
        return jsonify([dict(p) for p in productos])
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/productos', methods=['POST'])
def create_producto():
    """Create a new product."""
    try:
        data = request.get_json()
        
        nombre = data.get('nombre', '').strip()
        categoria_id = data.get('categoria_id')
        unidad_id = data.get('unidad_id')
        precio = data.get('precio', 0)
        stock = data.get('stock', 0)
        
        # Validation
        if not nombre:
            return jsonify({'error': 'El nombre es requerido'}), 400
        if not categoria_id:
            return jsonify({'error': 'La categoría es requerida'}), 400
        if not unidad_id:
            return jsonify({'error': 'La unidad es requerida'}), 400
        if precio <= 0:
            return jsonify({'error': 'El precio debe ser mayor a 0'}), 400
        
        # Check if category exists
        cat = query('SELECT id FROM categorias WHERE id = ?', (categoria_id,), fetch='one')
        if not cat:
            return jsonify({'error': 'Categoría no encontrada'}), 400
        
        # Check if unit exists
        unit = query('SELECT id FROM unidades WHERE id = ?', (unidad_id,), fetch='one')
        if not unit:
            return jsonify({'error': 'Unidad no encontrada'}), 400
        
        id = execute(
            '''INSERT INTO productos (nombre, categoria_id, unidad_id, precio, stock) 
               VALUES (?, ?, ?, ?, ?)''',
            (nombre, categoria_id, unidad_id, precio, stock)
        )
        
        return jsonify({
            'id': id,
            'nombre': nombre,
            'categoria_id': categoria_id,
            'unidad_id': unidad_id,
            'precio': precio,
            'stock': stock,
            'activo': 1,
            'agotado': 0
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/productos/<int:id>', methods=['PUT'])
def update_producto(id):
    """Update a product."""
    try:
        data = request.get_json()
        
        # Check if product exists
        prod = query('SELECT * FROM productos WHERE id = ?', (id,), fetch='one')
        if not prod:
            return jsonify({'error': 'Producto no encontrado'}), 404
        
        # Get fields to update
        updates = []
        params = []
        
        if 'nombre' in data:
            nombre = data.get('nombre', '').strip()
            if not nombre:
                return jsonify({'error': 'El nombre no puede estar vacío'}), 400
            updates.append('nombre = ?')
            params.append(nombre)
        
        if 'precio' in data:
            precio = data.get('precio', 0)
            if precio <= 0:
                return jsonify({'error': 'El precio debe ser mayor a 0'}), 400
            updates.append('precio = ?')
            params.append(precio)
        
        if 'stock' in data:
            stock = data.get('stock', 0)
            updates.append('stock = ?')
            params.append(stock)
        
        if 'categoria_id' in data:
            categoria_id = data.get('categoria_id')
            cat = query('SELECT id FROM categorias WHERE id = ?', (categoria_id,), fetch='one')
            if not cat:
                return jsonify({'error': 'Categoría no encontrada'}), 400
            updates.append('categoria_id = ?')
            params.append(categoria_id)
        
        if 'unidad_id' in data:
            unidad_id = data.get('unidad_id')
            unit = query('SELECT id FROM unidades WHERE id = ?', (unidad_id,), fetch='one')
            if not unit:
                return jsonify({'error': 'Unidad no encontrada'}), 400
            updates.append('unidad_id = ?')
            params.append(unidad_id)
        
        if updates:
            params.append(id)
            execute(f"UPDATE productos SET {', '.join(updates)} WHERE id = ?", tuple(params))
        
        # Fetch updated product
        updated = query(
            '''SELECT p.*, c.nombre as categoria, u.nombre as unidad 
               FROM productos p
               JOIN categorias c ON c.id = p.categoria_id
               JOIN unidades u ON u.id = p.unidad_id
               WHERE p.id = ?''',
            (id,),
            fetch='one'
        )
        return jsonify(dict(updated))
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/productos/<int:id>/toggle-activo', methods=['PATCH'])
def toggle_activo(id):
    """Toggle product active status."""
    try:
        prod = query('SELECT activo FROM productos WHERE id = ?', (id,), fetch='one')
        if not prod:
            return jsonify({'error': 'Producto no encontrado'}), 404
        
        new_activo = 1 - prod['activo']
        execute('UPDATE productos SET activo = ? WHERE id = ?', (new_activo, id))
        
        updated = query(
            '''SELECT p.*, c.nombre as categoria, u.nombre as unidad 
               FROM productos p
               JOIN categorias c ON c.id = p.categoria_id
               JOIN unidades u ON u.id = p.unidad_id
               WHERE p.id = ?''',
            (id,),
            fetch='one'
        )
        return jsonify(dict(updated))
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/productos/<int:id>/toggle-agotado', methods=['PATCH'])
def toggle_agotado(id):
    """Toggle product out-of-stock status."""
    try:
        prod = query('SELECT agotado FROM productos WHERE id = ?', (id,), fetch='one')
        if not prod:
            return jsonify({'error': 'Producto no encontrado'}), 404
        
        new_agotado = 1 - prod['agotado']
        execute('UPDATE productos SET agotado = ? WHERE id = ?', (new_agotado, id))
        
        updated = query(
            '''SELECT p.*, c.nombre as categoria, u.nombre as unidad 
               FROM productos p
               JOIN categorias c ON c.id = p.categoria_id
               JOIN unidades u ON u.id = p.unidad_id
               WHERE p.id = ?''',
            (id,),
            fetch='one'
        )
        return jsonify(dict(updated))
    except Exception as e:
        return jsonify({'error': str(e)}), 400
