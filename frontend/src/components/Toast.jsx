import React from 'react'

export default function Toast({ type, message }) {
  const bgColor = type === 'error' ? 'bg-red-500' : type === 'success' ? 'bg-green-500' : 'bg-blue-500'
  
  return (
    <div className={`fixed bottom-8 right-8 ${bgColor} text-white px-6 py-4 rounded-lg shadow-lg animate-pulse`}>
      {message}
    </div>
  )
}
