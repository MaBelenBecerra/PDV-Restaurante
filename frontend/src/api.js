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

// ==========================================
// CATEGORÍAS
// ==========================================
export async function getCategorias() {
  const companyCen = await getCompanyCen()
  const res = await apiCall(`/inventory/companies/${companyCen}/categories`)
  return res.map(cat => ({
    id: cat.cen,
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
    id: res.cen,
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
    id: res.cen,
    nombre: res.name
  }
}

// ==========================================
// UNIDADES
// ==========================================
export async function getUnidades() {
  const companyCen = await getCompanyCen()
  const res = await apiCall(`/inventory/companies/${companyCen}/units`)
  return res.map(u => ({
    id: u.cen,
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
    id: res.cen,
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
    id: res.cen,
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
  
  const res = await apiCall(endpoint)
  return res.items.map(p => ({
    id: p.cen,
    nombre: p.name,
    categoria_id: p.categoryCen,
    unidad_id: p.unitCen,
    precio: p.price,
    stock: p.stock || 0,
    activo: p.active ? 1 : 0,
    agotado: p.isOutOfStock ? 1 : 0,
    categoria: p.category ? p.category.nombre : '',
    unidad: p.unidad ? p.unidad.nombre : '',
    station_code: p.stationCode
  }))
}

export async function crearProducto(data) {
  const companyCen = await getCompanyCen()
  const res = await apiCall(`/inventory/companies/${companyCen}/products`, {
    method: 'POST',
    body: JSON.stringify({
      name: data.nombre,
      categoryCen: data.categoria_id,
      unitCen: data.unidad_id,
      price: data.precio,
      stock: data.stock || 0,
      stationCode: 'COCINA'
    })
  })
  return {
    id: res.cen,
    nombre: res.name,
    categoria_id: res.categoryCen,
    unidad_id: res.unitCen,
    precio: res.price,
    stock: res.stock || 0,
    activo: 1,
    agotado: 0
  }
}

export async function editarProducto(id, data) {
  const companyCen = await getCompanyCen()
  const res = await apiCall(`/inventory/companies/${companyCen}/products/${id}`, {
    method: 'PUT',
    body: JSON.stringify({
      name: data.nombre,
      categoryCen: data.categoria_id,
      unitCen: data.unidad_id,
      price: data.precio
    })
  })
  return {
    id: res.cen,
    nombre: res.name,
    categoria_id: res.categoryCen,
    unidad_id: res.unitCen,
    precio: res.price,
    stock: res.stock || 0,
    activo: 1,
    agotado: 0
  }
}

export async function toggleActivo(id) {
  const companyCen = await getCompanyCen()
  const products = await getProductos()
  const p = products.find(prod => prod.id === id)
  const newActive = p ? !p.activo : true
  
  const res = await apiCall(`/inventory/companies/${companyCen}/products/${id}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ active: newActive })
  })
  return {
    id: res.cen,
    activo: res.active ? 1 : 0
  }
}

export async function toggleAgotado(id) {
  const companyCen = await getCompanyCen()
  const products = await getProductos()
  const p = products.find(prod => prod.id === id)
  const newAgotado = p ? !p.agotado : false
  
  const res = await apiCall(`/inventory/companies/${companyCen}/products/${id}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ isOutOfStock: newAgotado })
  })
  return {
    id: res.cen,
    agotado: res.isOutOfStock ? 1 : 0
  }
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
  
  return stockItems.map(s => {
    const p = products.find(prod => prod.id === s.productCen) || {}
    let estado = 'ok'
    if (s.quantity <= 0) {
      estado = 'agotado'
    } else if (s.quantity < 5) {
      estado = 'bajo'
    }
    
    return {
      id: s.productCen,
      nombre: p.nombre || s.productCode,
      categoria: p.categoria || '',
      unidad: p.unidad || '',
      stock: s.quantity,
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
      productCen: data.producto_id,
      quantity: data.tipo === 'entrada' ? data.cantidad : -data.cantidad,
      reason: data.motivo
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
  const map_status = {'OPEN': 'abierto', 'PAID': 'pagado', 'CANCELLED': 'cancelado'}
  return res.map(t => ({
    id: t.cen,
    mesero: t.mesero,
    estado: map_status[t.status] || t.status.toLowerCase(),
    total: t.total,
    creado_en: t.createdAt
  }))
}

export async function crearTicket(data) {
  const companyCen = await getCompanyCen()
  const res = await apiCall(`/sales/companies/${companyCen}/tickets`, {
    method: 'POST',
    body: JSON.stringify({ mesero: data.mesero })
  })
  return {
    id: res.cen,
    mesero: res.mesero,
    estado: 'abierto',
    total: 0.0,
    creado_en: res.createdAt
  }
}

export async function getTicket(id) {
  const companyCen = await getCompanyCen()
  const [t, items, totals] = await Promise.all([
    apiCall(`/sales/companies/${companyCen}/tickets/${id}`),
    apiCall(`/sales/companies/${companyCen}/tickets/${id}/items`),
    apiCall(`/sales/companies/${companyCen}/tickets/${id}/totals`)
  ])
  
  const products = await getProductos()
  const mappedItems = items.map(item => {
    const p = products.find(prod => prod.id === item.productCen) || {}
    return {
      id: item.cen,
      producto_id: item.productCen,
      nombre: p.nombre || item.productCode,
      categoria: p.categoria || '',
      cantidad: item.quantity,
      precio_unitario: item.unitPrice,
      subtotal: item.quantity * item.unitPrice,
      nota: item.notes
    }
  })
  
  const map_status = {'OPEN': 'abierto', 'PAID': 'pagado', 'CANCELLED': 'cancelado'}
  return {
    id: t.cen,
    mesero: t.mesero,
    estado: map_status[t.status] || t.status.toLowerCase(),
    creado_en: t.createdAt,
    subtotal: totals.subtotal,
    impuesto: totals.tax,
    total: totals.total,
    tasa_impuesto: totals.taxRate,
    items: mappedItems
  }
}

export async function agregarItem(ticketId, data) {
  const companyCen = await getCompanyCen()
  const res = await apiCall(`/sales/companies/${companyCen}/tickets/${ticketId}/items`, {
    method: 'POST',
    body: JSON.stringify({
      productCen: data.producto_id,
      quantity: data.cantidad,
      notes: data.nota || ''
    })
  })
  
  const products = await getProductos()
  const p = products.find(prod => prod.id === res.productCen) || {}
  
  return {
    item: {
      id: res.cen,
      producto_id: res.productCen,
      nombre: p.nombre || '',
      categoria: p.categoria || '',
      cantidad: res.quantity,
      precio_unitario: res.unitPrice,
      subtotal: res.quantity * res.unitPrice,
      nota: res.notes
    },
    ticket_totals: res.ticket_totals
  }
}

export async function editarItem(ticketId, itemId, data) {
  const companyCen = await getCompanyCen()
  const res = await apiCall(`/sales/companies/${companyCen}/tickets/${ticketId}/items/${itemId}`, {
    method: 'PATCH',
    body: JSON.stringify({
      quantity: data.cantidad,
      notes: data.nota
    })
  })
  
  const items = await apiCall(`/sales/companies/${companyCen}/tickets/${ticketId}/items`)
  const item = items.find(i => i.cen === itemId) || {}
  const products = await getProductos()
  const p = products.find(prod => prod.id === item.productCen) || {}
  
  return {
    item: {
      id: item.cen,
      producto_id: item.productCen,
      nombre: p.nombre || '',
      categoria: p.categoria || '',
      cantidad: item.quantity,
      precio_unitario: item.unitPrice,
      subtotal: item.quantity * item.unitPrice,
      nota: item.notes
    },
    ticket_totals: res.ticket_totals
  }
}

export async function eliminarItem(ticketId, itemId) {
  const companyCen = await getCompanyCen()
  const res = await apiCall(`/sales/companies/${companyCen}/tickets/${ticketId}/items/${itemId}`, {
    method: 'DELETE'
  })
  return res
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
  
  let targetStation = estaciones.find(e => e.cen === estacionId)
  if (!targetStation) {
    if (estacionId === 1 || estacionId === '1') {
      targetStation = estaciones.find(e => e.stationType === 'KITCHEN')
    } else if (estacionId === 2 || estacionId === '2') {
      targetStation = estaciones.find(e => e.stationType === 'BAR')
    }
  }
  
  const stationCen = targetStation ? targetStation.cen : estacionId
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
  for (const item of res) {
    const ticketId = item.ticketCen
    if (!comandasGrouped[ticketId]) {
      comandasGrouped[ticketId] = {
        comanda_id: item.cen,
        ticket_id: ticketId,
        mesero: item.mesero || 'Mesero',
        hora: item.createdAt,
        items: []
      }
    }
    
    const map_status = {'PENDING': 'pendiente', 'IN_PROGRESS': 'en_preparacion', 'READY': 'listo'}
    comandasGrouped[ticketId].items.push({
      id: item.cen,
      nombre: item.productName,
      cantidad: item.quantity,
      nota: item.notes,
      estado: map_status[item.status] || item.status.toLowerCase()
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
  
  const mappedTopProducts = topProducts.map(tp => {
    const p = products.find(prod => prod.id === tp.productCen) || {}
    return {
      nombre: p.nombre || tp.productCen,
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
  for (const statusVal of kdsStatus) {
    const mappedKey = map_status[statusVal.status]
    if (mappedKey) comandas_estado[mappedKey] = statusVal.count
  }
  
  return {
    ventas_hoy: {
      total_tickets: 0,
      total_vendido: dailySales.total || 0.0,
      ticket_promedio: 0.0
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
  return { tasa_impuesto: res.taxRate }
}

export async function updateConfiguracion(data) {
  const companyCen = await getCompanyCen()
  const res = await apiCall(`/sales/companies/${companyCen}/tax-configuration`, {
    method: 'PUT',
    body: JSON.stringify({ taxRate: data.tasa_impuesto })
  })
  return { tasa_impuesto: res.taxRate }
}
