import { useState, useEffect } from 'react'

function App() {
  const [apiStatus, setApiStatus] = useState<string>('Checking...')

  useEffect(() => {
    // Test API connection
    fetch('/api/')
      .then(res => res.json())
      .then(data => {
        setApiStatus(`Connected: ${data.message}`)
      })
      .catch(() => {
        setApiStatus('API not available')
      })
  }, [])

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="container mx-auto px-4 py-16">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-4">
            DevMaster
          </h1>
          <p className="text-xl text-gray-600 dark:text-gray-300 mb-8">
            AI-Powered Full-Stack Development Platform
          </p>
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 max-w-md mx-auto">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              API Status: {apiStatus}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App