from flask import Blueprint, request, jsonify
import uuid
import datetime
from database import query, execute
from inventory_client import DownstreamServiceError

bp = Blueprint('sales', __name__)

def get_company(company_cen):
    company = query("SELECT * FROM empresas WHERE cen = %s AND activo = 1", (company_cen,), fetch='one')
    if not company:
        execute("INSERT INTO empresas (cen, nombre, nit, activo) VALUES (%s, %s, %s, 1) ON CONFLICT (cen) DO NOTHING", (company_cen, f"Empresa {company_cen[:8]}", "20123456789"))
        company = query("SELECT * FROM empresas WHERE cen = %s AND activo = 1", (company_cen,), fetch='one')
    return company

def ensure_local_product(company_cen, product_cen):
    prod = query("SELECT id, precio, nombre, code FROM productos WHERE cen = %s", (product_cen,), fetch='one')
    if prod: return prod
    from inventory_client import lookup_products
    details = lookup_products(company_cen, [product_cen])
    if not details: return None
    d = details[0]
    cat = query("SELECT id FROM categorias LIMIT 1", fetch='one')
    uni = query("SELECT id FROM unidades LIMIT 1", fetch='one')
    prod_id = execute("INSERT INTO productos (nombre, categoria_id, unidad_id, precio, stock, activo, agotado, cen, code, station_code) VALUES (%s, %s, %s, %s, 0, 1, 0, %s, %s, %s)", (d['name'], cat['id'] if cat else 1, uni['id'] if uni else 1, d['salePrice'], d['productCen'], d['sku'], d.get('stationCode', 'COCINA')))
    return {'id': prod_id, 'precio': d['salePrice'], 'nombre': d['name'], 'code': d['sku']}

@bp.route('/api/sales/companies/<company_cen>/tickets', methods=['GET'])
def sales_get_tickets(company_cen):
    status = request.args.get('status')
    sql = "SELECT cen as ticketCen, id as dailyNumber, CASE WHEN estado='abierto' THEN 'OPEN' WHEN estado='pagado' THEN 'PAID' ELSE 'CANCELLED' END as status, creado_en as createdAt, mesero as waiterName, vendor_cen as waiterCen, %s as companyCen, impuesto as taxAmount, total FROM tickets"
    params = [company_cen]
    if status:
        status_map = {'OPEN': 'abierto', 'PAID': 'pagado', 'CANCELLED': 'cancelado'}
        sql += " WHERE estado = %s"
        params.append(status_map.get(status, status.lower()))
    tickets = query(sql, tuple(params))
    return jsonify(tickets)

@bp.route('/api/sales/companies/<company_cen>/tickets', methods=['POST'])
def sales_create_ticket(company_cen):
    data = request.get_json() or {}
    new_cen = str(uuid.uuid4())
    count = query("SELECT COUNT(*) as count FROM tickets", fetch='one')['count']
    waiter = data.get('mesero') or data.get('waiterName') or data.get('waiterCen') or 'Mesero'
    execute("INSERT INTO tickets (mesero, vendor_cen, estado, tasa_impuesto, cen, code) VALUES (%s, %s, 'abierto', 0.13, %s, %s)", (waiter, data.get('waiterCen'), new_cen, f"TIC-{count+1:05d}"))
    return jsonify({'ticketCen': new_cen, 'dailyNumber': count+1, 'status': 'OPEN', 'createdAt': datetime.datetime.now().isoformat(), 'waiterName': waiter, 'waiterCen': data.get('waiterCen'), 'companyCen': company_cen, 'taxAmount': 0.0, 'total': 0.0}), 201

@bp.route('/api/sales/companies/<company_cen>/tickets/<ticket_cen>/items', methods=['GET'])
def sales_get_ticket_items(company_cen, ticket_cen):
    items = query("SELECT ti.cen as ticketItemCen, p.cen as productCen, p.nombre as productName, ti.cantidad as quantity, ti.precio_unitario as unitPrice, ti.nota as note, 'OPEN' as status FROM ticket_items ti JOIN productos p ON p.id = ti.producto_id JOIN tickets t ON t.id = ti.ticket_id WHERE t.cen = %s", (ticket_cen,))
    return jsonify(items)

@bp.route('/api/sales/companies/<company_cen>/tickets/<ticket_cen>/items', methods=['POST'])
def sales_add_ticket_item(company_cen, ticket_cen):
    data = request.get_json() or {}
    t = query("SELECT id FROM tickets WHERE cen = %s", (ticket_cen,), fetch='one')
    prod = ensure_local_product(company_cen, data.get('productCen'))
    item_cen = str(uuid.uuid4())
    execute("INSERT INTO ticket_items (ticket_id, producto_id, cantidad, precio_unitario, subtotal, nota, cen) VALUES (%s, %s, %s, %s, %s, %s, %s)", (t['id'], prod['id'], data.get('quantity', 1), prod['precio'], float(prod['precio'])*data.get('quantity', 1), data.get('note', ''), item_cen))
    return jsonify({'ticketItemCen': item_cen, 'productCen': data.get('productCen'), 'productName': prod['nombre'], 'quantity': data.get('quantity', 1), 'unitPrice': float(prod['precio']), 'note': data.get('note', ''), 'status': 'OPEN'}), 201

@bp.route('/api/sales/companies/<company_cen>/tickets/<ticket_cen>/items/<item_cen>', methods=['PATCH'])
def sales_patch_item(company_cen, ticket_cen, item_cen):
    data = request.get_json() or {}
    current = query("SELECT cantidad, nota FROM ticket_items WHERE cen = %s", (item_cen,), fetch='one')
    quantity = data.get('quantity', current['cantidad'])
    note = data.get('note', current['nota'])
    execute("UPDATE ticket_items SET cantidad = %s, nota = %s, subtotal = precio_unitario * %s WHERE cen = %s", (quantity, note, quantity, item_cen))
    return jsonify({'ticketItemCen': item_cen}), 200

@bp.route('/api/sales/companies/<company_cen>/tickets/<ticket_cen>/items/<item_cen>', methods=['DELETE'])
def sales_delete_item(company_cen, ticket_cen, item_cen):
    execute("DELETE FROM ticket_items WHERE cen = %s", (item_cen,))
    t = query("SELECT cen as ticketCen, subtotal, impuesto as taxAmount, total FROM tickets WHERE cen = %s", (ticket_cen,), fetch='one')
    return jsonify({'ticketItemCen': item_cen, 'ticket_totals': {'subtotal': float(t['subtotal']), 'impuesto': float(t['taxAmount']), 'total': float(t['total'])}}), 200

@bp.route('/api/sales/companies/<company_cen>/tickets/<ticket_cen>/payment', methods=['POST'])
def sales_pay_ticket(company_cen, ticket_cen):
    t = query("SELECT id, total, impuesto, subtotal FROM tickets WHERE cen = %s", (ticket_cen,), fetch='one')
    items = query("SELECT p.cen as productCen, ti.cantidad FROM ticket_items ti JOIN productos p ON p.id = ti.producto_id WHERE ti.ticket_id = %s", (t['id'],))
    from inventory_client import consume_stock
    consume_stock(company_cen, [{'productCen': i['productCen'], 'quantity': i['cantidad']} for i in items])
    pay_cen = str(uuid.uuid4())
    execute("INSERT INTO pagos (ticket_id, metodo, monto, cen) VALUES (%s, 'cash', %s, %s)", (t['id'], t['total'], pay_cen))
    execute("UPDATE tickets SET estado = 'pagado', pagado_en = CURRENT_TIMESTAMP WHERE id = %s", (t['id'],))
    return jsonify({'saleCen': pay_cen, 'ticketCen': ticket_cen, 'status': 'PAID', 'subtotal': float(t['subtotal']), 'taxAmount': float(t['impuesto']), 'total': float(t['total'])}), 200

@bp.route('/api/sales/companies/<company_cen>/dashboard/daily-sales', methods=['GET'])
def sales_daily_dashboard(company_cen):
    res = query("SELECT COALESCE(SUM(total), 0) as totalSales, COUNT(*) as ticketsCount, COALESCE(AVG(total), 0) as averageTicket FROM tickets WHERE estado = 'pagado' AND pagado_en::date = CURRENT_DATE", fetch='one')
    return jsonify({'totalSales': float(res['totalSales']), 'ticketsCount': int(res['ticketsCount']), 'averageTicket': float(res['averageTicket'])})

@bp.route('/api/sales/companies/<company_cen>/dashboard/top-products', methods=['GET'])
def sales_top_products_dashboard(company_cen):
    rows = query(
        """
        SELECT
            p.cen as productCen,
            p.nombre as productName,
            COALESCE(SUM(ti.cantidad), 0) as quantity
        FROM tickets t
        JOIN ticket_items ti ON ti.ticket_id = t.id
        JOIN productos p ON p.id = ti.producto_id
        WHERE t.estado = 'pagado'
        GROUP BY p.cen, p.nombre
        ORDER BY quantity DESC, p.nombre ASC
        LIMIT 10
        """,
        fetch='all'
    )
    return jsonify(rows)

@bp.route('/api/sales/companies/<company_cen>/dashboard/kds-status', methods=['GET'])
def sales_kds_status_dashboard(company_cen):
    rows = query(
        """
        SELECT
            CASE ci.estado
                WHEN 'pendiente' THEN 'PENDING'
                WHEN 'en_preparacion' THEN 'IN_PROGRESS'
                WHEN 'listo' THEN 'READY'
                ELSE UPPER(ci.estado)
            END as status,
            COUNT(*) as count
        FROM comanda_items ci
        GROUP BY ci.estado
        ORDER BY status
        """,
        fetch='all'
    )
    return jsonify(rows)

@bp.route('/api/sales/companies/<company_cen>/dashboard/monthly', methods=['GET'])
def sales_monthly_dashboard(company_cen):
    curr = query("SELECT SUM(total) as total FROM tickets WHERE estado = 'pagado' AND date_trunc('month', pagado_en) = date_trunc('month', CURRENT_DATE)", fetch='one')
    prev = query("SELECT SUM(total) as total FROM tickets WHERE estado = 'pagado' AND date_trunc('month', pagado_en) = date_trunc('month', CURRENT_DATE - interval '1 month')", fetch='one')
    return jsonify({'currentMonthTotal': float(curr['total'] or 0), 'previousMonthTotal': float(prev['total'] or 0), 'growthPercentage': 0.0})

@bp.route('/api/sales/companies/<company_cen>/kds/teams', methods=['GET'])
def sales_kds_teams(company_cen):
    teams = query("SELECT cen as teamCen, nombre as name FROM estaciones")
    return jsonify(teams)

@bp.route('/api/sales/companies/<company_cen>/kds/teams', methods=['POST'])
def sales_create_kds_team(company_cen):
    data = request.get_json() or {}
    new_cen = str(uuid.uuid4())
    execute("INSERT INTO estaciones (cen, nombre, tipo, code) VALUES (%s, %s, 'cocina', %s)", (new_cen, data.get('name'), new_cen[:8]))
    return jsonify({'teamCen': new_cen, 'name': data.get('name')}), 201

@bp.route('/api/sales/companies/<company_cen>/kds/teams/<team_cen>/items', methods=['GET'])
def sales_kds_items(company_cen, team_cen):
    items = query("SELECT ci.cen as ticketItemCen, t.cen as ticketCen, p.cen as productCen, p.nombre as productName, ti.cantidad as quantity, ci.estado as status, ti.nota as note FROM comanda_items ci JOIN comandas co ON co.id = ci.comanda_id JOIN ticket_items ti ON ti.id = ci.ticket_item_id JOIN tickets t ON t.id = co.ticket_id JOIN productos p ON p.id = ti.producto_id WHERE co.estacion_id = (SELECT id FROM estaciones WHERE cen = %s)", (team_cen,))
    return jsonify(items)

@bp.route('/api/sales/companies/<company_cen>/tax-configuration', methods=['GET'])
def sales_get_tax(company_cen):
    return jsonify({'companyCen': company_cen, 'globalTaxPercentage': 13.0})

@bp.route('/api/sales/companies/<company_cen>/tax-configuration', methods=['PUT'])
def sales_update_tax(company_cen):
    return jsonify({'companyCen': company_cen, 'globalTaxPercentage': request.get_json().get('globalTaxPercentage')})

@bp.route('/api/sales/companies/<company_cen>/waiters', methods=['GET'])
def sales_get_waiters(company_cen):
    waiters = query("SELECT cen as waiterCen, nombre as name FROM meseros")
    return jsonify(waiters)

@bp.route('/api/sales/companies/<company_cen>/waiters', methods=['POST'])
def sales_create_waiter(company_cen):
    data = request.get_json() or {}
    new_cen = str(uuid.uuid4())
    execute("INSERT INTO meseros (cen, nombre, activo) VALUES (%s, %s, 1)", (new_cen, data.get('name')))
    return jsonify({'waiterCen': new_cen, 'name': data.get('name')}), 201

@bp.route('/api/sales/companies/<company_cen>/tickets/<ticket_cen>/cancel', methods=['POST'])
def sales_cancel_ticket(company_cen, ticket_cen):
    execute("UPDATE tickets SET estado = 'cancelado' WHERE cen = %s", (ticket_cen,))
    return jsonify({'ticketCen': ticket_cen, 'status': 'CANCELLED'})

@bp.route('/api/sales/companies/<company_cen>/tickets/<ticket_cen>/send', methods=['POST'])
def sales_send_ticket(company_cen, ticket_cen):
    ticket = query("SELECT id FROM tickets WHERE cen = %s", (ticket_cen,), fetch='one')
    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404
    items = query("SELECT ti.id, ti.cen, p.station_code FROM ticket_items ti JOIN productos p ON p.id = ti.producto_id WHERE ti.ticket_id = %s", (ticket['id'],))
    created = []
    for item in items:
        station_type = 'bar' if item.get('station_code') == 'BAR' else 'cocina'
        station = query("SELECT id FROM estaciones WHERE tipo = %s LIMIT 1", (station_type,), fetch='one')
        if not station:
            continue
        existing = query("SELECT ci.cen FROM comanda_items ci JOIN comandas c ON c.id = ci.comanda_id WHERE c.ticket_id = %s AND ci.ticket_item_id = %s", (ticket['id'], item['id']), fetch='one')
        if existing:
            continue
        command_cen = str(uuid.uuid4())
        command_number = f"COM-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}-{item['id']}"
        command_id = execute("INSERT INTO comandas (ticket_id, estacion_id, nro_comanda, estado, cen) VALUES (%s, %s, %s, 'pendiente', %s)", (ticket['id'], station['id'], command_number, command_cen))
        item_cen = str(uuid.uuid4())
        execute("INSERT INTO comanda_items (comanda_id, ticket_item_id, estado, cen) VALUES (%s, %s, 'pendiente', %s)", (command_id, item['id'], item_cen))
        created.append({'commandCen': command_cen, 'ticketItemCen': item_cen})
    return jsonify(created)

@bp.route('/api/sales/companies/<company_cen>/tickets/<ticket_cen>/print', methods=['GET'])
def sales_print_ticket(company_cen, ticket_cen):
    return jsonify({'fileContents': 'base64data'})

@bp.route('/api/sales/companies/<company_cen>/tickets/<ticket_cen>/totals', methods=['GET'])
def sales_get_totals(company_cen, ticket_cen):
    t = query("SELECT cen as ticketCen, subtotal, impuesto as taxAmount, total FROM tickets WHERE cen = %s", (ticket_cen,), fetch='one')
    return jsonify(t)

@bp.route('/api/sales/companies/<company_cen>/kds/items/<item_cen>/status', methods=['PATCH'])
def sales_update_kds_item_status(company_cen, item_cen):
    data = request.get_json() or {}
    status_map = {'PENDING': 'pendiente', 'IN_PROGRESS': 'en_preparacion', 'READY': 'listo'}
    status = status_map.get(data.get('status'), data.get('status'))
    execute("UPDATE comanda_items SET estado = %s, actualizado_en = CURRENT_TIMESTAMP WHERE cen = %s", (status, item_cen))
    return jsonify({'ticketItemCen': item_cen, 'status': data.get('status')})

@bp.route('/api/sales/payment-methods', methods=['GET'])
def sales_pay_methods():
    return jsonify([{'paymentMethodCode': 'CASH', 'name': 'Efectivo', 'isActive': True}])
