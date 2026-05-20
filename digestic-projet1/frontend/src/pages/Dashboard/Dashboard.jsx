import React, { cloneElement, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  CircularProgress,
  Button,
  alpha,
  useTheme,
} from '@mui/material'
import LocalPharmacyIcon from '@mui/icons-material/LocalPharmacy'
import ReceiptIcon from '@mui/icons-material/Receipt'
import WarningIcon from '@mui/icons-material/Warning'
import CalendarTodayIcon from '@mui/icons-material/CalendarToday'
import ArrowForwardIcon from '@mui/icons-material/ArrowForward'
import { pharmacyService } from '../../services/pharmacyService'
import { invoiceService } from '../../services/invoiceService'
import PageHeader from '../../components/PageHeader/PageHeader'

function StatCard({ title, value, icon, color, onClick }) {
  return (
    <Card
      onClick={onClick}
      sx={{
        height: '100%',
        cursor: onClick ? 'pointer' : 'default',
        transition: 'transform 0.2s ease, box-shadow 0.2s ease',
        '&:hover': onClick
          ? {
              transform: 'translateY(-4px)',
              boxShadow: '0 12px 32px rgba(26, 35, 50, 0.12)',
            }
          : {},
      }}
    >
      <CardContent sx={{ p: 3 }}>
        <Box display="flex" alignItems="flex-start" justifyContent="space-between">
          <Box>
            <Typography variant="overline" color="text.secondary" sx={{ fontWeight: 600, letterSpacing: 1 }}>
              {title}
            </Typography>
            <Typography variant="h3" component="div" sx={{ fontWeight: 700, mt: 0.5, color: 'text.primary' }}>
              {value}
            </Typography>
          </Box>
          <Box
            sx={{
              width: 52,
              height: 52,
              borderRadius: 2.5,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              bgcolor: alpha(color, 0.12),
              color,
            }}
          >
            {icon}
          </Box>
        </Box>
        {onClick && (
          <Box sx={{ mt: 2, display: 'flex', alignItems: 'center', gap: 0.5, color: 'primary.main' }}>
            <Typography variant="body2" fontWeight={600}>
              Voir le détail
            </Typography>
            <ArrowForwardIcon sx={{ fontSize: 16 }} />
          </Box>
        )}
      </CardContent>
    </Card>
  )
}

function Dashboard() {
  const theme = useTheme()
  const navigate = useNavigate()
  const [user, setUser] = useState(null)
  const [stats, setStats] = useState({
    pharmacies: 0,
    pendingInvoices: 0,
    overdueInvoices: 0,
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    try {
      const raw = localStorage.getItem('user')
      if (raw) setUser(JSON.parse(raw))
    } catch {
      setUser(null)
    }
  }, [])

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const [pharmacyPage, invoices, overdue] = await Promise.all([
          pharmacyService.getList({ page: 1, page_size: 1, sort: 'name', order: 'asc' }),
          invoiceService.getAll({ status: 'pending' }),
          invoiceService.getOverdue(30),
        ])

        setStats({
          pharmacies: pharmacyPage?.total ?? 0,
          pendingInvoices: invoices.length,
          overdueInvoices: overdue.length,
        })
      } catch (error) {
        console.error('Error fetching stats:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchStats()
  }, [])

  const greeting = user?.first_name
    ? `Bonjour, ${user.first_name}`
    : user?.full_name
      ? `Bonjour, ${user.full_name.split(' ')[0]}`
      : 'Bonjour'

  const statCards = [
    {
      title: 'Pharmacies',
      value: stats.pharmacies,
      icon: <LocalPharmacyIcon />,
      color: theme.palette.primary.main,
      onClick: () => navigate('/pharmacies'),
    },
    {
      title: 'Factures en attente',
      value: stats.pendingInvoices,
      icon: <ReceiptIcon />,
      color: theme.palette.warning.main,
      onClick: () => navigate('/invoices'),
    },
    {
      title: 'Factures en retard',
      value: stats.overdueInvoices,
      icon: <WarningIcon />,
      color: theme.palette.error.main,
      onClick: () => navigate('/invoices'),
    },
  ]

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box>
      <PageHeader
        title={greeting}
        subtitle="Vue d’ensemble de votre activité — pharmacies, planning et facturation."
        action={
          <Button
            variant="contained"
            startIcon={<CalendarTodayIcon />}
            onClick={() => navigate('/planning')}
          >
            Ouvrir le planning
          </Button>
        }
      />

      <Grid container spacing={3}>
        {statCards.map((card) => (
          <Grid item xs={12} sm={6} md={4} key={card.title}>
            <StatCard {...card} icon={cloneElement(card.icon, { sx: { fontSize: 28 } })} />
          </Grid>
        ))}
      </Grid>

      <Card sx={{ mt: 3, bgcolor: alpha(theme.palette.primary.main, 0.04), border: 'none' }}>
        <CardContent sx={{ py: 2.5, px: 3 }}>
          <Typography variant="subtitle1" fontWeight={600} gutterBottom>
            Prochaine étape
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Consultez le planning du jour pour préparer vos visites terrain.
          </Typography>
          <Button variant="outlined" color="primary" onClick={() => navigate('/planning')}>
            Voir le planning
          </Button>
        </CardContent>
      </Card>
    </Box>
  )
}

export default Dashboard
