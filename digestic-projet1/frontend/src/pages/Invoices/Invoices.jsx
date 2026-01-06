import React, { useEffect, useState } from 'react'
import {
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  CircularProgress,
  Tabs,
  Tab,
} from '@mui/material'
import { invoiceService } from '../../services/invoiceService'
import { format } from 'date-fns'

function Invoices() {
  const [invoices, setInvoices] = useState([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState(0)

  useEffect(() => {
    fetchInvoices()
  }, [tab])

  const fetchInvoices = async () => {
    try {
      setLoading(true)
      let data
      if (tab === 1) {
        data = await invoiceService.getOverdue(30)
      } else {
        data = await invoiceService.getAll()
      }
      setInvoices(data)
    } catch (error) {
      console.error('Error fetching invoices:', error)
    } finally {
      setLoading(false)
    }
  }

  const getStatusColor = (status) => {
    const colors = {
      pending: 'warning',
      paid: 'success',
      overdue: 'error',
      cancelled: 'default',
    }
    return colors[status] || 'default'
  }

  const formatDate = (dateString) => {
    if (!dateString) return '-'
    try {
      return format(new Date(dateString), 'dd/MM/yyyy')
    } catch {
      return dateString
    }
  }

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Factures
      </Typography>

      <Tabs value={tab} onChange={(e, newValue) => setTab(newValue)} sx={{ mb: 3 }}>
        <Tab label="Toutes les factures" />
        <Tab label="Factures en retard" />
      </Tabs>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Numéro</TableCell>
              <TableCell>Pharmacie</TableCell>
              <TableCell>Montant</TableCell>
              <TableCell>Date d'émission</TableCell>
              <TableCell>Date d'échéance</TableCell>
              <TableCell>Statut</TableCell>
              <TableCell>Jours de retard</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {invoices.map((invoice) => (
              <TableRow key={invoice.id} hover>
                <TableCell>{invoice.invoice_number}</TableCell>
                <TableCell>{invoice.pharmacy_id}</TableCell>
                <TableCell>{invoice.amount.toFixed(2)} €</TableCell>
                <TableCell>{formatDate(invoice.issue_date)}</TableCell>
                <TableCell>{formatDate(invoice.due_date)}</TableCell>
                <TableCell>
                  <Chip
                    label={invoice.status}
                    color={getStatusColor(invoice.status)}
                    size="small"
                  />
                </TableCell>
                <TableCell>
                  {invoice.days_overdue > 0 ? `${invoice.days_overdue} jours` : '-'}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  )
}

export default Invoices

