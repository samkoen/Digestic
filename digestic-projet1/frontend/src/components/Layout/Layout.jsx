import React, { useState, useEffect, useMemo } from 'react'
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
  Avatar,
  Chip,
  alpha,
  useTheme,
} from '@mui/material'
import MenuIcon from '@mui/icons-material/Menu'
import DashboardIcon from '@mui/icons-material/Dashboard'
import LocalPharmacyIcon from '@mui/icons-material/LocalPharmacy'
import TuneIcon from '@mui/icons-material/Tune'
import CalendarTodayIcon from '@mui/icons-material/CalendarToday'
import ReceiptIcon from '@mui/icons-material/Receipt'
import PeopleIcon from '@mui/icons-material/People'
import LocalShippingIcon from '@mui/icons-material/LocalShipping'
import WarehouseIcon from '@mui/icons-material/Warehouse'
import Inventory2Icon from '@mui/icons-material/Inventory2'
import MarkEmailUnreadIcon from '@mui/icons-material/MarkEmailUnread'
import LogoutIcon from '@mui/icons-material/Logout'
import { authService } from '../../services/authService'
import { sidebarWidth } from '../../theme/theme'

function userInitials(user) {
  if (!user) return '?'
  const parts = (user.full_name || user.email || '').trim().split(/\s+/)
  if (parts.length >= 2) {
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
  }
  return (parts[0]?.[0] || '?').toUpperCase()
}

function Layout({ children }) {
  const theme = useTheme()
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

  const menuItems = useMemo(() => {
    const baseItems = [
      { text: 'Tableau de bord', icon: <DashboardIcon />, path: '/' },
      { text: 'Pharmacies', icon: <LocalPharmacyIcon />, path: '/pharmacies' },
      {
        text: 'Planning',
        icon: <CalendarTodayIcon />,
        path: '/planning',
        matchPathPrefix: '/planning',
      },
      { text: 'Factures', icon: <ReceiptIcon />, path: '/invoices' },
    ]

    if (user?.role === 'admin') {
      baseItems.push({ text: 'Bons de livraison', icon: <LocalShippingIcon />, path: '/delivery-notes' })
      baseItems.push({
        text: 'Filtres avancés',
        icon: <TuneIcon />,
        path: '/pharmacies/advanced-filters',
      })
      baseItems.push({ text: 'Dépôts', icon: <WarehouseIcon />, path: '/depots' })
      baseItems.push({ text: 'Produits', icon: <Inventory2Icon />, path: '/products' })
      baseItems.push({ text: 'Commerciaux', icon: <PeopleIcon />, path: '/users' })
      baseItems.push({
        text: "Modèles d'e-mail",
        icon: <MarkEmailUnreadIcon />,
        path: '/email-templates',
      })
    }

    return baseItems
  }, [user?.role])

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen)
  }

  const handleNavigation = (path) => {
    navigate(path)
    setMobileOpen(false)
  }

  const drawerContent = (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box
        sx={{
          px: 2.5,
          py: 2.5,
          background: `linear-gradient(135deg, ${theme.palette.primary.dark} 0%, ${theme.palette.primary.main} 100%)`,
          color: 'primary.contrastText',
        }}
      >
        <Typography variant="h6" fontWeight={700} letterSpacing="-0.02em">
          Digestic
        </Typography>
        <Typography variant="caption" sx={{ opacity: 0.9, display: 'block', mt: 0.25 }}>
          Espaces Pharmacies
        </Typography>
      </Box>
      <List sx={{ flex: 1, px: 1.5, py: 2 }}>
        {menuItems.map((item) => {
          const selected = item.matchPathPrefix
            ? location.pathname.startsWith(item.matchPathPrefix)
            : location.pathname === item.path
          return (
            <ListItem key={item.text} disablePadding sx={{ mb: 0.5 }}>
              <ListItemButton
                selected={selected}
                onClick={() => handleNavigation(item.path)}
                sx={{
                  borderRadius: 2,
                  py: 1.1,
                  '&.Mui-selected': {
                    bgcolor: alpha(theme.palette.primary.main, 0.12),
                    color: 'primary.dark',
                    '&:hover': { bgcolor: alpha(theme.palette.primary.main, 0.16) },
                    '& .MuiListItemIcon-root': { color: 'primary.main' },
                  },
                  '& .MuiListItemIcon-root': {
                    minWidth: 40,
                    color: selected ? 'primary.main' : 'text.secondary',
                  },
                }}
              >
                <ListItemIcon>{item.icon}</ListItemIcon>
                <ListItemText
                  primary={item.text}
                  primaryTypographyProps={{
                    fontSize: '0.9rem',
                    fontWeight: selected ? 600 : 500,
                  }}
                />
              </ListItemButton>
            </ListItem>
          )
        })}
      </List>
      {user && (
        <>
          <Divider />
          <Box sx={{ p: 2 }}>
            <Box display="flex" alignItems="center" gap={1.5}>
              <Avatar
                sx={{
                  width: 36,
                  height: 36,
                  bgcolor: 'primary.main',
                  fontSize: '0.85rem',
                  fontWeight: 700,
                }}
              >
                {userInitials(user)}
              </Avatar>
              <Box sx={{ minWidth: 0, flex: 1 }}>
                <Typography variant="body2" fontWeight={600} noWrap>
                  {user.full_name}
                </Typography>
                <Chip
                  label={user.role === 'admin' ? 'Admin' : 'Commercial'}
                  size="small"
                  sx={{
                    mt: 0.5,
                    height: 20,
                    fontSize: '0.65rem',
                    bgcolor: alpha(theme.palette.primary.main, 0.1),
                    color: 'primary.dark',
                  }}
                />
              </Box>
            </Box>
          </Box>
        </>
      )}
    </Box>
  )

  const drawerPaperSx = {
    boxSizing: 'border-box',
    width: sidebarWidth,
    borderRight: `1px solid ${theme.palette.divider}`,
    bgcolor: 'background.paper',
  }

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <CssBaseline />
      <AppBar
        position="fixed"
        elevation={0}
        sx={{
          width: { sm: `calc(100% - ${sidebarWidth}px)` },
          ml: { sm: `${sidebarWidth}px` },
          bgcolor: alpha(theme.palette.background.paper, 0.85),
          backdropFilter: 'blur(12px)',
          color: 'text.primary',
          borderBottom: `1px solid ${theme.palette.divider}`,
        }}
      >
        <Toolbar sx={{ minHeight: { xs: 56, sm: 64 } }}>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Box
            display="flex"
            justifyContent="space-between"
            alignItems="center"
            width="100%"
            gap={2}
          >
            <Box sx={{ minWidth: 0 }}>
              <Typography variant="h6" fontWeight={700} noWrap>
                Espaces Pharmacies
              </Typography>
              <Typography variant="caption" color="text.secondary" noWrap sx={{ display: { xs: 'none', md: 'block' } }}>
                Planning et suivi des visites pharmacies
              </Typography>
            </Box>
            {user && (
              <Box display="flex" alignItems="center" gap={1}>
                <Box sx={{ textAlign: 'right', display: { xs: 'none', sm: 'block' } }}>
                  <Typography variant="body2" fontWeight={600}>
                    {user.full_name}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {user.role === 'admin' ? 'Administrateur' : 'Commercial'}
                  </Typography>
                </Box>
                <IconButton
                  onClick={handleLogout}
                  size="small"
                  aria-label="Déconnexion"
                  sx={{
                    bgcolor: alpha(theme.palette.error.main, 0.08),
                    color: 'error.main',
                    '&:hover': { bgcolor: alpha(theme.palette.error.main, 0.14) },
                  }}
                >
                  <LogoutIcon fontSize="small" />
                </IconButton>
              </Box>
            )}
          </Box>
        </Toolbar>
      </AppBar>
      <Box component="nav" sx={{ width: { sm: sidebarWidth }, flexShrink: { sm: 0 } }}>
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': drawerPaperSx,
          }}
        >
          {drawerContent}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': drawerPaperSx,
          }}
          open
        >
          {drawerContent}
        </Drawer>
      </Box>
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: { xs: 2, sm: 3 },
          width: { sm: `calc(100% - ${sidebarWidth}px)` },
          minHeight: '100vh',
          bgcolor: 'background.default',
        }}
      >
        <Toolbar sx={{ minHeight: { xs: 56, sm: 64 } }} />
        <Box className="page-enter">{children}</Box>
      </Box>
    </Box>
  )
}

export default Layout
