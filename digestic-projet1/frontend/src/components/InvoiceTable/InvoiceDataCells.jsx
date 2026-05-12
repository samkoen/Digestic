import React from 'react'
import {
  Chip,
  Link,
  Typography,
  CircularProgress,
  IconButton,
  Tooltip,
  TableCell,
  Box,
} from '@mui/material'
import { Link as RouterLink } from 'react-router-dom'
import DownloadIcon from '@mui/icons-material/Download'
import EmailOutlinedIcon from '@mui/icons-material/EmailOutlined'
import ReceiptLongIcon from '@mui/icons-material/ReceiptLong'
import PaymentsIcon from '@mui/icons-material/Payments'
import NotificationsActiveOutlinedIcon from '@mui/icons-material/NotificationsActiveOutlined'
import { canOfferUnpaidReminderAction, canSendUnpaidReminder } from '../../utils/invoiceCreditNoteEligibility'
import { AlignedTableCell } from '../ResizableTableColumns/ResizableHeaderCell'
import InvoiceCreditNoteBadge from './InvoiceCreditNoteBadge'

function getStatusColor(status) {
  const colors = {
    pending: 'warning',
    paid: 'success',
    overdue: 'error',
    cancelled: 'default',
    credited: 'info',
    avoir: 'secondary',
  }
  return colors[status] || 'default'
}

function getStatusLabel(status) {
  const m = {
    pending: 'En attente',
    paid: 'Payée',
    overdue: 'En retard',
    cancelled: 'Annulée',
    credited: 'Avoir émis',
    avoir: 'Avoir VF',
  }
  return m[status] || status
}

/**
 * @param {object} p
 * @param {object} p.invoice — to_dict + pharmacy_name
 * @param {object} p.ctx — formatDate, canDownloadVosFacturesPdf, canIssueTotalCreditNote, canMarkInvoicePaid, requestIssueCreditNote, requestMarkPaid, handleDownloadPdf, pdfLoadingId, navigateToPharmacy, pharmacyMap, handleOpenInvoiceEmailComposer, invEmailBusyRowId, invEmailOpen, invReminderSendingId, handleSendInvoiceUnpaidReminder
 */
export function InvoiceTableBodyCell(p) {
  const { columnKey, invoice, fullWidths, ctx } = p
  const w = fullWidths[columnKey] ?? 80
  if (columnKey === 'invoiceNumber') {
    return (
      <AlignedTableCell width={w}>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            minWidth: 0,
          }}
        >
          <Typography
            variant="body2"
            noWrap
            component="span"
            sx={{ minWidth: 0 }}
            title={invoice.invoice_number}
          >
            {invoice.invoice_number}
          </Typography>
          <InvoiceCreditNoteBadge show={Boolean(invoice.has_credit_notes)} />
        </Box>
      </AlignedTableCell>
    )
  }
  if (columnKey === 'pharmacyName') {
    return (
      <AlignedTableCell width={w}>
        <Typography
          variant="body2"
          noWrap
          title={invoice.pharmacy_name}
          sx={{ color: 'primary.main', cursor: 'pointer' }}
          onClick={() => ctx?.navigateToPharmacy?.(invoice.pharmacy_id)}
        >
          {invoice.pharmacy_name || '—'}
        </Typography>
      </AlignedTableCell>
    )
  }
  if (columnKey === 'blNumber') {
    const did = invoice.deposit_id
    const label = (invoice.bl_number || '').trim()
    if (!label && !did) {
      return (
        <AlignedTableCell width={w}>
          <Typography variant="body2" color="text.secondary">
            —
          </Typography>
        </AlignedTableCell>
      )
    }
    const display = label || '—'
    if (!did) {
      return (
        <AlignedTableCell width={w}>
          <Typography variant="body2" noWrap title={display}>
            {display}
          </Typography>
        </AlignedTableCell>
      )
    }
    const blUrl = `/delivery-notes?deposit_id=${encodeURIComponent(did)}`
    return (
      <AlignedTableCell width={w}>
        <Link
          component={RouterLink}
          to={blUrl}
          variant="body2"
          title={label ? `Bon de livraison : ${label}` : `Dépôt : ${did}`}
          underline="hover"
          sx={{
            display: 'block',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {display}
        </Link>
      </AlignedTableCell>
    )
  }
  if (columnKey === 'amount') {
    return (
      <AlignedTableCell width={w}>
        <Typography variant="body2" noWrap>
          {Number(invoice.amount).toFixed(2)} €
        </Typography>
      </AlignedTableCell>
    )
  }
  if (columnKey === 'issueDate') {
    return (
      <AlignedTableCell width={w}>
        <Typography variant="body2" noWrap>
          {ctx.formatDate(invoice.issue_date)}
        </Typography>
      </AlignedTableCell>
    )
  }
  if (columnKey === 'dueDate') {
    return (
      <AlignedTableCell width={w}>
        <Typography variant="body2" noWrap>
          {ctx.formatDate(invoice.due_date)}
        </Typography>
      </AlignedTableCell>
    )
  }
  if (columnKey === 'status') {
    const paid = String(invoice.status || '')
      .toLowerCase()
      .trim() === 'paid'
    const pd = invoice.payment_date
    return (
      <AlignedTableCell width={w}>
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'flex-start',
            gap: 0.25,
            minWidth: 0,
          }}
        >
          <Chip
            label={getStatusLabel(invoice.status)}
            color={getStatusColor(invoice.status)}
            size="small"
          />
          {paid && pd ? (
            <Typography variant="caption" color="text.secondary" noWrap title={ctx.formatDate(pd)}>
              Paiement {ctx.formatDate(pd)}
            </Typography>
          ) : null}
        </Box>
      </AlignedTableCell>
    )
  }
  if (columnKey === 'daysOverdue') {
    const st = String(invoice.status || '')
      .toLowerCase()
      .trim()
    const d = invoice.days_overdue
    const credited = st === 'credited'
    const paid = st === 'paid'
    return (
      <AlignedTableCell width={w}>
        <Typography variant="body2" noWrap>
          {credited || paid ? '—' : d > 0 ? `${d} j` : '—'}
        </Typography>
      </AlignedTableCell>
    )
  }
  return <AlignedTableCell width={w}>—</AlignedTableCell>
}

export function InvoiceActionsCell({ invoice, fullWidths, ctx }) {
  const w = fullWidths.actions
  const isInvoice = invoice.row_kind !== 'credit_note'
  const pharmMeta = ctx.pharmacyMap?.[invoice.pharmacy_id]
  const mailOk =
    isInvoice &&
    !!(
      String(pharmMeta?.pharmacist_email || '').trim() ||
      String(pharmMeta?.email || '').trim()
    )
  const emailBusy = ctx.invEmailBusyRowId === invoice.id
  const pdfOk = ctx.canDownloadVosFacturesPdf(invoice)
  const avoirOk =
    typeof ctx.canIssueTotalCreditNote === 'function' && ctx.canIssueTotalCreditNote(invoice)
  const markPaidOk =
    typeof ctx.canMarkInvoicePaid === 'function' && ctx.canMarkInvoicePaid(invoice)
  const showReminderAction = mailOk && canOfferUnpaidReminderAction(invoice)
  const reminderSendOk = showReminderAction && canSendUnpaidReminder(invoice)
  const reminderBusy = ctx.invReminderSendingId === invoice.id
  const hasActions = pdfOk || avoirOk || markPaidOk || mailOk || showReminderAction
  return (
    <TableCell
      align="right"
      padding="none"
      sx={{
        width: w,
        minWidth: w,
        maxWidth: w,
        boxSizing: 'border-box',
        whiteSpace: 'nowrap',
        py: 0.5,
        px: 0.5,
        fontSize: '0.75rem',
        fontWeight: 600,
      }}
      onClick={(e) => e.stopPropagation()}
      onDoubleClick={(e) => e.stopPropagation()}
    >
      {hasActions ? (
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'flex-end',
            gap: 0.25,
          }}
        >
          {pdfOk && (
            <Tooltip title="Télécharger le PDF (VosFactures)">
              <span>
                <IconButton
                  size="small"
                  disabled={ctx.pdfLoadingId === invoice.id}
                  onClick={() => void ctx.handleDownloadPdf(invoice)}
                >
                  {ctx.pdfLoadingId === invoice.id ? (
                    <CircularProgress color="inherit" size={22} />
                  ) : (
                    <DownloadIcon fontSize="small" />
                  )}
                </IconButton>
              </span>
            </Tooltip>
          )}
          {mailOk && (
            <Tooltip title="Préparer et envoyer la facture par e-mail (aperçu modifiable avant envoi)">
              <span>
                <IconButton
                  size="small"
                  color="primary"
                  disabled={emailBusy || !!ctx.invEmailOpen}
                  aria-label={`Envoyer la facture ${invoice.invoice_number} par e-mail`}
                  onClick={() => void ctx.handleOpenInvoiceEmailComposer?.(invoice)}
                >
                  {emailBusy ? (
                    <CircularProgress color="inherit" size={22} />
                  ) : (
                    <EmailOutlinedIcon fontSize="small" />
                  )}
                </IconButton>
              </span>
            </Tooltip>
          )}
          {showReminderAction && typeof ctx.handleSendInvoiceUnpaidReminder === 'function' && (
            <Tooltip
              title={
                reminderSendOk
                  ? 'Relance impayée (modèle e-mail sans pièce jointe)'
                  : 'Relance : actif lorsque la date d’échéance est dépassée d’au moins un jour (comme pour l’envoi serveur).'
              }
            >
              <span>
                <IconButton
                  size="small"
                  color="warning"
                  disabled={
                    reminderBusy ||
                    !!ctx.invEmailOpen ||
                    !reminderSendOk
                  }
                  aria-label={`Relance impayée pour ${invoice.invoice_number}`}
                  onClick={() => void ctx.handleSendInvoiceUnpaidReminder(invoice)}
                >
                  {reminderBusy ? (
                    <CircularProgress color="inherit" size={22} />
                  ) : (
                    <NotificationsActiveOutlinedIcon fontSize="small" />
                  )}
                </IconButton>
              </span>
            </Tooltip>
          )}
          {markPaidOk && typeof ctx.requestMarkPaid === 'function' && (
            <Tooltip title="Marquer comme payée (date de règlement)">
              <span>
                <IconButton
                  size="small"
                  color="success"
                  aria-label={`Marquer comme payée ${invoice.invoice_number}`}
                  onClick={() => ctx.requestMarkPaid(invoice)}
                >
                  <PaymentsIcon fontSize="small" />
                </IconButton>
              </span>
            </Tooltip>
          )}
          {avoirOk && typeof ctx.requestIssueCreditNote === 'function' && (
            <Tooltip title="Avoir VosFactures (total ou partiel)">
              <span>
                <IconButton
                  size="small"
                  aria-label={`Avoir pour la facture ${invoice.invoice_number}`}
                  onClick={() => ctx.requestIssueCreditNote(invoice)}
                >
                  <ReceiptLongIcon fontSize="small" />
                </IconButton>
              </span>
            </Tooltip>
          )}
        </Box>
      ) : (
        <Typography variant="caption" color="text.secondary">
          —
        </Typography>
      )}
    </TableCell>
  )
}
