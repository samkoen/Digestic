import React, { useState } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  Grid,
  Chip,
  Divider,
  Card,
  CardContent,
  IconButton,
  Tooltip,
  CircularProgress,
  Alert,
} from '@mui/material'
import EmailIcon from '@mui/icons-material/Email'
import { format } from 'date-fns'
import api from '../../services/api'

function InvoiceDetail({ open, onClose, invoice, pharmacyEmail }) {
  const [sending, setSending] = useState(false)
  const [emailSent, setEmailSent] = useState(false)
  const [error, setError] = useState(null)
  if (!invoice) return null

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

  const handleSendEmail = async () => {
    if (!invoice || !pharmacyEmail) {
      setError('Email de la pharmacie non disponible')
      return
    }

    try {
      setSending(true)
      setError(null)
      setEmailSent(false)

      const response = await api.post(`/invoices/${invoice.id}/send-email`)
      
      if (response.data.message) {
        setEmailSent(true)
        setTimeout(() => {
          setEmailSent(false)
        }, 3000)
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Erreur lors de l\'envoi de l\'email')
    } finally {
      setSending(false)
    }
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h6">Détail de la Facture</Typography>
          {pharmacyEmail && (
            <Tooltip title={`Envoyer la facture par email à ${pharmacyEmail}`}>
              <IconButton
                color="primary"
                onClick={handleSendEmail}
                disabled={sending || emailSent}
                sx={{ ml: 2 }}
              >
                {sending ? <CircularProgress size={24} /> : <EmailIcon />}
              </IconButton>
            </Tooltip>
          )}
        </Box>
      </DialogTitle>
      <DialogContent>
        {emailSent && (
          <Alert severity="success" sx={{ mb: 2 }}>
            Facture envoyée avec succès à {pharmacyEmail}
          </Alert>
        )}
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        <Box sx={{ mt: 2 }}>
          <Card variant="outlined" sx={{ mb: 2 }}>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h6">
                  {invoice.invoice_number}
                </Typography>
                <Chip
                  label={getStatusLabel(invoice.status)}
                  color={getStatusColor(invoice.status)}
                  size="medium"
                />
              </Box>
              <Divider sx={{ mb: 2 }} />
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <Typography variant="body2" color="text.secondary">
                    Montant
                  </Typography>
                  <Typography variant="h5" fontWeight="bold" color="primary">
                    {invoice.amount.toFixed(2)} €
                  </Typography>
                </Grid>
                {invoice.days_overdue > 0 && (
                  <Grid item xs={12} sm={6}>
                    <Typography variant="body2" color="text.secondary">
                      Jours de retard
                    </Typography>
                    <Typography variant="h6" color="error">
                      {invoice.days_overdue} jours
                    </Typography>
                  </Grid>
                )}
              </Grid>
            </CardContent>
          </Card>

          <Card variant="outlined" sx={{ mb: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Dates
              </Typography>
              <Divider sx={{ mb: 2 }} />
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <Typography variant="body2" color="text.secondary">
                    Date d'émission
                  </Typography>
                  <Typography variant="body1" fontWeight="medium">
                    {formatDate(invoice.issue_date)}
                  </Typography>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Typography variant="body2" color="text.secondary">
                    Date d'échéance
                  </Typography>
                  <Typography variant="body1" fontWeight="medium">
                    {formatDate(invoice.due_date)}
                  </Typography>
                </Grid>
                {invoice.payment_date && (
                  <Grid item xs={12} sm={6}>
                    <Typography variant="body2" color="text.secondary">
                      Date de paiement
                    </Typography>
                    <Typography variant="body1" fontWeight="medium" color="success.main">
                      {formatDate(invoice.payment_date)}
                    </Typography>
                  </Grid>
                )}
              </Grid>
            </CardContent>
          </Card>

          {invoice.sage_reference && (
            <Card variant="outlined">
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Informations Sage
                </Typography>
                <Divider sx={{ mb: 2 }} />
                <Typography variant="body2" color="text.secondary">
                  Référence Sage
                </Typography>
                <Typography variant="body1" fontWeight="medium">
                  {invoice.sage_reference}
                </Typography>
              </CardContent>
            </Card>
          )}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Fermer</Button>
      </DialogActions>
    </Dialog>
  )
}

export default InvoiceDetail

