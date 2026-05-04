import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  IconButton,
  Typography,
  CircularProgress,
  Box,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
} from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'
import InvoiceCreditNoteBadge from '../InvoiceTable/InvoiceCreditNoteBadge'
import { format } from 'date-fns'
import { invoiceService } from '../../services/invoiceService'
import { deliveryNoteService } from '../../services/deliveryNoteService'
import { productService } from '../../services/productService'

/** Même logique que la liste BL pour une estimation indicative. */
function indicativeInvoiceTotals(bottles, product, pharmacyReductionPct = 0) {
  const n = Math.max(0, Number(bottles) || 0)
  if (!product || n <= 0) {
    return { ht: 0, vat: 0, ttc: 0 }
  }
  const rp = Math.max(0, Math.min(100, Number(pharmacyReductionPct) || 0))
  const factor = 1 - rp / 100
  const unitHt = Number(product.wholesale_unit_price) || 0
  const vatRate = Number(product.vat_rate) || 0
  const lht = Math.round(n * unitHt * factor * 10000) / 10000
  const lvat = Math.round(lht * (vatRate / 100) * 10000) / 10000
  const totalHt = Math.round(lht * 100) / 100
  const totalVat = Math.round(lvat * 100) / 100
  const ttc = Math.round((totalHt + totalVat) * 100) / 100
  return { ht: totalHt, vat: totalVat, ttc }
}

function formatEuro(n) {
  if (n == null || n === '' || Number.isNaN(Number(n))) return '—'
  return `${Number(n).toFixed(2)}\u00A0€`
}

function formatIssueDate(raw) {
  if (!raw) return '—'
  try {
    return format(new Date(raw), 'dd/MM/yyyy')
  } catch {
    return String(raw).slice(0, 10)
  }
}

function getStatusChipProps(status) {
  const labels = {
    paid: 'Payée',
    pending: 'En attente',
    overdue: 'En retard',
    cancelled: 'Annulée',
    credited: 'Avoir émis',
  }
  const colors = {
    paid: 'success',
    pending: 'warning',
    overdue: 'error',
    cancelled: 'default',
    credited: 'info',
  }
  return {
    label: labels[status] || status,
    color: colors[status] || 'default',
  }
}

/** Bons à afficher dans la modale : en attente (≥1 btl) ou tout dépôt-vente en attente de validation. */
function isBonEnAttenteOuDepotVente(note) {
  const st = note.status
  if (st === 'depot-vente') return true
  const qty = note.bottles_count || 0
  return st === 'pending' && qty >= 1
}

function blChipForPharmacyPendingModal(note) {
  if (note.status === 'depot-vente') {
    return { label: 'Dépôt-vente', color: 'secondary' }
  }
  return { label: 'Bon en attente', color: 'warning' }
}

function dateToSortMs(raw) {
  if (!raw) return 0
  const t = new Date(raw).getTime()
  return Number.isFinite(t) ? t : 0
}

/** Liste Factures : URL avec filtres pour centrer la ligne pertinente. */
function invoiceRowToFacturesSearchPath(inv) {
  const parts = []
  const depositId = (inv.deposit_id || '').trim()
  const pharmacyId = (inv.pharmacy_id || '').trim()
  const num = (inv.invoice_number || '').trim()
  if (depositId) parts.push(`deposit_id=${encodeURIComponent(depositId)}`)
  else if (pharmacyId) parts.push(`pharmacy_id=${encodeURIComponent(pharmacyId)}`)
  if (num) parts.push(`invoice_number=${encodeURIComponent(num)}`)
  if (!parts.length) return '/invoices'
  return `/invoices?${parts.join('&')}`
}

const INVOICE_SINGLE_CLICK_DELAY_MS = 260

function InvoiceList({ open, onClose, pharmacyId, onSelectInvoice, pharmacyEmail, pharmacyReduction }) {
  const navigate = useNavigate()
  const invoiceSingleClickTimerRef = useRef(null)
  const [invoices, setInvoices] = useState([])
  const [loadingInvoices, setLoadingInvoices] = useState(true)
  const [deliveryNotes, setDeliveryNotes] = useState([])
  const [loadingBl, setLoadingBl] = useState(true)
  const [billingProduct, setBillingProduct] = useState(null)

  const rpct = pharmacyReduction != null ? Number(pharmacyReduction) : 0

  useEffect(() => {
    if (!open || !pharmacyId) return
    let c = false
    ;(async () => {
      try {
        const list = await productService.list({ active_only: true })
        if (c) return
        const def = list.find((p) => p.is_default_for_billing) || list[0] || null
        setBillingProduct(def)
      } catch (e) {
        console.error(e)
        if (!c) setBillingProduct(null)
      }
    })()
    return () => {
      c = true
    }
  }, [open, pharmacyId])

  useEffect(() => {
    if (!open || !pharmacyId) return undefined
    let cancelled = false
    ;(async () => {
      try {
        setLoadingInvoices(true)
        const data = await invoiceService.getAll({ pharmacy_id: pharmacyId })
        if (!cancelled) setInvoices(Array.isArray(data) ? data : [])
      } catch (e) {
        console.error(e)
        if (!cancelled) setInvoices([])
      } finally {
        if (!cancelled) setLoadingInvoices(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [open, pharmacyId])

  useEffect(() => {
    if (!open || !pharmacyId) return undefined
    let cancelled = false
    ;(async () => {
      try {
        setLoadingBl(true)
        const data = await deliveryNoteService.getAll({ pharmacy_id: pharmacyId })
        if (!cancelled) setDeliveryNotes(Array.isArray(data) ? data : [])
      } catch (e) {
        console.error(e)
        if (!cancelled) setDeliveryNotes([])
      } finally {
        if (!cancelled) setLoadingBl(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [open, pharmacyId])

  const unifiedRows = useMemo(() => {
    const pendingBls = deliveryNotes
      .filter(isBonEnAttenteOuDepotVente)
      .sort((a, b) => dateToSortMs(b.delivery_date) - dateToSortMs(a.delivery_date))

    const invSorted = [...invoices].sort(
      (a, b) => dateToSortMs(b.issue_date) - dateToSortMs(a.issue_date),
    )

    const out = []
    for (const note of pendingBls) {
      out.push({ kind: 'bl', key: `bl-${note.id}`, note })
    }
    for (const inv of invSorted) {
      out.push({ kind: 'invoice', key: `inv-${inv.id}`, invoice: inv })
    }
    return out
  }, [deliveryNotes, invoices])

  const clearInvoiceClickTimer = useCallback(() => {
    if (invoiceSingleClickTimerRef.current != null) {
      clearTimeout(invoiceSingleClickTimerRef.current)
      invoiceSingleClickTimerRef.current = null
    }
  }, [])

  useEffect(
    () => () => clearInvoiceClickTimer(),
    [clearInvoiceClickTimer],
  )

  useEffect(() => {
    if (!open) {
      clearInvoiceClickTimer()
    }
  }, [open, clearInvoiceClickTimer])

  const openBonLivraisonPage = useCallback(
    (note) => {
      const id = (note?.id || '').trim()
      if (!id) return
      navigate(`/delivery-notes?deposit_id=${encodeURIComponent(id)}`)
      onClose?.()
    },
    [navigate, onClose],
  )

  const openFacturesPageForInvoice = useCallback(
    (inv) => {
      navigate(invoiceRowToFacturesSearchPath(inv))
      onClose?.()
    },
    [navigate, onClose],
  )

  const handleInvoiceRowClick = useCallback(
    (inv) => (e) => {
      if (!onSelectInvoice) return
      if (e.detail > 1) return
      clearInvoiceClickTimer()
      invoiceSingleClickTimerRef.current = setTimeout(() => {
        invoiceSingleClickTimerRef.current = null
        onSelectInvoice(inv)
      }, INVOICE_SINGLE_CLICK_DELAY_MS)
    },
    [onSelectInvoice, clearInvoiceClickTimer],
  )

  const handleInvoiceRowDoubleClick = useCallback(
    (inv) => (e) => {
      e.preventDefault()
      clearInvoiceClickTimer()
      openFacturesPageForInvoice(inv)
    },
    [clearInvoiceClickTimer, openFacturesPageForInvoice],
  )

  const loading = loadingInvoices || loadingBl

  return (
    <Dialog open={open} onClose={onClose} maxWidth="xl" fullWidth>
      <DialogTitle sx={{ pr: 5 }}>
        Factures et bons en attente
        <IconButton
          aria-label="fermer"
          onClick={onClose}
          sx={{ position: 'absolute', right: 8, top: 8 }}
          size="small"
        >
          <CloseIcon fontSize="small" />
        </IconButton>
      </DialogTitle>
      <DialogContent>
        {!pharmacyEmail ? null : (
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
            Contact lié&nbsp;: {pharmacyEmail}
          </Typography>
        )}
        <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
          Les <strong>bons</strong> (<em>en attente</em> avec au moins une bouteille, ou tout bon en{' '}
          <em>dépôt-vente</em>) sont listés en premier (date de livraison, du plus récent au plus ancien), puis les{' '}
          <strong>factures</strong> (date d&apos;émission, même ordre). Montants BL{' '}
          <strong>indicatifs</strong> — réduction pharmacie&nbsp;{(Number.isFinite(rpct) ? rpct : 0).toFixed(2)}
          %.
        </Typography>
        <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
          <strong>Double-clic</strong> sur une ligne ouvre la page <strong>Bons de livraison</strong> ou{' '}
          <strong>Factures</strong> préfiltrée sur ce document ; un clic simple sur une facture ouvre
          l&apos;aperçu local.
        </Typography>

        {loading ? (
          <Box display="flex" justifyContent="center" py={4}>
            <CircularProgress />
          </Box>
        ) : unifiedRows.length === 0 ? (
          <Typography variant="body2" color="text.secondary" sx={{ py: 3 }}>
            Aucune facture ni bon (en attente, dépôt-vente avec bouteilles, etc.) pour cette pharmacie.
          </Typography>
        ) : (
          <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 480 }}>
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 700 }}>N° facture&nbsp;/ BL</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Date</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Statut</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 700 }}>
                    Qté (bouteilles)
                  </TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>Remise</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 700 }}>
                    Montant&nbsp;HT
                  </TableCell>
                  <TableCell align="right" sx={{ fontWeight: 700 }}>
                    Montant&nbsp;TTC
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {unifiedRows.map((row) => {
                  if (row.kind === 'bl') {
                    const note = row.note
                    const est =
                      billingProduct &&
                      indicativeInvoiceTotals(note.bottles_count, billingProduct, rpct)
                    const remise =
                      Number.isFinite(rpct) && rpct > 0 ? `${rpct}% (pharmacie)` : '—'
                    const blChip = blChipForPharmacyPendingModal(note)
                    return (
                      <TableRow
                        key={row.key}
                        hover
                        onDoubleClick={(e) => {
                          e.stopPropagation()
                          openBonLivraisonPage(note)
                        }}
                        sx={{
                          bgcolor: 'action.hover',
                          cursor: 'pointer',
                        }}
                      >
                        <TableCell sx={{ whiteSpace: 'nowrap', fontFamily: 'monospace', fontSize: '0.8rem' }}>
                          {note.bl_number || 'BL'}
                        </TableCell>
                        <TableCell>{formatIssueDate(note.delivery_date)}</TableCell>
                        <TableCell>
                          <Chip label={blChip.label} color={blChip.color} size="small" />
                        </TableCell>
                        <TableCell align="right">{note.bottles_count ?? 0}</TableCell>
                        <TableCell>{remise}</TableCell>
                        <TableCell align="right">{est ? formatEuro(est.ht) : '—'}</TableCell>
                        <TableCell align="right">{est ? formatEuro(est.ttc) : '—'}</TableCell>
                      </TableRow>
                    )
                  }

                  const inv = row.invoice
                  const qty = Number(inv.paying_bottles ?? 0)
                  const rem =
                    inv.line_discount_percent != null && Number(inv.line_discount_percent) > 0
                      ? `${Number(inv.line_discount_percent).toLocaleString('fr-FR')}\u202F%`
                      : '—'
                  const ht = inv.amount_ht != null ? inv.amount_ht : null
                  const ttc =
                    inv.amount_ttc != null ? inv.amount_ttc : inv.amount != null ? inv.amount : null
                  const st = getStatusChipProps(inv.status)

                  return (
                    <TableRow
                      key={row.key}
                      hover
                      {...(onSelectInvoice ? { onClick: handleInvoiceRowClick(inv) } : {})}
                      onDoubleClick={handleInvoiceRowDoubleClick(inv)}
                      sx={{
                        cursor: 'pointer',
                        '&:last-child td': { borderBottom: 0 },
                      }}
                    >
                      <TableCell sx={{ whiteSpace: 'nowrap' }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', minWidth: 0 }}>
                          <Typography
                            variant="body2"
                            fontWeight="medium"
                            component="span"
                            noWrap
                            sx={{ minWidth: 0 }}
                          >
                            {inv.invoice_number}
                          </Typography>
                          <InvoiceCreditNoteBadge show={Boolean(inv.has_credit_notes)} />
                        </Box>
                        {inv.deposit_bl_number ? (
                          <Typography variant="caption" color="text.secondary">
                            BL {inv.deposit_bl_number}
                          </Typography>
                        ) : null}
                      </TableCell>
                      <TableCell>{formatIssueDate(inv.issue_date)}</TableCell>
                      <TableCell>
                        <Chip label={st.label} color={st.color} size="small" />
                        {inv.status !== 'paid' &&
                        inv.status !== 'credited' &&
                        inv.days_overdue > 0 ? (
                          <Typography variant="caption" color="error" display="block">
                            Retard&nbsp;: {inv.days_overdue}&nbsp;j
                          </Typography>
                        ) : null}
                      </TableCell>
                      <TableCell align="right">{qty}</TableCell>
                      <TableCell>{rem}</TableCell>
                      <TableCell align="right">{formatEuro(ht)}</TableCell>
                      <TableCell align="right">{formatEuro(ttc)}</TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </DialogContent>
    </Dialog>
  )
}

export default InvoiceList
