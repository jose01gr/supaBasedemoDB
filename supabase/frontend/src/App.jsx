import { useEffect, useRef, useState } from 'react'

const API = 'http://127.0.0.1:8000'

function formatRelativeTime(isoString) {
  if (!isoString) return 'Nunca'
  const diff = Date.now() - new Date(isoString).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'hace un momento'
  if (mins < 60) return `hace ${mins} min`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `hace ${hours}h`
  return `hace ${Math.floor(hours / 24)}d`
}

function App() {
  const [summary, setSummary] = useState([])
  const [pendingReview, setPendingReview] = useState([])
  const [snapshots, setSnapshots] = useState([])
  const [comparisonResults, setComparisonResults] = useState([])
  const [selectedStatus, setSelectedStatus] = useState('ALL')
  const [excludedStatuses, setExcludedStatuses] = useState(new Set())
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [syncStatus, setSyncStatus] = useState(null)
  const [syncLogs, setSyncLogs] = useState([])
  const [biginWithoutScId, setBiginWithoutScId] = useState([])
  const [searchBiginNoSc, setSearchBiginNoSc] = useState('')
  const syncPollRef = useRef(null)

  const loadDashboardData = async () => {
    const [summaryData, pendingData, snapshotsData, comparisonData, biginNoScData] = await Promise.all([
      fetch(`${API}/summary`).then((r) => r.json()),
      fetch(`${API}/pending-review`).then((r) => r.json()),
      fetch(`${API}/snapshots`).then((r) => r.json()),
      fetch(`${API}/comparison-results`).then((r) => r.json()),
      fetch(`${API}/bigin-without-scid`).then((r) => r.json()),
    ])
    setSummary(summaryData)
    setPendingReview(pendingData)
    setSnapshots(snapshotsData)
    setComparisonResults(comparisonData)
    setBiginWithoutScId(biginNoScData)
  }

  const loadSyncStatus = () => {
    Promise.all([
      fetch(`${API}/sync/status`).then((r) => r.json()),
      fetch(`${API}/sync/logs`).then((r) => r.json()),
    ])
      .then(([statusData, logsData]) => {
        const wasRunning =
          syncStatus?.sellercloud?.status === 'running' ||
          syncStatus?.bigin?.status === 'running'
        const nowIdle =
          statusData.sellercloud.status !== 'running' &&
          statusData.bigin.status !== 'running'

        setSyncStatus(statusData)
        setSyncLogs(logsData)

        if (wasRunning && nowIdle) {
          loadDashboardData()
        }
      })
      .catch(console.error)
  }

  useEffect(() => {
    loadDashboardData()
      .catch((err) => console.error('Error loading dashboard:', err))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    loadSyncStatus()
  }, [])

  useEffect(() => {
    clearInterval(syncPollRef.current)
    const isRunning =
      syncStatus?.sellercloud?.status === 'running' ||
      syncStatus?.bigin?.status === 'running'
    const interval = isRunning ? 4000 : 60000
    syncPollRef.current = setInterval(loadSyncStatus, interval)
    return () => clearInterval(syncPollRef.current)
  }, [syncStatus?.sellercloud?.status, syncStatus?.bigin?.status])

  const triggerSync = async (source) => {
    const url = source === 'all' ? `${API}/sync/all` : `${API}/sync/${source}`
    await fetch(url, { method: 'POST' })
    setTimeout(loadSyncStatus, 500)
  }

  const getValue = (metric) =>
    summary.find((item) => item.metric === metric)?.value ?? '-'

  const downloadReport = (reportType) =>
    window.open(`${API}/reports/${reportType}`, '_blank')

  const createSnapshot = async () => {
    const response = await fetch(`${API}/snapshots`, { method: 'POST' })
    const newSnapshot = await response.json()
    setSnapshots((current) => [newSnapshot, ...current])
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

  const toggleExclude = (status) => {
    setExcludedStatuses((prev) => {
      const next = new Set(prev)
      if (next.has(status)) next.delete(status)
      else next.add(status)
      return next
    })
  }

  const filteredComparisonResults = comparisonResults.filter((customer) => {
    if (selectedStatus !== 'ALL') return customer.match_status === selectedStatus
    if (excludedStatuses.size > 0) return !excludedStatuses.has(customer.match_status)
    return true
  })

  const scStatus = syncStatus?.sellercloud
  const biginStatus = syncStatus?.bigin

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900">
      <div className="mx-auto max-w-7xl px-6 py-8">
        <div className="mb-8">
          <p className="text-sm font-medium text-slate-500">Demo técnica empresarial</p>
          <h1 className="mt-2 text-3xl font-bold">Customer Data Hub</h1>
          <p className="mt-2 text-slate-600">
            Comparación centralizada entre Sellercloud y Bigin.
          </p>
        </div>

        {/* ── Sync panel ── */}
        <div className="mb-6 rounded-2xl bg-white p-6 shadow-sm">
          <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
            <div>
              <h2 className="text-xl font-semibold">Sincronización de datos</h2>
              <p className="text-sm text-slate-500">
                Actualización automática cada 6 horas. También puedes sincronizar manualmente.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <SyncButton
                label="Sincronizar SellerCloud"
                running={scStatus?.status === 'running'}
                onClick={() => triggerSync('sellercloud')}
              />
              <SyncButton
                label="Sincronizar Bigin"
                running={biginStatus?.status === 'running'}
                onClick={() => triggerSync('bigin')}
              />
              <SyncButton
                label="Sincronizar todo"
                running={scStatus?.status === 'running' || biginStatus?.status === 'running'}
                onClick={() => triggerSync('all')}
                primary
              />
            </div>
          </div>

          <div className="mt-5 grid gap-4 md:grid-cols-2">
            <SyncStatusCard
              title="SellerCloud"
              status={scStatus?.status ?? 'idle'}
              lastSync={scStatus?.last_completed_at}
              records={scStatus?.last_records_updated}
              error={scStatus?.last_error}
            />
            <SyncStatusCard
              title="Bigin (clientes activos)"
              status={biginStatus?.status ?? 'idle'}
              lastSync={biginStatus?.last_completed_at}
              records={biginStatus?.last_records_updated}
              error={biginStatus?.last_error}
            />
          </div>

          {syncLogs.length > 0 && (
            <div className="mt-5">
              <p className="mb-2 text-sm font-medium text-slate-600">Historial reciente</p>
              <div className="overflow-hidden rounded-xl border border-slate-200">
                <table className="min-w-full divide-y divide-slate-200 text-xs">
                  <thead className="bg-slate-50">
                    <tr>
                      <TableHead>Fuente</TableHead>
                      <TableHead>Inicio</TableHead>
                      <TableHead>Duración</TableHead>
                      <TableHead>Registros</TableHead>
                      <TableHead>Estado</TableHead>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 bg-white">
                    {syncLogs.slice(0, 6).map((log) => {
                      const duration =
                        log.completed_at && log.started_at
                          ? Math.round(
                              (new Date(log.completed_at) - new Date(log.started_at)) / 1000
                            ) + 's'
                          : '—'
                      return (
                        <tr key={log.id} className="hover:bg-slate-50">
                          <TableCell>{log.source}</TableCell>
                          <TableCell>{new Date(log.started_at).toLocaleString()}</TableCell>
                          <TableCell>{duration}</TableCell>
                          <TableCell>{log.records_updated ?? '—'}</TableCell>
                          <TableCell>
                            <StatusBadge status={log.status} />
                          </TableCell>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {loading ? (
          <div className="rounded-2xl bg-white p-6 shadow-sm">Cargando datos...</div>
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
                <ReportButton label="Sellercloud customers" reportType="sellercloud-customers" downloadReport={downloadReport} />
                <ReportButton label="Bigin active contacts" reportType="bigin-active-contacts" downloadReport={downloadReport} />
                <ReportButton label="Email and name match" reportType="email-and-name-match" downloadReport={downloadReport} />
                <ReportButton label="Email match, name different" reportType="email-match-name-different" downloadReport={downloadReport} />
                <ReportButton label="Name match, email different" reportType="name-match-email-different" downloadReport={downloadReport} />
                <ReportButton label="Pending review" reportType="pending-review" downloadReport={downloadReport} />
              </div>
            </div>

            <div className="mt-6 rounded-2xl bg-white p-6 shadow-sm">
              <h2 className="text-xl font-semibold">Match results</h2>
              <div className="mt-4 grid gap-4 md:grid-cols-4">
                <MiniCard title="Email and name match" value={getValue('Email and name match')} />
                <MiniCard title="Email match, name different" value={getValue('Email match, name different')} />
                <MiniCard title="Name match, email different" value={getValue('Name match, email different')} />
                <MiniCard title="SC ID match" value={getValue('SC ID match')} />
              </div>

              <div className="mt-5">
                <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-400">Mostrar solo</p>
                <div className="flex flex-wrap gap-2">
                  <StatusButton label="Todos" status="ALL" selectedStatus={selectedStatus} setSelectedStatus={setSelectedStatus} />
                  <StatusButton label="Email + Nombre" status="EMAIL_AND_NAME_MATCH" selectedStatus={selectedStatus} setSelectedStatus={setSelectedStatus} />
                  <StatusButton label="Email / Nombre diferente" status="EMAIL_MATCH_NAME_DIFFERENT" selectedStatus={selectedStatus} setSelectedStatus={setSelectedStatus} />
                  <StatusButton label="Nombre / Email diferente" status="NAME_MATCH_EMAIL_DIFFERENT" selectedStatus={selectedStatus} setSelectedStatus={setSelectedStatus} />
                  <StatusButton label="SC ID match" status="SC_ID_MATCH" selectedStatus={selectedStatus} setSelectedStatus={setSelectedStatus} />
                  <StatusButton label="Sin match" status="NO_MATCH_IN_BIGIN" selectedStatus={selectedStatus} setSelectedStatus={setSelectedStatus} />
                </div>
              </div>

              {selectedStatus === 'ALL' && (
                <div className="mt-4">
                  <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-400">Excluir de la lista</p>
                  <div className="flex flex-wrap gap-2">
                    <ExcludeButton label="Email + Nombre" status="EMAIL_AND_NAME_MATCH" excludedStatuses={excludedStatuses} toggleExclude={toggleExclude} />
                    <ExcludeButton label="Email / Nombre diferente" status="EMAIL_MATCH_NAME_DIFFERENT" excludedStatuses={excludedStatuses} toggleExclude={toggleExclude} />
                    <ExcludeButton label="Nombre / Email diferente" status="NAME_MATCH_EMAIL_DIFFERENT" excludedStatuses={excludedStatuses} toggleExclude={toggleExclude} />
                    <ExcludeButton label="SC ID match" status="SC_ID_MATCH" excludedStatuses={excludedStatuses} toggleExclude={toggleExclude} />
                    <ExcludeButton label="Sin match" status="NO_MATCH_IN_BIGIN" excludedStatuses={excludedStatuses} toggleExclude={toggleExclude} />
                    {excludedStatuses.size > 0 && (
                      <button
                        onClick={() => setExcludedStatuses(new Set())}
                        className="rounded-full border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-medium text-red-600 transition hover:bg-red-100"
                      >
                        Limpiar exclusiones
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>

            <div className="mt-6 rounded-2xl bg-white p-6 shadow-sm">
              <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                <div>
                  <h2 className="text-xl font-semibold">Comparison results</h2>
                  <p className="text-sm text-slate-500">Resultados filtrados por estado de coincidencia.</p>
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
                        <TableHead>SC ID (Bigin)</TableHead>
                        <TableHead>Status</TableHead>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 bg-white">
                      {filteredComparisonResults.map((customer) => (
                        <tr key={`${customer.sellercloud_customer_id}-${customer.match_status}`} className="hover:bg-slate-50">
                          <TableCell>{customer.sellercloud_customer_id}</TableCell>
                          <TableCell>{customer.sellercloud_name}</TableCell>
                          <TableCell>{customer.sellercloud_email}</TableCell>
                          <TableCell>{customer.bigin_name_email || customer.bigin_name_match || customer.bigin_name_scid || '-'}</TableCell>
                          <TableCell>{customer.bigin_email_match || customer.bigin_email_name_match || customer.bigin_email_scid || '-'}</TableCell>
                          <TableCell>{customer.bigin_registered_scid || '-'}</TableCell>
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
                  <p className="text-sm text-slate-500">Clientes de Sellercloud sin match claro en Bigin.</p>
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
                        <tr key={customer.sellercloud_customer_id} className="hover:bg-slate-50">
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
                  <h2 className="text-xl font-semibold">Bigin sin SellerCloud ID</h2>
                  <p className="text-sm text-slate-500">
                    Clientes activos de Bigin que no tienen el SC Client ID registrado.
                  </p>
                </div>
                <div className="rounded-full bg-orange-100 px-4 py-2 text-sm font-medium text-orange-700">
                  {biginWithoutScId.length} sin SC ID
                </div>
              </div>

              <div className="mt-4">
                <input
                  type="text"
                  value={searchBiginNoSc}
                  onChange={(e) => setSearchBiginNoSc(e.target.value)}
                  placeholder="Buscar por nombre, email o dueño..."
                  className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none transition focus:border-slate-400 focus:ring-2 focus:ring-slate-200"
                />
              </div>

              <div className="mt-4 overflow-hidden rounded-xl border border-slate-200">
                <div className="max-h-[360px] overflow-auto">
                  <table className="min-w-full divide-y divide-slate-200 text-sm">
                    <thead className="sticky top-0 bg-slate-50">
                      <tr>
                        <TableHead>Bigin ID</TableHead>
                        <TableHead>Nombre</TableHead>
                        <TableHead>Email</TableHead>
                        <TableHead>Teléfono</TableHead>
                        <TableHead>Dueño</TableHead>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 bg-white">
                      {biginWithoutScId
                        .filter((c) => {
                          const s = searchBiginNoSc.toLowerCase()
                          return (
                            !s ||
                            c.full_name?.toLowerCase().includes(s) ||
                            c.email?.toLowerCase().includes(s) ||
                            c.owner_name?.toLowerCase().includes(s)
                          )
                        })
                        .map((c) => (
                          <tr key={c.bigin_contact_id} className="hover:bg-slate-50">
                            <TableCell>{c.bigin_contact_id}</TableCell>
                            <TableCell>{c.full_name || '-'}</TableCell>
                            <TableCell>{c.email || '-'}</TableCell>
                            <TableCell>{c.phone || c.mobile || '-'}</TableCell>
                            <TableCell>{c.owner_name || '-'}</TableCell>
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
                  <p className="text-sm text-slate-500">Histórico de comparaciones guardadas.</p>
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
                        <TableCell>{new Date(snapshot.created_at).toLocaleString()}</TableCell>
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

// ── UI components ─────────────────────────────────────────────────────────────

function SyncStatusCard({ title, status, lastSync, records, error }) {
  const statusColors = {
    idle: 'bg-slate-100 text-slate-600',
    running: 'bg-blue-100 text-blue-700',
    success: 'bg-green-100 text-green-700',
    error: 'bg-red-100 text-red-700',
  }
  const statusLabels = {
    idle: 'Sin sincronizar',
    running: 'Sincronizando...',
    success: 'Actualizado',
    error: 'Error',
  }

  return (
    <div className="rounded-xl border border-slate-200 p-4">
      <div className="flex items-center justify-between">
        <p className="font-medium text-slate-800">{title}</p>
        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusColors[status] ?? statusColors.idle}`}>
          {statusLabels[status] ?? status}
        </span>
      </div>
      <p className="mt-2 text-sm text-slate-500">
        Última sync: <span className="font-medium text-slate-700">{formatRelativeTime(lastSync)}</span>
      </p>
      {records != null && (
        <p className="text-sm text-slate-500">
          Registros: <span className="font-medium text-slate-700">{records.toLocaleString()}</span>
        </p>
      )}
      {error && (
        <p className="mt-1 truncate text-xs text-red-600" title={error}>
          {error}
        </p>
      )}
    </div>
  )
}

function SyncButton({ label, running, onClick, primary }) {
  return (
    <button
      onClick={onClick}
      disabled={running}
      className={`rounded-full px-4 py-2 text-sm font-medium transition disabled:opacity-50 ${
        primary
          ? 'bg-slate-900 text-white hover:bg-slate-700'
          : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
      }`}
    >
      {running ? 'Sincronizando...' : label}
    </button>
  )
}

function StatusBadge({ status }) {
  const colors = {
    running: 'bg-blue-100 text-blue-700',
    success: 'bg-green-100 text-green-700',
    error: 'bg-red-100 text-red-700',
  }
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${colors[status] ?? 'bg-slate-100 text-slate-600'}`}>
      {status}
    </span>
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
  return <td className="whitespace-nowrap px-4 py-3 text-slate-700">{children}</td>
}

function StatusButton({ label, status, selectedStatus, setSelectedStatus }) {
  const isActive = selectedStatus === status
  return (
    <button
      onClick={() => setSelectedStatus(status)}
      className={`rounded-full px-4 py-2 text-sm font-medium transition ${
        isActive ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
      }`}
    >
      {label}
    </button>
  )
}

function ExcludeButton({ label, status, excludedStatuses, toggleExclude }) {
  const isExcluded = excludedStatuses.has(status)
  return (
    <button
      onClick={() => toggleExclude(status)}
      className={`rounded-full px-4 py-2 text-sm font-medium transition ${
        isExcluded
          ? 'bg-red-100 text-red-700 line-through'
          : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
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
