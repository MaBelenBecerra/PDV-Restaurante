import React, { useEffect, useState } from 'react'
import { getKDS, cambiarEstadoItem } from '../api'

export default function KDS({ estacion, showToast }) {
  const [comandas, setComandas] = useState([])
  const [loading, setLoading] = useState(true)

  const estacionNames = {
    1: 'Cocina',
    2: 'Bar'
  }

  useEffect(() => {
    loadKDS()
    const interval = setInterval(loadKDS, 15000)
    return () => clearInterval(interval)
  }, [estacion])

  const loadKDS = async () => {
    try {
      const data = await getKDS(estacion)
      setComandas(data)
    } catch (error) {
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const handleChangeEstado = async (itemId, currentEstado) => {
    const estados = ['pendiente', 'en_preparacion', 'listo']
    const currentIndex = estados.indexOf(currentEstado)
    const newEstado = estados[(currentIndex + 1) % estados.length]

    try {
      await cambiarEstadoItem(itemId, newEstado)
      await loadKDS()
      showToast('success', `Item: ${newEstado}`)
    } catch (error) {
      showToast('error', error.message)
    }
  }

  const getEstadoColor = (estado) => {
    const colors = {
      'pendiente': 'bg-red-500',
      'en_preparacion': 'bg-yellow-500',
      'listo': 'bg-green-500'
    }
    return colors[estado] || 'bg-gray-500'
  }

  const getEstadoLabel = (estado) => {
    const labels = {
      'pendiente': 'PENDIENTE',
      'en_preparacion': 'EN PREP',
      'listo': 'LISTO'
    }
    return labels[estado] || estado
  }

  if (loading) {
    return (
      <div className="h-screen bg-gray-900 text-white flex items-center justify-center">
        <p className="text-3xl">Cargando {estacionNames[estacion]}...</p>
      </div>
    )
  }

  return (
    <div className="h-screen bg-gray-900 text-white p-6">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-5xl font-bold">🍳 {estacionNames[estacion]}</h1>
        <button
          onClick={loadKDS}
          className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-xl font-semibold"
        >
          ↻ Actualizar
        </button>
      </div>

      {comandas.length === 0 ? (
        <div className="flex items-center justify-center h-5/6">
          <p className="text-4xl text-gray-400">✓ Sin pendientes</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 2xl:grid-cols-3 gap-6">
          {comandas.map(comanda => (
            <div
              key={comanda.comanda_id}
              className="bg-gray-800 rounded-lg shadow-2xl border-2 border-gray-700 overflow-hidden"
            >
              {/* Header */}
              <div className="bg-gray-700 p-6 border-b-2 border-gray-600">
                <div className="flex justify-between items-start mb-2">
                  <h2 className="text-4xl font-bold text-white">#{comanda.ticket_id}</h2>
                  <span className="text-sm text-gray-300">{new Date(comanda.hora).toLocaleTimeString()}</span>
                </div>
                <p className="text-2xl text-gray-300">{comanda.mesero}</p>
              </div>

              {/* Items */}
              <div className="p-6 space-y-3 max-h-96 overflow-y-auto">
                {comanda.items.map(item => (
                  <div
                    key={item.id}
                    className={`p-4 rounded-lg transition ${
                      item.estado === 'listo'
                        ? 'bg-gray-700 opacity-50'
                        : 'bg-gray-700'
                    }`}
                  >
                    <div className="flex justify-between items-start mb-3">
                      <div>
                        <p className="text-2xl font-bold">{item.nombre}</p>
                        {item.nota && (
                          <p className="text-sm text-yellow-300 mt-1">💬 {item.nota}</p>
                        )}
                      </div>
                      <p className="text-2xl font-bold text-blue-300">x{item.cantidad}</p>
                    </div>

                    <button
                      onClick={() => handleChangeEstado(item.id, item.estado)}
                      className={`w-full px-4 py-3 rounded-lg font-bold text-white text-lg transition hover:opacity-90 ${getEstadoColor(item.estado)}`}
                    >
                      {getEstadoLabel(item.estado)}
                    </button>
                  </div>
                ))}
              </div>

              {/* Footer Stats */}
              <div className="bg-gray-700 p-4 border-t-2 border-gray-600 text-center">
                <p className="text-sm text-gray-400">
                  {comanda.items.filter(i => i.estado === 'listo').length} / {comanda.items.length} LISTOS
                </p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Auto-refresh indicator */}
      <div className="fixed bottom-6 right-6 text-gray-400 text-sm">
        Se actualiza automáticamente cada 15 segundos
      </div>
    </div>
  )
}
