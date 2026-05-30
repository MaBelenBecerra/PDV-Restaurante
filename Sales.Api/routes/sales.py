from flask import Blueprint, request, jsonify
import uuid
import datetime
from database import query, execute

bp = Blueprint('sales', __name__)

def get_company(company_cen):
    """Retrieve active company by CEN GUID, auto-creating it if missing for seamless interoperability."""
    company = query("SELECT * FROM empresas WHERE cen = %s AND activo = 1", (company_cen,), fetch='one')
    if not company:
        execute(
            "INSERT INTO empresas (cen, nombre, nit, activo) VALUES (%s, %s, %s, 1) ON CONFLICT (cen) DO NOTHING",
            (company_cen, f"Empresa {company_cen[:8]}", "20123456789")
        )
        company = query("SELECT * FROM empresas WHERE cen = %s AND activo = 1", (company_cen,), fetch='one')
    return company

def datetime_now_str():
    return datetime.datetime.now().isoformat()

def ensure_local_product(company_cen, product_cen):
    """Check if product exists locally in PostgreSQL. If not, fetch detail from Inventory.Api and insert a stub."""
    prod = query("SELECT id, precio, nombre, code FROM productos WHERE cen = %s", (product_cen,), fetch='one')
    if prod:
        return prod
        
    # Sync from Inventory API via HTTP
    from inventory_client import lookup_products
    details = lookup_products(company_cen, [product_cen])
    if not details:
        return None
        
    d = details[0]
    cat = query("SELECT id FROM categorias LIMIT 1", fetch='one')
    cat_id = cat['id'] if cat else 1
    
    uni = query("SELECT id FROM unidades LIMIT 1", fetch='one')
    uni_id = uni['id'] if uni else 1
    
    # Insert stub product to satisfy foreign key constraints
    prod_id = execute('''
        INSERT INTO productos (nombre, categoria_id, unidad_id, precio, stock, activo, agotado, cen, code, station_code)
        VALUES (%s, %s, %s, %s, 0, 1, 0, %s, %s, %s)
    ''', (d['name'], cat_id, uni_id, d['price'], d['cen'], d['code'], d.get('stationCode', 'COCINA')))
    
    return {'id': prod_id, 'precio': d['price'], 'nombre': d['name'], 'code': d['code']}

# ==========================================
# 1. TICKETS ENDPOINTS
# ==========================================

@bp.route('/api/sales/companies/<company_cen>/tickets', methods=['GET'])
def sales_get_tickets(company_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        estado = request.args.get('status', '').strip().upper()
        
        sql = 'SELECT * FROM tickets WHERE 1=1'
        params = []
        
        if estado:
            map_est = {'OPEN': 'abierto', 'PAID': 'pagado', 'CANCELLED': 'cancelado'}
            mapped = map_est.get(estado)
            if mapped:
                sql += ' AND estado = %s'
                params.append(mapped)
                
        sql += ' ORDER BY id DESC'
        tickets = query(sql, tuple(params) if params else None)
        
        res = []
        for t in tickets:
            item_count = query("SELECT SUM(cantidad) as qty FROM ticket_items WHERE ticket_id = %s", (t['id'],), fetch='one')['qty'] or 0
            map_status = {'abierto': 'OPEN', 'pagado': 'PAID', 'cancelado': 'CANCELLED'}
            res.append({
                'cen': t['cen'],
                'ticketNumber': t['code'] or f"TIC-{t['id']:05d}",
                'status': map_status.get(t['estado'], 'OPEN'),
                'itemCount': item_count,
                'createdAt': t['creado_en'].isoformat() if hasattr(t['creado_en'], 'isoformat') else str(t['creado_en']),
                'mesero': t['mesero'],
                'total': float(t['total'])
            })
        return jsonify(res)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/sales/companies/<company_cen>/tickets', methods=['POST'])
def sales_create_ticket(company_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        data = request.get_json() or {}
        mesero = data.get('mesero', 'Mesero Demo').strip()
        
        config = query("SELECT tasa_impuesto FROM configuracion WHERE id = 1", fetch='one')
        tasa_impuesto = config['tasa_impuesto'] if config else 0.13
        
        new_cen = str(uuid.uuid4())
        count = query("SELECT COUNT(*) as count FROM tickets", fetch='one')['count']
        new_code = f"TIC-{count+1:05d}"
        
        id = execute('''
            INSERT INTO tickets (mesero, estado, tasa_impuesto, cen, code)
            VALUES (%s, 'abierto', %s, %s, %s)
        ''', (mesero, tasa_impuesto, new_cen, new_code))
        
        return jsonify({
            'cen': new_cen,
            'ticketNumber': new_code,
            'status': 'OPEN',
            'itemCount': 0,
            'createdAt': datetime_now_str(),
            'mesero': mesero,
            'total': 0.0
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/sales/companies/<company_cen>/tickets/<ticket_cen>', methods=['GET'])
def sales_get_ticket_detail(company_cen, ticket_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        t = query("SELECT * FROM tickets WHERE cen = %s", (ticket_cen,), fetch='one')
        if not t: return jsonify({'error': 'Ticket not found'}), 404
        
        item_count = query("SELECT SUM(cantidad) as qty FROM ticket_items WHERE ticket_id = %s", (t['id'],), fetch='one')['qty'] or 0
        map_status = {'abierto': 'OPEN', 'pagado': 'PAID', 'cancelado': 'CANCELLED'}
        
        return jsonify({
            'cen': t['cen'],
            'ticketNumber': t['code'] or f"TIC-{t['id']:05d}",
            'status': map_status.get(t['estado'], 'OPEN'),
            'itemCount': item_count,
            'createdAt': t['creado_en'].isoformat() if hasattr(t['creado_en'], 'isoformat') else str(t['creado_en']),
            'mesero': t['mesero'],
            'total': float(t['total'])
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/sales/companies/<company_cen>/tickets/<ticket_cen>/items', methods=['GET'])
def sales_get_ticket_items(company_cen, ticket_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        t = query("SELECT id FROM tickets WHERE cen = %s", (ticket_cen,), fetch='one')
        if not t: return jsonify({'error': 'Ticket not found'}), 404
        
        items = query('''
            SELECT ti.*, p.cen as product_cen, p.code as product_code, p.nombre as product_name
            FROM ticket_items ti
            JOIN productos p ON p.id = ti.producto_id
            WHERE ti.ticket_id = %s
            ORDER BY ti.id ASC
        ''', (t['id'],))
        
        return jsonify([{
            'cen': item['cen'] or str(uuid.uuid4()),
            'productCen': item['product_cen'],
            'productCode': item['product_code'],
            'productName': item['product_name'],
            'quantity': item['cantidad'],
            'unitPrice': float(item['precio_unitario']),
            'notes': item['nota'] or ''
        } for item in items])
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/sales/companies/<company_cen>/tickets/<ticket_cen>/totals', methods=['GET'])
def sales_get_ticket_totals(company_cen, ticket_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        t = query("SELECT subtotal, impuesto, total, tasa_impuesto FROM tickets WHERE cen = %s", (ticket_cen,), fetch='one')
        if not t: return jsonify({'error': 'Ticket not found'}), 404
        
        return jsonify({
            'subtotal': float(t['subtotal']),
            'tax': float(t['impuesto']),
            'total': float(t['total']),
            'taxRate': float(t['tasa_impuesto'])
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/sales/companies/<company_cen>/tickets/<ticket_cen>/items', methods=['POST'])
def sales_add_ticket_item(company_cen, ticket_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        t = query("SELECT id, estado FROM tickets WHERE cen = %s", (ticket_cen,), fetch='one')
        if not t: return jsonify({'error': 'Ticket not found'}), 404
        
        if t['estado'] != 'abierto':
            return jsonify({'error': 'Cannot add items to a closed ticket'}), 400
            
        data = request.get_json() or {}
        product_cen = data.get('productCen')
        qty = data.get('quantity', 1)
        notes = data.get('notes', '').strip()
        
        if not product_cen: return jsonify({'error': 'Product CEN is required'}), 400
        
        # Ensure product is synchronized locally
        prod = ensure_local_product(company_cen, product_cen)
        if not prod: return jsonify({'error': 'Product not found in inventory'}), 404
        
        # HTTP stock validation
        from inventory_client import validate_stock
        has_stock = validate_stock(company_cen, product_cen, qty)
        if not has_stock:
            return jsonify({'error': 'Stock insuficiente en inventario'}), 400
            
        subtotal = float(prod['precio']) * qty
        new_cen = str(uuid.uuid4())
        
        execute('''
            INSERT INTO ticket_items (ticket_id, producto_id, cantidad, precio_unitario, subtotal, nota, cen)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (t['id'], prod['id'], qty, prod['precio'], subtotal, notes, new_cen))
        
        updated_t = query("SELECT subtotal, impuesto, total FROM tickets WHERE id = %s", (t['id'],), fetch='one')
        
        return jsonify({
            'cen': new_cen,
            'productCen': product_cen,
            'quantity': qty,
            'unitPrice': float(prod['precio']),
            'notes': notes,
            'ticket_totals': {
                'subtotal': float(updated_t['subtotal']),
                'impuesto': float(updated_t['impuesto']),
                'total': float(updated_t['total'])
            }
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/sales/companies/<company_cen>/tickets/<ticket_cen>/items/<item_cen>', methods=['PATCH'])
def sales_update_ticket_item(company_cen, ticket_cen, item_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        t = query("SELECT id, estado FROM tickets WHERE cen = %s", (ticket_cen,), fetch='one')
        if not t: return jsonify({'error': 'Ticket not found'}), 404
        
        if t['estado'] != 'abierto':
            return jsonify({'error': 'Cannot edit items on a closed ticket'}), 400
            
        item = query("SELECT * FROM ticket_items WHERE cen = %s AND ticket_id = %s", (item_cen, t['id']), fetch='one')
        if not item: return jsonify({'error': 'Ticket item not found'}), 404
        
        data = request.get_json() or {}
        qty = data.get('quantity')
        notes = data.get('notes')
        
        updates = []
        params = []
        
        if qty is not None:
            if qty <= 0: return jsonify({'error': 'Quantity must be greater than 0'}), 400
            
            # Resolve product cen
            prod = query("SELECT cen, precio FROM productos WHERE id = %s", (item['producto_id'],), fetch='one')
            
            # HTTP stock validation
            from inventory_client import validate_stock
            has_stock = validate_stock(company_cen, prod['cen'], qty)
            if not has_stock:
                return jsonify({'error': f'Stock insuficiente en inventario'}), 400
                
            subtotal = float(prod['precio']) * qty
            updates.append("cantidad = %s")
            updates.append("subtotal = %s")
            params.extend([qty, subtotal])
            
        if notes is not None:
            updates.append("nota = %s")
            params.append(notes.strip())
            
        if updates:
            params.append(item_cen)
            execute(f"UPDATE ticket_items SET {', '.join(updates)} WHERE cen = %s", tuple(params))
            
        updated_t = query("SELECT subtotal, impuesto, total FROM tickets WHERE id = %s", (t['id'],), fetch='one')
        
        return jsonify({
            'cen': item_cen,
            'ticket_totals': {
                'subtotal': float(updated_t['subtotal']),
                'impuesto': float(updated_t['impuesto']),
                'total': float(updated_t['total'])
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/sales/companies/<company_cen>/tickets/<ticket_cen>/items/<item_cen>', methods=['DELETE'])
def sales_delete_ticket_item(company_cen, ticket_cen, item_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        t = query("SELECT id, estado FROM tickets WHERE cen = %s", (ticket_cen,), fetch='one')
        if not t: return jsonify({'error': 'Ticket not found'}), 404
        
        if t['estado'] != 'abierto':
            return jsonify({'error': 'Cannot delete items from a closed ticket'}), 400
            
        item = query("SELECT id FROM ticket_items WHERE cen = %s AND ticket_id = %s", (item_cen, t['id']), fetch='one')
        if not item: return jsonify({'error': 'Ticket item not found'}), 404
        
        execute("DELETE FROM ticket_items WHERE cen = %s", (item_cen,))
        
        updated_t = query("SELECT subtotal, impuesto, total FROM tickets WHERE id = %s", (t['id'],), fetch='one')
        
        return jsonify({
            'ticket_totals': {
                'subtotal': float(updated_t['subtotal']),
                'impuesto': float(updated_t['impuesto']),
                'total': float(updated_t['total'])
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/sales/companies/<company_cen>/tickets/<ticket_cen>/cancel', methods=['POST'])
def sales_cancel_ticket(company_cen, ticket_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        t = query("SELECT id, estado FROM tickets WHERE cen = %s", (ticket_cen,), fetch='one')
        if not t: return jsonify({'error': 'Ticket not found'}), 404
        
        if t['estado'] != 'abierto':
            return jsonify({'error': 'Only open tickets can be cancelled'}), 400
            
        execute("UPDATE tickets SET estado = 'cancelado' WHERE cen = %s", (ticket_cen,))
        return jsonify({'status': 'CANCELLED'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/sales/companies/<company_cen>/tickets/<ticket_cen>/payment', methods=['POST'])
def sales_pay_ticket(company_cen, ticket_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        t = query("SELECT id, estado, total FROM tickets WHERE cen = %s", (ticket_cen,), fetch='one')
        if not t: return jsonify({'error': 'Ticket not found'}), 404
        
        if t['estado'] != 'abierto':
            return jsonify({'error': 'Ticket is not open'}), 400
            
        items = query('''
            SELECT ti.producto_id, ti.cantidad, p.cen as product_cen, p.nombre
            FROM ticket_items ti
            JOIN productos p ON p.id = ti.producto_id
            WHERE ti.ticket_id = %s
        ''', (t['id'],))
        
        if not items:
            return jsonify({'error': 'Ticket has no items'}), 400
            
        data = request.get_json() or {}
        payment_method = data.get('paymentMethod', 'CASH').upper()
        amount = data.get('amount', t['total'])
        
        map_met = {'CASH': 'efectivo', 'QR': 'qr', 'CARD': 'tarjeta', 'CREDIT_CARD': 'tarjeta'}
        mapped_met = map_met.get(payment_method, 'efectivo')
        
        # HTTP Stock Consumption
        from inventory_client import consume_stock
        for item in items:
            success = consume_stock(company_cen, item['product_cen'], item['cantidad'])
            if not success:
                return jsonify({'error': f"Stock insuficiente en inventario para {item['nombre']}"}), 400
                
        new_pago_cen = str(uuid.uuid4())
        execute('''
            INSERT INTO pagos (ticket_id, metodo, monto, cen)
            VALUES (%s, %s, %s, %s)
        ''', (t['id'], mapped_met, amount, new_pago_cen))
        
        # Set ticket status to PAID explicitly
        execute("UPDATE tickets SET estado = 'pagado', pagado_en = CURRENT_TIMESTAMP WHERE id = %s", (t['id'],))
        
        return jsonify({
            'paymentCen': new_pago_cen,
            'status': 'PAID',
            'amount': float(amount)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ==========================================
# 2. COMANDAS & KDS ENDPOINTS
# ==========================================

@bp.route('/api/sales/companies/<company_cen>/tickets/<ticket_cen>/send', methods=['POST'])
def sales_send_command(company_cen, ticket_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        t = query("SELECT id FROM tickets WHERE cen = %s", (ticket_cen,), fetch='one')
        if not t: return jsonify({'error': 'Ticket not found'}), 404
        
        items_sin_enviar = query('''
            SELECT ti.id, ti.producto_id, ti.cantidad, p.station_code, p.nombre, ti.nota, ti.cen
            FROM ticket_items ti
            JOIN productos p ON p.id = ti.producto_id
            WHERE ti.ticket_id = %s AND ti.id NOT IN (
                SELECT DISTINCT ticket_item_id FROM comanda_items
            )
        ''', (t['id'],))
        
        if not items_sin_enviar:
            return jsonify({'message': 'No new items to send to KDS'}), 200
            
        estaciones_items = {}
        for item in items_sin_enviar:
            st_code = item['station_code'] or 'COCINA'
            est = query("SELECT id FROM estaciones WHERE UPPER(tipo) = %s OR UPPER(nombre) = %s", (st_code, st_code), fetch='one')
            est_id = est['id'] if est else 1
            
            if est_id not in estaciones_items:
                estaciones_items[est_id] = []
            estaciones_items[est_id].append(item)
            
        comandas_creadas = []
        for est_id, items in estaciones_items.items():
            new_comanda_cen = str(uuid.uuid4())
            comanda_id = execute('''
                INSERT INTO comandas (ticket_id, estacion_id, es_reenvio, cen)
                VALUES (%s, %s, 0, %s)
            ''', (t['id'], est_id, new_comanda_cen))
            
            for item in items:
                new_item_cen = str(uuid.uuid4())
                execute('''
                    INSERT INTO comanda_items (comanda_id, ticket_item_id, estado, cen)
                    VALUES (%s, %s, 'pendiente', %s)
                ''', (comanda_id, item['id'], new_item_cen))
                
            comandas_creadas.append({
                'comandaCen': new_comanda_cen,
                'stationId': est_id,
                'itemsCount': len(items)
            })
            
        return jsonify({
            'ticketCen': ticket_cen,
            'commands': comandas_creadas
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/sales/companies/<company_cen>/kds/teams', methods=['GET'])
def sales_get_kds_teams(company_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        estaciones = query("SELECT * FROM estaciones")
        return jsonify([{
            'cen': est['cen'],
            'name': est['nombre'],
            'stationType': 'KITCHEN' if est['tipo'].lower() == 'cocina' else 'BAR'
        } for est in estaciones])
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/sales/companies/<company_cen>/kds/teams/<station_cen>/items', methods=['GET'])
def sales_get_kds_items(company_cen, station_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        if station_cen.isdigit():
            est = query("SELECT id FROM estaciones WHERE cen = %s OR tipo = %s OR id = %s", (station_cen, station_cen.lower(), int(station_cen)), fetch='one')
        else:
            est = query("SELECT id FROM estaciones WHERE cen = %s OR tipo = %s", (station_cen, station_cen.lower()), fetch='one')
        if not est: return jsonify({'error': 'Station not found'}), 404
        
        items = query('''
            SELECT ci.id, ci.cen as item_cen, ci.estado, co.cen as comanda_cen, t.cen as ticket_cen, t.mesero, co.creado_en,
                   p.cen as product_cen, p.nombre as product_name, ti.cantidad, ti.nota
            FROM comanda_items ci
            JOIN comandas co ON co.id = ci.comanda_id
            JOIN tickets t ON t.id = co.ticket_id AND t.estado = 'abierto'
            JOIN ticket_items ti ON ti.id = ci.ticket_item_id
            JOIN productos p ON p.id = ti.producto_id
            WHERE co.estacion_id = %s
            ORDER BY co.creado_en ASC, ci.id ASC
        ''', (est['id'],))
        
        res = []
        map_status = {'pendiente': 'PENDING', 'en_preparacion': 'IN_PROGRESS', 'listo': 'READY'}
        for item in items:
            res.append({
                'cen': item['item_cen'],
                'ticketCen': item['ticket_cen'],
                'productCen': item['product_cen'],
                'productName': item['product_name'],
                'quantity': item['cantidad'],
                'notes': item['nota'] or '',
                'status': map_status.get(item['estado'], 'PENDING'),
                'createdAt': item['creado_en'].isoformat() if hasattr(item['creado_en'], 'isoformat') else str(item['creado_en']),
                'mesero': item['mesero']
            })
        return jsonify(res)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/sales/companies/<company_cen>/kds/items/<item_cen>/status', methods=['PATCH'])
def sales_update_kds_item_status(company_cen, item_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        item = query("SELECT id, estado FROM comanda_items WHERE cen = %s", (item_cen,), fetch='one')
        if not item: return jsonify({'error': 'KDS item not found'}), 404
        
        data = request.get_json() or {}
        status = data.get('status', '').upper()
        
        map_status = {'PENDING': 'pendiente', 'IN_PROGRESS': 'en_preparacion', 'PREPARING': 'en_preparacion', 'READY': 'listo'}
        mapped = map_status.get(status, 'listo')
        
        execute("UPDATE comanda_items SET estado = %s, actualizado_en = CURRENT_TIMESTAMP WHERE cen = %s", (mapped, item_cen))
        return jsonify({'status': status})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ==========================================
# 3. CONFIGURATION & DASHBOARD ENDPOINTS
# ==========================================

@bp.route('/api/sales/companies/<company_cen>/tax-configuration', methods=['GET'])
def sales_get_tax_config(company_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        config = query("SELECT tasa_impuesto FROM configuracion WHERE id = 1", fetch='one')
        return jsonify({'taxRate': float(config['tasa_impuesto']) if config else 0.13})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/sales/companies/<company_cen>/tax-configuration', methods=['PUT'])
def sales_update_tax_config(company_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        data = request.get_json() or {}
        tax_rate = data.get('taxRate')
        
        if tax_rate is None:
            return jsonify({'error': 'taxRate is required'}), 400
            
        execute("UPDATE configuracion SET tasa_impuesto = %s WHERE id = 1", (tax_rate,))
        return jsonify({'taxRate': float(tax_rate)})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/sales/companies/<company_cen>/dashboard/daily-sales', methods=['GET'])
def sales_dashboard_daily(company_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        ventas_hoy = query('SELECT * FROM v_ventas_hoy', fetch='one')
        total = ventas_hoy['total_vendido'] if (ventas_hoy and ventas_hoy['total_vendido'] is not None) else 0.0
        return jsonify({'total': round(float(total), 2)})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/sales/companies/<company_cen>/dashboard/top-products', methods=['GET'])
def sales_dashboard_top_products(company_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        top = query('''
            SELECT p.cen as product_cen, SUM(ti.cantidad) as quantity
            FROM ticket_items ti
            JOIN tickets t ON t.id = ti.ticket_id AND t.estado = 'pagado'
            JOIN productos p ON p.id = ti.producto_id
            GROUP BY p.id, p.cen
            ORDER BY quantity DESC
            LIMIT 10
        ''')
        return jsonify([{
            'productCen': row['product_cen'],
            'quantity': row['quantity']
        } for row in top])
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/api/sales/companies/<company_cen>/dashboard/kds-status', methods=['GET'])
def sales_dashboard_kds_status(company_cen):
    try:
        c = get_company(company_cen)
        if not c: return jsonify({'error': 'Company not found'}), 404
        
        comandas_estado = query('SELECT * FROM v_comandas_estado')
        map_status = {'pendiente': 'PENDING', 'en_preparacion': 'IN_PROGRESS', 'listo': 'READY'}
        
        return jsonify([{
            'status': map_status.get(row['estado'], row['estado'].upper()),
            'count': row['cantidad']
        } for row in comandas_estado])
    except Exception as e:
        return jsonify({'error': str(e)}), 400
