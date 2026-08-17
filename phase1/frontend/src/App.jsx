import React, { useState, useEffect } from 'react'

const API = '/api'

export default function App() {
  const [tab, setTab] = useState('dashboard')
  const [data, setData] = useState({ dashboard: null, exceptions: [], notifications: [], decisions: [] })
  const [selected, setSelected] = useState(null)
  const [filters, setFilters] = useState({ type: '', severity: '', status: '' })

  useEffect(() => { loadAll() }, [])

  const loadAll = async () => {
    try {
      const [dash, exc, notif, dec] = await Promise.all([
        fetch(`${API}/dashboard`).then(r => r.json()),
        fetch(`${API}/exceptions`).then(r => r.json()),
        fetch(`${API}/notifications`).then(r => r.json()),
        fetch(`${API}/decisions`).then(r => r.json()),
      ])
      setData({ dashboard: dash, exceptions: exc.exceptions || [], notifications: notif.notifications || [], decisions: dec.decisions || [] })
    } catch (err) { console.error(err) }
  }

  const handleAssign = async (id) => {
    const name = prompt('Assign to:')
    if (name) {
      await fetch(`${API}/exceptions/${id}/assign`, {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ assigned_to: name })
      })
      loadAll()
    }
  }

  const handleResolve = async (id) => {
    if (confirm('Resolve this exception?')) {
      await fetch(`${API}/exceptions/${id}/resolve`, {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({})
      })
      setSelected(null)
      loadAll()
    }
  }

  const handleDecision = async (excId, decision) => {
    await fetch(`${API}/decisions`, {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ exception_id: excId, decision, decided_by: 'Coordinator' })
    })
    loadAll()
  }

  const handleDetect = async () => {
    const res = await fetch(`${API}/detect`, { method: 'POST' })
    const data = await res.json()
    alert(`Scanned ${data.containers_scanned} containers, found ${data.new_exceptions} new exceptions`)
    loadAll()
  }

  const filtered = data.exceptions.filter(e => {
    if (filters.type && e.exception_type !== filters.type) return false
    if (filters.severity && e.severity !== filters.severity) return false
    if (filters.status && e.status !== filters.status) return false
    return true
  })

  const s = data.dashboard?.summary || {}

  return (
    <div className="app">
      <nav className="sidebar">
        <h1>Kratos</h1>
        <p>Phase 1 - Foundation</p>
        <ul className="nav-links">
          {['dashboard', 'exceptions', 'notifications', 'decisions'].map(t => (
            <li key={t} className={tab === t ? 'active' : ''} onClick={() => setTab(t)}>
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </li>
          ))}
        </ul>
      </nav>

      <main className="content">
        {tab === 'dashboard' && (
          <>
            <div className="stats">
              <div className="stat"><h3>Containers</h3><div className="value">{s.total_containers || 0}</div></div>
              <div className="stat"><h3>Exceptions</h3><div className="value">{s.total_exceptions || 0}</div></div>
              <div className="stat"><h3>Open</h3><div className="value">{s.open_exceptions || 0}</div></div>
              <div className="stat"><h3>High Risk</h3><div className="value" style={{color:'#e53e3e'}}>{s.high_risk || 0}</div></div>
            </div>
            <div className="card">
              <h2>Exception by Type</h2>
              <table>
                <thead><tr><th>Type</th><th>Count</th></tr></thead>
                <tbody>
                  {Object.entries(data.dashboard?.by_type || {}).map(([t, c]) => (
                    <tr key={t}><td>{t}</td><td>{c}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}

        {tab === 'exceptions' && (
          <div className="card">
            <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:'16px'}}>
              <h2>Exceptions</h2>
              <button className="btn btn-primary" onClick={handleDetect}>Run Detection</button>
            </div>
            <div className="filters">
              <select value={filters.type} onChange={e => setFilters({...filters, type: e.target.value})}>
                <option value="">All Types</option>
                <option value="delay">Delay</option>
                <option value="damage">Damage</option>
                <option value="customs_hold">Customs Hold</option>
                <option value="misroute">Misroute</option>
              </select>
              <select value={filters.severity} onChange={e => setFilters({...filters, severity: e.target.value})}>
                <option value="">All Severity</option>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
              <select value={filters.status} onChange={e => setFilters({...filters, status: e.target.value})}>
                <option value="">All Status</option>
                <option value="detected">Detected</option>
                <option value="diagnosed">Diagnosed</option>
                <option value="resolved">Resolved</option>
              </select>
            </div>
            <table>
              <thead>
                <tr><th>ID</th><th>Container</th><th>Type</th><th>Severity</th><th>Risk</th><th>Status</th><th>Assigned</th><th>Actions</th></tr>
              </thead>
              <tbody>
                {filtered.map(e => (
                  <tr key={e.exception_id}>
                    <td>{e.exception_id}</td>
                    <td>{e.container_number}</td>
                    <td>{e.exception_type}</td>
                    <td><span className={`badge badge-${e.severity}`}>{e.severity}</span></td>
                    <td>{e.risk_score}</td>
                    <td><span className={`badge badge-${e.status}`}>{e.status}</span></td>
                    <td>{e.assigned_to || '-'}</td>
                    <td>
                      <button className="btn btn-primary btn-sm" onClick={() => setSelected(e)}>View</button>
                      {!e.assigned_to && e.status !== 'resolved' && (
                        <button className="btn btn-success btn-sm" style={{marginLeft:4}} onClick={() => handleAssign(e.exception_id)}>Assign</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {tab === 'notifications' && (
          <div className="card">
            <h2>Notifications</h2>
            <table>
              <thead><tr><th>ID</th><th>Customer</th><th>Phase</th><th>Status</th><th>Created</th></tr></thead>
              <tbody>
                {data.notifications.map(n => (
                  <tr key={n.notification_id}>
                    <td>{n.notification_id}</td>
                    <td>{n.customer_name}</td>
                    <td>Phase {n.phase}</td>
                    <td><span className={`badge badge-${n.status === 'sent' ? 'resolved' : 'detected'}`}>{n.status}</span></td>
                    <td>{new Date(n.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {tab === 'decisions' && (
          <div className="card">
            <h2>Decisions</h2>
            <table>
              <thead><tr><th>ID</th><th>Exception</th><th>By</th><th>Decision</th><th>Time</th></tr></thead>
              <tbody>
                {data.decisions.map(d => (
                  <tr key={d.decision_id}>
                    <td>{d.decision_id}</td>
                    <td>{d.exception_id}</td>
                    <td>{d.decided_by}</td>
                    <td><span className={`badge badge-${d.decision === 'approve' ? 'resolved' : 'detected'}`}>{d.decision}</span></td>
                    <td>{new Date(d.decided_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {selected && (
          <div className="modal" onClick={() => setSelected(null)}>
            <div className="modal-content" onClick={e => e.stopPropagation()}>
              <div className="modal-header">
                <h2>Exception Detail</h2>
                <button className="btn" onClick={() => setSelected(null)}>X</button>
              </div>
              <div className="detail-grid">
                <div className="detail-item"><div className="detail-label">ID</div><div className="detail-value">{selected.exception_id}</div></div>
                <div className="detail-item"><div className="detail-label">Container</div><div className="detail-value">{selected.container_number}</div></div>
                <div className="detail-item"><div className="detail-label">Type</div><div className="detail-value">{selected.exception_type}</div></div>
                <div className="detail-item"><div className="detail-label">Severity</div><div className="detail-value"><span className={`badge badge-${selected.severity}`}>{selected.severity}</span></div></div>
                <div className="detail-item"><div className="detail-label">Risk Score</div><div className="detail-value">{selected.risk_score}</div></div>
                <div className="detail-item"><div className="detail-label">Confidence</div><div className="detail-value">{selected.ai_confidence ? `${(selected.ai_confidence*100).toFixed(0)}%` : 'N/A'}</div></div>
              </div>
              <div className="detail-item"><div className="detail-label">Root Cause</div><div className="detail-value">{selected.root_cause || 'N/A'}</div></div>
              <div className="detail-item"><div className="detail-label">AI Diagnosis</div><div className="detail-value">{selected.ai_diagnosis || 'N/A'}</div></div>
              <div className="detail-item"><div className="detail-label">Recommended Action</div><div className="detail-value">{selected.recommended_action || 'N/A'}</div></div>
              <div style={{marginTop:16, display:'flex', gap:8}}>
                {selected.status !== 'resolved' && (
                  <>
                    <button className="btn btn-success" onClick={() => {handleDecision(selected.exception_id, 'approve'); handleResolve(selected.exception_id)}}>Approve & Resolve</button>
                    <button className="btn" style={{background:'#e53e3e',color:'white'}} onClick={() => handleDecision(selected.exception_id, 'reject')}>Reject</button>
                  </>
                )}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
