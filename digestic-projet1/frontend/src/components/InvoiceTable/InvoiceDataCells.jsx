import React from 'react'
import { Chip, Link, Typography, CircularProgress, IconButton, Tooltip, TableCell } from '@mui/material'
import { Link as RouterLink } from 'react-router-dom'
import DownloadIcon from '@mui/icons-material/Download'
import { AlignedTableCell } from '../ResizableTableColumns/ResizableHeaderCell'

function getStatusColor(status) {
  const colors = {
    pending: 'warning',
    paid: 'success',
    overdue: 'error',
    cancelled: 'default',
  }
  return colors[status] || 'default'
}

/**
 * @param {object} p
 * @param {object} p.invoice — to_dict + pharmacy_name
 * @param {object} p.ctx — formatDate, canDownloadVosFacturesPdf, handleDownloadPdf, pdfLoadingId, navigate
 */
export function InvoiceTableBodyCell(p) {
  const { columnKey, invoice, fullWidths, ctx } = p
  const w = fullWidths[columnKey] ?? 80
  if (columnKey === 'invoiceNumber') {
    return (
      <AlignedTableCell width={w}>
        <Typography variant="body2" noWrap title={invoice.invoice_number}>
          {invoice.invoice_number}
        </Typography>
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
          onClick={() => ctx?.navigate?.(`/pharmacies/${invoice.pharmacy_id}`)}
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
    return (
      <AlignedTableCell width={w}>
        <Chip label={invoice.status} color={getStatusColor(invoice.status)} size="small" />
      </AlignedTableCell>
    )
  }
  if (columnKey === 'daysOverdue') {
    const d = invoice.days_overdue
    return (
      <AlignedTableCell width={w}>
        <Typography variant="body2" noWrap>
          {d > 0 ? `${d} j` : '—'}
        </Typography>
      </AlignedTableCell>
    )
  }
  return <AlignedTableCell width={w}>—</AlignedTableCell>
}

export function InvoiceActionsCell({ invoice, fullWidths, ctx }) {
  const w = fullWidths.actions
  const ok = ctx.canDownloadVosFacturesPdf(invoice)
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
        px: 1,
        fontSize: '0.75rem',
        fontWeight: 600,
      }}
    >
      {ok ? (
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
      ) : (
        <Typography variant="caption" color="text.secondary">
          —
        </Typography>
      )}
    </TableCell>
  )
}
