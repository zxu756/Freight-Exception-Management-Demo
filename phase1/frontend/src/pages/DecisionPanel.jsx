import React, { useState } from 'react'

export default function DecisionPanel({ exceptions }) {
  const [selectedException, setSelectedException] = useState(null)
  const [decision, setDecision] = useState({
    action: '',
    reason: '',
    notes: ''
  })

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!selectedException) {
      alert('Please select an exception')
      return
    }
    
    console.log('Decision submitted:', {
      exceptionId: selectedException.id || selectedException.exception_id,
      ...decision
    })
    
    alert('Decision recorded (demo mode)')
    setDecision({ action: '', reason: '', notes: '' })
  }

  return (
    <div className="decision-panel">
      <h2>Decision Panel</h2>

      <div className="detail-card">
        <h3>Select Exception</h3>
        <select
          value={selectedException ? (selectedException.id || selectedException.exception_id) : ''}
          onChange={(e) => {
            const exc = exceptions.find(ex => 
              (ex.id || ex.exception_id) === e.target.value
            )
            setSelectedException(exc || null)
          }}
          style={{ width: '100%', padding: '10px', borderRadius: '4px', border: '1px solid #ddd' }}
        >
          <option value="">-- Select an exception --</option>
          {exceptions.map((exc, idx) => (
            <option key={idx} value={exc.id || exc.exception_id}>
              [{exc.type}] {exc.id || exc.exception_id}
            </option>
          ))}
        </select>
      </div>

      {selectedException && (
        <div className="detail-card">
          <h3>Exception Info</h3>
          <div className="detail-row">
            <span className="detail-label">ID:</span>
            <span className="detail-value">{selectedException.id || selectedException.exception_id}</span>
          </div>
          <div className="detail-row">
            <span className="detail-label">Type:</span>
            <span className="detail-value">{selectedException.type}</span>
          </div>
          <div className="detail-row">
            <span className="detail-label">Status:</span>
            <span className="detail-value">{selectedException.status}</span>
          </div>
        </div>
      )}

      <form className="decision-form" onSubmit={handleSubmit}>
        <h3>Make Decision</h3>
        
        <div className="form-group">
          <label>Action *</label>
          <select
            value={decision.action}
            onChange={(e) => setDecision({ ...decision, action: e.target.value })}
            required
          >
            <option value="">-- Select action --</option>
            <option value="approve">Approve</option>
            <option value="reject">Reject</option>
            <option value="escalate">Escalate</option>
            <option value="reroute">Reroute</option>
            <option value="hold">Hold</option>
          </select>
        </div>

        <div className="form-group">
          <label>Reason *</label>
          <textarea
            value={decision.reason}
            onChange={(e) => setDecision({ ...decision, reason: e.target.value })}
            placeholder="Enter reason for this decision..."
            required
          />
        </div>

        <div className="form-group">
          <label>Additional Notes</label>
          <textarea
            value={decision.notes}
            onChange={(e) => setDecision({ ...decision, notes: e.target.value })}
            placeholder="Any additional notes..."
          />
        </div>

        <button type="submit" className="btn btn-primary">
          Submit Decision
        </button>
      </form>
    </div>
  )
}
