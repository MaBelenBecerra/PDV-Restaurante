const API_URL = 'http://localhost:5000/api'

// Helper function for API calls
async function apiCall(endpoint, options = {}) {
  const url = `${API_URL}${endpoint}`
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

// CATEGORÍAS
export async function getCategorias() {
  return apiCall('/categorias')
}

export async function crearCategoria(data) {
  return apiCall('/categorias', {
    method: 'POST',
    body: JSON.stringify(data)
  })
}

export async function editarCategoria(id, data) {
  return apiCall(`/categorias/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data)
  })
}

// UNIDADES
export async function getUnidades() {
  return apiCall('/unidades')
}

export async function crearUnidad(data) {
  return apiCall('/unidades', {
    method: 'POST',
    body: JSON.stringify(data)
  })
}

export async function editarUnidad(id, data) {
  return apiCall(`/unidades/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data)
  })
}

// PRODUCTOS
export async function getProductos(filtros = {}) {
  let endpoint = '/productos'
  const params = new URLSearchParams()
  
  if (filtros.categoria_id) params.append('categoria_id', filtros.categoria_id)
  if (filtros.activo !== undefined) params.append('activo', filtros.activo)
  if (filtros.buscar) params.append('buscar', filtros.buscar)
  
  if (params.toString()) {
    endpoint += '?' + params.toString()
  }
  
  return apiCall(endpoint)
}

export async function crearProducto(data) {
  return apiCall('/productos', {
    method: 'POST',
    body: JSON.stringify(data)
  })
}

export async function editarProducto(id, data) {
  return apiCall(`/productos/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data)
  })
}

export async function toggleActivo(id) {
  return apiCall(`/productos/${id}/toggle-activo`, {
    method: 'PATCH'
  })
}

export async function toggleAgotado(id) {
  return apiCall(`/productos/${id}/toggle-agotado`, {
    method: 'PATCH'
  })
}

// INVENTARIO
export async function getInventario() {
  return apiCall('/inventario')
}

export async function ajustarStock(data) {
  return apiCall('/inventario/ajuste', {
    method: 'POST',
    body: JSON.stringify(data)
  })
}

// TICKETS
export async function getTickets(estado = '') {
  let endpoint = '/tickets'
  if (estado) {
    endpoint += '?estado=' + estado
  }
  return apiCall(endpoint)
}

export async function crearTicket(data) {
  return apiCall('/tickets', {
    method: 'POST',
    body: JSON.stringify(data)
  })
}

export async function getTicket(id) {
  return apiCall(`/tickets/${id}`)
}

export async function agregarItem(ticketId, data) {
  return apiCall(`/tickets/${ticketId}/items`, {
    method: 'POST',
    body: JSON.stringify(data)
  })
}

export async function editarItem(ticketId, itemId, data) {
  return apiCall(`/tickets/${ticketId}/items/${itemId}`, {
    method: 'PUT',
    body: JSON.stringify(data)
  })
}

export async function eliminarItem(ticketId, itemId) {
  return apiCall(`/tickets/${ticketId}/items/${itemId}`, {
    method: 'DELETE'
  })
}

export async function cancelarTicket(id) {
  return apiCall(`/tickets/${id}/cancelar`, {
    method: 'PATCH'
  })
}

export async function pagarTicket(id, data) {
  return apiCall(`/tickets/${id}/pagar`, {
    method: 'POST',
    body: JSON.stringify(data)
  })
}

// COMANDAS
export async function enviarComanda(ticketId, esReenvio = false) {
  return apiCall(`/tickets/${ticketId}/comanda`, {
    method: 'POST',
    body: JSON.stringify({ es_reenvio: esReenvio ? 1 : 0 })
  })
}

export async function getKDS(estacionId) {
  return apiCall(`/kds/${estacionId}`)
}

export async function cambiarEstadoItem(comandaItemId, estado) {
  return apiCall(`/kds/item/${comandaItemId}/estado`, {
    method: 'PATCH',
    body: JSON.stringify({ estado })
  })
}

// DASHBOARD
export async function getDashboard() {
  return apiCall('/dashboard')
}

// CONFIGURACIÓN
export async function getConfiguracion() {
  return apiCall('/configuracion')
}

export async function updateConfiguracion(data) {
  return apiCall('/configuracion', {
    method: 'PUT',
    body: JSON.stringify(data)
  })
}
