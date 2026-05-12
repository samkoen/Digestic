import React, { useCallback, useEffect, useState } from 'react'
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
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  TableContainer,
} from '@mui/material'
import EmailIcon from '@mui/icons-material/Email'
import ReceiptLongIcon from '@mui/icons-material/ReceiptLong'
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf'
import PaymentsIcon from '@mui/icons-material/Payments'
import NotificationsActiveOutlinedIcon from '@mui/icons-material/NotificationsActiveOutlined'
import { format } from 'date-fns'
import { creditNoteService } from '../../services/creditNoteService'
import { invoiceService } from '../../services/invoiceService'
import IssueTotalCreditNoteDialog from '../InvoiceTable/IssueTotalCreditNoteDialog'
import MarkInvoicePaidDialog from '../InvoiceTable/MarkInvoicePaidDialog'
import SendEmailComposerDialog from '../SendEmailComposerDialog/SendEmailComposerDialog'
import { canIssueTotalCreditNote, canMarkInvoicePaid, canOfferUnpaidReminderAction, canSendUnpaidReminder } from '../../utils/invoiceCreditNoteEligibility'

function formatEuro(n) {
  if (n == null || n === '' || Number.isNaN(Number(n))) return '—'
  return `${Number(n).toFixed(2)}\u00A0€`
}

function InvoiceDetail({
  open,
  onClose,
  invoice,
  pharmacyEmail,
  onCreditNotesChanged,
  onInvoicePatched,
}) {
  const [emailComposerOpen, setEmailComposerOpen] = useState(false)
  const [emailDraft, setEmailDraft] = useState(null)
  const [emailDraftLoading, setEmailDraftLoading] = useState(false)
  const [emailDraftError, setEmailDraftError] = useState(null)
  const [emailComposeSending, setEmailComposeSending] = useState(false)
  const [emailComposeSendError, setEmailComposeSendError] = useState(null)
  const [bannerSuccess, setBannerSuccess] = useState(null)
  const [error, setError] = useState(null)

  const [creditNotes, setCreditNotes] = useState([])
  const [creditNotesLoading, setCreditNotesLoading] = useState(false)
  const [issueDialogOpen, setIssueDialogOpen] = useState(false)
  const [markPaidDialogOpen, setMarkPaidDialogOpen] = useState(false)
  const [pdfLoadingCnId, setPdfLoadingCnId] = useState(null)
  const [unpaidReminderSending, setUnpaidReminderSending] = useState(false)

  const loadCreditNotes = useCallback(async () => {
    if (!invoice?.id) return
    setCreditNotesLoading(true)
    try {
      const list = await creditNoteService.listByInvoiceId(invoice.id)
      setCreditNotes(list)
    } catch (e) {
      console.error(e)
      setCreditNotes([])
    } finally {
      setCreditNotesLoading(false)
    }
  }, [invoice?.id])

  const resetInvoiceEmailComposer = useCallback(() => {
    setEmailComposerOpen(false)
    setEmailDraft(null)
    setEmailDraftError(null)
    setEmailComposeSendError(null)
    setEmailDraftLoading(false)
    setEmailComposeSending(false)
  }, [])

  const openInvoiceEmailComposer = useCallback(async () => {
    if (!invoice?.id || !String(pharmacyEmail || '').trim()) {
      setError('Email de la pharmacie non disponible')
      return
    }
    setError(null)
    setEmailComposerOpen(true)
    setEmailDraft(null)
    setEmailDraftError(null)
    setEmailComposeSendError(null)
    setEmailDraftLoading(true)
    try {
      const d = await invoiceService.getEmailDraft(invoice.id)
      setEmailDraft(d)
    } catch (err) {
      setEmailDraftError(err.response?.data?.error || err.message || 'Impossible de charger le brouillon')
    } finally {
      setEmailDraftLoading(false)
    }
  }, [invoice?.id, pharmacyEmail])

  const handleConfirmInvoiceEmail = useCallback(
    async ({ subject, body_html }) => {
      if (!invoice?.id) {
        return
      }
      setEmailComposeSendError(null)
      setEmailComposeSending(true)
      try {
        const res = await invoiceService.sendEmail(invoice.id, { subject, body_html })
        if (res?.message || res?.email) {
          setBannerSuccess(res.message || (res.email ? `Facture envoyée avec succès à ${res.email}` : null))
          setTimeout(() => {
            setBannerSuccess(null)
          }, 4000)
        }
        resetInvoiceEmailComposer()
      } catch (err) {
        setEmailComposeSendError(err.response?.data?.error || "Erreur lors de l'envoi de l'email")
      } finally {
        setEmailComposeSending(false)
      }
    },
    [invoice?.id, resetInvoiceEmailComposer],
  )

  const handleSendUnpaidReminder = useCallback(async () => {
    if (!invoice?.id) return
    setError(null)
    setUnpaidReminderSending(true)
    try {
      const res = await invoiceService.sendUnpaidReminderEmail(invoice.id)
      setBannerSuccess(
        res?.message ||
          (res?.email ? `Relance impayée envoyée à ${res.email}` : 'Relance impayée envoyée.'),
      )
      if (typeof onInvoicePatched === 'function') {
        const refreshed = await invoiceService.getById(invoice.id)
        onInvoicePatched(refreshed)
      }
      if (!(res?.message || res?.email)) {
        console.info('Relance envoyée', res)
      }
      setTimeout(() => {
        setBannerSuccess(null)
      }, 5000)
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Impossible d’envoyer la relance')
    } finally {
      setUnpaidReminderSending(false)
    }
  }, [invoice?.id, onInvoicePatched])

  useEffect(() => {
    if (!open) {
      resetInvoiceEmailComposer()
      setBannerSuccess(null)
      setError(null)
    }
  }, [open, resetInvoiceEmailComposer])

  useEffect(() => {
    resetInvoiceEmailComposer()
  }, [invoice?.id, resetInvoiceEmailComposer])

  useEffect(() => {
    if (!open || !invoice?.id) {
      return undefined
    }
    setIssueDialogOpen(false)
    setMarkPaidDialogOpen(false)
    void loadCreditNotes()
    return undefined
  }, [open, invoice?.id, loadCreditNotes])

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
      credited: 'info',
    }
    return colors[status] || 'default'
  }

  const getStatusLabel = (status) => {
    const labels = {
      paid: 'Payée',
      pending: 'En attente',
      overdue: 'En retard',
      cancelled: 'Annulée',
      credited: 'Avoir émis',
    }
    return labels[status] || status
  }

  const eligibleAvoir = canIssueTotalCreditNote(invoice)
  const eligibleMarkPaid = canMarkInvoicePaid(invoice)
  const showUnpaidReminder = Boolean(pharmacyEmail?.trim()) && canOfferUnpaidReminderAction(invoice)
  const unpaidReminderCanSend = showUnpaidReminder && canSendUnpaidReminder(invoice)

  const handleDownloadCnPdf = async (cnId) => {
    try {
      setPdfLoadingCnId(cnId)
      await creditNoteService.downloadVosFacturesPdf(cnId)
    } catch (e) {
      setError(e.message || 'PDF avoir indisponible')
    } finally {
      setPdfLoadingCnId(null)
    }
  }

  return (
    <>
      <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
        <DialogTitle>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Typography variant="h6">Détail de la facture</Typography>
            {pharmacyEmail && (
              <Tooltip title={`Préparer l’e-mail (aperçu et édition) — ${pharmacyEmail}`}>
                <IconButton
                  color="primary"
                  onClick={() => void openInvoiceEmailComposer()}
                  disabled={Boolean(bannerSuccess) || emailComposerOpen}
                  sx={{ ml: 2 }}
                  aria-label="Préparer l'envoi de la facture par e-mail"
                >
                  <EmailIcon />
                </IconButton>
              </Tooltip>
            )}
          </Box>
        </DialogTitle>
        <DialogContent>
          {bannerSuccess && (
            <Alert severity="success" sx={{ mb: 2 }}>
              {bannerSuccess}
            </Alert>
          )}
          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}
          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              Pour émettre un avoir (total ou partiel) depuis la vue globale, utilisez également la liste{' '}
              <strong>Factures</strong> (icône ticket à côté du PDF dans la colonne Actions).
            </Typography>
            <Card variant="outlined" sx={{ mb: 2 }}>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                  <Typography variant="h6">{invoice.invoice_number}</Typography>
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
                  {invoice.days_overdue > 0 &&
                    String(invoice.status || '')
                      .toLowerCase()
                      .trim() !== 'credited' &&
                    String(invoice.status || '')
                      .toLowerCase()
                      .trim() !== 'paid' && (
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
                {(eligibleMarkPaid || showUnpaidReminder) && (
                  <Box sx={{ mt: 2, display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                    {eligibleMarkPaid && (
                      <Button
                        variant="contained"
                        color="success"
                        size="small"
                        startIcon={<PaymentsIcon />}
                        onClick={() => setMarkPaidDialogOpen(true)}
                      >
                        Marquer comme payée
                      </Button>
                    )}
                    {showUnpaidReminder && (
                      <Tooltip
                        title={
                          unpaidReminderCanSend
                            ? `Modèle admin « Rappel de facture impayée » — ${pharmacyEmail ?? ''}`
                            : 'Échéance encore à jour : la relance n’est envoyée qu’au moins un jour après l’échéance.'
                        }
                      >
                        <span>
                          <Button
                            variant="outlined"
                            color="warning"
                            size="small"
                            startIcon={
                              unpaidReminderSending ? (
                                <CircularProgress size={18} color="inherit" />
                              ) : (
                                <NotificationsActiveOutlinedIcon />
                              )
                            }
                            onClick={() => void handleSendUnpaidReminder()}
                            disabled={
                              Boolean(bannerSuccess) ||
                              unpaidReminderSending ||
                              emailComposerOpen ||
                              !unpaidReminderCanSend
                            }
                          >
                            Relance impayée (e-mail)
                          </Button>
                        </span>
                      </Tooltip>
                    )}
                  </Box>
                )}
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
                      Date d&apos;émission
                    </Typography>
                    <Typography variant="body1" fontWeight="medium">
                      {formatDate(invoice.issue_date)}
                    </Typography>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Typography variant="body2" color="text.secondary">
                      Date d&apos;échéance
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
              <Card variant="outlined" sx={{ mb: 2 }}>
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

            <Card variant="outlined" sx={{ mb: 2 }}>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={2} flexWrap="wrap" gap={1}>
                    <Typography variant="h6">Avoirs (VosFactures)</Typography>
                  <Tooltip
                    title={
                      !eligibleAvoir ? 'Facture avec identifiant VosFactures requis pour un avoir.' : ''
                    }
                  >
                    <span>
                      <Button
                        size="small"
                        variant="outlined"
                        startIcon={<ReceiptLongIcon />}
                        disabled={!eligibleAvoir}
                        onClick={() => setIssueDialogOpen(true)}
                      >
                        Nouvel avoir VF
                      </Button>
                    </span>
                  </Tooltip>
                </Box>
                <Alert severity="info" sx={{ mb: 2 }}>
                  Les avoirs sont créés dans VosFactures avec votre motif ; Digestic enregistre la trace (total ou partiel :
                  lignes sélectionnables dans le dialogue).
                </Alert>
                {creditNotesLoading ? (
                  <Box display="flex" justifyContent="center" py={2}>
                    <CircularProgress size={28} />
                  </Box>
                ) : creditNotes.length === 0 ? (
                  <Typography variant="body2" color="text.secondary">
                    Aucun avoir enregistré pour cette facture.
                  </Typography>
                ) : (
                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Type</TableCell>
                          <TableCell>N° avoir</TableCell>
                          <TableCell>Émission</TableCell>
                          <TableCell align="right">Montant TTC</TableCell>
                          <TableCell>Motif</TableCell>
                          <TableCell align="right">PDF</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {creditNotes.map((cn) => (
                          <TableRow key={cn.id}>
                            <TableCell>
                              {(cn.credit_scope || 'full') === 'partial' ? (
                                <Chip size="small" label="Partiel" color="secondary" variant="outlined" />
                              ) : (
                                <Chip size="small" label="Total" variant="outlined" />
                              )}
                            </TableCell>
                            <TableCell>{cn.credit_note_number}</TableCell>
                            <TableCell>{formatDate(cn.issue_date)}</TableCell>
                            <TableCell align="right">{formatEuro(cn.amount_ttc)}</TableCell>
                            <TableCell>
                              <Typography variant="body2" noWrap title={cn.reason || ''} sx={{ maxWidth: 200 }}>
                                {cn.reason || '—'}
                              </Typography>
                            </TableCell>
                            <TableCell align="right">
                              {cn.external_provider === 'vosfactures' ? (
                                <Tooltip title="Télécharger PDF (VosFactures)">
                                  <IconButton
                                    size="small"
                                    onClick={() => handleDownloadCnPdf(cn.id)}
                                    disabled={pdfLoadingCnId === cn.id}
                                  >
                                    {pdfLoadingCnId === cn.id ? (
                                      <CircularProgress size={22} />
                                    ) : (
                                      <PictureAsPdfIcon fontSize="small" />
                                    )}
                                  </IconButton>
                                </Tooltip>
                              ) : (
                                <Typography variant="caption" color="text.secondary">
                                  mock
                                </Typography>
                              )}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                )}
              </CardContent>
            </Card>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Fermer</Button>
        </DialogActions>
      </Dialog>

      <IssueTotalCreditNoteDialog
        open={issueDialogOpen}
        invoice={invoice}
        onClose={() => setIssueDialogOpen(false)}
        onSuccess={() => {
          void loadCreditNotes()
          if (typeof onCreditNotesChanged === 'function') {
            onCreditNotesChanged()
          }
        }}
      />

      <MarkInvoicePaidDialog
        open={markPaidDialogOpen}
        invoice={invoice}
        onClose={() => setMarkPaidDialogOpen(false)}
        onSuccess={(updated) => {
          if (updated && typeof onInvoicePatched === 'function') {
            onInvoicePatched(updated)
          }
          if (typeof onCreditNotesChanged === 'function') {
            onCreditNotesChanged()
          }
        }}
      />

      <SendEmailComposerDialog
        open={emailComposerOpen}
        title="Envoyer la facture par e-mail"
        onClose={() => {
          if (!emailComposeSending) {
            resetInvoiceEmailComposer()
          }
        }}
        draftLoading={emailDraftLoading}
        draftError={emailDraftError}
        draft={emailDraft}
        onSend={handleConfirmInvoiceEmail}
        sending={emailComposeSending}
        sendError={emailComposeSendError}
      />
    </>
  )
}

export default InvoiceDetail
