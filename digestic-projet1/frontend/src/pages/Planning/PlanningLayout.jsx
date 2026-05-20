import React, { useEffect, useMemo, useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { Box, Paper, Tab, Tabs } from '@mui/material'

function readStoredUser() {
  try {
    const raw = localStorage.getItem('user')
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function PlanningLayout() {
  const location = useLocation()
  const navigate = useNavigate()
  const [user, setUser] = useState(readStoredUser)

  useEffect(() => {
    setUser(readStoredUser())
  }, [])

  const isAdmin = user?.role === 'admin'

  const tabs = useMemo(() => {
    const items = [{ label: 'Calendrier', path: '/planning' }]
    if (isAdmin) {
      items.push({ label: 'Paramètres', path: '/planning/parametres' })
    }
    items.push({ label: 'Évaluation terrain', path: '/planning/evaluation' })
    return items
  }, [isAdmin])

  const tabIndex = useMemo(() => {
    const path = location.pathname
    if (path.startsWith('/planning/parametres')) {
      return isAdmin ? 1 : false
    }
    if (path.startsWith('/planning/evaluation')) {
      return isAdmin ? 2 : 1
    }
    if (path === '/planning' || path === '/planning/') {
      return 0
    }
    return 0
  }, [location.pathname, isAdmin])

  const handleTabChange = (_event, nextIndex) => {
    const target = tabs[nextIndex]
    if (target) navigate(target.path)
  }

  const safeIndex = tabIndex === false ? 0 : tabIndex

  return (
    <Box>
      <Paper elevation={0} sx={{ mb: 3, border: 1, borderColor: 'divider' }}>
        <Tabs
          value={safeIndex}
          onChange={handleTabChange}
          variant="scrollable"
          allowScrollButtonsMobile
          aria-label="Sections planning"
          sx={{ px: 1 }}
        >
          {tabs.map((t) => (
            <Tab key={t.path} label={t.label} />
          ))}
        </Tabs>
      </Paper>
      <Outlet />
    </Box>
  )
}

export default PlanningLayout
