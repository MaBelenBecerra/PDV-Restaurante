from flask import Blueprint, request, jsonify
from database import query, execute

bp = Blueprint('tickets', __name__)

@bp.route('/api/tickets', methods=['GET'])
def get_tickets():
    """Get tickets with optional state filter."""
    try:
        estado = request.args.get('estado', '').strip()
        
        sql = 'SELECT * FROM tickets WHERE 1=1'
        params = []
        
        if estado and estado in ['abierto', 'pagado', 'cancelado']:
            sql += ' AND estado = ?'
            params.append(estado)
        
        sql += ' ORDER BY id DESC'
        
        tickets = query(sql, tuple(params) if params else None)
        return jsonify([dict(t) for t in tickets])
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/tickets', methods=['POST'])
def create_ticket():
    """Create a new ticket."""
    try:
        data = request.get_json()
        
        mesero = data.get('mesero', '').strip()
        cliente_id = data.get('cliente_id')
        
        if not mesero:
            return jsonify({'error': 'El mesero es requerido'}), 400
        
        # Get default tax rate
        config = query('SELECT tasa_impuesto FROM configuracion WHERE id = 1', fetch='one')
        tasa_impuesto = config['tasa_impuesto'] if config else 0.13
        
        id = execute(
            '''INSERT INTO tickets (mesero, cliente_id, tasa_impuesto) 
               VALUES (?, ?, ?)''',
            (mesero, cliente_id, tasa_impuesto)
        )
        
        ticket = query('SELECT * FROM tickets WHERE id = ?', (id,), fetch='one')
        return jsonify(dict(ticket)), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/tickets/<int:id>', methods=['GET'])
def get_ticket(id):
    """Get ticket details with items."""
    try:
        ticket = query('SELECT * FROM tickets WHERE id = ?', (id,), fetch='one')
        if not ticket:
            return jsonify({'error': 'Ticket no encontrado'}), 404
        
        items = query('''
            SELECT ti.id, ti.producto_id, ti.cantidad, ti.precio_unitario, 
                   ti.subtotal, ti.nota, p.nombre, c.nombre as categoria
            FROM ticket_items ti
            JOIN productos p ON p.id = ti.producto_id
            JOIN categorias c ON c.id = p.categoria_id
            WHERE ti.ticket_id = ?
            ORDER BY ti.id ASC
        ''', (id,))
        
        result = dict(ticket)
        result['items'] = [dict(item) for item in items]
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/tickets/<int:ticket_id>/items', methods=['POST'])
def agregar_item(ticket_id):
    """Add item to ticket."""
    try:
        data = request.get_json()
        
        producto_id = data.get('producto_id')
        cantidad = data.get('cantidad', 1)
        nota = data.get('nota', '').strip()
        
        # Check ticket exists and is open
        ticket = query('SELECT * FROM tickets WHERE id = ?', (ticket_id,), fetch='one')
        if not ticket:
            return jsonify({'error': 'Ticket no encontrado'}), 404
        
        if ticket['estado'] != 'abierto':
            return jsonify({'error': 'Solo se pueden agregar items a tickets abiertos'}), 400
        
        # Check product exists
        prod = query('SELECT * FROM productos WHERE id = ?', (producto_id,), fetch='one')
        if not prod:
            return jsonify({'error': 'Producto no encontrado'}), 404
        
        # Validation
        if prod['activo'] == 0:
            return jsonify({'error': 'El producto está inactivo'}), 400
        
        if prod['agotado'] == 1:
            return jsonify({'error': 'El producto está agotado'}), 400
        
        if cantidad <= 0:
            return jsonify({'error': 'La cantidad debe ser mayor a 0'}), 400
        
        if prod['stock'] < cantidad:
            return jsonify({'error': f'Stock insuficiente. Disponible: {prod["stock"]}'}), 400
        
        # Calculate subtotal
        precio_unitario = prod['precio']
        subtotal = precio_unitario * cantidad
        
        # Create item
        item_id = execute(
            '''INSERT INTO ticket_items (ticket_id, producto_id, cantidad, 
                                         precio_unitario, subtotal, nota)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (ticket_id, producto_id, cantidad, precio_unitario, subtotal, nota)
        )
        
        # Fetch item with product info
        item = query('''
            SELECT ti.id, ti.producto_id, ti.cantidad, ti.precio_unitario,
                   ti.subtotal, ti.nota, p.nombre, c.nombre as categoria
            FROM ticket_items ti
            JOIN productos p ON p.id = ti.producto_id
            JOIN categorias c ON c.id = p.categoria_id
            WHERE ti.id = ?
        ''', (item_id,), fetch='one')
        
        # Fetch updated ticket totals (triggers will have calculated them)
        updated_ticket = query('SELECT * FROM tickets WHERE id = ?', (ticket_id,), fetch='one')
        
        return jsonify({
            'item': dict(item),
            'ticket_totals': {
                'subtotal': updated_ticket['subtotal'],
                'impuesto': updated_ticket['impuesto'],
                'total': updated_ticket['total']
            }
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/tickets/<int:ticket_id>/items/<int:item_id>', methods=['PUT'])
def editar_item(ticket_id, item_id):
    """Edit ticket item."""
    try:
        data = request.get_json()
        
        # Check ticket exists and is open
        ticket = query('SELECT * FROM tickets WHERE id = ?', (ticket_id,), fetch='one')
        if not ticket:
            return jsonify({'error': 'Ticket no encontrado'}), 404
        
        if ticket['estado'] != 'abierto':
            return jsonify({'error': 'No se pueden editar items de tickets pagados o cancelados'}), 400
        
        # Check item exists
        item = query('SELECT * FROM ticket_items WHERE id = ? AND ticket_id = ?', 
                     (item_id, ticket_id), fetch='one')
        if not item:
            return jsonify({'error': 'Item no encontrado'}), 404
        
        # Update fields
        if 'cantidad' in data:
            cantidad = data.get('cantidad', 1)
            if cantidad <= 0:
                return jsonify({'error': 'La cantidad debe ser mayor a 0'}), 400
            
            # Check stock availability
            prod = query('SELECT stock FROM productos WHERE id = ?', (item['producto_id'],), fetch='one')
            total_cantidad_needed = cantidad + query(
                '''SELECT COALESCE(SUM(cantidad),0) as total FROM ticket_items 
                   WHERE ticket_id = ? AND producto_id = ? AND id != ?''',
                (ticket_id, item['producto_id'], item_id),
                fetch='one'
            )['total']
            
            if prod['stock'] < total_cantidad_needed:
                return jsonify({'error': f'Stock insuficiente. Disponible: {prod["stock"]}'}), 400
            
            subtotal = item['precio_unitario'] * cantidad
            execute(
                'UPDATE ticket_items SET cantidad = ?, subtotal = ? WHERE id = ?',
                (cantidad, subtotal, item_id)
            )
        
        if 'nota' in data:
            nota = data.get('nota', '').strip()
            execute('UPDATE ticket_items SET nota = ? WHERE id = ?', (nota, item_id))
        
        # Fetch updated item
        updated_item = query('''
            SELECT ti.id, ti.producto_id, ti.cantidad, ti.precio_unitario,
                   ti.subtotal, ti.nota, p.nombre, c.nombre as categoria
            FROM ticket_items ti
            JOIN productos p ON p.id = ti.producto_id
            JOIN categorias c ON c.id = p.categoria_id
            WHERE ti.id = ?
        ''', (item_id,), fetch='one')
        
        # Fetch updated ticket totals
        updated_ticket = query('SELECT * FROM tickets WHERE id = ?', (ticket_id,), fetch='one')
        
        return jsonify({
            'item': dict(updated_item),
            'ticket_totals': {
                'subtotal': updated_ticket['subtotal'],
                'impuesto': updated_ticket['impuesto'],
                'total': updated_ticket['total']
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/tickets/<int:ticket_id>/items/<int:item_id>', methods=['DELETE'])
def eliminar_item(ticket_id, item_id):
    """Remove item from ticket."""
    try:
        # Check ticket exists and is open
        ticket = query('SELECT * FROM tickets WHERE id = ?', (ticket_id,), fetch='one')
        if not ticket:
            return jsonify({'error': 'Ticket no encontrado'}), 404
        
        if ticket['estado'] != 'abierto':
            return jsonify({'error': 'No se pueden eliminar items de tickets pagados o cancelados'}), 400
        
        # Check item exists
        item = query('SELECT * FROM ticket_items WHERE id = ? AND ticket_id = ?',
                     (item_id, ticket_id), fetch='one')
        if not item:
            return jsonify({'error': 'Item no encontrado'}), 404
        
        execute('DELETE FROM ticket_items WHERE id = ?', (item_id,))
        
        # Fetch updated ticket totals
        updated_ticket = query('SELECT * FROM tickets WHERE id = ?', (ticket_id,), fetch='one')
        
        return jsonify({
            'ticket_totals': {
                'subtotal': updated_ticket['subtotal'],
                'impuesto': updated_ticket['impuesto'],
                'total': updated_ticket['total']
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/tickets/<int:id>/cancelar', methods=['PATCH'])
def cancelar_ticket(id):
    """Cancel a ticket."""
    try:
        ticket = query('SELECT * FROM tickets WHERE id = ?', (id,), fetch='one')
        if not ticket:
            return jsonify({'error': 'Ticket no encontrado'}), 404
        
        if ticket['estado'] != 'abierto':
            return jsonify({'error': 'Solo se pueden cancelar tickets abiertos'}), 400
        
        execute('UPDATE tickets SET estado = ? WHERE id = ?', ('cancelado', id))
        
        updated = query('SELECT * FROM tickets WHERE id = ?', (id,), fetch='one')
        return jsonify(dict(updated))
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/tickets/<int:id>/pagar', methods=['POST'])
def pagar_ticket(id):
    """Pay a ticket."""
    try:
        data = request.get_json()
        metodo = data.get('metodo', '').strip()
        
        # Validation
        if metodo not in ['efectivo', 'qr', 'tarjeta']:
            return jsonify({'error': 'El método de pago debe ser: efectivo, qr o tarjeta'}), 400
        
        # Check ticket exists
        ticket = query('SELECT * FROM tickets WHERE id = ?', (id,), fetch='one')
        if not ticket:
            return jsonify({'error': 'Ticket no encontrado'}), 404
        
        if ticket['estado'] != 'abierto':
            return jsonify({'error': 'El ticket no está abierto'}), 400
        
        if not ticket['mesero']:
            return jsonify({'error': 'El ticket debe tener asignado un mesero'}), 400
        
        # Check ticket has items
        items = query('SELECT COUNT(*) as count FROM ticket_items WHERE ticket_id = ?', 
                      (id,), fetch='one')
        if items['count'] == 0:
            return jsonify({'error': 'El ticket no tiene items'}), 400
        
        # Check stock availability for all items
        all_items = query('''
            SELECT ti.producto_id, ti.cantidad, p.stock
            FROM ticket_items ti
            JOIN productos p ON p.id = ti.producto_id
            WHERE ti.ticket_id = ?
        ''', (id,))
        
        faltantes = []
        for item in all_items:
            if item['stock'] < item['cantidad']:
                prod = query('SELECT nombre FROM productos WHERE id = ?', 
                            (item['producto_id'],), fetch='one')
                faltantes.append({
                    'producto_id': item['producto_id'],
                    'nombre': prod['nombre'],
                    'stock': item['stock'],
                    'requerido': item['cantidad']
                })
        
        if faltantes:
            return jsonify({
                'error': 'Stock insuficiente para completar la venta',
                'productos_faltantes': faltantes
            }), 400
        
        # Create payment (trigger will update stock and mark as paid)
        pago_id = execute(
            '''INSERT INTO pagos (ticket_id, metodo, monto) 
               VALUES (?, ?, ?)''',
            (id, metodo, ticket['total'])
        )
        
        # Fetch updated ticket
        updated = query('SELECT * FROM tickets WHERE id = ?', (id,), fetch='one')
        
        return jsonify({
            'pago_id': pago_id,
            'ticket': dict(updated)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400
