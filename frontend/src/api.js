function readEnvValue(keys) {
  for (const key of keys) {
    const value = import.meta.env[key]
    if (typeof value === 'string' && value.trim()) {
      return value
    }
  }
  return ''
}

function normalizeApiBaseUrl(baseUrl, apiPrefix, defaultPort) {
  const normalizedBaseUrl = (baseUrl || '').replace(/\/$/, '')
  const fallbackBaseUrl = `${window.location.protocol}//${window.location.hostname}:${defaultPort}`
  const resolvedBaseUrl = normalizedBaseUrl || fallbackBaseUrl
  return resolvedBaseUrl.endsWith(apiPrefix) ? resolvedBaseUrl : `${resolvedBaseUrl}${apiPrefix}`
}

const DEFAULT_COMPANY_CEN = '9f2a4e4e-ac9d-46a4-98ea-412d1c168d12'

const INVENTORY_API_URL = normalizeApiBaseUrl(readEnvValue(['VITE_INVENTORY_API_URL']), '/api/inventory', '5143')
const SALES_API_URL = normalizeApiBaseUrl(readEnvValue(['VITE_SALES_API_URL', 'VITE_SALE_API_URL']), '/api/sales', '5074')
const PURCHASES_API_URL = normalizeApiBaseUrl(readEnvValue(['VITE_PURCHASES_API_URL', 'VITE_PURCHASE_API_URL']), '/api/purchases', '5229')

function getApiUrl(endpoint) {
  if (endpoint.startsWith('/inventory')) {
    return `${INVENTORY_API_URL}${endpoint.substring(10)}`
  } else if (endpoint.startsWith('/sales')) {
    return `${SALES_API_URL}${endpoint.substring(6)}`
  } else if (endpoint.startsWith('/purchases')) {
    return `${PURCHASES_API_URL}${endpoint.substring(10)}`
  }
  return `${INVENTORY_API_URL}${endpoint}`
}

function sanitizeEndpoint(endpoint) {
  return endpoint.replace(/\/companies\/(undefined|null)(?=\/|$)/g, `/companies/${DEFAULT_COMPANY_CEN}`)
}

// Cache company CEN in localStorage
let cachedCompanyCen = localStorage.getItem('companyCen')
if (cachedCompanyCen === 'undefined' || cachedCompanyCen === 'null' || !cachedCompanyCen?.trim()) {
  cachedCompanyCen = null
}

// Helper function to resolve active company CEN dynamically
async function getCompanyCen() {
  if (cachedCompanyCen) return cachedCompanyCen
  try {
    const res = await apiCall('/inventory/companies')
    if (res && res.length > 0) {
      cachedCompanyCen = res[0].companyCen || res[0].cen
      localStorage.setItem('companyCen', cachedCompanyCen)
      return cachedCompanyCen
    }
  } catch (e) {
    console.error("Failed to load company CEN", e)
  }
  return DEFAULT_COMPANY_CEN
}

// Helper function for API calls
async function apiCall(endpoint, options = {}) {
  const url = getApiUrl(sanitizeEndpoint(endpoint))
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  }
  
  try {
    const response = await fetch(url, {
      ...options,
      headers,
    })
    
    const data = await response.json()
    
    if (!response.ok) {
      throw new Error(data.error || 'Error en la solicitud')
    }
    
    return data
  } catch (error) {
    throw error
  }
}

function asArray(value) {
  if (Array.isArray(value)) return value
  if (Array.isArray(value?.items)) return value.items
  if (Array.isArray(value?.data)) return value.data
  return []
}

function asNumber(value, fallback = 0) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

function productId(product) {
  return product.productCen || product.cen || product.id
}

function categoryId(category) {
  return category.categoryCen || category.cen || category.id
}

function unitId(unit) {
  return unit.unitCen || unit.cen || unit.id
}

function ticketId(ticket) {
  return ticket.ticketCen || ticket.cen || ticket.id
}

function ticketItemId(item) {
  return item.ticketItemCen || item.cen || item.id
}

function mapProduct(product, stockByProduct = new Map()) {
  const id = productId(product)
  const stockInfo = stockByProduct.get(id) || {}
  const stock = asNumber(
    product.stock ?? product.availableQuantity ?? product.initialStock ?? stockInfo.availableQuantity ?? stockInfo.quantity,
    0
  )
  const status = product.status || (product.active === false ? 'INACTIVE' : 'ACTIVE')

  return {
    id,
    nombre: product.name || product.nombre || product.productName || '',
    categoria_id: product.categoryCen || product.categoria_id || '',
    unidad_id: product.unitCen || product.unidad_id || '',
    precio: asNumber(product.salePrice ?? product.price ?? product.precio, 0),
    stock,
    activo: status === 'INACTIVE' || product.active === false ? 0 : 1,
    agotado: product.isOutOfStock || stock <= 0 ? 1 : 0,
    categoria: product.categoryName || product.category?.name || product.category?.nombre || '',
    unidad: product.unitName || product.unit?.name || product.unidad?.nombre || '',
    station_code: product.stationCode || product.station_code
  }
}

function mapTicket(ticket, fallback = {}) {
  const mapStatus = { OPEN: 'abierto', PAID: 'pagado', CANCELLED: 'cancelado' }
  const status = ticket.status || fallback.status || 'OPEN'

  return {
    id: ticketId(ticket),
    mesero: ticket.mesero || ticket.waiterName || ticket.waiterCen || fallback.mesero || 'Mesero',
    estado: mapStatus[status] || String(status).toLowerCase(),
    total: asNumber(ticket.total ?? ticket.totalAmount ?? fallback.total, 0),
    creado_en: ticket.createdAt || ticket.creado_en || fallback.creado_en || new Date().toISOString()
  }
}

function mapTotals(totals = {}) {
  const subtotal = asNumber(totals.subtotal, 0)
  const tax = asNumber(totals.tax ?? totals.taxAmount ?? totals.impuesto, 0)
  const total = asNumber(totals.total, subtotal + tax)

  return {
    subtotal,
    impuesto: tax,
    total,
    tasa_impuesto: subtotal > 0 ? tax / subtotal : 0.13
  }
}

// ==========================================
// CATEGORÍAS
// ==========================================
export async function getCategorias() {
  const companyCen = await getCompanyCen()
  const res = await apiCall(`/inventory/companies/${companyCen}/categories`)
  return asArray(res).map(cat => ({
    id: categoryId(cat),
    nombre: cat.name
  }))
}

export async function crearCategoria(data) {
  const companyCen = await getCompanyCen()
  const res = await apiCall(`/inventory/companies/${companyCen}/categories`, {
    method: 'POST',
    body: JSON.stringify({ name: data.nombre })
  })
  return {
    id: categoryId(res),
    nombre: res.name
  }
}

export async function editarCategoria(id, data) {
  const companyCen = await getCompanyCen()
  const res = await apiCall(`/inventory/companies/${companyCen}/categories/${id}`, {
    method: 'PUT',
    body: JSON.stringify({ name: data.nombre })
  })
  return {
    id: categoryId(res),
    nombre: res.name
  }
}

// ==========================================
// UNIDADES
// ==========================================
export async function getUnidades() {
  const companyCen = await getCompanyCen()
  const res = await apiCall(`/inventory/companies/${companyCen}/units`)
  return asArray(res).map(u => ({
    id: unitId(u),
    nombre: u.name
  }))
}

export async function crearUnidad(data) {
  const companyCen = await getCompanyCen()
  const res = await apiCall(`/inventory/companies/${companyCen}/units`, {
    method: 'POST',
    body: JSON.stringify({ name: data.nombre })
  })
  return {
    id: unitId(res),
    nombre: res.name
  }
}

export async function editarUnidad(id, data) {
  const companyCen = await getCompanyCen()
  const res = await apiCall(`/inventory/companies/${companyCen}/units/${id}`, {
    method: 'PUT',
    body: JSON.stringify({ name: data.nombre })
  })
  return {
    id: unitId(res),
    nombre: res.name
  }
}

// ==========================================
// PRODUCTOS
// ==========================================
export async function getProductos(filtros = {}) {
  const companyCen = await getCompanyCen()
  let endpoint = `/inventory/companies/${companyCen}/products`
  const params = new URLSearchParams()
  
  if (filtros.categoria_id) params.append('categoryCen', filtros.categoria_id)
  if (filtros.buscar) params.append('search', filtros.buscar)
  
  if (params.toString()) {
    endpoint += '?' + params.toString()
  }
  
  const [productsRes, stockRes] = await Promise.all([
    apiCall(endpoint),
    apiCall(`/inventory/companies/${companyCen}/stock`).catch(() => [])
  ])
  const stockByProduct = new Map(asArray(stockRes).map(item => [item.productCen, item]))

  return asArray(productsRes)
    .map(product => mapProduct(product, stockByProduct))
    .filter(product => filtros.activo == null || product.activo === filtros.activo)
}

export async function crearProducto(data) {
  const companyCen = await getCompanyCen()
  const res = await apiCall(`/inventory/companies/${companyCen}/products`, {
    method: 'POST',
    body: JSON.stringify({
      name: data.nombre,
      categoryCen: data.categoria_id,
      unitCen: data.unidad_id,
      salePrice: data.precio,
      initialStock: data.stock || 0,
      stationCode: 'COCINA'
    })
  })
  return mapProduct({ ...res, categoryCen: data.categoria_id, unitCen: data.unidad_id, salePrice: data.precio, initialStock: data.stock })
}

export async function editarProducto(id, data) {
  const companyCen = await getCompanyCen()
  const res = await apiCall(`/inventory/companies/${companyCen}/products/${id}`, {
    method: 'PUT',
    body: JSON.stringify({
      name: data.nombre,
      categoryCen: data.categoria_id,
      unitCen: data.unidad_id,
      salePrice: data.precio
    })
  })
  return mapProduct({ ...res, categoryCen: data.categoria_id, unitCen: data.unidad_id, salePrice: data.precio, stock: data.stock })
}

export async function toggleActivo(id) {
  const companyCen = await getCompanyCen()
  const products = await getProductos()
  const p = products.find(prod => prod.id === id)
  const newActive = p ? !p.activo : true
  
  const res = await apiCall(`/inventory/companies/${companyCen}/products/${id}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status: newActive ? 'ACTIVE' : 'INACTIVE' })
  })
  return {
    id: productId(res),
    activo: res.status === 'ACTIVE' ? 1 : 0
  }
}

export async function toggleAgotado(id) {
  const product = (await getProductos()).find(prod => prod.id === id)
  return { id, agotado: product?.stock <= 0 ? 1 : 0 }
}

// ==========================================
// INVENTARIO
// ==========================================
export async function getInventario() {
  const companyCen = await getCompanyCen()
  const [stockItems, products] = await Promise.all([
    apiCall(`/inventory/companies/${companyCen}/stock`),
    getProductos()
  ])
  
  return asArray(stockItems).map(s => {
    const p = products.find(prod => prod.id === s.productCen) || {}
    let estado = 'ok'
    const quantity = asNumber(s.availableQuantity ?? s.quantity, 0)
    if (quantity <= 0) {
      estado = 'agotado'
    } else if (quantity < 5) {
      estado = 'bajo'
    }
    
    return {
      id: s.productCen,
      nombre: p.nombre || s.productName || s.productCode,
      categoria: p.categoria || '',
      unidad: p.unidad || s.unitName || '',
      stock: quantity,
      estado,
      precio: p.precio || 0.0
    }
  })
}

export async function ajustarStock(data) {
  const companyCen = await getCompanyCen()
  const res = await apiCall(`/inventory/companies/${companyCen}/stock/adjustments`, {
    method: 'POST',
    body: JSON.stringify({
      lines: [{
        productCen: data.producto_id,
        quantity: data.cantidad,
        adjustmentType: data.tipo === 'entrada' ? 'INCREASE' : 'DECREASE',
        reason: data.motivo
      }]
    })
  })
  return res
}

// ==========================================
// TICKETS
// ==========================================
export async function getTickets(estado = '') {
  const companyCen = await getCompanyCen()
  let statusParam = ''
  if (estado === 'abierto') statusParam = 'OPEN'
  if (estado === 'pagado') statusParam = 'PAID'
  if (estado === 'cancelado') statusParam = 'CANCELLED'
  
  const res = await apiCall(`/sales/companies/${companyCen}/tickets` + (statusParam ? `?status=${statusParam}` : ''))
  return asArray(res).map(mapTicket)
}

export async function crearTicket(data) {
  const companyCen = await getCompanyCen()
  const res = await apiCall(`/sales/companies/${companyCen}/tickets`, {
    method: 'POST',
    body: JSON.stringify({ waiterCen: data.mesero, mesero: data.mesero })
  })
  return mapTicket(res, { mesero: data.mesero, total: 0 })
}

export async function getTicket(id) {
  const companyCen = await getCompanyCen()
  const [tickets, items, totals] = await Promise.all([
    apiCall(`/sales/companies/${companyCen}/tickets`),
    apiCall(`/sales/companies/${companyCen}/tickets/${id}/items`),
    apiCall(`/sales/companies/${companyCen}/tickets/${id}/totals`)
  ])
  const t = asArray(tickets).find(ticket => ticketId(ticket) === id) || { ticketCen: id }
  
  const products = await getProductos()
  const mappedItems = asArray(items).map(item => {
    const p = products.find(prod => prod.id === item.productCen) || {}
    return {
      id: ticketItemId(item),
      producto_id: item.productCen,
      nombre: p.nombre || item.productName || item.productCode,
      categoria: p.categoria || '',
      cantidad: item.quantity,
      precio_unitario: item.unitPrice,
      subtotal: item.quantity * item.unitPrice,
      nota: item.note || item.notes || ''
    }
  })
  
  const mappedTicket = mapTicket(t)
  const mappedTotals = mapTotals(totals)
  return {
    ...mappedTicket,
    ...mappedTotals,
    items: mappedItems
  }
}

async function getTicketTotals(companyCen, ticketId) {
  return mapTotals(await apiCall(`/sales/companies/${companyCen}/tickets/${ticketId}/totals`))
}

async function getMappedTicketItem(companyCen, ticketId, itemId) {
  const [items, products] = await Promise.all([
    apiCall(`/sales/companies/${companyCen}/tickets/${ticketId}/items`),
    getProductos()
  ])
  const item = asArray(items).find(i => ticketItemId(i) === itemId) || {}
  const product = products.find(prod => prod.id === item.productCen) || {}

  return {
    id: ticketItemId(item),
    producto_id: item.productCen,
    nombre: product.nombre || item.productName || '',
    categoria: product.categoria || '',
    cantidad: asNumber(item.quantity, 0),
    precio_unitario: asNumber(item.unitPrice, 0),
    subtotal: asNumber(item.quantity, 0) * asNumber(item.unitPrice, 0),
    nota: item.note || item.notes || ''
  }
}

export async function agregarItem(ticketId, data) {
  const companyCen = await getCompanyCen()
  const res = await apiCall(`/sales/companies/${companyCen}/tickets/${ticketId}/items`, {
    method: 'POST',
    body: JSON.stringify({
      productCen: data.producto_id,
      quantity: data.cantidad,
      note: data.nota || ''
    })
  })
  
  const item = await getMappedTicketItem(companyCen, ticketId, ticketItemId(res))
  const ticketTotals = await getTicketTotals(companyCen, ticketId)
  
  return {
    item,
    ticket_totals: ticketTotals
  }
}

export async function editarItem(ticketId, itemId, data) {
  const companyCen = await getCompanyCen()
  const res = await apiCall(`/sales/companies/${companyCen}/tickets/${ticketId}/items/${itemId}`, {
    method: 'PATCH',
    body: JSON.stringify({
      ...(data.cantidad != null ? { quantity: data.cantidad } : {}),
      ...(data.nota != null ? { note: data.nota } : {})
    })
  })
  
  const item = await getMappedTicketItem(companyCen, ticketId, itemId)
  const ticketTotals = await getTicketTotals(companyCen, ticketId)
  
  return {
    item,
    ticket_totals: ticketTotals
  }
}

export async function eliminarItem(ticketId, itemId) {
  const companyCen = await getCompanyCen()
  const res = await apiCall(`/sales/companies/${companyCen}/tickets/${ticketId}/items/${itemId}`, {
    method: 'DELETE'
  })
  return {
    ...res,
    ticket_totals: res.ticket_totals || await getTicketTotals(companyCen, ticketId)
  }
}

export async function cancelarTicket(id) {
  const companyCen = await getCompanyCen()
  const res = await apiCall(`/sales/companies/${companyCen}/tickets/${id}/cancel`, {
    method: 'POST'
  })
  return res
}

export async function pagarTicket(id, data) {
  const companyCen = await getCompanyCen()
  const paymentMethod = data.metodo === 'efectivo' ? 'CASH' : data.metodo === 'qr' ? 'QR' : 'CARD'
  const res = await apiCall(`/sales/companies/${companyCen}/tickets/${id}/payment`, {
    method: 'POST',
    body: JSON.stringify({
      paymentMethod
    })
  })
  return res
}

// ==========================================
// COMANDAS & KDS
// ==========================================
export async function enviarComanda(ticketId) {
  const companyCen = await getCompanyCen()
  const res = await apiCall(`/sales/companies/${companyCen}/tickets/${ticketId}/send`, {
    method: 'POST'
  })
  return res
}

export async function getKDS(estacionId) {
  const companyCen = await getCompanyCen()
  const estaciones = await apiCall(`/sales/companies/${companyCen}/kds/teams`)
  
  const stations = asArray(estaciones)
  let targetStation = stations.find(e => e.teamCen === estacionId || e.cen === estacionId)
  if (!targetStation) {
    if (estacionId === 1 || estacionId === '1') {
      targetStation = stations.find(e => e.stationType === 'KITCHEN' || e.name?.toLowerCase().includes('cocina')) || stations[0]
    } else if (estacionId === 2 || estacionId === '2') {
      targetStation = stations.find(e => e.stationType === 'BAR' || e.name?.toLowerCase().includes('bar')) || stations[1]
    }
  }
  
  const stationCen = targetStation ? (targetStation.teamCen || targetStation.cen) : estacionId
  const res = await apiCall(`/sales/companies/${companyCen}/kds/teams/${stationCen}/items`)
  
  if (res && res.length > 0 && res[0].items !== undefined) {
    const products = await getProductos()
    return res.map(comanda => {
      return {
        comanda_id: comanda.id,
        ticket_id: comanda.ticketId,
        mesero: comanda.mesero || 'Mesero',
        hora: comanda.fechaEnvio,
        items: comanda.items.map(i => {
          const p = products.find(prod => prod.id === i.producto) || {}
          return {
            id: i.id,
            nombre: p.nombre || i.producto,
            cantidad: i.cantidad,
            nota: i.nota,
            estado: i.estado === 'PENDING' ? 'pendiente' : i.estado === 'IN_PROGRESS' ? 'en_preparacion' : 'listo'
          }
        })
      }
    })
  }

  const comandasGrouped = {}
  for (const item of asArray(res)) {
    const ticketId = item.ticketCen || item.ticket_id
    if (!comandasGrouped[ticketId]) {
      comandasGrouped[ticketId] = {
        comanda_id: ticketId,
        ticket_id: ticketId,
        mesero: item.mesero || 'Mesero',
        hora: item.createdAt || new Date().toISOString(),
        items: []
      }
    }
    
    const map_status = {'PENDING': 'pendiente', 'IN_PROGRESS': 'en_preparacion', 'READY': 'listo', pendiente: 'pendiente', en_preparacion: 'en_preparacion', listo: 'listo'}
    comandasGrouped[ticketId].items.push({
      id: ticketItemId(item),
      nombre: item.productName || item.productCen,
      cantidad: asNumber(item.quantity, 0),
      nota: item.note || item.notes || '',
      estado: map_status[item.status] || String(item.status || 'PENDING').toLowerCase()
    })
  }
  
  return Object.values(comandasGrouped)
}

export async function cambiarEstadoItem(comandaItemId, estado) {
  const companyCen = await getCompanyCen()
  const map_status = {'pendiente': 'PENDING', 'en_preparacion': 'IN_PROGRESS', 'listo': 'READY'}
  const res = await apiCall(`/sales/companies/${companyCen}/kds/items/${comandaItemId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status: map_status[estado] })
  })
  return res
}

// ==========================================
// DASHBOARD
// ==========================================
export async function getDashboard() {
  const companyCen = await getCompanyCen()
  const [dailySales, topProducts, kdsStatus, products] = await Promise.all([
    apiCall(`/sales/companies/${companyCen}/dashboard/daily-sales`),
    apiCall(`/sales/companies/${companyCen}/dashboard/top-products`),
    apiCall(`/sales/companies/${companyCen}/dashboard/kds-status`),
    getProductos()
  ])
  
  const mappedTopProducts = asArray(topProducts).map(tp => {
    const p = products.find(prod => prod.id === tp.productCen) || {}
    return {
      nombre: p.nombre || tp.productName || tp.productCen,
      categoria: p.categoria || '',
      unidades_vendidas: tp.quantity,
      total_vendido: tp.quantity * (p.precio || 0.0)
    }
  })
  
  const comandas_estado = {
    pendiente: 0,
    en_preparacion: 0,
    listo: 0
  }
  
  const map_status = {'PENDING': 'pendiente', 'IN_PROGRESS': 'en_preparacion', 'READY': 'listo'}
  for (const statusVal of asArray(kdsStatus)) {
    const mappedKey = map_status[statusVal.status]
    if (mappedKey) comandas_estado[mappedKey] = statusVal.count
  }
  
  return {
    ventas_hoy: {
      total_tickets: asNumber(dailySales.ticketsCount ?? dailySales.totalTickets, 0),
      total_vendido: asNumber(dailySales.totalSales ?? dailySales.total, 0),
      ticket_promedio: asNumber(dailySales.averageTicket, 0)
    },
    top_productos: mappedTopProducts,
    productos_agotados: products.filter(p => p.stock <= 0).map(p => ({ id: p.id, nombre: p.nombre, stock: 0 })),
    stock_bajo: products.filter(p => p.stock > 0 && p.stock < 5).map(p => ({ id: p.id, nombre: p.nombre, stock: p.stock })),
    comandas_estado
  }
}

// ==========================================
// CONFIGURACIÓN
// ==========================================
export async function getConfiguracion() {
  const companyCen = await getCompanyCen()
  const res = await apiCall(`/sales/companies/${companyCen}/tax-configuration`)
  const value = asNumber(res.taxRate ?? res.globalTaxPercentage, 13)
  return { tasa_impuesto: value > 1 ? value / 100 : value }
}

export async function updateConfiguracion(data) {
  const companyCen = await getCompanyCen()
  const percentage = asNumber(data.tasa_impuesto, 0)
  const res = await apiCall(`/sales/companies/${companyCen}/tax-configuration`, {
    method: 'PUT',
    body: JSON.stringify({ globalTaxPercentage: percentage > 1 ? percentage : percentage * 100 })
  })
  const value = asNumber(res.taxRate ?? res.globalTaxPercentage, percentage)
  return { tasa_impuesto: value > 1 ? value / 100 : value }
}
