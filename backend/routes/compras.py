from flask import Blueprint, request, jsonify
from database import query, execute

bp = Blueprint('compras', __name__)

# PROVEEDORES
@bp.route('/api/proveedores', methods=['GET'])
def get_proveedores():
    """Get all suppliers."""
    try:
        proveedores = query('SELECT * FROM proveedores ORDER BY nombre ASC')
        return jsonify([dict(p) for p in proveedores])
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/proveedores', methods=['POST'])
def create_proveedor():
    """Create a new supplier."""
    try:
        data = request.get_json()
        nombre = data.get('nombre', '').strip()
        contacto = data.get('contacto', '').strip()
        telefono = data.get('telefono', '').strip()
        email = data.get('email', '').strip()
        
        if not nombre:
            return jsonify({'error': 'El nombre del proveedor es requerido'}), 400
        
        # Check if supplier already exists
        exists = query('SELECT id FROM proveedores WHERE nombre = ?', (nombre,), fetch='one')
        if exists:
            return jsonify({'error': 'El proveedor ya existe'}), 400
        
        id = execute(
            'INSERT INTO proveedores (nombre, contacto, telefono, email) VALUES (?, ?, ?, ?)',
            (nombre, contacto, telefono, email)
        )
        return jsonify({
            'id': id,
            'nombre': nombre,
            'contacto': contacto,
            'telefono': telefono,
            'email': email
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# COMPRAS
@bp.route('/api/purchases/orders', methods=['GET'])
def get_compras():
    """Get all purchase orders."""
    try:
        estado = request.args.get('estado', '').strip()
        
        sql = '''
            SELECT c.id, c.proveedor_id, p.nombre AS proveedor, c.estado,
                   COALESCE(SUM(ci.cantidad),0) AS total_items,
                   c.total, c.fecha, c.creado_en, c.confirmado_en
            FROM compras c
            JOIN proveedores p ON p.id = c.proveedor_id
            LEFT JOIN compra_items ci ON ci.compra_id = c.id
            WHERE 1=1
        '''
        params = []
        
        if estado and estado in ['pendiente', 'confirmada', 'cancelada']:
            sql += ' AND c.estado = ?'
            params.append(estado)
        
        sql += ' GROUP BY c.id ORDER BY c.fecha DESC'
        
        compras = query(sql, tuple(params) if params else None)
        return jsonify([dict(c) for c in compras])
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/purchases/orders', methods=['POST'])
def create_compra():
    """Create a new purchase order."""
    try:
        data = request.get_json()
        proveedor_id = data.get('proveedor_id')
        
        if not proveedor_id:
            return jsonify({'error': 'El proveedor es requerido'}), 400
        
        # Check if supplier exists
        prov = query('SELECT id FROM proveedores WHERE id = ?', (proveedor_id,), fetch='one')
        if not prov:
            return jsonify({'error': 'Proveedor no encontrado'}), 404
        
        id = execute(
            'INSERT INTO compras (proveedor_id, estado) VALUES (?, ?)',
            (proveedor_id, 'pendiente')
        )
        
        compra = query(
            '''SELECT c.id, c.proveedor_id, p.nombre AS proveedor, c.estado,
                      0 AS total_items, 0 AS total, c.fecha, c.creado_en
               FROM compras c
               JOIN proveedores p ON p.id = c.proveedor_id
               WHERE c.id = ?''',
            (id,),
            fetch='one'
        )
        return jsonify(dict(compra)), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/purchases/orders/<int:id>', methods=['GET'])
def get_compra(id):
    """Get purchase order details with items."""
    try:
        compra = query(
            '''SELECT c.id, c.proveedor_id, p.nombre AS proveedor, c.estado,
                      c.total, c.fecha, c.creado_en, c.confirmado_en
               FROM compras c
               JOIN proveedores p ON p.id = c.proveedor_id
               WHERE c.id = ?''',
            (id,),
            fetch='one'
        )
        if not compra:
            return jsonify({'error': 'Compra no encontrada'}), 404
        
        items = query('''
            SELECT ci.id, ci.producto_id, ci.cantidad, ci.precio_unitario,
                   ci.subtotal, p.nombre, c.nombre AS categoria
            FROM compra_items ci
            JOIN productos p ON p.id = ci.producto_id
            JOIN categorias c ON c.id = p.categoria_id
            WHERE ci.compra_id = ?
            ORDER BY ci.id ASC
        ''', (id,))
        
        result = dict(compra)
        result['items'] = [dict(item) for item in items]
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/purchases/orders/<int:compra_id>/items', methods=['POST'])
def agregar_item_compra(compra_id):
    """Add item to purchase order."""
    try:
        data = request.get_json()
        
        producto_id = data.get('producto_id')
        cantidad = data.get('cantidad', 1)
        precio_unitario = data.get('precio_unitario', 0)
        
        # Check purchase exists and is pending
        compra = query('SELECT * FROM compras WHERE id = ?', (compra_id,), fetch='one')
        if not compra:
            return jsonify({'error': 'Compra no encontrada'}), 404
        
        if compra['estado'] != 'pendiente':
            return jsonify({'error': 'Solo se pueden agregar items a compras pendientes'}), 400
        
        # Check product exists
        prod = query('SELECT * FROM productos WHERE id = ?', (producto_id,), fetch='one')
        if not prod:
            return jsonify({'error': 'Producto no encontrado'}), 404
        
        # Validation
        if cantidad <= 0:
            return jsonify({'error': 'La cantidad debe ser mayor a 0'}), 400
        
        if precio_unitario <= 0:
            return jsonify({'error': 'El precio unitario debe ser mayor a 0'}), 400
        
        # Calculate subtotal
        subtotal = precio_unitario * cantidad
        
        # Create item
        item_id = execute(
            '''INSERT INTO compra_items (compra_id, producto_id, cantidad,
                                         precio_unitario, subtotal)
               VALUES (?, ?, ?, ?, ?)''',
            (compra_id, producto_id, cantidad, precio_unitario, subtotal)
        )
        
        # Update purchase total
        total = query(
            'SELECT COALESCE(SUM(subtotal),0) as total FROM compra_items WHERE compra_id = ?',
            (compra_id,),
            fetch='one'
        )['total']
        
        execute('UPDATE compras SET total = ? WHERE id = ?', (total, compra_id))
        
        # Fetch item with product info
        item = query('''
            SELECT ci.id, ci.producto_id, ci.cantidad, ci.precio_unitario,
                   ci.subtotal, p.nombre, c.nombre as categoria
            FROM compra_items ci
            JOIN productos p ON p.id = ci.producto_id
            JOIN categorias c ON c.id = p.categoria_id
            WHERE ci.id = ?
        ''', (item_id,), fetch='one')
        
        return jsonify({
            'item': dict(item),
            'compra_total': total
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/purchases/orders/<int:compra_id>/items/<int:item_id>', methods=['PUT'])
def editar_item_compra(compra_id, item_id):
    """Edit purchase item."""
    try:
        data = request.get_json()
        
        # Check purchase exists and is pending
        compra = query('SELECT * FROM compras WHERE id = ?', (compra_id,), fetch='one')
        if not compra:
            return jsonify({'error': 'Compra no encontrada'}), 404
        
        if compra['estado'] != 'pendiente':
            return jsonify({'error': 'No se pueden editar items de compras confirmadas'}), 400
        
        # Check item exists
        item = query('SELECT * FROM compra_items WHERE id = ? AND compra_id = ?',
                     (item_id, compra_id), fetch='one')
        if not item:
            return jsonify({'error': 'Item no encontrado'}), 404
        
        # Update fields
        if 'cantidad' in data:
            cantidad = data.get('cantidad', 1)
            if cantidad <= 0:
                return jsonify({'error': 'La cantidad debe ser mayor a 0'}), 400
            
            precio = item['precio_unitario']
            subtotal = precio * cantidad
            execute(
                'UPDATE compra_items SET cantidad = ?, subtotal = ? WHERE id = ?',
                (cantidad, subtotal, item_id)
            )
        
        if 'precio_unitario' in data:
            precio = data.get('precio_unitario', 0)
            if precio <= 0:
                return jsonify({'error': 'El precio debe ser mayor a 0'}), 400
            
            cant = item['cantidad']
            subtotal = precio * cant
            execute(
                'UPDATE compra_items SET precio_unitario = ?, subtotal = ? WHERE id = ?',
                (precio, subtotal, item_id)
            )
        
        # Update purchase total
        total = query(
            'SELECT COALESCE(SUM(subtotal),0) as total FROM compra_items WHERE compra_id = ?',
            (compra_id,),
            fetch='one'
        )['total']
        
        execute('UPDATE compras SET total = ? WHERE id = ?', (total, compra_id))
        
        # Fetch updated item
        updated_item = query('''
            SELECT ci.id, ci.producto_id, ci.cantidad, ci.precio_unitario,
                   ci.subtotal, p.nombre, c.nombre as categoria
            FROM compra_items ci
            JOIN productos p ON p.id = ci.producto_id
            JOIN categorias c ON c.id = p.categoria_id
            WHERE ci.id = ?
        ''', (item_id,), fetch='one')
        
        return jsonify({
            'item': dict(updated_item),
            'compra_total': total
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/purchases/orders/<int:compra_id>/items/<int:item_id>', methods=['DELETE'])
def eliminar_item_compra(compra_id, item_id):
    """Remove item from purchase order."""
    try:
        # Check purchase exists and is pending
        compra = query('SELECT * FROM compras WHERE id = ?', (compra_id,), fetch='one')
        if not compra:
            return jsonify({'error': 'Compra no encontrada'}), 404
        
        if compra['estado'] != 'pendiente':
            return jsonify({'error': 'No se pueden eliminar items de compras confirmadas'}), 400
        
        # Check item exists
        item = query('SELECT * FROM compra_items WHERE id = ? AND compra_id = ?',
                     (item_id, compra_id), fetch='one')
        if not item:
            return jsonify({'error': 'Item no encontrado'}), 404
        
        execute('DELETE FROM compra_items WHERE id = ?', (item_id,))
        
        # Update purchase total
        total = query(
            'SELECT COALESCE(SUM(subtotal),0) as total FROM compra_items WHERE compra_id = ?',
            (compra_id,),
            fetch='one'
        )['total']
        
        execute('UPDATE compras SET total = ? WHERE id = ?', (total, compra_id))
        
        return jsonify({'compra_total': total})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/purchases/orders/<int:id>/confirm', methods=['POST'])
def confirmar_compra(id):
    """Confirm purchase order and increase inventory."""
    try:
        # Check purchase exists
        compra = query('SELECT * FROM compras WHERE id = ?', (id,), fetch='one')
        if not compra:
            return jsonify({'error': 'Compra no encontrada'}), 404
        
        if compra['estado'] != 'pendiente':
            return jsonify({'error': 'La compra no está pendiente'}), 400
        
        # Check purchase has items
        items = query('SELECT COUNT(*) as count FROM compra_items WHERE compra_id = ?',
                      (id,), fetch='one')
        if items['count'] == 0:
            return jsonify({'error': 'La compra no tiene items'}), 400
        
        # Update purchase status to confirmed (trigger will increase stock)
        execute(
            'UPDATE compras SET estado = ?, confirmado_en = datetime(\'now\') WHERE id = ?',
            ('confirmada', id)
        )
        
        # Fetch updated purchase
        updated = query(
            '''SELECT c.id, c.proveedor_id, p.nombre AS proveedor, c.estado,
                      c.total, c.fecha, c.creado_en, c.confirmado_en
               FROM compras c
               JOIN proveedores p ON p.id = c.proveedor_id
               WHERE c.id = ?''',
            (id,),
            fetch='one'
        )
        
        return jsonify({
            'message': 'Compra confirmada y stock actualizado',
            'compra': dict(updated)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/purchases/orders/<int:id>/cancel', methods=['PATCH'])
def cancelar_compra(id):
    """Cancel a purchase order."""
    try:
        compra = query('SELECT * FROM compras WHERE id = ?', (id,), fetch='one')
        if not compra:
            return jsonify({'error': 'Compra no encontrada'}), 404
        
        if compra['estado'] != 'pendiente':
            return jsonify({'error': 'Solo se pueden cancelar compras pendientes'}), 400
        
        execute('UPDATE compras SET estado = ? WHERE id = ?', ('cancelada', id))
        
        updated = query(
            '''SELECT c.id, c.proveedor_id, p.nombre AS proveedor, c.estado,
                      c.total, c.fecha, c.creado_en
               FROM compras c
               JOIN proveedores p ON p.id = c.proveedor_id
               WHERE c.id = ?''',
            (id,),
            fetch='one'
        )
        return jsonify(dict(updated))
    except Exception as e:
        return jsonify({'error': str(e)}), 400
