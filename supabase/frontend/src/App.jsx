import { useEffect, useState } from 'react'

function App() {
  const [summary, setSummary] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('http://127.0.0.1:8000/summary')
      .then((response) => response.json())
      .then((data) => {
        setSummary(data)
        setLoading(false)
      })
      .catch((error) => {
        console.error('Error loading summary:', error)
        setLoading(false)
      })
  }, [])

  const getValue = (metric) => {
    return summary.find((item) => item.metric === metric)?.value ?? '-'
  }

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900">
      <div className="mx-auto max-w-7xl px-6 py-8">
        <div className="mb-8">
          <p className="text-sm font-medium text-slate-500">
            Demo técnica empresarial
          </p>
          <h1 className="mt-2 text-3xl font-bold">
            Customer Data Hub
          </h1>
          <p className="mt-2 text-slate-600">
            Comparación centralizada entre Sellercloud y Bigin.
          </p>
        </div>

        {loading ? (
          <div className="rounded-2xl bg-white p-6 shadow-sm">
            Cargando datos...
          </div>
        ) : (
          <>
            <div className="grid gap-4 md:grid-cols-3">
              <div className="rounded-2xl bg-white p-6 shadow-sm">
                <p className="text-sm text-slate-500">Sellercloud customers</p>
                <p className="mt-2 text-3xl font-bold">
                  {getValue('Sellercloud customers')}
                </p>
              </div>

              <div className="rounded-2xl bg-white p-6 shadow-sm">
                <p className="text-sm text-slate-500">Bigin active contacts</p>
                <p className="mt-2 text-3xl font-bold">
                  {getValue('Bigin active contacts')}
                </p>
              </div>

              <div className="rounded-2xl bg-white p-6 shadow-sm">
                <p className="text-sm text-slate-500">Pending review</p>
                <p className="mt-2 text-3xl font-bold">
                  {getValue('Pending review')}
                </p>
              </div>
            </div>

            <div className="mt-6 rounded-2xl bg-white p-6 shadow-sm">
              <h2 className="text-xl font-semibold">Match results</h2>

              <div className="mt-4 grid gap-4 md:grid-cols-3">
                <div className="rounded-xl border border-slate-200 p-4">
                  <p className="text-sm text-slate-500">Email and name match</p>
                  <p className="mt-2 text-2xl font-bold">
                    {getValue('Email and name match')}
                  </p>
                </div>

                <div className="rounded-xl border border-slate-200 p-4">
                  <p className="text-sm text-slate-500">
                    Email match, name different
                  </p>
                  <p className="mt-2 text-2xl font-bold">
                    {getValue('Email match, name different')}
                  </p>
                </div>

                <div className="rounded-xl border border-slate-200 p-4">
                  <p className="text-sm text-slate-500">
                    Name match, email different
                  </p>
                  <p className="mt-2 text-2xl font-bold">
                    {getValue('Name match, email different')}
                  </p>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default App