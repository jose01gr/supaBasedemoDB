import { useEffect, useState } from 'react'

function App() {
  const [summary, setSummary] = useState([])
  const [pendingReview, setPendingReview] = useState([])
  const [snapshots, setSnapshots] = useState([])
  const [comparisonResults, setComparisonResults] = useState([])
  const [selectedStatus, setSelectedStatus] = useState('ALL')
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')

  useEffect(() => {
   Promise.all([
      fetch('http://127.0.0.1:8000/summary').then((response) => response.json()),
      fetch('http://127.0.0.1:8000/pending-review').then((response) => response.json()),
      fetch('http://127.0.0.1:8000/snapshots').then((response) => response.json()),
      fetch('http://127.0.0.1:8000/comparison-results').then((response) => response.json()),
    ])
      .then(([summaryData, pendingData, snapshotsData, comparisonData]) => {
        setSummary(summaryData)
        setPendingReview(pendingData)
        setSnapshots(snapshotsData)
        setComparisonResults(comparisonData)
        setLoading(false)
      })
      .catch((error) => {
        console.error('Error loading dashboard data:', error)
        setLoading(false)
      })
  }, [])

  const getValue = (metric) => {
    return summary.find((item) => item.metric === metric)?.value ?? '-'
  }

  const downloadReport = (reportType) => {
  window.open(`http://127.0.0.1:8000/reports/${reportType}`, '_blank')
}

const createSnapshot = async () => {
  const response = await fetch('http://127.0.0.1:8000/snapshots', {
    method: 'POST',
  })

  const newSnapshot = await response.json()

  setSnapshots((currentSnapshots) => [
    newSnapshot,
    ...currentSnapshots,
  ])
}

  const filteredPendingReview = pendingReview.filter((customer) => {
  const search = searchTerm.toLowerCase()

  return (
    customer.sellercloud_customer_id?.toLowerCase().includes(search) ||
    customer.sellercloud_name?.toLowerCase().includes(search) ||
    customer.sellercloud_email?.toLowerCase().includes(search) ||
    customer.sales_man?.toLowerCase().includes(search) ||
    customer.phone_1?.toLowerCase().includes(search)
  )
})

const filteredComparisonResults = comparisonResults.filter((customer) => {
  if (selectedStatus === 'ALL') {
    return true
  }

  return customer.match_status === selectedStatus
})

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
              <SummaryCard title="Sellercloud customers" value={getValue('Sellercloud customers')} />
              <SummaryCard title="Bigin active contacts" value={getValue('Bigin active contacts')} />
              <SummaryCard title="Pending review" value={getValue('Pending review')} />
            </div>

            <div className="mt-6 rounded-2xl bg-white p-6 shadow-sm">
              <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                <div>
                  <h2 className="text-xl font-semibold">Excel reports</h2>
                  <p className="text-sm text-slate-500">
                    Descarga reportes filtrados para revisión o análisis.
                  </p>
                </div>
              </div>

              <div className="mt-5 grid gap-3 md:grid-cols-3">
                <ReportButton
                  label="Sellercloud customers"
                  reportType="sellercloud-customers"
                  downloadReport={downloadReport}
                />
                <ReportButton
                  label="Bigin active contacts"
                  reportType="bigin-active-contacts"
                  downloadReport={downloadReport}
                />
                <ReportButton
                  label="Email and name match"
                  reportType="email-and-name-match"
                  downloadReport={downloadReport}
                />
                <ReportButton
                  label="Email match, name different"
                  reportType="email-match-name-different"
                  downloadReport={downloadReport}
                />
                <ReportButton
                  label="Name match, email different"
                  reportType="name-match-email-different"
                  downloadReport={downloadReport}
                />
                <ReportButton
                  label="Pending review"
                  reportType="pending-review"
                  downloadReport={downloadReport}
                />
              </div>
            </div>

            <div className="mt-6 rounded-2xl bg-white p-6 shadow-sm">
              <h2 className="text-xl font-semibold">Match results</h2>

              <div className="mt-4 grid gap-4 md:grid-cols-3">
                <MiniCard title="Email and name match" value={getValue('Email and name match')} />
                <MiniCard title="Email match, name different" value={getValue('Email match, name different')} />
                <MiniCard title="Name match, email different" value={getValue('Name match, email different')} />
              </div>
              <div className="mt-5 flex flex-wrap gap-2">
                <StatusButton
                  label="All"
                  status="ALL"
                  selectedStatus={selectedStatus}
                  setSelectedStatus={setSelectedStatus}
                />
                <StatusButton
                  label="Email + Name"
                  status="EMAIL_AND_NAME_MATCH"
                  selectedStatus={selectedStatus}
                  setSelectedStatus={setSelectedStatus}
                />
                <StatusButton
                  label="Email match / Name different"
                  status="EMAIL_MATCH_NAME_DIFFERENT"
                  selectedStatus={selectedStatus}
                  setSelectedStatus={setSelectedStatus}
                />
                <StatusButton
                  label="Name match / Email different"
                  status="NAME_MATCH_EMAIL_DIFFERENT"
                  selectedStatus={selectedStatus}
                  setSelectedStatus={setSelectedStatus}
                />
                <StatusButton
                  label="No match"
                  status="NO_MATCH_IN_BIGIN"
                  selectedStatus={selectedStatus}
                  setSelectedStatus={setSelectedStatus}
                />
              </div>
            </div>

            <div className="mt-6 rounded-2xl bg-white p-6 shadow-sm">
              <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                <div>
                  <h2 className="text-xl font-semibold">Comparison results</h2>
                  <p className="text-sm text-slate-500">
                    Resultados filtrados por estado de coincidencia.
                  </p>
                </div>

                <div className="rounded-full bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700">
                  {filteredComparisonResults.length} registros
                </div>
              </div>

              <div className="mt-5 overflow-hidden rounded-xl border border-slate-200">
                <div className="max-h-[360px] overflow-auto">
                  <table className="min-w-full divide-y divide-slate-200 text-sm">
                    <thead className="sticky top-0 bg-slate-50">
                      <tr>
                        <TableHead>ID</TableHead>
                        <TableHead>Sellercloud Name</TableHead>
                        <TableHead>Sellercloud Email</TableHead>
                        <TableHead>Bigin Name</TableHead>
                        <TableHead>Bigin Email</TableHead>
                        <TableHead>Status</TableHead>
                      </tr>
                    </thead>

                    <tbody className="divide-y divide-slate-100 bg-white">
                      {filteredComparisonResults.map((customer) => (
                        <tr key={`${customer.sellercloud_customer_id}-${customer.match_status}`} className="hover:bg-slate-50">
                          <TableCell>{customer.sellercloud_customer_id}</TableCell>
                          <TableCell>{customer.sellercloud_name}</TableCell>
                          <TableCell>{customer.sellercloud_email}</TableCell>
                          <TableCell>
                            {customer.bigin_name_email || customer.bigin_name_match || '-'}
                          </TableCell>
                          <TableCell>
                            {customer.bigin_email_match || customer.bigin_email_name_match || '-'}
                          </TableCell>
                          <TableCell>{customer.match_status}</TableCell>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            <div className="mt-6 rounded-2xl bg-white p-6 shadow-sm">
              <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                <div>
                  <h2 className="text-xl font-semibold">Pending review</h2>
                  <p className="text-sm text-slate-500">
                    Clientes de Sellercloud sin match claro en Bigin.
                  </p>
                </div>

                <div className="rounded-full bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700">
                  {filteredPendingReview.length} de {pendingReview.length} registros
                </div>
              </div>

              <div className="mt-4">
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(event) => setSearchTerm(event.target.value)}
                  placeholder="Buscar por nombre, email, vendedor, teléfono o ID..."
                  className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none transition focus:border-slate-400 focus:ring-2 focus:ring-slate-200"
                />
              </div>

              <div className="mt-5 overflow-hidden rounded-xl border border-slate-200">
                <div className="max-h-[420px] overflow-auto">
                  <table className="min-w-full divide-y divide-slate-200 text-sm">
                    <thead className="sticky top-0 bg-slate-50">
                      <tr>
                        <TableHead>ID</TableHead>
                        <TableHead>Cliente</TableHead>
                        <TableHead>Email</TableHead>
                        <TableHead>Vendedor</TableHead>
                        <TableHead>Teléfono</TableHead>
                      </tr>
                    </thead>

                    <tbody className="divide-y divide-slate-100 bg-white">
                      {filteredPendingReview.map((customer) => (
                        <tr
                          key={customer.sellercloud_customer_id}
                          className="hover:bg-slate-50"
                        >
                          <TableCell>{customer.sellercloud_customer_id}</TableCell>
                          <TableCell>{customer.sellercloud_name}</TableCell>
                          <TableCell>{customer.sellercloud_email}</TableCell>
                          <TableCell>{customer.sales_man || '-'}</TableCell>
                          <TableCell>{customer.phone_1 || '-'}</TableCell>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
                        <div className="mt-6 rounded-2xl bg-white p-6 shadow-sm">
              <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                <div>
                  <h2 className="text-xl font-semibold">Snapshots</h2>
                  <p className="text-sm text-slate-500">
                    Histórico de comparaciones guardadas.
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={createSnapshot}
                    className="rounded-full bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-700"
                  >
                    Create snapshot
                  </button>

                  <div className="rounded-full bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700">
                    {snapshots.length} snapshots
                  </div>
                </div>
              </div>

              <div className="mt-5 overflow-hidden rounded-xl border border-slate-200">
                <table className="min-w-full divide-y divide-slate-200 text-sm">
                  <thead className="bg-slate-50">
                    <tr>
                      <TableHead>ID</TableHead>
                      <TableHead>Nombre</TableHead>
                      <TableHead>Sellercloud</TableHead>
                      <TableHead>Bigin</TableHead>
                      <TableHead>Match exacto</TableHead>
                      <TableHead>Pendientes</TableHead>
                      <TableHead>Fecha</TableHead>
                    </tr>
                  </thead>

                  <tbody className="divide-y divide-slate-100 bg-white">
                    {snapshots.map((snapshot) => (
                      <tr key={snapshot.id} className="hover:bg-slate-50">
                        <TableCell>{snapshot.id}</TableCell>
                        <TableCell>{snapshot.snapshot_name}</TableCell>
                        <TableCell>{snapshot.total_sellercloud_customers}</TableCell>
                        <TableCell>{snapshot.total_bigin_contacts}</TableCell>
                        <TableCell>{snapshot.email_and_name_match}</TableCell>
                        <TableCell>{snapshot.pending_review}</TableCell>
                        <TableCell>
                          {new Date(snapshot.created_at).toLocaleString()}
                        </TableCell>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function SummaryCard({ title, value }) {
  return (
    <div className="rounded-2xl bg-white p-6 shadow-sm">
      <p className="text-sm text-slate-500">{title}</p>
      <p className="mt-2 text-3xl font-bold">{value}</p>
    </div>
  )
}

function MiniCard({ title, value }) {
  return (
    <div className="rounded-xl border border-slate-200 p-4">
      <p className="text-sm text-slate-500">{title}</p>
      <p className="mt-2 text-2xl font-bold">{value}</p>
    </div>
  )
}

function TableHead({ children }) {
  return (
    <th className="whitespace-nowrap px-4 py-3 text-left font-semibold text-slate-700">
      {children}
    </th>
  )
}

function TableCell({ children }) {
  return (
    <td className="whitespace-nowrap px-4 py-3 text-slate-700">
      {children}
    </td>
  )
}

function StatusButton({ label, status, selectedStatus, setSelectedStatus }) {
  const isActive = selectedStatus === status

  return (
    <button
      onClick={() => setSelectedStatus(status)}
      className={`rounded-full px-4 py-2 text-sm font-medium transition ${
        isActive
          ? 'bg-slate-900 text-white'
          : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
      }`}
    >
      {label}
    </button>
  )
}

function ReportButton({ label, reportType, downloadReport }) {
  return (
    <button
      onClick={() => downloadReport(reportType)}
      className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-left text-sm font-medium text-slate-700 transition hover:bg-slate-50 hover:shadow-sm"
    >
      Download {label}
    </button>
  )
}

export default App