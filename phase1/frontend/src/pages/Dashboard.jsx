import React from 'react'

export default function Dashboard({ stats, exceptions }) {
  const recentExceptions = exceptions.slice(0, 10)

  return (
    <div className="dashboard">
      <h2>Dashboard</h2>
      
      <div className="stats-grid">
        <div className="stat-card total">
          <h3>Total Active</h3>
          <div className="value">{stats?.total || 0}</div>
        </div>
        <div className="stat-card air">
          <h3>Air Cargo</h3>
          <div className="value">{stats?.air || 0}</div>
        </div>
        <div className="stat-card road">
          <h3>Road Freight</h3>
          <div className="value">{stats?.road || 0}</div>
        </div>
        <div className="stat-card sea">
          <h3>Sea Freight</h3>
          <div className="value">{stats?.sea || 0}</div>
        </div>
      </div>

      <div className="recent-section">
        <h3>Recent Exceptions</h3>
        {recentExceptions.length > 0 ? (
          <table className="exception-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Type</th>
                <th>Status</th>
                <th>Created At</th>
              </tr>
            </thead>
            <tbody>
              {recentExceptions.map((exc, idx) => (
                <tr key={idx}>
                  <td>{exc.id || exc.exception_id}</td>
                  <td><span className={`badge ${exc.type}`}>{exc.type}</span></td>
                  <td><span className={`badge ${exc.status}`}>{exc.status}</span></td>
                  <td>{exc.created_at || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="empty-state">No recent exceptions</div>
        )}
      </div>
    </div>
  )
}
