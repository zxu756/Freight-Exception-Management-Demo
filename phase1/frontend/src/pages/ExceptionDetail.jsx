import React from 'react'

export default function ExceptionDetail({ exception, onBack }) {
  return (
    <div className="exception-detail">
      <button className="btn btn-secondary back-btn" onClick={onBack}>
        ← Back to List
      </button>

      <h2>Exception Detail</h2>

      <div className="detail-card">
        <h3>Basic Information</h3>
        <div className="detail-row">
          <span className="detail-label">Exception ID:</span>
          <span className="detail-value">{exception.id || exception.exception_id}</span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Type:</span>
          <span className="detail-value">
            <span className={`badge ${exception.type}`}>{exception.type}</span>
          </span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Status:</span>
          <span className="detail-value">
            <span className={`badge ${exception.status}`}>{exception.status}</span>
          </span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Created At:</span>
          <span className="detail-value">{exception.created_at || '-'}</span>
        </div>
      </div>

      {exception.exception_type && (
        <div className="detail-card">
          <h3>Exception Details</h3>
          <div className="detail-row">
            <span className="detail-label">Exception Type:</span>
            <span className="detail-value">{exception.exception_type}</span>
          </div>
          {exception.description && (
            <div className="detail-row">
              <span className="detail-label">Description:</span>
              <span className="detail-value">{exception.description}</span>
            </div>
          )}
          {exception.severity && (
            <div className="detail-row">
              <span className="detail-label">Severity:</span>
              <span className="detail-value">{exception.severity}</span>
            </div>
          )}
        </div>
      )}

      {exception.impact_at && (
        <div className="detail-card">
          <h3>Impact Information</h3>
          <div className="detail-row">
            <span className="detail-label">Impact At:</span>
            <span className="detail-value">{exception.impact_at}</span>
          </div>
          {exception.recovery_cost && (
            <div className="detail-row">
              <span className="detail-label">Recovery Cost:</span>
              <span className="detail-value">${exception.recovery_cost}</span>
            </div>
          )}
        </div>
      )}

      {exception.recommended_action && (
        <div className="detail-card">
          <h3>Recommended Action</h3>
          <div className="detail-row">
            <span className="detail-label">Action:</span>
            <span className="detail-value">{exception.recommended_action}</span>
          </div>
          {exception.recommendation_reason && (
            <div className="detail-row">
              <span className="detail-label">Reason:</span>
              <span className="detail-value">{exception.recommendation_reason}</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
