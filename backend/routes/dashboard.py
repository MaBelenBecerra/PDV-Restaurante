from flask import Blueprint, request, jsonify
from database import query, execute

bp = Blueprint('dashboard', __name__)

@bp.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    """Get dashboard data."""
    try:
        # Ventas hoy
        ventas_hoy = query('SELECT * FROM v_ventas_hoy', fetch='one')
        ventas_data = {
            'total_tickets': ventas_hoy['total_tickets'] if ventas_hoy else 0,
            'total_vendido': round(ventas_hoy['total_vendido'], 2) if ventas_hoy else 0.0,
            'ticket_promedio': round(ventas_hoy['ticket_promedio'], 2) if ventas_hoy else 0.0
        }
        
        # Top 5 productos
        top_productos = query('''
            SELECT nombre, categoria, unidades_vendidas, 
                   ROUND(total_vendido, 2) as total_vendido
            FROM v_top_productos
            LIMIT 5
        ''')
        
        # Productos agotados
        agotados = query('''
            SELECT id, nombre, stock
            FROM productos
            WHERE agotado = 1 OR stock = 0
            ORDER BY nombre ASC
        ''')
        
        # Stock bajo (< 5)
        stock_bajo = query('''
            SELECT id, nombre, stock
            FROM productos
            WHERE stock > 0 AND stock < 5 AND agotado = 0
            ORDER BY stock ASC, nombre ASC
        ''')
        
        # Comandas por estado
        comandas_estado = query('SELECT * FROM v_comandas_estado')
        comandas_dict = {
            'pendiente': 0,
            'en_preparacion': 0,
            'listo': 0
        }
        for row in comandas_estado:
            if row['estado'] in comandas_dict:
                comandas_dict[row['estado']] = row['cantidad']
        
        return jsonify({
            'ventas_hoy': ventas_data,
            'top_productos': [dict(p) for p in top_productos],
            'productos_agotados': [dict(p) for p in agotados],
            'stock_bajo': [dict(p) for p in stock_bajo],
            'comandas_estado': comandas_dict
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/configuracion', methods=['GET'])
def get_configuracion():
    """Get system configuration."""
    try:
        config = query('SELECT tasa_impuesto FROM configuracion WHERE id = 1', fetch='one')
        return jsonify({'tasa_impuesto': config['tasa_impuesto'] if config else 0.13})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/configuracion', methods=['PUT'])
def update_configuracion():
    """Update system configuration."""
    try:
        data = request.get_json()
        
        tasa_impuesto = data.get('tasa_impuesto')
        
        if tasa_impuesto is None:
            return jsonify({'error': 'La tasa de impuesto es requerida'}), 400
        
        if tasa_impuesto < 0 or tasa_impuesto > 1:
            return jsonify({'error': 'La tasa de impuesto debe estar entre 0 y 1'}), 400
        
        execute(
            'UPDATE configuracion SET tasa_impuesto = ?, actualizado_en = datetime(\'now\') WHERE id = 1',
            (tasa_impuesto,)
        )
        
        config = query('SELECT tasa_impuesto FROM configuracion WHERE id = 1', fetch='one')
        return jsonify({'tasa_impuesto': config['tasa_impuesto']})
    except Exception as e:
        return jsonify({'error': str(e)}), 400
