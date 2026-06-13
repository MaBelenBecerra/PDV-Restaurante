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
    tickets = query("SELECT cen as ticketCen, id as dailyNumber, CASE WHEN estado='abierto' THEN 'OPEN' WHEN estado='pagado' THEN 'PAID' ELSE 'CANCELLED' END as status, creado_en as createdAt, vendor_cen as waiterCen, %s as companyCen, impuesto as taxAmount FROM tickets", (company_cen,))
    return jsonify(tickets)

@bp.route('/api/sales/companies/<company_cen>/tickets', methods=['POST'])
def sales_create_ticket(company_cen):
    data = request.get_json() or {}
    new_cen = str(uuid.uuid4())
    count = query("SELECT COUNT(*) as count FROM tickets", fetch='one')['count']
    execute("INSERT INTO tickets (mesero, vendor_cen, estado, tasa_impuesto, cen, code) VALUES (%s, %s, 'abierto', 0.13, %s, %s)", ('Mesero', data.get('waiterCen'), new_cen, f"TIC-{count+1:05d}"))
    return jsonify({'ticketCen': new_cen, 'dailyNumber': count+1, 'status': 'OPEN', 'createdAt': datetime.datetime.now().isoformat(), 'waiterCen': data.get('waiterCen'), 'companyCen': company_cen, 'taxAmount': 0.0}), 201

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
    execute("UPDATE ticket_items SET cantidad = %s, nota = %s WHERE cen = %s", (data.get('quantity'), data.get('note'), item_cen))
    return jsonify({'ticketItemCen': item_cen}), 200

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
    return jsonify([])

@bp.route('/api/sales/companies/<company_cen>/tickets/<ticket_cen>/print', methods=['GET'])
def sales_print_ticket(company_cen, ticket_cen):
    return jsonify({'fileContents': 'base64data'})

@bp.route('/api/sales/companies/<company_cen>/tickets/<ticket_cen>/totals', methods=['GET'])
def sales_get_totals(company_cen, ticket_cen):
    t = query("SELECT cen as ticketCen, subtotal, impuesto as taxAmount, total FROM tickets WHERE cen = %s", (ticket_cen,), fetch='one')
    return jsonify(t)

@bp.route('/api/sales/payment-methods', methods=['GET'])
def sales_pay_methods():
    return jsonify([{'paymentMethodCode': 'CASH', 'name': 'Efectivo', 'isActive': True}])
