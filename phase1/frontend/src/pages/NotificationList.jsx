import React from 'react'

export default function NotificationList({ notifications }) {
  return (
    <div className="notification-list">
      <h2>Notifications</h2>

      {notifications.length > 0 ? (
        notifications.map((notif, idx) => (
          <div key={idx} className="notification-item">
            <div className="notification-header">
              <span><strong>{notif.exception_id || notif.id}</strong></span>
              <span className={`badge ${notif.status || 'pending'}`}>
                {notif.status || 'pending'}
              </span>
            </div>
            <div className="notification-message">
              {notif.message || notif.content || 'No message content'}
            </div>
            {notif.created_at && (
              <div style={{ marginTop: '10px', fontSize: '0.85rem', color: '#888' }}>
                {notif.created_at}
              </div>
            )}
          </div>
        ))
      ) : (
        <div className="empty-state">No notifications</div>
      )}
    </div>
  )
}
