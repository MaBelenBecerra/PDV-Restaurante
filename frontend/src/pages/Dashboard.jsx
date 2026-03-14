import React, { useEffect, useState } from 'react'
import { getDashboard } from '../api'

export default function Dashboard({ showToast }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const result = await getDashboard()
      setData(result)
    } catch (error) {
      showToast('error', error.message)
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div className="p-6">Cargando...</div>

  if (!data) return <div className="p-6">No hay datos disponibles</div>

  const StatCard = ({ label, value, color }) => (
    <div className={`p-6 rounded-lg shadow ${color}`}>
      <p className="text-gray-600 mb-2">{label}</p>
      <p className="text-3xl font-bold text-gray-800">{value}</p>
    </div>
  )

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <button
          onClick={loadData}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          ↻ Actualizar
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <StatCard
          label="Total Vendido Hoy"
          value={`$${data.ventas_hoy.total_vendido.toFixed(2)}`}
          color="bg-green-100"
        />
        <StatCard
          label="Número de Tickets"
          value={data.ventas_hoy.total_tickets}
          color="bg-blue-100"
        />
        <StatCard
          label="Ticket Promedio"
          value={`$${data.ventas_hoy.ticket_promedio.toFixed(2)}`}
          color="bg-purple-100"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Top Productos */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold mb-4">Top 5 Productos</h2>
          <div className="space-y-3">
            {data.top_productos.map((p, i) => (
              <div key={i} className="flex justify-between items-center py-2 border-b">
                <div>
                  <p className="font-semibold">{p.nombre}</p>
                  <p className="text-sm text-gray-600">{p.categoria}</p>
                </div>
                <div className="text-right">
                  <p className="font-semibold">{p.unidades_vendidas}</p>
                  <p className="text-sm text-gray-600">${p.total_vendido.toFixed(2)}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Comandas Estado */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold mb-4">Estado de Comandas</h2>
          <div className="space-y-4">
            <div className="flex justify-between items-center p-4 bg-red-50 rounded">
              <span className="font-semibold">Pendiente</span>
              <span className="text-2xl font-bold text-red-600">{data.comandas_estado.pendiente}</span>
            </div>
            <div className="flex justify-between items-center p-4 bg-yellow-50 rounded">
              <span className="font-semibold">En Preparación</span>
              <span className="text-2xl font-bold text-yellow-600">{data.comandas_estado.en_preparacion}</span>
            </div>
            <div className="flex justify-between items-center p-4 bg-green-50 rounded">
              <span className="font-semibold">Listo</span>
              <span className="text-2xl font-bold text-green-600">{data.comandas_estado.listo}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Alertas de Inventario */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
        {/* Agotados */}
        {data.productos_agotados.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold mb-4 text-red-600">Productos Agotados</h2>
            <div className="space-y-2">
              {data.productos_agotados.map(p => (
                <div key={p.id} className="flex justify-between p-2 bg-red-50 rounded">
                  <span>{p.nombre}</span>
                  <span className="font-semibold text-red-600">Stock: {p.stock}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Stock Bajo */}
        {data.stock_bajo.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold mb-4 text-yellow-600">Stock Bajo</h2>
            <div className="space-y-2">
              {data.stock_bajo.map(p => (
                <div key={p.id} className="flex justify-between p-2 bg-yellow-50 rounded">
                  <span>{p.nombre}</span>
                  <span className="font-semibold text-yellow-600">Stock: {p.stock}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
