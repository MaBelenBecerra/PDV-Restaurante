from flask import Blueprint, request, jsonify
from database import query, execute

bp = Blueprint('inventario', __name__)

@bp.route('/api/inventario', methods=['GET'])
def get_inventario():
    """Get inventory with product stock and status."""
    try:
        productos = query('''
            SELECT p.id, p.nombre, p.categoria_id, p.unidad_id, p.stock, 
                   p.activo, p.agotado, p.precio,
                   c.nombre as categoria, u.nombre as unidad
            FROM productos p
            JOIN categorias c ON c.id = p.categoria_id
            JOIN unidades u ON u.id = p.unidad_id
            ORDER BY p.nombre ASC
        ''')
        
        result = []
        for p in productos:
            item = dict(p)
            if item['agotado'] == 1:
                item['estado'] = 'agotado'
            elif item['stock'] < 5:
                item['estado'] = 'bajo'
            else:
                item['estado'] = 'ok'
            result.append(item)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/inventario/ajuste', methods=['POST'])
def ajuste_stock():
    """Adjust product stock."""
    try:
        data = request.get_json()
        
        producto_id = data.get('producto_id')
        tipo = data.get('tipo', '').lower()
        cantidad = data.get('cantidad', 0)
        motivo = data.get('motivo', '').strip()
        
        # Validation
        if not producto_id:
            return jsonify({'error': 'El producto es requerido'}), 400
        
        if tipo not in ['entrada', 'salida']:
            return jsonify({'error': 'El tipo debe ser entrada o salida'}), 400
        
        if cantidad <= 0:
            return jsonify({'error': 'La cantidad debe ser mayor a 0'}), 400
        
        if not motivo:
            return jsonify({'error': 'El motivo es requerido'}), 400
        
        # Check if product exists
        prod = query('SELECT stock FROM productos WHERE id = ?', (producto_id,), fetch='one')
        if not prod:
            return jsonify({'error': 'Producto no encontrado'}), 404
        
        # For 'salida', check if there's enough stock
        if tipo == 'salida' and prod['stock'] < cantidad:
            return jsonify({'error': f'Stock insuficiente. Disponible: {prod["stock"]}'}), 400
        
        # Create adjustment record
        id = execute(
            '''INSERT INTO ajustes_stock (producto_id, tipo, cantidad, motivo) 
               VALUES (?, ?, ?, ?)''',
            (producto_id, tipo, cantidad, motivo)
        )
        
        # Update product stock
        if tipo == 'entrada':
            execute('UPDATE productos SET stock = stock + ? WHERE id = ?', (cantidad, producto_id))
        else:  # salida
            execute('UPDATE productos SET stock = stock - ? WHERE id = ?', (cantidad, producto_id))
        
        # Get updated product
        updated = query('''
            SELECT p.id, p.nombre, p.stock, p.agotado,
                   c.nombre as categoria, u.nombre as unidad
            FROM productos p
            JOIN categorias c ON c.id = p.categoria_id
            JOIN unidades u ON u.id = p.unidad_id
            WHERE p.id = ?
        ''', (producto_id,), fetch='one')
        
        return jsonify({
            'ajuste_id': id,
            'producto': dict(updated)
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400
