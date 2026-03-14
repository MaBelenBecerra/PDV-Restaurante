from flask import Blueprint, request, jsonify
from database import query, execute

bp = Blueprint('comandas', __name__)

def get_estacion_for_categoria(categoria_id):
    """Determine which station (cocina or bar) a product belongs to."""
    categoria = query('SELECT nombre FROM categorias WHERE id = ?', (categoria_id,), fetch='one')
    if not categoria:
        return 1  # Default to cocina
    
    categoria_nombre = categoria['nombre'].lower()
    bar_categories = ['bebidas', 'cócteles']
    
    if any(c in categoria_nombre for c in bar_categories):
        return 2  # Bar
    else:
        return 1  # Cocina

@bp.route('/api/tickets/<int:ticket_id>/comanda', methods=['POST'])
def enviar_comanda(ticket_id):
    """Generate and send kitchen commands for new items."""
    try:
        data = request.get_json()
        es_reenvio = data.get('es_reenvio', 0)
        
        # Check ticket exists
        ticket = query('SELECT * FROM tickets WHERE id = ?', (ticket_id,), fetch='one')
        if not ticket:
            return jsonify({'error': 'Ticket no encontrado'}), 404
        
        # Get items that haven't been sent to comanda yet
        items_sin_enviar = query('''
            SELECT ti.id, ti.producto_id, ti.cantidad, p.categoria_id, 
                   p.nombre, ti.nota
            FROM ticket_items ti
            JOIN productos p ON p.id = ti.producto_id
            WHERE ti.ticket_id = ? AND ti.id NOT IN (
                SELECT DISTINCT ticket_item_id FROM comanda_items
            )
            ORDER BY p.categoria_id
        ''', (ticket_id,))
        
        if not items_sin_enviar:
            return jsonify({'error': 'No hay items nuevos para enviar a comanda'}), 400
        
        # Group items by station
        estaciones_items = {}
        for item in items_sin_enviar:
            estacion_id = get_estacion_for_categoria(item['categoria_id'])
            if estacion_id not in estaciones_items:
                estaciones_items[estacion_id] = []
            estaciones_items[estacion_id].append(item)
        
        # Create comandas for each station
        comandas_creadas = []
        for estacion_id, items in estaciones_items.items():
            comanda_id = execute(
                '''INSERT INTO comandas (ticket_id, estacion_id, es_reenvio) 
                   VALUES (?, ?, ?)''',
                (ticket_id, estacion_id, es_reenvio)
            )
            
            # Create comanda_items for each item in this comanda
            for item in items:
                execute(
                    '''INSERT INTO comanda_items (comanda_id, ticket_item_id, estado) 
                       VALUES (?, ?, ?)''',
                    (comanda_id, item['id'], 'pendiente')
                )
            
            comandas_creadas.append({
                'comanda_id': comanda_id,
                'estacion_id': estacion_id,
                'items_count': len(items)
            })
        
        return jsonify({
            'ticket_id': ticket_id,
            'comandas': comandas_creadas
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/kds/<int:estacion_id>', methods=['GET'])
def get_kds(estacion_id):
    """Get pending and in-preparation items for a station."""
    try:
        # Check if station exists
        estacion = query('SELECT * FROM estaciones WHERE id = ?', (estacion_id,), fetch='one')
        if not estacion:
            return jsonify({'error': 'Estación no encontrada'}), 404
        
        # Get all open tickets with their comandas for this station
        comandas = query('''
            SELECT c.id as comanda_id, c.ticket_id, t.mesero, c.creado_en,
                   COUNT(*) as total_items
            FROM comandas c
            JOIN tickets t ON t.id = c.ticket_id AND t.estado = 'abierto'
            LEFT JOIN comanda_items ci ON ci.comanda_id = c.id
            WHERE c.estacion_id = ?
            GROUP BY c.id
            ORDER BY c.creado_en ASC
        ''', (estacion_id,))
        
        result = []
        for comanda in comandas:
            # Get items for this comanda
            items = query('''
                SELECT ci.id, ci.comanda_id, ci.ticket_item_id, ci.estado,
                       p.nombre, ti.cantidad, ti.nota
                FROM comanda_items ci
                JOIN ticket_items ti ON ti.id = ci.ticket_item_id
                JOIN productos p ON p.id = ti.producto_id
                WHERE ci.comanda_id = ?
                ORDER BY ci.estado DESC, ci.id ASC
            ''', (comanda['comanda_id'],))
            
            result.append({
                'comanda_id': comanda['comanda_id'],
                'ticket_id': comanda['ticket_id'],
                'mesero': comanda['mesero'],
                'hora': comanda['creado_en'],
                'items': [dict(item) for item in items]
            })
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/kds/item/<int:comanda_item_id>/estado', methods=['PATCH'])
def cambiar_estado_item(comanda_item_id):
    """Change the state of a kitchen command item."""
    try:
        data = request.get_json()
        nuevo_estado = data.get('estado', '').strip()
        
        # Validation
        if nuevo_estado not in ['pendiente', 'en_preparacion', 'listo']:
            return jsonify({'error': 'El estado debe ser: pendiente, en_preparacion o listo'}), 400
        
        # Check item exists
        item = query('SELECT * FROM comanda_items WHERE id = ?', (comanda_item_id,), fetch='one')
        if not item:
            return jsonify({'error': 'Item de comanda no encontrado'}), 404
        
        # Update state
        execute('UPDATE comanda_items SET estado = ?, actualizado_en = datetime(\'now\') WHERE id = ?',
                (nuevo_estado, comanda_item_id))
        
        # Fetch updated item
        updated = query('''
            SELECT ci.id, ci.comanda_id, ci.ticket_item_id, ci.estado,
                   p.nombre, ti.cantidad, ti.nota
            FROM comanda_items ci
            JOIN ticket_items ti ON ti.id = ci.ticket_item_id
            JOIN productos p ON p.id = ti.producto_id
            WHERE ci.id = ?
        ''', (comanda_item_id,), fetch='one')
        
        return jsonify(dict(updated))
    except Exception as e:
        return jsonify({'error': str(e)}), 400
