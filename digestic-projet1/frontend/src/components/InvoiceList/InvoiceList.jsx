import React, { useEffect, useState } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Typography,
  CircularProgress,
  Box,
  Divider,
  Chip,
} from '@mui/material'
import { format } from 'date-fns'
import { invoiceService } from '../../services/invoiceService'

function InvoiceList({ open, onClose, pharmacyId, onSelectInvoice, pharmacyEmail }) {
  const [invoices, setInvoices] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (open && pharmacyId) {
      fetchInvoices()
    }
  }, [open, pharmacyId])

  const fetchInvoices = async () => {
    try {
      setLoading(true)
      const data = await invoiceService.getAll({ pharmacy_id: pharmacyId })
      // Trier par date d'émission décroissante (plus récent en premier)
      const sorted = data.sort((a, b) => 
        new Date(b.issue_date) - new Date(a.issue_date)
      )
      setInvoices(sorted)
    } catch (error) {
      console.error('Error fetching invoices:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateString) => {
    if (!dateString) return '-'
    try {
      return format(new Date(dateString), 'dd/MM/yyyy')
    } catch {
      return dateString
    }
  }

  const getStatusColor = (status) => {
    const colors = {
      paid: 'success',
      pending: 'warning',
      overdue: 'error',
      cancelled: 'default',
    }
    return colors[status] || 'default'
  }

  const getStatusLabel = (status) => {
    const labels = {
      paid: 'Payée',
      pending: 'En attente',
      overdue: 'En retard',
      cancelled: 'Annulée',
    }
    return labels[status] || status
  }

  const handleInvoiceClick = (invoice) => {
    if (onSelectInvoice) {
      onSelectInvoice(invoice)
    }
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Factures</DialogTitle>
      <DialogContent>
        {loading ? (
          <Box display="flex" justifyContent="center" p={3}>
            <CircularProgress />
          </Box>
        ) : invoices.length === 0 ? (
          <Typography variant="body2" color="text.secondary" sx={{ p: 2 }}>
            Aucune facture pour cette pharmacie
          </Typography>
        ) : (
          <List>
            {invoices.map((invoice, index) => (
              <React.Fragment key={invoice.id}>
                <ListItem disablePadding>
                  <ListItemButton onClick={() => handleInvoiceClick(invoice)}>
                    <ListItemText
                      primary={
                        <Box display="flex" alignItems="center" gap={1}>
                          <Typography variant="body1" fontWeight="medium">
                            {invoice.invoice_number}
                          </Typography>
                          <Chip
                            label={getStatusLabel(invoice.status)}
                            color={getStatusColor(invoice.status)}
                            size="small"
                          />
                        </Box>
                      }
                      secondary={
                        <Box>
                          <Typography variant="body2" color="text.secondary">
                            {formatDate(invoice.issue_date)} - {invoice.amount.toFixed(2)} €
                          </Typography>
                          {invoice.days_overdue > 0 && (
                            <Typography variant="caption" color="error">
                              {invoice.days_overdue} jours de retard
                            </Typography>
                          )}
                        </Box>
                      }
                    />
                  </ListItemButton>
                </ListItem>
                {index < invoices.length - 1 && <Divider />}
              </React.Fragment>
            ))}
          </List>
        )}
      </DialogContent>
    </Dialog>
  )
}

export default InvoiceList

