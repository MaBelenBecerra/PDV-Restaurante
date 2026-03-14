import React, { useState } from 'react'
import Dashboard from './pages/Dashboard'
import Catalogo from './pages/Catalogo'
import Inventario from './pages/Inventario'
import PDV from './pages/PDV'
import KDS from './pages/KDS'
import Toast from './components/Toast'

export default function App() {
  const [currentPage, setCurrentPage] = useState('dashboard')
  const [toast, setToast] = useState(null)

  const showToast = (type, message) => {
    setToast({ type, message })
    setTimeout(() => setToast(null), 3000)
  }

  const menuItems = [
    { id: 'dashboard', label: '🏠 Dashboard', icon: '📊' },
    { id: 'catalogo', label: '🛍️ Catálogo', icon: '📦' },
    { id: 'inventario', label: '📦 Inventario', icon: '📋' },
    { id: 'pdv', label: '🧾 PDV', icon: '💳' },
    { id: 'cocina', label: '👨‍🍳 Cocina', icon: '🔥' },
    { id: 'bar', label: '🍸 Bar', icon: '🍹' },
  ]

  const renderPage = () => {
    switch (currentPage) {
      case 'dashboard':
        return <Dashboard showToast={showToast} />
      case 'catalogo':
        return <Catalogo showToast={showToast} />
      case 'inventario':
        return <Inventario showToast={showToast} />
      case 'pdv':
        return <PDV showToast={showToast} />
      case 'cocina':
        return <KDS estacion={1} showToast={showToast} />
      case 'bar':
        return <KDS estacion={2} showToast={showToast} />
      default:
        return <Dashboard showToast={showToast} />
    }
  }

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="w-64 bg-gray-800 text-white shadow-lg flex flex-col">
        <div className="p-6 border-b border-gray-700">
          <h1 className="text-2xl font-bold">🍽️ PDV Restaurante</h1>
        </div>
        
        <nav className="flex-1 p-4">
          {menuItems.map(item => (
            <button
              key={item.id}
              onClick={() => setCurrentPage(item.id)}
              className={`w-full text-left px-4 py-3 rounded-lg transition-colors mb-2 ${
                currentPage === item.id
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-300 hover:bg-gray-700'
              }`}
            >
              {item.label}
            </button>
          ))}
        </nav>

        <div className="p-4 border-t border-gray-700">
          <p className="text-xs text-gray-400">v1.0.0</p>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        <div className="flex-1 overflow-auto">
          {renderPage()}
        </div>
      </div>

      {/* Toast */}
      {toast && <Toast type={toast.type} message={toast.message} />}
    </div>
  )
}
