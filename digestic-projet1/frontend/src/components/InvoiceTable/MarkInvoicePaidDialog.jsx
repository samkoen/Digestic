import React, { useEffect, useState } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  TextField,
  Alert,
  CircularProgress,
  IconButton,
  FormControlLabel,
  Checkbox,
} from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'
import { invoiceService } from '../../services/invoiceService'

/** YYYY-MM-DD pour le champ « date » : privilégie l’échéance (= délai 30/60 j du BL/pharmacie), sinon le jour courant. */
export function defaultPaymentDateForInvoice(inv) {
  if (!inv) return new Date().toISOString().slice(0, 10)
  const raw = inv.due_date
  if (raw != null && String(raw).trim()) {
    const s = String(raw).trim()
    if (/^\d{4}-\d{2}-\d{2}/.test(s)) {
      return s.slice(0, 10)
    }
    const parsed = new Date(s)
    if (!Number.isNaN(parsed.getTime())) {
      return parsed.toISOString().slice(0, 10)
    }
  }
  return new Date().toISOString().slice(0, 10)
}

/** Facture émise côté VosFactures réel (eligible sync paiement VF). */
export function isVosFacturesSyncedInvoice(inv) {
  if (!inv) return false
  const p = String(inv.external_provider || '')
    .toLowerCase()
    .trim()
  const extId = String(inv.external_invoice_id ?? '').trim()
  return p === 'vosfactures' && Boolean(extId)
}

/** Saisie manuelle : facture payée + date de règlement (modèle Digestic). */
export default function MarkInvoicePaidDialog({ open, invoice, onClose, onSuccess }) {
  const [paymentDate, setPaymentDate] = useState('')
  const [localOnly, setLocalOnly] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (open && invoice?.id) {
      setPaymentDate(defaultPaymentDateForInvoice(invoice))
      setLocalOnly(false)
      setError(null)
      setSubmitting(false)
    }
  }, [open, invoice?.id, invoice?.due_date])

  if (!invoice) return null

  /**
   * @param {boolean|undefined} digesticOnly - si défini : force ce mode (pour réessai après erreur VF)
   */
  const submit = async (digesticOnly) => {
    const sendDigesticOnly = typeof digesticOnly === 'boolean' ? digesticOnly : localOnly
    try {
      setSubmitting(true)
      setError(null)
      const payload = {}
      if (paymentDate && String(paymentDate).trim()) {
        payload.payment_date = String(paymentDate).trim().slice(0, 10)
      }
      if (sendDigesticOnly) {
        payload.local_only = true
      }
      const updated = await invoiceService.markPaid(invoice.id, payload)
      onSuccess?.(updated)
      onClose?.()
    } catch (err) {
      const msg =
        err.response?.data?.error || err.message || 'Impossible de marquer la facture comme payée.'
      setError(msg)
    } finally {
      setSubmitting(false)
    }
  }

  const showVfBypass = Boolean(error && isVosFacturesSyncedInvoice(invoice) && !localOnly)

  return (
    <Dialog open={Boolean(open)} onClose={() => !submitting && onClose?.()} maxWidth="xs" fullWidth>
      <DialogTitle>
        Marquer comme payée — {invoice.invoice_number}
        <IconButton
          aria-label="fermer"
          onClick={() => !submitting && onClose?.()}
          sx={{ position: 'absolute', right: 8, top: 8 }}
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      <DialogContent>
        {error && (
          <Alert
            severity="error"
            sx={{ mb: 2 }}
            action={
              showVfBypass ? (
                <Button
                  color="inherit"
                  size="small"
                  disabled={submitting}
                  onClick={() => {
                    setLocalOnly(true)
                    void submit(true)
                  }}
                >
                  Digestic seulement
                </Button>
              ) : null
            }
          >
            {error}
            {showVfBypass ? (
              <Typography variant="caption" display="block" sx={{ mt: 1 }}>
                La synchronisation avec VosFactures a peut-être échoué ; vous pouvez enregistrer le paiement
                uniquement dans Digestic puis régulariser VF manuellement.
              </Typography>
            ) : null}
          </Alert>
        )}
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Le statut passera à <strong>payée</strong> et la date de règlement sera enregistrée. Par défaut la date proposée
          est la <strong>date d&apos;échéance</strong> de la facture (alignée sur le mode de paiement 30 / 60 jours du flux
          BL/pharmacie). Si vous videz la date, le serveur utilise le jour courant.
        </Typography>
        {isVosFacturesSyncedInvoice(invoice) && (
          <Alert severity="info" sx={{ mb: 2 }}>
            Par défaut, un paiement est aussi enregistré sur VosFactures. Cochez l’option ci-dessous pour ne mettre à jour que Digestic (ex. échec API, solde déjà saisi sur VF).
          </Alert>
        )}
        <TextField
          label="Date de paiement"
          type="date"
          fullWidth
          InputLabelProps={{ shrink: true }}
          value={paymentDate}
          onChange={(e) => setPaymentDate(e.target.value)}
          sx={{ mb: 1 }}
        />
        {isVosFacturesSyncedInvoice(invoice) && (
          <FormControlLabel
            control={
              <Checkbox
                checked={localOnly}
                onChange={(e) => setLocalOnly(e.target.checked)}
                disabled={submitting}
              />
            }
            label="Uniquement Digestic (ne pas synchroniser VosFactures)"
          />
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={() => onClose?.()} disabled={submitting}>
          Annuler
        </Button>
        <Button variant="contained" color="success" onClick={() => void submit(undefined)} disabled={submitting}>
          {submitting ? <CircularProgress size={22} /> : 'Confirmer'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}
