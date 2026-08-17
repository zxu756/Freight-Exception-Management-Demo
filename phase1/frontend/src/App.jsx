import React, { useState, useEffect } from 'react'
import Dashboard from './pages/Dashboard'
import ExceptionList from './pages/ExceptionList'
import ExceptionDetail from './pages/ExceptionDetail'
import NotificationList from './pages/NotificationList'
import DecisionPanel from './pages/DecisionPanel'

const API_BASE = '/api'

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [selectedException, setSelectedException] = useState(null)
  const [stats, setStats] = useState(null)
  const [exceptions, setExceptions] = useState([])
  const [notifications, setNotifications] = useState([])

  useEffect(() => {
    fetchStats()
    fetchExceptions()
    fetchNotifications()
  }, [])

  const fetchStats = async () => {
    try {
      const [airRes, roadRes, seaRes] = await Promise.all([
        fetch(`${API_BASE}/air/exceptions?status=active`),
        fetch(`${API_BASE}/road/exceptions?status=active`),
        fetch(`${API_BASE}/sea/exceptions?status=active`)
      ])
      const [air, road, sea] = await Promise.all([
        airRes.json(),
        roadRes.json(),
        seaRes.json()
      ])
      setStats({
        air: air.count || 0,
        road: road.count || 0,
        sea: sea.count || 0,
        total: (air.count || 0) + (road.count || 0) + (sea.count || 0)
      })
    } catch (err) {
      console.error('Failed to fetch stats:', err)
    }
  }

  const fetchExceptions = async () => {
    try {
      const [airRes, roadRes, seaRes] = await Promise.all([
        fetch(`${API_BASE}/air/exceptions`),
        fetch(`${API_BASE}/road/exceptions`),
        fetch(`${API_BASE}/sea/exceptions`)
      ])
      const [air, road, sea] = await Promise.all([
        airRes.json(),
        roadRes.json(),
        seaRes.json()
      ])
      const all = [
        ...(air.exceptions || []).map(e => ({ ...e, type: 'air' })),
        ...(road.exceptions || []).map(e => ({ ...e, type: 'road' })),
        ...(sea.exceptions || []).map(e => ({ ...e, type: 'sea' }))
      ]
      setExceptions(all)
    } catch (err) {
      console.error('Failed to fetch exceptions:', err)
    }
  }

  const fetchNotifications = async () => {
    try {
      const res = await fetch(`${API_BASE}/air/notifications`)
      if (res.ok) {
        const data = await res.json()
        setNotifications(data.notifications || [])
      }
    } catch (err) {
      console.error('Failed to fetch notifications:', err)
    }
  }

  const handleViewDetail = (exception) => {
    setSelectedException(exception)
    setActiveTab('detail')
  }

  return (
    <div className="app">
      <nav className="sidebar">
        <div className="logo">
          <h1>Freight Exception</h1>
          <p>Phase 1 Demo</p>
        </div>
        <ul className="nav-links">
          <li 
            className={activeTab === 'dashboard' ? 'active' : ''}
            onClick={() => setActiveTab('dashboard')}
          >
            Dashboard
          </li>
          <li 
            className={activeTab === 'exceptions' ? 'active' : ''}
            onClick={() => setActiveTab('exceptions')}
          >
            Exceptions
          </li>
          <li 
            className={activeTab === 'notifications' ? 'active' : ''}
            onClick={() => setActiveTab('notifications')}
          >
            Notifications
          </li>
          <li 
            className={activeTab === 'decisions' ? 'active' : ''}
            onClick={() => setActiveTab('decisions')}
          >
            Decisions
          </li>
        </ul>
      </nav>
      <main className="content">
        {activeTab === 'dashboard' && (
          <Dashboard stats={stats} exceptions={exceptions} />
        )}
        {activeTab === 'exceptions' && (
          <ExceptionList 
            exceptions={exceptions} 
            onViewDetail={handleViewDetail} 
          />
        )}
        {activeTab === 'detail' && selectedException && (
          <ExceptionDetail 
            exception={selectedException} 
            onBack={() => setActiveTab('exceptions')}
          />
        )}
        {activeTab === 'notifications' && (
          <NotificationList notifications={notifications} />
        )}
        {activeTab === 'decisions' && (
          <DecisionPanel exceptions={exceptions} />
        )}
      </main>
    </div>
  )
}
