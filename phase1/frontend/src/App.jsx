import React, { useState, useEffect } from 'react'

const API = '/api'

export default function App() {
  const [tab, setTab] = useState('dashboard')
  const [data, setData] = useState({ dashboard: null, exceptions: [], notifications: [], decisions: [], employees: [] })
  const [selected, setSelected] = useState(null)
  const [advice, setAdvice] = useState(null)
  const [filters, setFilters] = useState({ type: '', severity: '', status: '' })
  const [resolveModal, setResolveModal] = useState(false)
  const [selectedEmployee, setSelectedEmployee] = useState('')

  useEffect(() => { loadAll() }, [])

  const loadAll = async () => {
    try {
      const [dash, exc, notif, dec, emp] = await Promise.all([
        fetch(`${API}/dashboard`).then(r => r.json()),
        fetch(`${API}/exceptions`).then(r => r.json()),
        fetch(`${API}/notifications`).then(r => r.json()),
        fetch(`${API}/decisions`).then(r => r.json()),
        fetch(`${API}/employees`).then(r => r.json()),
      ])
      setData({ 
        dashboard: dash, 
        exceptions: exc.exceptions || [], 
        notifications: notif.notifications || [], 
        decisions: dec.decisions || [],
        employees: emp.employees || []
      })
    } catch (err) { console.error(err) }
  }

  const loadAdvice = async (exceptionId) => {
    try {
      const res = await fetch(`${API}/advice/${exceptionId}`)
      const data = await res.json()
      setAdvice(data)
    } catch (err) { console.error(err) }
  }

  const handleViewDetail = async (exc) => {
    setSelected(exc)
    await loadAdvice(exc.exception_id)
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

  const handleResolveClick = () => {
    setResolveModal(true)
  }

  const handleResolveConfirm = async () => {
    if (!selectedEmployee) {
      alert('Please select an employee')
      return
    }
    
    const employee = data.employees.find(e => e.employee_id === selectedEmployee)
    
    // Create decision
    await fetch(`${API}/decisions`, {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ 
        exception_id: selected.exception_id, 
        decision: 'approve', 
        decided_by: employee.name,
        note: `Resolved by ${employee.name} (${employee.role})`
      })
    })
    
    // Resolve exception
    await fetch(`${API}/exceptions/${selected.exception_id}/resolve`, {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ resolved_by: employee.name })
    })
    
    setResolveModal(false)
    setSelectedEmployee('')
    setSelected(null)
    setAdvice(null)
    loadAll()
  }

  const handleReject = async () => {
    const employee = data.employees.find(e => e.employee_id === selectedEmployee) || { name: 'Coordinator' }
    await fetch(`${API}/decisions`, {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ 
        exception_id: selected.exception_id, 
        decision: 'reject', 
        decided_by: employee.name 
      })
    })
    setSelected(null)
    setAdvice(null)
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
                      <button className="btn btn-primary btn-sm" onClick={() => handleViewDetail(e)}>View</button>
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

        {/* Exception Detail Modal */}
        {selected && (
          <div className="modal" onClick={() => {setSelected(null); setAdvice(null)}}>
            <div className="modal-content" onClick={e => e.stopPropagation()}>
              <div className="modal-header">
                <h2>Exception Detail</h2>
                <button className="btn" onClick={() => {setSelected(null); setAdvice(null)}}>X</button>
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

              {/* AI Advice Section */}
              {advice && (
                <div className="advice-section">
                  <h3>AI Advice & Recommendations</h3>
                  
                  <div className="quick-response">
                    <h4>Quick Response</h4>
                    <div className="detail-grid">
                      <div className="detail-item"><div className="detail-label">Immediate Action</div><div className="detail-value">{advice.quick_response?.immediate_action}</div></div>
                      <div className="detail-item"><div className="detail-label">Response Time</div><div className="detail-value">{advice.quick_response?.timeline}</div></div>
                      <div className="detail-item"><div className="detail-label">Escalation</div><div className="detail-value">{advice.quick_response?.escalation}</div></div>
                      <div className="detail-item"><div className="detail-label">Est. Cost</div><div className="detail-value">${advice.estimated_recovery_cost}</div></div>
                    </div>
                  </div>

                  <div className="detailed-advice">
                    <h4>Recommended Actions</h4>
                    {advice.advice?.advice?.map(a => (
                      <div key={a.id} className={`advice-card priority-${a.priority}`}>
                        <div className="advice-header">
                          <span className="advice-title">{a.title}</span>
                          <span className={`badge badge-${a.priority === 'high' ? 'critical' : 'medium'}`}>{a.priority}</span>
                        </div>
                        <div className="advice-action">{a.action}</div>
                        <div className="advice-reason">{a.reason}</div>
                        <div className="advice-meta">
                          {a.estimated_cost > 0 && <span className="cost">Cost: ${a.estimated_cost}</span>}
                          {a.estimated_time_saved !== 'N/A' && <span className="time">Time saved: {a.estimated_time_saved}</span>}
                          {a.requires_approval && <span className="approval">Requires approval</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div style={{marginTop:16, display:'flex', gap:8}}>
                {selected.status !== 'resolved' && (
                  <>
                    <button className="btn btn-success" onClick={handleResolveClick}>Resolve</button>
                    <button className="btn" style={{background:'#e53e3e',color:'white'}} onClick={handleReject}>Reject</button>
                  </>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Resolve Modal */}
        {resolveModal && (
          <div className="modal" onClick={() => setResolveModal(false)}>
            <div className="modal-content" onClick={e => e.stopPropagation()} style={{maxWidth: '400px'}}>
              <div className="modal-header">
                <h2>Resolve Exception</h2>
                <button className="btn" onClick={() => setResolveModal(false)}>X</button>
              </div>
              
              <div style={{marginBottom: 16}}>
                <div className="detail-label" style={{marginBottom: 8}}>Select Employee</div>
                <select 
                  className="full-width"
                  value={selectedEmployee} 
                  onChange={e => setSelectedEmployee(e.target.value)}
                >
                  <option value="">-- Select Employee --</option>
                  {data.employees.map(emp => (
                    <option key={emp.employee_id} value={emp.employee_id}>
                      {emp.name} - {emp.role}
                    </option>
                  ))}
                </select>
              </div>

              {selectedEmployee && (
                <div className="employee-info" style={{background: '#f8f9fa', padding: 12, borderRadius: 8, marginBottom: 16}}>
                  {(() => {
                    const emp = data.employees.find(e => e.employee_id === selectedEmployee)
                    return emp ? (
                      <>
                        <div><strong>{emp.name}</strong></div>
                        <div style={{fontSize: 12, color: '#666'}}>{emp.role} | {emp.department}</div>
                        <div style={{fontSize: 12, color: '#666'}}>{emp.email}</div>
                      </>
                    ) : null
                  })()}
                </div>
              )}

              <div style={{display: 'flex', gap: 8, justifyContent: 'flex-end'}}>
                <button className="btn" onClick={() => setResolveModal(false)}>Cancel</button>
                <button className="btn btn-success" onClick={handleResolveConfirm}>Confirm Resolve</button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
