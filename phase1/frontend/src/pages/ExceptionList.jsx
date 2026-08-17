import React, { useState } from 'react'

export default function ExceptionList({ exceptions, onViewDetail }) {
  const [filter, setFilter] = useState('all')
  const [searchTerm, setSearchTerm] = useState('')

  const filteredExceptions = exceptions.filter(exc => {
    const matchesFilter = filter === 'all' || exc.type === filter
    const matchesSearch = !searchTerm || 
      (exc.id && exc.id.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (exc.exception_id && exc.exception_id.toLowerCase().includes(searchTerm.toLowerCase()))
    return matchesFilter && matchesSearch
  })

  return (
    <div className="exception-list">
      <h2>Exception List</h2>
      
      <div style={{ marginBottom: '20px', display: 'flex', gap: '10px' }}>
        <input
          type="text"
          placeholder="Search by ID..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={{ padding: '8px 12px', borderRadius: '4px', border: '1px solid #ddd', flex: 1 }}
        />
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          style={{ padding: '8px 12px', borderRadius: '4px', border: '1px solid #ddd' }}
        >
          <option value="all">All Types</option>
          <option value="air">Air Cargo</option>
          <option value="road">Road Freight</option>
          <option value="sea">Sea Freight</option>
        </select>
      </div>

      {filteredExceptions.length > 0 ? (
        <table className="exception-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Type</th>
              <th>Status</th>
              <th>Created At</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {filteredExceptions.map((exc, idx) => (
              <tr key={idx}>
                <td>{exc.id || exc.exception_id}</td>
                <td><span className={`badge ${exc.type}`}>{exc.type}</span></td>
                <td><span className={`badge ${exc.status}`}>{exc.status}</span></td>
                <td>{exc.created_at || '-'}</td>
                <td>
                  <button 
                    className="btn btn-primary"
                    onClick={() => onViewDetail(exc)}
                  >
                    View
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div className="empty-state">No exceptions found</div>
      )}
    </div>
  )
}
