import React, { useEffect, useState } from 'react'
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  CircularProgress,
} from '@mui/material'
import LocalPharmacyIcon from '@mui/icons-material/LocalPharmacy'
import ReceiptIcon from '@mui/icons-material/Receipt'
import WarningIcon from '@mui/icons-material/Warning'
import { pharmacyService } from '../../services/pharmacyService'
import { invoiceService } from '../../services/invoiceService'

function Dashboard() {
  const [stats, setStats] = useState({
    pharmacies: 0,
    pendingInvoices: 0,
    overdueInvoices: 0,
  })
  const [loading, setLoading] = useState(true)

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

  const statCards = [
    {
      title: 'Pharmacies',
      value: stats.pharmacies,
      icon: <LocalPharmacyIcon sx={{ fontSize: 40 }} />,
      color: '#1976d2',
    },
    {
      title: 'Factures en Attente',
      value: stats.pendingInvoices,
      icon: <ReceiptIcon sx={{ fontSize: 40 }} />,
      color: '#ed6c02',
    },
    {
      title: 'Factures en Retard',
      value: stats.overdueInvoices,
      icon: <WarningIcon sx={{ fontSize: 40 }} />,
      color: '#d32f2f',
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
      <Typography variant="h4" gutterBottom sx={{ mb: 4 }}>
        Tableau de bord
      </Typography>
      <Grid container spacing={3}>
        {statCards.map((card, index) => (
          <Grid item xs={12} sm={6} md={4} key={index}>
            <Card
              sx={{
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                transition: 'transform 0.2s',
                '&:hover': {
                  transform: 'translateY(-4px)',
                  boxShadow: 4,
                },
              }}
            >
              <CardContent>
                <Box display="flex" alignItems="center" justifyContent="space-between">
                  <Box>
                    <Typography color="textSecondary" gutterBottom variant="h6">
                      {card.title}
                    </Typography>
                    <Typography variant="h3" component="div" sx={{ fontWeight: 'bold' }}>
                      {card.value}
                    </Typography>
                  </Box>
                  <Box sx={{ color: card.color }}>
                    {card.icon}
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  )
}

export default Dashboard


