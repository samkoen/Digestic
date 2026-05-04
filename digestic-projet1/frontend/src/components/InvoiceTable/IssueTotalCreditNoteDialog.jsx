import React, { useCallback, useEffect, useMemo, useState } from 'react'
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
  Tabs,
  Tab,
  Box,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
} from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'
import { creditNoteService } from '../../services/creditNoteService'
import { invoiceService } from '../../services/invoiceService'

function TabPanel({ hidden, children }) {
  if (hidden) return null
  return (
    <Box sx={{ pt: 2 }} role="tabpanel">
      {children}
    </Box>
  )
}

/** Dialogue : avoir total ou partiel VosFactures pour une facture. */
export default function IssueTotalCreditNoteDialog({ open, invoice, onClose, onSuccess }) {
  const [tab, setTab] = useState(0)
  const [motif, setMotif] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  const [lines, setLines] = useState([])
  const [linesLoading, setLinesLoading] = useState(false)
  const [qtyByLineId, setQtyByLineId] = useState(() => ({}))

  useEffect(() => {
    if (open && invoice?.id) {
      setTab(0)
      setMotif('')
      setError(null)
      setSubmitting(false)
      setQtyByLineId({})
      setLines([])
    }
  }, [open, invoice?.id])

  useEffect(() => {
    if (!open || !invoice?.id) return undefined
    let cancelled = false
    ;(async () => {
      setLinesLoading(true)
      try {
        const data = await invoiceService.getLinesForCredit(invoice.id)
        if (!cancelled) {
          setLines(Array.isArray(data) ? data : [])
          const init = {}
          for (const row of data || []) {
            init[row.invoice_line_id] = ''
          }
          setQtyByLineId(init)
        }
      } catch {
        if (!cancelled) setLines([])
      } finally {
        if (!cancelled) setLinesLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [open, invoice?.id])

  const payableLines = useMemo(
    () =>
      (lines || []).filter((l) => !l.is_free_unit && Number(l.quantity_remaining || 0) > 0),
    [lines],
  )

  const setQty = useCallback((lineId, raw) => {
    setQtyByLineId((prev) => ({ ...prev, [lineId]: raw }))
  }, [])

  const hasPartialSelection = useMemo(() => {
    for (const l of payableLines) {
      const q = parseInt(String(qtyByLineId[l.invoice_line_id] ?? '').trim(), 10)
      if (Number.isFinite(q) && q > 0) return true
    }
    return false
  }, [payableLines, qtyByLineId])

  const submitTotal = async () => {
    const r = motif.trim()
    if (r.length < 3) {
      setError('Motif trop court (minimum 3 caractères).')
      return
    }
    try {
      setSubmitting(true)
      setError(null)
      await creditNoteService.issue(invoice.id, { correction_reason: r })
      onSuccess?.()
      onClose?.()
    } catch (err) {
      const msg =
        err.response?.data?.error || err.message || "Impossible d'émettre l'avoir (VosFactures)."
      setError(msg)
    } finally {
      setSubmitting(false)
    }
  }

  const submitPartial = async () => {
    const r = motif.trim()
    if (r.length < 3) {
      setError('Motif trop court (minimum 3 caractères).')
      return
    }
    const partial_lines = []
    for (const l of payableLines) {
      const q = parseInt(String(qtyByLineId[l.invoice_line_id] ?? '').trim(), 10)
      if (!Number.isFinite(q) || q <= 0) continue
      const max = Number(l.quantity_remaining || 0)
      if (q > max) {
        setError(
          `Quantité trop élevée pour « ${l.product_name || 'ligne'} » : maximum ${max} unité(s) créditable(s).`,
        )
        return
      }
      partial_lines.push({ invoice_line_id: l.invoice_line_id, quantity: q })
    }
    if (partial_lines.length === 0) {
      setError('Indiquez au moins une quantité à créditer sur une ligne.')
      return
    }
    try {
      setSubmitting(true)
      setError(null)
      await creditNoteService.issue(invoice.id, {
        correction_reason: r,
        partial_lines,
      })
      onSuccess?.()
      onClose?.()
    } catch (err) {
      const msg =
        err.response?.data?.error || err.message || "Impossible d'émettre l'avoir partiel (VosFactures)."
      setError(msg)
    } finally {
      setSubmitting(false)
    }
  }

  const submit = () => {
    if (tab === 0) void submitTotal()
    else void submitPartial()
  }

  const motifOk = motif.trim().length >= 3

  const disableSubmit =
    submitting ||
    !motifOk ||
    (tab === 1 &&
      (linesLoading || payableLines.length === 0 || !hasPartialSelection))

  if (!invoice) {
    return null
  }

  return (
    <Dialog open={Boolean(open)} onClose={() => !submitting && onClose?.()} maxWidth="md" fullWidth>
      <DialogTitle>
        Avoir VosFactures — {invoice.invoice_number}
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
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tab label="Avoir total" />
          <Tab label="Avoir partiel" />
        </Tabs>

        <TabPanel hidden={tab !== 0}>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Annule la facture en totalité côté VosFactures (la facture Digestic passera en statut « Avoir émis »).
            Indiquez le motif (retour complet, annulation, etc.).
          </Typography>
        </TabPanel>

        <TabPanel hidden={tab !== 1}>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Crédite une partie des quantités payantes (lignes avec TVA). Les unités gratuites ne sont pas concernées.
            Les quantités déjà couvertes par des avoirs partiels précédents sont déduites automatiquement.
          </Typography>
          {linesLoading ? (
            <Box display="flex" justifyContent="center" py={3}>
              <CircularProgress size={32} />
            </Box>
          ) : payableLines.length === 0 ? (
            <Alert severity="warning">
              Aucune ligne payante avec quantité restante à créditer. Utilisez l&apos;onglet « Avoir total » si
              applicable.
            </Alert>
          ) : (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Produit</TableCell>
                  <TableCell align="right">Facturé</TableCell>
                  <TableCell align="right">Déjà crédité</TableCell>
                  <TableCell align="right">Restant</TableCell>
                  <TableCell align="right" width={120}>
                    À créditer
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {payableLines.map((l) => (
                  <TableRow key={l.invoice_line_id}>
                    <TableCell>
                      <Typography variant="body2" noWrap title={l.product_name}>
                        {l.product_name}
                      </Typography>
                      {l.product_code ? (
                        <Typography variant="caption" color="text.secondary">
                          {l.product_code}
                        </Typography>
                      ) : null}
                    </TableCell>
                    <TableCell align="right">{l.quantity}</TableCell>
                    <TableCell align="right">{l.quantity_already_credited}</TableCell>
                    <TableCell align="right">{l.quantity_remaining}</TableCell>
                    <TableCell align="right">
                      <TextField
                        size="small"
                        type="number"
                        inputProps={{ min: 0, max: l.quantity_remaining, step: 1 }}
                        value={qtyByLineId[l.invoice_line_id] ?? ''}
                        onChange={(e) => setQty(l.invoice_line_id, e.target.value)}
                        sx={{ width: 88 }}
                      />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </TabPanel>

        <TextField
          label="Motif"
          multiline
          minRows={3}
          fullWidth
          required
          sx={{ mt: 2 }}
          value={motif}
          onChange={(e) => setMotif(e.target.value)}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={() => onClose?.()} disabled={submitting}>
          Annuler
        </Button>
        <Button variant="contained" onClick={() => void submit()} disabled={disableSubmit}>
          {submitting ? (
            <CircularProgress size={22} />
          ) : tab === 0 ? (
            'Émettre avoir total'
          ) : (
            'Émettre avoir partiel'
          )}
        </Button>
      </DialogActions>
    </Dialog>
  )
}
