import React, { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  Box,
  Drawer,
  AppBar,
  Toolbar,
  List,
  Typography,
  Divider,
  IconButton,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  CssBaseline,
} from '@mui/material'
import MenuIcon from '@mui/icons-material/Menu'
import DashboardIcon from '@mui/icons-material/Dashboard'
import LocalPharmacyIcon from '@mui/icons-material/LocalPharmacy'
import EventIcon from '@mui/icons-material/Event'
import CalendarTodayIcon from '@mui/icons-material/CalendarToday'
import ReceiptIcon from '@mui/icons-material/Receipt'
import DescriptionIcon from '@mui/icons-material/Description'
import PeopleIcon from '@mui/icons-material/People'
import LocalShippingIcon from '@mui/icons-material/LocalShipping'
import WarehouseIcon from '@mui/icons-material/Warehouse'
import LogoutIcon from '@mui/icons-material/Logout'
import { authService } from '../../services/authService'

const drawerWidth = 240

function Layout({ children }) {
  const [mobileOpen, setMobileOpen] = useState(false)
  const [user, setUser] = useState(null)
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    const storedUser = localStorage.getItem('user')
    if (storedUser) {
      setUser(JSON.parse(storedUser))
    }
  }, [])

  const handleLogout = async () => {
    try {
      await authService.logout()
      localStorage.removeItem('user')
      navigate('/login')
    } catch (error) {
      console.error('Error logging out:', error)
      localStorage.removeItem('user')
      navigate('/login')
    }
  }

  // Menu items selon le rôle
  const getMenuItems = () => {
    const baseItems = [
      { text: 'Tableau de bord', icon: <DashboardIcon />, path: '/' },
      { text: 'Pharmacies', icon: <LocalPharmacyIcon />, path: '/pharmacies' },
      { text: 'Visites', icon: <EventIcon />, path: '/visits' },
      { text: 'Planning', icon: <CalendarTodayIcon />, path: '/planning' },
      { text: 'Factures', icon: <ReceiptIcon />, path: '/invoices' },
      { text: 'Supports Commerciaux', icon: <DescriptionIcon />, path: '/materials' },
    ]

    if (user?.role === 'admin') {
      baseItems.push({ text: 'Bons de livraison', icon: <LocalShippingIcon />, path: '/delivery-notes' })
      baseItems.push({ text: 'Dépôts', icon: <WarehouseIcon />, path: '/depots' })
      baseItems.push({ text: 'Commerciaux', icon: <PeopleIcon />, path: '/users' })
    }

    return baseItems
  }

  const menuItems = getMenuItems()

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen)
  }

  const handleNavigation = (path) => {
    navigate(path)
    setMobileOpen(false)
  }

  const drawer = (
    <Box>
      <Toolbar
        sx={{
          backgroundColor: '#1976d2',
          color: 'white',
        }}
      >
        <Typography variant="h6" noWrap component="div">
          GRCP
        </Typography>
      </Toolbar>
      <Divider />
      <List>
        {menuItems.map((item) => (
          <ListItem key={item.text} disablePadding>
            <ListItemButton
              selected={location.pathname === item.path}
              onClick={() => handleNavigation(item.path)}
            >
              <ListItemIcon sx={{ color: location.pathname === item.path ? '#1976d2' : 'inherit' }}>
                {item.icon}
              </ListItemIcon>
              <ListItemText primary={item.text} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
    </Box>
  )

  return (
    <Box sx={{ display: 'flex' }}>
      <CssBaseline />
      <AppBar
        position="fixed"
        sx={{
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          ml: { sm: `${drawerWidth}px` },
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Box display="flex" justifyContent="space-between" alignItems="center" width="100%">
            <Typography variant="h6" noWrap component="div">
              Gestion Relation Commerciale Pharmacie
            </Typography>
            {user && (
              <Box display="flex" alignItems="center" gap={2}>
                <Typography variant="body2">
                  {user.full_name} ({user.role === 'admin' ? 'Admin' : 'Commercial'})
                </Typography>
                <IconButton color="inherit" onClick={handleLogout} size="small">
                  <LogoutIcon />
                </IconButton>
              </Box>
            )}
          </Box>
        </Toolbar>
      </AppBar>
      <Box
        component="nav"
        sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}
      >
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{
            keepMounted: true,
          }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
          }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          minHeight: '100vh',
          backgroundColor: '#f5f5f5',
        }}
      >
        <Toolbar />
        {children}
      </Box>
    </Box>
  )
}

export default Layout

